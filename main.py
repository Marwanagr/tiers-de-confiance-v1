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
    caption: str = Form(...),
    image: UploadFile = File(...),
    image_id: str = Form(...)
):
    try:
        content = await image.read()
        
        # Vérifie la taille (max 10MB)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image trop lourde (max 10MB).")
        
        # Stocke en base64 pour éviter les problèmes d'encodage
        image_b64 = base64.b64encode(content).decode()
        
        posts_col.insert_one({
            "image_id": image_id,
            "user_id": user_id,
            "caption": caption,
            "image": image_b64
        })
        return {"message": "Publication ajoutée"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))