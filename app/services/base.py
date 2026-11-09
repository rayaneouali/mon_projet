"""Service « base de données » : état de la connexion vu par l'interface."""

from db import connexion


def etat_connexion() -> tuple[bool, str]:
    """Renvoie (True, 'Base connectée') ou (False, message d'erreur en français)."""
    return connexion.verifier_connexion()
