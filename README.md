# 🔐 Sovrizon - Tiers de Confiance

Ce dépôt contient le code source du serveur **tiers de confiance** pour le projet **Sovrizon V2**, un système décentralisé de gestion et de partage sécurisé des données personnelles.

## 🎯 Objectif

Le tiers de confiance est un composant essentiel du système Sovrizon. Il est responsable de :

- **🔑 Génération de clés de chiffrement** pour les images (AES-256-GCM)
- **💾 Stockage sécurisé des clés** dans une base de données MongoDB
- **👤 Gestion des utilisateurs** : inscription, connexion, authentification via tokens
- **🛡️ Contrôle d'accès granulaire** : autorisation et révocation d'accès par utilisateur
- **🔄 Chiffrement/Déchiffrement automatique** des images stockées
- **🎨 Filigrane DCT** pour la traçabilité des images
- **📝 Publication sécurisée de posts** avec autorisations conditionnelles

## 🧱 Technologies

- **Backend** : Python, FastAPI
- **Base de données** : MongoDB
- **Sécurité** : 
  - Chiffrement AES-256-GCM (AEAD)
  - Tokens JWT avec expiration (24h)
  - Hash de mots de passe avec bcrypt
  - Filigrane DCT (Discrete Cosine Transform)
- **Traitement d'images** : OpenCV, NumPy

## 🚀 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/Sovrizon/tiers-de-confiance.git
cd tiers-de-confiance
```

### 2. Configuration de MongoDB

#### Option A : MongoDB Atlas (Cloud) - Recommandé

1. Créez un compte sur [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Créez un cluster gratuit
3. Copiez votre URI de connexion

#### Option B : MongoDB Local

**Installation :**

```bash
# Sur Windows
choco install mongodb

# Sur macOS
brew install mongodb-community

# Sur Linux (Ubuntu/Debian)
sudo apt-get install -y mongodb
```

**Démarrer le service :**

```bash
# Windows
mongod --dbpath "C:\data\db"

# macOS/Linux
mongod --dbpath /usr/local/var/mongodb
```

**Créer un utilisateur (local) :**

```bash
mongosh
use admin
db.createUser({ user: "admin", pwd: "password", roles: ["root"] })
```

### 3. Configuration du fichier `.env`

Créez un fichier `.env` à la racine du projet :

```env
# MongoDB Atlas (Cloud)
MONGO_URI="mongodb+srv://<username>:<password>@<cluster>.mongodb.net/tiers-de-confiance?retryWrites=true&w=majority"

# Ou MongoDB Local
# MONGO_URI="mongodb://admin:password@localhost:27017"

PORT=8300
```

### 4. Créer un environnement virtuel et lancer l'application

```bash
# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement
# Sur Windows :
.\venv\Scripts\activate
# Sur macOS/Linux :
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
uvicorn main:app --reload --port 8300
```

L'application sera accessible sur : **http://localhost:8300**

Interface interactive : **http://localhost:8300/docs** (Swagger UI)

## 📦 Fonctionnalités

### 🔐 Authentification et Gestion des Utilisateurs

| Route | Méthode | Description |
|-------|---------|-------------|
| `/auth/register` | POST | Enregistrement d'un nouvel utilisateur |
| `/auth/login` | POST | Connexion et récupération du token |
| `/auth/logout` | POST | Déconnexion et invalidation du token |

**Exemple : Inscription**
```json
POST /auth/register
{
  "username": "alice",
  "password": "secure_password_123"
}
```

**Réponse :**
```json
{
  "message": "Inscription réussie",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 🔑 Gestion des Clés de Chiffrement

| Route | Méthode | Description |
|-------|---------|-------------|
| `/get_key/{image_id}` | POST | Récupérer la clé (avec autorisation) |
| `/delete_key/{username}/{image_id}` | DELETE | Supprimer une clé |
| `/update_validity/{owner_username}/{image_id}` | POST | Activer/désactiver une clé |

---

### 📝 Publication de Posts Sécurisés

| Route | Méthode | Description |
|-------|---------|-------------|
| `/add_post` | POST | Créer un post avec image chiffrée et autorisations |
| `/posts/{image_id}` | POST | Récupérer un post (chiffré ou déchiffré selon autorisations) |
| `/authorize/{image_id}` | POST | Accorder l'accès à des utilisateurs |
| `/revoke/{image_id}/{target_username}` | DELETE | Révoquer l'accès d'un utilisateur |

**Exemple : Ajouter un post**
```json
POST /add_post (form-data)
user_id: "550e8400-e29b-41d4-a716-446655440000"
caption: "Ma première publication"
authorized_users: ["bob", "charlie"]
image: [fichier image]
```

**Réponse :**
```json
{
  "message": "Publication ajoutée avec succès.",
  "image_id": "img_12345",
  "autorisations": ["bob", "charlie"]
}
```

**Exemple : Accorder l'accès**
```json
POST /authorize/img_12345
{
  "owner_username": "alice",
  "token": "abc123def456...",
  "authorized_users": ["david"]
}
```
---

### 🔄 Chiffrement/Déchiffrement d'Images

| Route | Méthode | Description |
|-------|---------|-------------|
| `/encrypt_image/{image_id}` | POST | Chiffrer une image avec la clé associée |
| `/decrypt_image/{image_id}` | POST | Déchiffrer une image |
| `/test_encrypt_decrypt` | POST | Tester le cycle complet chiffrement/déchiffrement |

**Exemple : Chiffrer une image**
```
POST /encrypt_image/img_001 (form-data)
image: [fichier image]
```

**Réponse :**
```json
{
  "encrypted_image": "base64_encrypted_data..."
}
```

---

### 🎨 Filigrane DCT

| Route | Méthode | Description |
|-------|---------|-------------|
| `/trust/watermark` | POST | Ajouter un filigrane DCT à une image |

**Exemple :**
```
POST /trust/watermark (form-data)
image: [fichier image]
username: "alice"
```

**Réponse :**
```json
{
  "watermarked_image_b64": "base64_watermarked_image..."
}
```

---

### 🔎 Tokens et Vérification

| Route | Méthode | Description |
|-------|---------|-------------|
| `/trust_token/{username}` | GET | Récupérer le token de confiance d'un utilisateur |

---

## 🧩 Structure de la Base de Données

### Collections MongoDB

#### `users` - Utilisateurs enregistrés
```json
{
  "user_id": "uuid",
  "username": "alice",
  "password": "hash_bcrypt",
  "created_at": "2025-03-17T10:00:00Z"
}
```

#### `tokens` - Sessions actives
```json
{
  "user_id": "uuid",
  "username": "alice",
  "token": "hex_token_64",
  "created_at": "2025-03-17T10:00:00Z",
  "expires_at": "2025-03-18T10:00:00Z"
}
```

#### `keys` - Clés de chiffrement avec autorisations
```json
{
  "image_id": "img_001",
  "user_id": "uuid",
  "owner_username": "alice",
  "key": "base64_aes_key",
  "valid": true,
  "valid_from": "2025-03-17T10:00:00Z",
  "valid_to": "2025-03-24T10:00:00Z",
  "autorisations": ["bob", "charlie"],
  "created_at": "2025-03-17T10:00:00Z"
}
```

#### `posts` - Publications avec images chiffrées
```json
{
  "image_id": "img_001",
  "user_id": "uuid",
  "caption": "Ma première publication",
  "image": "encrypted_base64_data"
}
```

---

## 📋 Scénario Complet de Test

Testez les routes dans cet ordre sur http://localhost:8300/docs

### Étape 1 : Inscription

**POST** `/auth/register`

```json
{
  "username": "marwan",
  "password": "test123"
}
```

✅ **Réponse attendue :**
```json
{
  "message": "Inscription réussie",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

📋 **Copie** : `user_id` et `username`

---

### Étape 2 : Connexion

**POST** `/auth/login`

```json
{
  "username": "marwan",
  "password": "test123"
}
```

✅ **Réponse attendue :**
```json
{
  "message": "Connexion réussie",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "marwan",
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "expires_at": "2025-03-18T10:30:00"
}
```

📋 **Copie** : `token`, `user_id`

---

### Étape 3 : Créer une Clé pour une Image

**POST** `/set_key`

```json
{
  "owner_username": "marwan",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "image_id": "img_001",
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "valid": true
}
```

✅ **Réponse attendue :**
```json
{
  "message": "Clé enregistrée avec succès.",
  "key": "j3K9mL2pQ4xYz1wA+bC5dE8fG7hI6jK5lM4nO3pQ2rS1tU0vW/x..."
}
```

📋 **Copie** : `key`

---

### Étape 4 : Ajouter un Post avec Image

**POST** `/add_post` (formulaire)

- `user_id`: `550e8400-e29b-41d4-a716-446655440000`
- `caption`: `"Mon premier post"`
- `authorized_users`: `["user2", "user3"]` (JSON array ou CSV)
- `image`: [Sélectionner une image]

✅ **Réponse attendue :**
```json
{
  "message": "Publication ajoutée avec succès.",
  "image_id": "img_12345",
  "autorisations": ["user2", "user3"]
}
```

📋 **Copie** : `image_id`

---

### Étape 5 : Récupérer la Clé

**POST** `/get_key/img_001`

```json
{
  "username": "marwan",
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

✅ **Réponse attendue :**
```json
{
  "key": "j3K9mL2pQ4xYz1wA+bC5dE8fG7hI6jK5lM4nO3pQ2rS1tU0vW/x..."
}
```

---

### Étape 6 : Consulter un Post

**POST** `/posts/img_001`

```json
{
  "username": "marwan",
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

✅ **Réponse attendue (Propriétaire - Image déchiffrée) :**
```json
{
  "image_id": "img_001",
  "caption": "Mon premier post",
  "image": "base64_decrypted_image...",
  "decrypted": true
}
```

---

### Étape 7 : Accorder l'Accès à d'Autres Utilisateurs

**POST** `/authorize/img_001`

```json
{
  "owner_username": "marwan",
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "authorized_users": ["alice", "bob"]
}
```

✅ **Réponse attendue :**
```json
{
  "message": "Accès accordé.",
  "image_id": "img_001",
  "autorisations": ["user2", "user3", "alice", "bob"]
}
```

---

### Étape 8 : Révoquer l'Accès d'un Utilisateur

**DELETE** `/revoke/img_001/alice`

```json
{
  "owner_username": "marwan",
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

✅ **Réponse attendue :**
```json
{
  "message": "Accès révoqué pour alice.",
  "image_id": "img_001",
  "autorisations": ["user2", "user3", "bob"]
}
```

---

### Étape 9 : Déconnexion

**POST** `/auth/logout`

```json
{
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

✅ **Réponse attendue :**
```json
{
  "message": "Déconnexion réussie."
}
```

---

## 🔐 Flux de Sécurité Complet

```
1. INSCRIPTION (Registration)
   POST /auth/register → Crée user + hash password

2. CONNEXION (Login)
   POST /auth/login → Crée session + token (24h)

3. CRÉATION DE POST
   POST /add_post
   ├─ Génère image_id (UUID)
   ├─ Chiffre l'image (AES-256-GCM) 🔒
   ├─ Stocke image CHIFFRÉE + clé
   └─ Sauvegarde autorisations (liste d'utilisateurs)

4. CONSULTATION DE POST
   POST /posts/{image_id}
   ├─ Vérifie token de l'utilisateur
   ├─ Vérifie si propriétaire OU dans autorisations
   ├─ OUI → Déchiffre et retourne 🔓
   └─ NON → Retourne image chiffrée 🔒

5. RÉVOCATION D'ACCÈS
   DELETE /revoke/{image_id}/{username}
   ├─ Vérifie propriétaire
   ├─ Retire l'utilisateur de la liste
   └─ Prochaines tentatives → image chiffrée 🔒
```

---

## 🛠️ Commandes Utiles

### Développement

```bash
# Lancer FastAPI avec rechargement automatique
uvicorn main:app --reload --port 8300

# Vérifier la syntaxe Python
python -m py_compile main.py auth.py db.py utils.py

# Tester une route avec curl
curl -X POST "http://localhost:8300/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "pass"}'
```

### MongoDB

```bash
# Lancer MongoDB localement
mongod --dbpath "C:\data\db"

# Se connecter avec mongosh
mongosh "mongodb://localhost:27017"

# Lister les collections
use tiers-de-confiance
show collections

# Voir les documents d'une collection
db.users.find()
db.keys.find()
db.posts.find()
```

### Virtual Environment

```bash
# Créer l'environnement
python -m venv venv

# Activer (Windows)
.\venv\Scripts\activate

# Activer (macOS/Linux)
source venv/bin/activate

# Désactiver
deactivate
```

---

## 📊 Variables d'Environnement

| Variable | Description | Exemple |
|----------|-------------|---------|
| `MONGO_URI` | URI de connexion MongoDB | `mongodb://localhost:27017` |
| `PORT` | Port du serveur FastAPI | `8300` |

---

## 🧩 Intégration Système

Ce serveur est conçu pour fonctionner en conjonction avec :

- 📱 **Application Web** (Secugram) : Chiffre les images côté client
- 🔌 **Extension Chrome** : Déchiffre les images dans le navigateur
- 🖥️ **Mobile App** : Intégration native iOS/Android

---

## 📁 Structure du Projet

```
tiers-de-confiance/
├── main.py              # Routes principales et gestion des posts
├── auth.py              # Routes d'authentification
├── db.py                # Connexion MongoDB et collections
├── utils.py             # Fonctions utilitaires (chiffrement, hash)
├── requirements.txt     # Dépendances Python
├── .env                 # Variables d'environnement (à créer)
└── README.md            # Ce fichier
```

---

## 🚨 Sécurité et Bonnes Pratiques

✅ **Implémenté :**
- ✓ Tokens JWT avec expiration (24 heures)
- ✓ Hash des mots de passe (bcrypt)
- ✓ Chiffrement AES-256-GCM pour les images
- ✓ Vérification des droits d'accès (propriétaire/autorisés)
- ✓ Validité des tokens côté serveur
- ✓ Filigrane DCT pour traçabilité

⚠️ **À Améliorer :**
- Implémenter HTTPS en production
- Ajouter rate limiting sur les routes sensibles
- Utiliser CORS plus restrictif
- Ajouter logging/audit trail
- Configurer des variables sensibles en secrets

---

## 👥 Auteurs et Contribution

Ce projet a été développé par :

- **Rémy GASMI**
- **Simon VINCENT**
- **Loqmen ANANI**

Les contributions sont bienvenues ! Veuillez créer une pull request.

---

## 📄 Licence

© 2025 Sovrizon – Tous droits réservés.

---

## 🤝 Support

Pour des questions ou des problèmes :
1. Vérifiez que MongoDB est démarré
2. Vérifiez la variable `MONGO_URI` dans `.env`
3. Consultez les logs FastAPI
4. Créez une issue sur le dépôt GitHub

