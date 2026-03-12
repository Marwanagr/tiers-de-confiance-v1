from hashlib import sha256
from db import users_col
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64
from db import users_col, tokens_col
from datetime import datetime



def hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def get_user(username: str):
    return users_col.find_one({"username": username})
def verify_token(username: str, token: str) -> bool:
    session = tokens_col.find_one({"username": username, "token": token})
    if not session:
        return False
    if session["expires_at"] < datetime.utcnow():
        tokens_col.delete_one({"token": token})  # supprime le token expiré
        return False
    return True
def encrypt_image(image_bytes: bytes, key_base64: str) -> str:
    key = base64.b64decode(key_base64)
    iv = os.urandom(12)
    aesgcm = AESGCM(key)
    encrypted = aesgcm.encrypt(iv, image_bytes, None)
    result = iv + encrypted
    return base64.b64encode(result).decode()

def decrypt_image(encrypted_base64: str, key_base64: str) -> bytes:
    key = base64.b64decode(key_base64)
    data = base64.b64decode(encrypted_base64)
    iv = data[:12]
    encrypted = data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, encrypted, None)