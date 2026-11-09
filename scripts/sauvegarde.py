"""Sauvegarde : exporte chaque table de la base dans un fichier CSV (ouvrable dans Excel).

Utilisation (depuis la racine du projet) :
    uv run python scripts/sauvegarde.py                    # -> sauvegardes/AAAA-MM-JJ/
    uv run python scripts/sauvegarde.py --dossier ma_copie
La base sauvegardée est celle de DATABASE_URL. GitHub Actions le lance chaque dimanche soir.
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from db import connexion, requetes  # noqa: E402
from log import configurer_logging  # noqa: E402

logger = logging.getLogger("suivi.sauvegarde")
BOM_UTF8 = b"\xef\xbb\xbf"  # marque invisible : Excel affiche alors bien les accents


def sauvegarder(dossier: Path) -> dict[str, int]:
    """Écrit un fichier CSV par table dans `dossier` ; renvoie le nombre de lignes par table."""
    dossier.mkdir(parents=True, exist_ok=True)
    nombres = {}
    with connexion.ouvrir_connexion() as conn:
        for table in requetes.TABLES_DANS_L_ORDRE:
            chemin = dossier / f"{table}.csv"
            with chemin.open("wb") as fichier:
                fichier.write(BOM_UTF8)
                requetes.exporter_table_csv(conn, table, fichier)
            with chemin.open(encoding="utf-8-sig") as fichier:
                nombres[table] = sum(1 for _ in fichier) - 1  # moins la ligne d'en-tête
    logger.info("Sauvegarde dans %s : %s", dossier, nombres)
    return nombres


def main() -> None:
    """Lit l'option --dossier et lance la sauvegarde."""
    parseur = argparse.ArgumentParser(description="Sauvegarde de la base en fichiers CSV")
    parseur.add_argument(
        "--dossier", type=Path, default=Path("sauvegardes") / date.today().isoformat()
    )
    options = parseur.parse_args()
    configurer_logging()
    sauvegarder(options.dossier)


if __name__ == "__main__":
    main()
