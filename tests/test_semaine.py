"""Tests du calcul de la vue « Semaine », sur des données fabriquées à la main (sans base)."""

from datetime import date
from io import BytesIO

import pandas as pd

from services import semaine
from services.references import References

LUNDI = date(2026, 11, 9)
MARDI = date(2026, 11, 10)
MERCREDI = date(2026, 11, 11)
SAMEDI = date(2026, 11, 14)
DIMANCHE = date(2026, 11, 15)

REFS = References(
    equipes=[
        {"id": 1, "nom": "Équipe 1", "chef": "Karim"},
        {"id": 2, "nom": "Équipe 2", "chef": "Mehdi"},
        {"id": 3, "nom": "Équipe vide", "chef": ""},
    ],
    gars=[
        {"id": 10, "nom": "Karim", "equipe_id": 1, "equipe": "Équipe 1", "actif": True},
        {"id": 11, "nom": "Yanis", "equipe_id": 1, "equipe": "Équipe 1", "actif": True},
        {"id": 12, "nom": "Ancien", "equipe_id": 1, "equipe": "Équipe 1", "actif": False},
        {"id": 13, "nom": "Parti", "equipe_id": 1, "equipe": "Équipe 1", "actif": False},
        {"id": 20, "nom": "Samir", "equipe_id": 2, "equipe": "Équipe 2", "actif": True},
    ],
    dossiers=[],
)


def saisie(jour: date, gars_id: int, nom: str, equipe_id: int, **autres: object) -> dict:
    """Fabrique une ligne de saisie comme celles que renvoie la base."""
    ligne = {
        "date": jour,
        "gars_id": gars_id,
        "gars": nom,
        "equipe_id": equipe_id,
        "equipe": f"Équipe {equipe_id}",
        "statut": "present",
        "motif": None,
        "dossier": "D-001",
        "dossier_id": 1,
    }
    ligne.update(autres)
    return ligne


SAISIES = [
    saisie(LUNDI, 10, "Karim", 1),
    saisie(LUNDI, 11, "Yanis", 1, statut="absent", motif="Malade", dossier=None),
    saisie(LUNDI, 12, "Ancien", 1),
    saisie(LUNDI, 20, "Samir", 1),  # Samir (Équipe 2) en renfort chez l'Équipe 1
    saisie(MARDI, 11, "Yanis", 1, statut="absent", motif="Malade", dossier=None),
    saisie(MARDI, 10, "Karim", 1, dossier=None),
    saisie(MARDI, 20, "Samir", 2, dossier="D-002"),
]
DEMANDES = [
    {
        "samedi": SAMEDI,
        "gars_id": 10,
        "gars": "Karim",
        "equipe": "Équipe 1",
        "dossier": "D-001",
        "statut": "accepte",
        "note": "allée 4",
    },
]


def grille() -> pd.DataFrame:
    """La grille de la semaine de test, indexée par nom de gars."""
    return semaine.construire_grille(LUNDI, REFS, SAISIES, DEMANDES).set_index("Gars")


def test_colonnes_lundi_a_samedi_sans_dimanche() -> None:
    """Sans saisie le dimanche, le tableau va du lundi au samedi."""
    assert list(grille().columns) == [
        "Équipe",
        "lun. 9 nov.",
        "mar. 10 nov.",
        "mer. 11 nov.",
        "jeu. 12 nov.",
        "ven. 13 nov.",
        "sam. 14 nov.",
    ]


def test_dimanche_affiche_seulement_s_il_y_a_des_saisies() -> None:
    """Une saisie le dimanche ajoute la colonne dimanche."""
    avec_dimanche = SAISIES + [saisie(DIMANCHE, 10, "Karim", 1)]
    tableau = semaine.construire_grille(LUNDI, REFS, avec_dimanche, [])
    assert "dim. 15 nov." in tableau.columns


def test_contenu_des_cases() -> None:
    """Code dossier, ABS · motif, tiret, « Présent » sans dossier, « avec Équipe X »."""
    g = grille()
    assert g.loc["Karim", "lun. 9 nov."] == "D-001"
    assert g.loc["Yanis", "lun. 9 nov."] == "ABS · Malade"
    assert g.loc["Karim", "mer. 11 nov."] == "—"
    assert g.loc["Karim", "mar. 10 nov."] == "Présent"
    assert g.loc["Samir", "lun. 9 nov."] == "D-001 · avec Équipe 1"
    assert g.loc["Samir", "mar. 10 nov."] == "D-002"


def test_statut_du_samedi_dans_la_colonne_samedi() -> None:
    """La colonne samedi montre le statut de la demande."""
    assert grille().loc["Karim", "sam. 14 nov."] == "Samedi : Accepté"


def test_gars_inactif_visible_seulement_s_il_a_travaille_cette_semaine() -> None:
    """Un gars inactif avec historique cette semaine reste visible ; sinon il disparaît."""
    noms = list(grille().index)
    assert "Ancien" in noms
    assert "Parti" not in noms


def test_regroupement_par_equipe_et_filtre() -> None:
    """Les gars sont groupés par équipe ; le filtre ne garde qu'une équipe."""
    g = grille()
    assert g.loc["Samir", "Équipe"] == "Équipe 2"
    filtre = semaine.construire_grille(LUNDI, REFS, SAISIES, DEMANDES, equipe_filtre=2)
    assert list(filtre["Gars"]) == ["Samir"]


def test_saisi_et_manquant() -> None:
    """Saisi si l'équipe a des lignes ; manquant seulement les jours ouvrés passés."""
    suivi = semaine.construire_suivi(LUNDI, REFS, SAISIES, aujourdhui=MERCREDI)
    suivi = suivi.set_index("Équipe")
    assert suivi.loc["Équipe 1", "lun. 9 nov."] == semaine.SAISI
    assert suivi.loc["Équipe 2", "lun. 9 nov."] == semaine.MANQUANT
    assert suivi.loc["Équipe 1", "mer. 11 nov."] == semaine.MANQUANT  # aujourd'hui, pas fait
    assert suivi.loc["Équipe 1", "jeu. 12 nov."] == ""  # futur
    assert suivi.loc["Équipe 1", "sam. 14 nov."] == ""  # pas un jour ouvré


def test_equipe_sans_gars_jamais_manquante() -> None:
    """Une équipe sans gars actif n'est pas marquée « manquant »."""
    suivi = semaine.construire_suivi(LUNDI, REFS, SAISIES, aujourdhui=MERCREDI)
    assert set(suivi.set_index("Équipe").loc["Équipe vide"].drop("Chef")) == {""}


def test_resume_absences_par_gars() -> None:
    """Résumé : dates et motifs des absences, par gars."""
    absences = semaine.resume_absences(SAISIES).set_index("Gars")
    assert absences.loc["Yanis", "Jours"] == 2
    assert absences.loc["Yanis", "Absences"] == "lun. 9 nov. (Malade), mar. 10 nov. (Malade)"


def test_jours_homme_par_dossier() -> None:
    """Jours-homme : présents avec un dossier, du plus gros au plus petit."""
    tableau = semaine.jours_homme_par_dossier(SAISIES)
    assert tableau.to_dict("records") == [
        {"Dossier": "D-001", "Jours-homme": 3},
        {"Dossier": "D-002", "Jours-homme": 1},
    ]


def test_couleur_stable_par_dossier() -> None:
    """Le même code dossier donne toujours la même couleur."""
    assert semaine.couleur_dossier("D-2026-001") == semaine.couleur_dossier("D-2026-001")
    assert semaine.couleur_dossier("D-2026-001") in semaine.COULEURS


def test_styles() -> None:
    """ABS en rouge, tiret en gris, dossier coloré."""
    assert "#c0392b" in semaine.style_case("ABS · Malade")
    assert "#c3c9d3" in semaine.style_case("—")
    fond, _ = semaine.couleur_dossier("D-001")
    assert fond in semaine.style_case("D-001 · avec Équipe 1")


def test_export_excel_lisible() -> None:
    """L'export produit un vrai fichier Excel avec l'onglet Planning."""
    vue = semaine.construire_vue(LUNDI, REFS, SAISIES, DEMANDES, aujourdhui=MERCREDI)
    contenu = semaine.exporter_excel(vue)
    planning = pd.read_excel(BytesIO(contenu), sheet_name="Planning")
    assert "Karim" in list(planning["Gars"])
    assert set(pd.ExcelFile(BytesIO(contenu)).sheet_names) == {
        "Planning",
        "Saisies des chefs",
        "Absences",
        "Jours-homme",
        "Samedis",
    }
