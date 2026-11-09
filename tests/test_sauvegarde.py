"""Tests de la sauvegarde CSV et de la restauration."""

import importlib.util
from datetime import date
from pathlib import Path
from types import ModuleType

import pandas as pd

from services import saisie, samedis
from services.references import charger_references

LUNDI = date(2026, 11, 9)
SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def charger_script(nom: str) -> ModuleType:
    """Importe un script du dossier scripts/ comme un module."""
    spec = importlib.util.spec_from_file_location(nom, SCRIPTS / f"{nom}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sauvegarde_puis_restauration(exemples: dict[str, int], tmp_path: Path) -> None:
    """Sauvegarder, tout casser, restaurer : on retrouve les données, et on peut continuer."""
    sauvegarde, restauration = charger_script("sauvegarde"), charger_script("restauration")
    saisie.enregistrer_saisie(
        LUNDI,
        exemples["Équipe 1"],
        exemples["D-001"],
        [
            saisie.LigneSaisie(exemples["Karim"]),
            saisie.LigneSaisie(exemples["Yanis"], "absent", "Congé"),
        ],
        LUNDI,
    )
    samedis.creer_demandes(date(2026, 11, 14), [(exemples["Lucas"], "Lucas")], None, "allée 4")

    nombres = sauvegarde.sauvegarder(tmp_path)
    assert nombres == {"equipes": 2, "gars": 6, "dossiers": 2, "saisies": 2, "demandes_samedi": 1}
    lu = pd.read_csv(tmp_path / "gars.csv", sep=";", encoding="utf-8-sig")
    assert "Karim" in list(lu["nom"])  # le CSV s'ouvre (séparateur ; et accents OK)

    samedis.creer_demandes(date(2026, 11, 21), [(exemples["Karim"], "Karim")], None, "")
    restauration.restaurer(tmp_path)

    refs = charger_references()
    assert len(refs.gars) == 6 and len(refs.equipes) == 2
    assert len(samedis.lister_demandes(LUNDI)) == 1  # la demande ajoutée après a disparu
    # Les compteurs d'id sont recalés : on peut de nouveau créer sans conflit.
    samedis.creer_demandes(date(2026, 11, 21), [(exemples["Karim"], "Karim")], None, "")
    assert len(samedis.lister_demandes(LUNDI)) == 2
