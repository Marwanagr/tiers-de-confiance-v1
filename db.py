from pymongo import MongoClient, errors
from dotenv import load_dotenv
import os


load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

try:
    print("[INFO] Connexion à MongoDB...")
    client = MongoClient(MONGO_URI)
    db = client["tiers-de-confiance"]
    print("[OK] Connexion établie.")
except errors.ConnectionFailure as e:
    print(f"[ERREUR] Échec de connexion : {e}")
    exit(1)

try:
    collections = db.list_collection_names()

    for col_name in ["keys", "tokens", "users", "posts"]:
        if col_name not in collections:
            db.create_collection(col_name)
            print(f"[OK] Collection '{col_name}' créée.")

    users_col  = db["users"]
    posts_col  = db["posts"]
    keys_col   = db["keys"]
    tokens_col = db["tokens"]
    print("[OK] Accès aux collections réussi.")

except errors.PyMongoError as e:
    print(f"[ERREUR] Problème lors de l'accès aux collections : {e}")
    exit(1)