import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Clé utilisée par Flask pour sécuriser les sessions (cookies de connexion).
    # En production, on la définira via une variable d'environnement.
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-moi-en-production")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
