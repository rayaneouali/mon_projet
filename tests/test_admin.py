"""Tests de la page Admin (comparaison des tableaux, désactivation au lieu de suppression)."""

from datetime import date

import pandas as pd
import pytest

from db import connexion, requetes
from erreurs import ErreurMetier
from services import admin, saisie
from services.references import charger_references

LUNDI = date(2026, 11, 9)


# ------------------------------------------------------------- comparaison sans base


def test_calculer_changements() -> None:
    """Ajout, modification, suppression et ligne vide ignorée sont bien reconnus."""
    avant = pd.DataFrame(
        [{"id": 1, "Nom": "Équipe 1", "Chef": "Karim"}, {"id": 2, "Nom": "Équipe 2", "Chef": ""}]
    )
    apres = pd.DataFrame(
        [
            {"id": 1, "Nom": "Équipe 1 ", "Chef": "Yanis"},  # chef changé (espace ignoré)
            {"id": None, "Nom": "Équipe 3", "Chef": None},  # nouvelle ligne
            {"id": None, "Nom": None, "Chef": None},  # ligne vide : ignorée
        ]
    )
    changements = admin.calculer_changements(avant, apres)
    assert changements.modifications == [{"id": 1, "Nom": "Équipe 1", "Chef": "Yanis"}]
    assert changements.ajouts == [{"Nom": "Équipe 3", "Chef": ""}]
    assert changements.suppressions == [2]


def test_aucun_changement() -> None:
    """Un tableau rendu tel quel ne produit aucun changement."""
    avant = pd.DataFrame([{"id": 1, "Code": "D-1", "Client": "", "Lieu": "", "Actif": True}])
    assert admin.calculer_changements(avant, avant.copy()) == admin.Changements()


# ------------------------------------------------------------- avec la base


def test_gars_avec_historique_desactive_au_lieu_de_supprime(exemples: dict[str, int]) -> None:
    """Supprimer un gars qui a des saisies le passe en inactif ; sans historique, il part."""
    saisie.enregistrer_saisie(
        LUNDI, exemples["Équipe 1"], None, [saisie.LigneSaisie(exemples["Karim"])], LUNDI
    )
    refs = charger_references()
    avant = admin.tableau_gars(refs)
    apres = avant[~avant["Nom"].isin(["Karim", "Lucas"])]  # on « supprime » Karim et Lucas
    bilan = admin.enregistrer_gars(avant, apres, refs)
    assert "Karim" in bilan
    gars = {g["nom"]: g["actif"] for g in charger_references().gars}
    assert gars["Karim"] is False  # gardé, inactif
    assert "Lucas" not in gars  # sans historique : supprimé


def test_dossier_avec_historique_desactive(exemples: dict[str, int]) -> None:
    """Même règle pour un dossier qui a servi."""
    saisie.enregistrer_saisie(
        LUNDI,
        exemples["Équipe 1"],
        exemples["D-001"],
        [saisie.LigneSaisie(exemples["Karim"])],
        LUNDI,
    )
    refs = charger_references()
    avant = admin.tableau_dossiers(refs)
    admin.enregistrer_dossiers(avant, avant[avant["Code"] != "D-001"])
    dossiers = {d["code"]: d["actif"] for d in charger_references().dossiers}
    assert dossiers["D-001"] is False


def test_equipe_avec_gars_non_supprimable(exemples: dict[str, int]) -> None:
    """Une équipe qui a des gars ne peut pas être supprimée : message clair, rien ne change."""
    refs = charger_references()
    avant = admin.tableau_equipes(refs)
    with pytest.raises(ErreurMetier, match="ne peut pas la supprimer"):
        admin.enregistrer_equipes(avant, avant[avant["Nom"] != "Équipe 1"])
    assert len(charger_references().equipes) == 2


def test_ajouter_un_vrai_gars_le_rend_disponible(exemples: dict[str, int]) -> None:
    """Un gars ajouté dans Admin apparaît parmi les gars actifs de son équipe."""
    refs = charger_references()
    avant = admin.tableau_gars(refs)
    nouveau = pd.DataFrame([{"id": None, "Nom": "Bilal", "Équipe": "Équipe 2", "Actif": None}])
    admin.enregistrer_gars(avant, pd.concat([avant, nouveau], ignore_index=True), refs)
    refs = charger_references()
    assert "Bilal" in [g["nom"] for g in refs.gars_actifs_de(exemples["Équipe 2"])]


def test_doublon_de_nom_message_clair(exemples: dict[str, int]) -> None:
    """Deux gars du même nom : message lisible, pas d'erreur technique."""
    refs = charger_references()
    avant = admin.tableau_gars(refs)
    doublon = pd.DataFrame([{"id": None, "Nom": "Karim", "Équipe": "Équipe 1", "Actif": True}])
    with pytest.raises(ErreurMetier, match="existe déjà"):
        admin.enregistrer_gars(avant, pd.concat([avant, doublon], ignore_index=True), refs)


def test_nom_vide_refuse(exemples: dict[str, int]) -> None:
    """Une équipe renommée en vide est refusée."""
    refs = charger_references()
    avant = admin.tableau_equipes(refs)
    apres = avant.copy()
    apres.loc[0, "Nom"] = "  "
    with pytest.raises(ErreurMetier, match="obligatoire"):
        admin.enregistrer_equipes(avant, apres)
    with connexion.ouvrir_connexion() as conn:
        assert [e["nom"] for e in requetes.lister_equipes(conn)] == ["Équipe 1", "Équipe 2"]
