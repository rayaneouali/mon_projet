"""Lecture de la configuration : fichier .env en local, « Secrets » sur Streamlit Cloud."""

import os
from pathlib import Path

from dotenv import load_dotenv

RACINE_PROJET = Path(__file__).resolve().parent.parent

# Charge le fichier .env s'il existe (en local). Ne remplace pas une variable déjà définie.
load_dotenv(RACINE_PROJET / ".env")


def lire(nom: str, defaut: str = "") -> str:
    """Renvoie une variable de configuration : environnement d'abord, puis st.secrets."""
    valeur = os.environ.get(nom, "").strip()
    if valeur:
        return valeur
    return _lire_secret_streamlit(nom) or defaut


def _lire_secret_streamlit(nom: str) -> str:
    """Lit une valeur dans st.secrets (Streamlit Cloud) ; renvoie '' si elle n'existe pas."""
    try:
        import streamlit as st

        return str(st.secrets.get(nom, "")).strip()
    except Exception:  # pas de fichier secrets.toml en local : c'est normal
        return ""


def database_url() -> str:
    """Adresse de connexion à PostgreSQL (DATABASE_URL)."""
    return lire("DATABASE_URL")


def schema_base() -> str:
    """Schéma PostgreSQL à utiliser ; vide = schéma par défaut (public). Sert aux tests."""
    return lire("DB_SCHEMA")


def log_level() -> str:
    """Niveau de log demandé (LOG_LEVEL), INFO par défaut."""
    return lire("LOG_LEVEL", "INFO").upper()


def code_chefs() -> str:
    """Code d'accès des chefs d'équipe (CODE_CHEFS)."""
    return lire("CODE_CHEFS")


def code_admin() -> str:
    """Code d'accès administrateur (CODE_ADMIN)."""
    return lire("CODE_ADMIN")
