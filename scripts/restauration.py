"""Restauration : recharge une sauvegarde CSV dans la base DATABASE_URL.

ATTENTION : la base est d'abord VIDÉE, puis remplie avec la sauvegarde.
Utilisation (depuis la racine du projet) :
    uv run python scripts/restauration.py sauvegardes/2026-11-15 --oui
Sans --oui, le script explique ce qu'il va faire et s'arrête.
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import config  # noqa: E402
from db import connexion, requetes  # noqa: E402
from log import configurer_logging  # noqa: E402

logger = logging.getLogger("suivi.restauration")


def verifier_dossier(dossier: Path) -> None:
    """Vérifie que la sauvegarde contient bien un fichier par table."""
    manquants = [t for t in requetes.TABLES_DANS_L_ORDRE if not (dossier / f"{t}.csv").exists()]
    if manquants:
        raise SystemExit(f"Sauvegarde incomplète dans {dossier} : il manque {manquants}")


def restaurer(dossier: Path) -> None:
    """Vide la base et recharge chaque table depuis la sauvegarde, en une seule transaction."""
    verifier_dossier(dossier)
    connexion.appliquer_schema()
    with connexion.ouvrir_connexion() as conn, conn.transaction():
        requetes.vider_toutes_les_tables(conn)
        for table in requetes.TABLES_DANS_L_ORDRE:  # ordre imposé par les clés étrangères
            with (dossier / f"{table}.csv").open("rb") as fichier:
                requetes.importer_table_csv(conn, table, fichier)
    logger.info("Restauration terminée depuis %s", dossier)


def main() -> None:
    """Lit les options et lance la restauration (seulement avec --oui)."""
    parseur = argparse.ArgumentParser(description="Restauration d'une sauvegarde CSV")
    parseur.add_argument("dossier", type=Path, help="dossier contenant les fichiers CSV")
    parseur.add_argument("--oui", action="store_true", help="confirme : la base sera VIDÉE")
    options = parseur.parse_args()
    configurer_logging()
    hote = config.database_url().split("@")[-1]  # sans le mot de passe
    if not options.oui:
        raise SystemExit(
            f"La base « {hote} » va être VIDÉE puis remplie avec {options.dossier}.\n"
            "Relance avec --oui pour confirmer."
        )
    restaurer(options.dossier)


if __name__ == "__main__":
    main()
