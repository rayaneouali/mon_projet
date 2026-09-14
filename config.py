import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Le dossier "instance" contient la base de données SQLite. On le crée s'il
# n'existe pas encore, pour ne pas avoir à y penser lors d'un premier
# déploiement sur un nouvel hébergeur.
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)


class Config:
    # Clé utilisée par Flask pour sécuriser les sessions (cookies de connexion).
    # En production, on la définira via une variable d'environnement.
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-moi-en-production")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
