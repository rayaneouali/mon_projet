"""Service « base de données » : préparation et état de la connexion vus par l'interface."""

from db import connexion


def preparer_base() -> None:
    """Crée les tables manquantes au démarrage de l'app (sans risque si elles existent)."""
    connexion.appliquer_schema()


def etat_connexion() -> tuple[bool, str]:
    """Renvoie (True, 'Base connectée') ou (False, message d'erreur en français)."""
    return connexion.verifier_connexion()
