"""Tests des règles des demandes de samedi."""

from datetime import date

import pytest

from erreurs import ErreurMetier
from services import samedis

SAMEDI = date(2026, 11, 14)
LUNDI = date(2026, 11, 9)


def test_creer_une_demande_par_gars(exemples: dict[str, int]) -> None:
    """Une demande « demandé » est créée pour chaque gars coché."""
    gars = [(exemples["Karim"], "Karim"), (exemples["Yanis"], "Yanis")]
    resultat = samedis.creer_demandes(SAMEDI, gars, exemples["D-001"], " allée 4 ")
    assert resultat.crees == ["Karim", "Yanis"]
    demandes = samedis.lister_demandes(LUNDI)
    assert [(d["gars"], d["statut"], d["note"]) for d in demandes] == [
        ("Karim", "demande", "allée 4"),
        ("Yanis", "demande", "allée 4"),
    ]


def test_doublon_signale_proprement_sans_erreur(exemples: dict[str, int]) -> None:
    """Redemander le même gars le même samedi : message clair, et les autres sont créés."""
    samedis.creer_demandes(SAMEDI, [(exemples["Karim"], "Karim")], None, "")
    resultat = samedis.creer_demandes(
        SAMEDI, [(exemples["Karim"], "Karim"), (exemples["Lucas"], "Lucas")], None, ""
    )
    assert resultat.deja_demandes == ["Karim"]
    assert resultat.crees == ["Lucas"]
    succes, avertissement = samedis.message_resultat(resultat)
    assert "Lucas" in succes
    assert "Déjà demandé" in avertissement and "Karim" in avertissement


def test_date_qui_n_est_pas_un_samedi_refusee(exemples: dict[str, int]) -> None:
    """Le service refuse un autre jour qu'un samedi, avec un message clair."""
    with pytest.raises(ErreurMetier, match="pas un samedi"):
        samedis.creer_demandes(LUNDI, [(exemples["Karim"], "Karim")], None, "")


def test_aucun_gars_coche_refuse() -> None:
    """Il faut cocher au moins un gars."""
    with pytest.raises(ErreurMetier, match="au moins un gars"):
        samedis.creer_demandes(SAMEDI, [], None, "")


def test_changer_statut_et_statut_inconnu(exemples: dict[str, int]) -> None:
    """Le statut passe à accepté ; un statut inventé est refusé."""
    samedis.creer_demandes(SAMEDI, [(exemples["Karim"], "Karim")], None, "")
    demande = samedis.lister_demandes(LUNDI)[0]
    samedis.changer_statut(demande["id"], "accepte")
    assert samedis.lister_demandes(LUNDI)[0]["statut"] == "accepte"
    with pytest.raises(ErreurMetier, match="inconnu"):
        samedis.changer_statut(demande["id"], "peut-etre")


def test_changer_statut_d_une_demande_supprimee(exemples: dict[str, int]) -> None:
    """Modifier une demande supprimée entre-temps donne un message clair."""
    samedis.creer_demandes(SAMEDI, [(exemples["Karim"], "Karim")], None, "")
    demande = samedis.lister_demandes(LUNDI)[0]
    samedis.supprimer_demande(demande["id"])
    assert samedis.lister_demandes(LUNDI) == []
    with pytest.raises(ErreurMetier, match="n'existe plus"):
        samedis.changer_statut(demande["id"], "fait")


def test_liste_a_partir_de_la_semaine_derniere(exemples: dict[str, int]) -> None:
    """La liste montre les demandes depuis 7 jours, pas les plus anciennes."""
    samedis.creer_demandes(date(2026, 10, 31), [(exemples["Karim"], "Karim")], None, "")
    samedis.creer_demandes(date(2026, 11, 7), [(exemples["Karim"], "Karim")], None, "")
    samedis.creer_demandes(SAMEDI, [(exemples["Yanis"], "Yanis")], None, "")
    groupes = samedis.grouper_par_samedi(samedis.lister_demandes(LUNDI))
    assert list(groupes) == [date(2026, 11, 7), SAMEDI]
