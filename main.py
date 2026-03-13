import base64
import os
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Header, Body, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from secrets import token_hex
from dotenv import load_dotenv
from datetime import datetime

from db import keys_col, tokens_col, posts_col
from utils import encrypt_image, decrypt_image, verify_token
from auth import router as auth_router
from WatermarkingModule.engine import Watermarker
import uuid

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion du router auth
app.include_router(auth_router, prefix="/auth", tags=["auth"])

# ---- Models ----
class KeyPayload(BaseModel):
    owner_username: str
    user_id: str
    image_id: str
    token: str
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    valid: Optional[bool] = True

class ViewerPayload(BaseModel):
    viewer_username: str

class UpdateValidityPayload(BaseModel):
    valid: bool
    token: str




### les ROUTES : 



@app.post("/set_key")
def set_key(payload: KeyPayload):
    # Vérifie le token
    if not verify_token(payload.owner_username, payload.token):
        raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

    # Génère une clé unique pour cette image
    generated_key = base64.b64encode(os.urandom(32)).decode()

    existing_key = keys_col.find_one({"image_id": payload.image_id})

    if existing_key:
        keys_col.update_one(
            {"image_id": payload.image_id},
            {"$set": {
                "user_id": payload.user_id,
                "owner_username": payload.owner_username,
                "key": generated_key,
                "valid": payload.valid,
                "valid_from": payload.valid_from,
                "valid_to": payload.valid_to,
                "updated_at": datetime.utcnow()
            }}
        )
    else:
        keys_col.insert_one({
            "image_id": payload.image_id,
            "user_id": payload.user_id,
            "owner_username": payload.owner_username,
            "key": generated_key,
            "valid": payload.valid,
            "valid_from": payload.valid_from,
            "valid_to": payload.valid_to,
            "created_at": datetime.utcnow()
        })

    return {
        "message": "Clé enregistrée avec succès.",
        "key": generated_key,
    }


'''@app.post("/register_viewer")
def register_viewer(payload: ViewerPayload):
    existing_viewer = tokens_col.find_one({"username": payload.viewer_username})

    if existing_viewer:
        return {"message": "Utilisateur déjà enregistré.", "token": existing_viewer["token"]}

    token = token_hex(16)
    tokens_col.insert_one({
        "username": payload.viewer_username,
        "token": token
    })

    return {"message": "Utilisateur enregistré avec succès.", "token": token}'''


@app.get("/trust_token/{username}")
def get_trust_token(username: str):
    viewer = tokens_col.find_one({"username": username})
    if not viewer:
        raise HTTPException(status_code=404, detail="Utilisateur inconnu.")

    return {"token": viewer["token"]}


@app.post("/get_key/{image_id}")
def get_key(image_id: str, payload: dict = Body(...)):
    viewer_username = payload.get("username")
    token = payload.get("token")
    # Check if key exists
    key_data = keys_col.find_one({"image_id": image_id})
    if not key_data:
        raise HTTPException(status_code=404, detail="Clé non trouvée.")

    # Verify viewer token
    viewer = tokens_col.find_one({"username": viewer_username})
    is_valid_viewer = viewer and viewer["token"] == token

    if not is_valid_viewer:
        raise HTTPException(status_code=403, detail="Token ou identifiant utilisateur invalide.")

    if not key_data["valid"]:
        raise HTTPException(status_code=403, detail="Clé invalide ou expirée.")

    return {"key": key_data["key"]}


@app.delete("/delete_key/{username}/{image_id}")
def delete_key(username: str, image_id: str, token: Optional[str] = Header(None)):
    key_data = keys_col.find_one({"image_id": image_id, "owner_username": username})

    if not key_data:
        raise HTTPException(status_code=404, detail="Clé non trouvée.")

    viewer = tokens_col.find_one({"username": username})
    if not viewer or viewer["token"] != token:
        raise HTTPException(status_code=403, detail="Token invalide.")

    keys_col.delete_one({"image_id": image_id, "owner_username": username})
    return {"message": "Clé supprimée avec succès."}


@app.post("/update_validity/{owner_username}/{image_id}")
def update_validity(
        owner_username: str,
        image_id: str,
        payload: UpdateValidityPayload = Body(...)
):
    key_data = keys_col.find_one({"image_id": image_id})

    if not key_data:
        raise HTTPException(status_code=404, detail="Clé non trouvée.")

    if key_data["owner_username"] != owner_username:
        raise HTTPException(status_code=403, detail="Nom d'utilisateur non autorisé.")

    viewer = tokens_col.find_one({"username": owner_username})
    if not viewer or viewer["token"] != payload.token:
        raise HTTPException(status_code=403, detail="Token invalide.")

    keys_col.update_one(
        {"image_id": image_id},
        {"$set": {"valid": payload.valid}}
    )

    return {"message": f"Validité mise à jour : {payload.valid}"}

# Intégration du filigrane
wm = Watermarker(alpha=0.2)

@app.post("/trust/watermark")
async def trust_process(image: UploadFile = File(...), username: str = Form(...)):
    try:
        # 1. Lecture de l'image envoyée par React
        file_bytes = await image.read()
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 2. Sauvegarde temporaire pour ton module qui travaille sur fichiers
        temp_in = f"in_{username}.png"
        temp_out = f"out_{username}.png"
        cv2.imwrite(temp_in, img)

        # 3. Appel de ta fonction encode
        # On utilise le 'username' comme message à tatouer
        success = wm.encode(temp_in, username, temp_out)

        if not success:
            return {"error": "Erreur lors du tatouage DCT"}

        # 4. Encodage du résultat en Base64 pour le renvoyer au Front-end
        with open(temp_out, "rb") as f:
            b64_result = base64.b64encode(f.read()).decode('utf-8')

        # 5. Nettoyage des fichiers temporaires
        if os.path.exists(temp_in): os.remove(temp_in)
        if os.path.exists(temp_out): os.remove(temp_out)

        return {"watermarked_image_b64": b64_result}

    except Exception as e:
        return {"error": str(e)}

@app.post("/encrypt_image/{image_id}")
async def encrypt(image_id: str, image: UploadFile = File(...)):
    key_data = keys_col.find_one({"image_id": image_id})
    if not key_data:
        raise HTTPException(status_code=404, detail="Clé non trouvée.")
    
    image_bytes = await image.read()
    encrypted = encrypt_image(image_bytes, key_data["key"])
    return {"encrypted_image": encrypted}


@app.post("/decrypt_image/{image_id}")
async def decrypt(image_id: str, payload: dict = Body(...)):
    key_data = keys_col.find_one({"image_id": image_id})
    if not key_data:
        raise HTTPException(status_code=404, detail="Clé non trouvée.")
    
    decrypted_bytes = decrypt_image(payload["encrypted_image"], key_data["key"])
    return {"decrypted_image": base64.b64encode(decrypted_bytes).decode()}


@app.post("/add_post")
async def add_post(
    user_id: str = Form(...),
    owner_username: str = Form(...),
    token: str = Form(...),
    caption: str = Form(...),
    image: UploadFile = File(...),
    authorized_users: str = Form(default="")
):
    try:
        # 1. Vérifie le token du propriétaire
        if not verify_token(owner_username, token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        # 2. Parse la liste des utilisateurs autorisés
        if authorized_users.strip() == "":
            authorized_list = []
        else:
            authorized_list = [u.strip() for u in authorized_users.split(",") if u.strip()]

        # 3. Vérifie que les users existent
        from db import users_col
        invalid_users = [u for u in authorized_list if not users_col.find_one({"username": u})]
        if invalid_users:
            raise HTTPException(status_code=404, detail=f"Utilisateurs introuvables : {invalid_users}")

        # 4. Lit et vérifie l'image
        content = await image.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image trop lourde (max 10MB).")

        # 5. Génère l'image_id unique
        image_id = str(uuid.uuid4())

        # 6. Génère la clé AES-256 EN PREMIER
        generated_key = base64.b64encode(os.urandom(32)).decode()

        # 7. Chiffre l'image avec la clé
        encrypted_image = encrypt_image(content, generated_key)

        # 8. Stocke l'image CHIFFRÉE
        posts_col.insert_one({
            "image_id": image_id,
            "user_id": user_id,
            "caption": caption,
            "image": encrypted_image  # ← chiffrée 🔒
        })

        # 9. Stocke la clé avec les autorisations
        keys_col.insert_one({
            "image_id": image_id,
            "user_id": user_id,
            "owner_username": owner_username,
            "key": generated_key,
            "valid": True,
            "autorisations": authorized_list,
            "created_at": datetime.utcnow()
        })

        return {
            "message": "Publication ajoutée avec succès.",
            "image_id": image_id,
            "autorisations": authorized_list
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

'''
**Le changement clé :**
```
AVANT :
  image_b64 = base64.b64encode(content).decode()  ← clair 🚨
  posts_col.insert_one({ "image": image_b64 })

APRÈS :
  generated_key = ...                              ← clé d'abord
  encrypted_image = encrypt_image(content, key)   ← chiffrement
  posts_col.insert_one({ "image": encrypted_image }) ← chiffré ✅

#Ce que fait la route dans l'ordre :**
1. Vérifie le token du propriétaire
2. Vérifie que les users autorisés existent en base
3. Vérifie la taille de l'image
4. Génère image_id (uuid)
5. Stocke l'image → posts_col
6. Génère clé AES-256 + stocke autorisations → keys_col 
'''
@app.post("/posts/{image_id}")
def get_post(image_id: str, payload: dict = Body(default={})):
    try:
        username = payload.get("username")
        token = payload.get("token")

        # 1. Récupère le post
        post = posts_col.find_one({"image_id": image_id})
        if not post:
            raise HTTPException(status_code=404, detail="Post non trouvé.")

        # 2. Récupère les données de la clé
        key_data = keys_col.find_one({"image_id": image_id})
        if not key_data:
            raise HTTPException(status_code=404, detail="Clé non trouvée.")

        # 3. Vérifie si l'utilisateur est autorisé
        is_owner = username == key_data["owner_username"]
        is_authorized = username in key_data.get("autorisations", [])
        has_valid_token = username and token and verify_token(username, token)

        if has_valid_token and (is_owner or is_authorized):
            # ✅ Autorisé → déchiffre et retourne image claire
            decrypted_bytes = decrypt_image(post["image"], key_data["key"])
            return {
                "image_id": image_id,
                "caption": post["caption"],
                "image": base64.b64encode(decrypted_bytes).decode(),
                "decrypted": True
            }
        else:
            # 🔒 Non autorisé → retourne image chiffrée telle quelle
            return {
                "image_id": image_id,
                "caption": post["caption"],
                "image": post["image"],
                "decrypted": False
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''
**Le flow complet est maintenant :**
```
POST /add_post
    → chiffre l'image 🔒
    → stocke image chiffrée + clé + autorisations

POST /posts/{image_id}
    ├── sans token / non autorisé → image chiffrée 🔒
    ├── owner                     → déchiffre ✅
    └── user dans autorisations   → déchiffre ✅   
'''

# ---- Models ----
class AuthorizePayload(BaseModel):
    owner_username: str
    token: str
    authorized_users: list[str]  # ["bob", "charlie"]

class RevokePayload(BaseModel):
    owner_username: str
    token: str


@app.post("/authorize/{image_id}")
def authorize_users(image_id: str, payload: AuthorizePayload):
    try:
        # 1. Vérifie le token du propriétaire
        if not verify_token(payload.owner_username, payload.token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        # 2. Vérifie que l'image existe
        key_data = keys_col.find_one({"image_id": image_id})
        if not key_data:
            raise HTTPException(status_code=404, detail="Image non trouvée.")

        # 3. Vérifie que c'est bien le propriétaire
        if key_data["owner_username"] != payload.owner_username:
            raise HTTPException(status_code=403, detail="Vous n'êtes pas le propriétaire.")

        # 4. Vérifie que les users existent
        from db import users_col
        invalid_users = [u for u in payload.authorized_users if not users_col.find_one({"username": u})]
        if invalid_users:
            raise HTTPException(status_code=404, detail=f"Utilisateurs introuvables : {invalid_users}")

        # 5. Ajoute sans doublons grâce à $addToSet
        keys_col.update_one(
            {"image_id": image_id},
            {"$addToSet": {"autorisations": {"$each": payload.authorized_users}}}
        )

        # 6. Retourne la liste mise à jour
        updated = keys_col.find_one({"image_id": image_id})
        return {
            "message": "Accès accordé.",
            "image_id": image_id,
            "autorisations": updated.get("autorisations", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/revoke/{image_id}/{target_username}")
def revoke_access(image_id: str, target_username: str, payload: RevokePayload = Body(...)):
    try:
        # 1. Vérifie le token du propriétaire
        if not verify_token(payload.owner_username, payload.token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        # 2. Vérifie que l'image existe
        key_data = keys_col.find_one({"image_id": image_id})
        if not key_data:
            raise HTTPException(status_code=404, detail="Image non trouvée.")

        # 3. Vérifie que c'est bien le propriétaire
        if key_data["owner_username"] != payload.owner_username:
            raise HTTPException(status_code=403, detail="Vous n'êtes pas le propriétaire.")

        # 4. Vérifie que le user cible est bien dans la liste
        if target_username not in key_data.get("autorisations", []):
            raise HTTPException(status_code=404, detail=f"{target_username} n'est pas dans les autorisations.")

        # 5. Retire le user
        keys_col.update_one(
            {"image_id": image_id},
            {"$pull": {"autorisations": target_username}}
        )

        # 6. Retourne la liste mise à jour
        updated = keys_col.find_one({"image_id": image_id})
        return {
            "message": f"Accès révoqué pour {target_username}.",
            "image_id": image_id,
            "autorisations": updated.get("autorisations", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''
**Résumé des 3 routes de contrôle d'accès :**
POST /add_post                        → autorisations initiales à la création
POST /authorize/{image_id}            → ajouter des users après coup
DELETE /revoke/{image_id}/{username}  → retirer un user 
'''
#################### des routes de test
@app.post("/test_encrypt_decrypt")
async def test_encrypt_decrypt(image: UploadFile = File(...)):
    try:
        # 1. Lit l'image originale
        original_bytes = await image.read()

        # 2. Génère une clé de test
        test_key = base64.b64encode(os.urandom(32)).decode()

        # 3. Chiffre
        encrypted = encrypt_image(original_bytes, test_key)

        # 4. Déchiffre
        decrypted_bytes = decrypt_image(encrypted, test_key)

        # 5. Vérifie que original == déchiffré
        match = original_bytes == decrypted_bytes

        return {
            "key": test_key,
            "original_size": len(original_bytes),
            "encrypted_size": len(encrypted),
            "decrypted_size": len(decrypted_bytes),
            "match": match  # ✅ doit être True
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))