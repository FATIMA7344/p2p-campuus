-- ========================================================
-- Script d'initialisation de la base de données PostgreSQL
-- Peer2Peer Campus – ENCG Marrakech
-- ========================================================

-- 1. Créer l'utilisateur et la base de données
--    (à exécuter en tant que superuser PostgreSQL)

CREATE USER p2p_user WITH PASSWORD 'p2p_password';
CREATE DATABASE p2p_campus OWNER p2p_user;
GRANT ALL PRIVILEGES ON DATABASE p2p_campus TO p2p_user;

-- ========================================================
-- Les tables sont créées automatiquement par Flask-SQLAlchemy
-- via db.create_all() au démarrage de l'application.
-- ========================================================
-- Vous pouvez aussi les créer manuellement ici :

\c p2p_campus;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(200) NOT NULL,
    annee_etude VARCHAR(20) NOT NULL,
    filiere VARCHAR(50) NOT NULL,
    bio TEXT DEFAULT '',
    portfolio TEXT DEFAULT '',
    credits INTEGER DEFAULT 50,
    total_gagne INTEGER DEFAULT 0,
    total_depense INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS competences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    nom VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS missions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    titre VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    type_mission VARCHAR(20) NOT NULL,
    competence VARCHAR(100) NOT NULL,
    credits INTEGER NOT NULL,
    statut VARCHAR(20) DEFAULT 'ouvert',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    expediteur_id INTEGER REFERENCES users(id),
    destinataire_id INTEGER REFERENCES users(id),
    contenu TEXT,
    fichier VARCHAR(300),
    lu BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    expediteur_id INTEGER REFERENCES users(id),
    destinataire_id INTEGER REFERENCES users(id),
    montant INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    message VARCHAR(300) NOT NULL,
    lu BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluations (
    id SERIAL PRIMARY KEY,
    evalue_id INTEGER REFERENCES users(id),
    evaluateur_id INTEGER REFERENCES users(id),
    note INTEGER NOT NULL CHECK (note BETWEEN 1 AND 5),
    commentaire TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
