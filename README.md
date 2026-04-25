# 🎓 Peer2Peer Campus – ENCG Marrakech

Plateforme de partage des compétences entre étudiants de l'ENCG Marrakech.

---

## 📁 Structure du projet

```
p2p_campus/
├── app.py                  ← Application Flask principale
├── requirements.txt        ← Dépendances Python
├── init_db.sql             ← Script SQL (optionnel, Flask le fait auto)
├── .env.example            ← Variables d'environnement
├── static/
│   ├── css/style.css       ← Feuille de style principale
│   ├── js/main.js          ← JavaScript
│   └── uploads/            ← Fichiers uploadés par les étudiants
└── templates/
    ├── base.html           ← Template de base (sidebar)
    ├── login.html          ← Page connexion
    ├── register.html       ← Page inscription
    ├── accueil.html        ← Page d'accueil
    ├── profil.html         ← Page profil
    ├── missions.html       ← Mission Board
    ├── messages.html       ← Liste des messages
    ├── conversation.html   ← Conversation individuelle
    └── wallet.html         ← Portefeuille de crédits
```

---

## ⚙️ Installation – Étape par étape

### 1. Prérequis

- Python 3.10+ installé
- PostgreSQL installé et en cours d'exécution
- VS Code avec l'extension Python

---

### 2. Créer la base de données PostgreSQL

Ouvrir un terminal et se connecter à PostgreSQL :

```bash
# Sur Windows (si PostgreSQL est installé)
psql -U postgres

# Sur Mac/Linux
sudo -u postgres psql
```

Puis exécuter ces commandes :

```sql
CREATE USER p2p_user WITH PASSWORD 'p2p_password';
CREATE DATABASE p2p_campus OWNER p2p_user;
GRANT ALL PRIVILEGES ON DATABASE p2p_campus TO p2p_user;
\q
```

---

### 3. Configurer l'environnement Python

Dans VS Code, ouvrir le dossier `p2p_campus/` puis ouvrir le terminal :

```bash
# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
# Windows :
venv\Scripts\activate
# Mac/Linux :
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

---

### 4. Configurer les variables d'environnement

Copier `.env.example` en `.env` :

```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

Modifier `.env` si besoin (mot de passe PostgreSQL différent, etc.)

---

### 5. Lancer l'application

```bash
python app.py
```

Les tables sont créées automatiquement au premier lancement.

Ouvrir le navigateur sur : **http://127.0.0.1:5000**

---

## 🚀 Fonctionnalités

| Page | Description |
|------|-------------|
| **Login/Inscription** | Authentification avec validation @uca.ac.ma |
| **Accueil** | Page de bienvenue avec infos de la plateforme |
| **Profil** | Compétences, portfolio, évaluations (5 étoiles) |
| **Mission Board** | Publier/chercher des offres et demandes |
| **Messages** | Messagerie avec upload de fichiers |
| **Wallet** | Solde, envoi de crédits en 3 étapes, historique |

---

## 🎨 Couleurs de la plateforme

Inspirées du logo ENCG Marrakech :
- **Vert principal** : `#1a7a4a`
- **Orange accent** : `#e8821e`

---

## 🛠️ Problèmes fréquents

**Erreur de connexion PostgreSQL** :
- Vérifier que PostgreSQL est démarré
- Vérifier les identifiants dans `.env`

**ModuleNotFoundError** :
- S'assurer que l'environnement virtuel est activé (`venv\Scripts\activate`)

**Port déjà utilisé** :
- Changer le port : modifier `app.run(debug=True, port=5001)`
