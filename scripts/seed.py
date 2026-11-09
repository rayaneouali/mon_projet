"""Données d'exemple : 2 équipes, 6 gars, 2 dossiers. Sans doublon si on le relance.

Utilisation (depuis la racine du projet) :
    uv run python scripts/seed.py            # ajoute les exemples
    uv run python scripts/seed.py --effacer  # les retire (avant de donner l'app aux chefs)
"""

import argparse
import logging
import sys
from pathlib import Path

# Permet d'importer les modules de app/ (config, db…) depuis ce script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from db import connexion, requetes  # noqa: E402
from log import configurer_logging  # noqa: E402

logger = logging.getLogger("suivi.seed")

EQUIPES = [("Équipe 1", "Karim"), ("Équipe 2", "Mehdi")]
GARS = [
    ("Karim", "Équipe 1"),
    ("Yanis", "Équipe 1"),
    ("Lucas", "Équipe 1"),
    ("Mehdi", "Équipe 2"),
    ("Samir", "Équipe 2"),
    ("Thomas", "Équipe 2"),
]
DOSSIERS = [
    ("D-2026-001", "Client exemple", "Orléans"),
    ("D-2026-002", "Client exemple 2", "Tours"),
]


def ajouter_exemples() -> None:
    """Insère les équipes, gars et dossiers d'exemple s'ils n'existent pas déjà."""
    with connexion.ouvrir_connexion() as conn:
        ids_equipes = {
            nom: requetes.inserer_equipe_si_absente(conn, nom, chef) for nom, chef in EQUIPES
        }
        for nom, equipe in GARS:
            requetes.inserer_gars_si_absent(conn, nom, ids_equipes[equipe])
        for code, client, lieu in DOSSIERS:
            requetes.inserer_dossier_si_absent(conn, code, client, lieu)
    logger.info(
        "Exemples en place : %d équipes, %d gars, %d dossiers",
        len(EQUIPES),
        len(GARS),
        len(DOSSIERS),
    )


def effacer_exemples() -> None:
    """Retire les données d'exemple et leur historique (les vraies données ne bougent pas)."""
    with connexion.ouvrir_connexion() as conn:
        requetes.effacer_exemples(
            conn,
            equipes=[nom for nom, _ in EQUIPES],
            gars=[nom for nom, _ in GARS],
            dossiers=[code for code, _, _ in DOSSIERS],
        )
    logger.info("Données d'exemple effacées")


def main() -> None:
    """Lit l'option --effacer et lance l'action demandée."""
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("--effacer", action="store_true", help="retire les données d'exemple")
    options = parseur.parse_args()
    configurer_logging()
    connexion.appliquer_schema()
    if options.effacer:
        effacer_exemples()
    else:
        ajouter_exemples()


if __name__ == "__main__":
    main()
