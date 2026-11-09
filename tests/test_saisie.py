"""Tests des règles de la « Saisie du jour »."""

from datetime import date

import pytest

from db import connexion, requetes
from erreurs import ErreurMetier
from services import saisie
from services.saisie import LigneSaisie

LUNDI = date(2026, 11, 9)
MARDI = date(2026, 11, 10)


# ------------------------------------------------------------- règles sans base


def test_choix_present_et_absent_avec_motif() -> None:
    """Le menu « Absent · Malade » devient statut absent + motif Malade, et inversement."""
    assert saisie.choix_vers_ligne(1, "Présent") == LigneSaisie(1, "present", None)
    ligne = saisie.choix_vers_ligne(1, "Absent · Malade")
    assert ligne == LigneSaisie(1, "absent", "Malade")
    assert saisie.ligne_vers_choix(ligne) == "Absent · Malade"


def test_les_cinq_motifs_sont_proposes() -> None:
    """Motifs : Malade, Congé, Accident, Injustifié, Autre."""
    assert saisie.MOTIFS == ["Malade", "Congé", "Accident", "Injustifié", "Autre"]
    assert len(saisie.CHOIX) == 6


def test_nouvelle_saisie_tous_presents_et_dernier_dossier() -> None:
    """Pas de saisie existante : gars actifs de l'équipe tous présents, dernier dossier repris."""
    etat = saisie.preparer_etat([], equipe_id=1, gars_actifs_equipe=[10, 11], dernier_dossier=7)
    assert not etat.deja_saisi
    assert etat.lignes == [LigneSaisie(10), LigneSaisie(11)]
    assert etat.dossier_id == 7


def test_saisie_existante_rechargee_pour_correction() -> None:
    """Une saisie existante de l'équipe est rechargée telle quelle."""
    du_jour = [
        {
            "equipe_id": 1,
            "equipe": "Équipe 1",
            "gars_id": 10,
            "statut": "absent",
            "motif": "Congé",
            "dossier_id": 3,
        },
    ]
    etat = saisie.preparer_etat(du_jour, 1, [10, 11], dernier_dossier=7)
    assert etat.deja_saisi
    assert etat.lignes == [LigneSaisie(10, "absent", "Congé")]
    assert etat.dossier_id == 3


def test_gars_deja_note_ailleurs_signale() -> None:
    """Un gars noté dans une autre équipe ce jour-là est signalé (avertissement)."""
    du_jour = [
        {
            "equipe_id": 2,
            "equipe": "Équipe 2",
            "gars_id": 20,
            "statut": "present",
            "motif": None,
            "dossier_id": None,
        },
    ]
    etat = saisie.preparer_etat(du_jour, 1, [10], None)
    assert etat.ailleurs == {20: "Équipe 2"}


def test_equipe_sans_gars_donne_une_saisie_vide() -> None:
    """Une équipe sans gars actif : liste vide (la page affiche un avertissement)."""
    etat = saisie.preparer_etat([], 1, [], None)
    assert etat.lignes == []


def test_confirmation_si_presents_sans_dossier() -> None:
    """Pas de dossier + au moins un présent → on demande confirmation."""
    assert saisie.besoin_confirmation(None, [LigneSaisie(1)])
    assert not saisie.besoin_confirmation(None, [LigneSaisie(1, "absent", "Malade")])
    assert not saisie.besoin_confirmation(5, [LigneSaisie(1)])


def test_saisie_vide_refusee() -> None:
    """Au moins un gars est obligatoire."""
    with pytest.raises(ErreurMetier, match="Aucun gars"):
        saisie.verifier_saisie(LUNDI, [], aujourdhui=LUNDI)


def test_date_future_refusee() -> None:
    """On ne saisit pas un jour qui n'est pas encore arrivé."""
    with pytest.raises(ErreurMetier, match="pas encore arrivé"):
        saisie.verifier_saisie(MARDI, [LigneSaisie(1)], aujourdhui=LUNDI)


def test_absent_sans_motif_refuse() -> None:
    """Un absent doit avoir un motif de la liste."""
    with pytest.raises(ErreurMetier, match="motif"):
        saisie.verifier_saisie(LUNDI, [LigneSaisie(1, "absent", None)], aujourdhui=LUNDI)


def test_gars_en_double_refuse() -> None:
    """Le même gars ne peut pas apparaître deux fois dans une saisie."""
    with pytest.raises(ErreurMetier, match="deux fois"):
        saisie.verifier_saisie(LUNDI, [LigneSaisie(1), LigneSaisie(1)], aujourdhui=LUNDI)


# ------------------------------------------------------------- avec la base


def test_enregistrer_puis_recharger(exemples: dict[str, int]) -> None:
    """Après enregistrement, la saisie est rechargée (déjà saisi) avec le bon contenu."""
    e1 = exemples["Équipe 1"]
    lignes = [LigneSaisie(exemples["Karim"]), LigneSaisie(exemples["Yanis"], "absent", "Malade")]
    nombre = saisie.enregistrer_saisie(LUNDI, e1, exemples["D-001"], lignes, aujourdhui=LUNDI)
    assert nombre == 2
    etat = saisie.charger_saisie(LUNDI, e1, [exemples["Karim"], exemples["Yanis"]])
    assert etat.deja_saisi
    assert etat.dossier_id == exemples["D-001"]
    assert LigneSaisie(exemples["Yanis"], "absent", "Malade") in etat.lignes


def test_le_lendemain_reprend_le_dossier_de_la_veille(exemples: dict[str, int]) -> None:
    """Nouvelle saisie : le dossier proposé est celui de la dernière saisie de l'équipe."""
    e1 = exemples["Équipe 1"]
    saisie.enregistrer_saisie(LUNDI, e1, exemples["D-002"], [LigneSaisie(exemples["Karim"])], LUNDI)
    etat = saisie.charger_saisie(MARDI, e1, [exemples["Karim"]])
    assert not etat.deja_saisi
    assert etat.dossier_id == exemples["D-002"]


def test_renfort_deplace_depuis_l_autre_equipe(exemples: dict[str, int]) -> None:
    """Un renfort noté ailleurs est signalé, puis déplacé à l'enregistrement."""
    e1, e2 = exemples["Équipe 1"], exemples["Équipe 2"]
    saisie.enregistrer_saisie(LUNDI, e2, None, [LigneSaisie(exemples["Samir"])], LUNDI)
    etat = saisie.charger_saisie(LUNDI, e1, [exemples["Karim"]])
    assert etat.ailleurs == {exemples["Samir"]: "Équipe 2"}
    saisie.enregistrer_saisie(
        LUNDI, e1, None, [LigneSaisie(exemples["Karim"]), LigneSaisie(exemples["Samir"])], LUNDI
    )
    with connexion.ouvrir_connexion() as conn:
        lignes = requetes.lire_saisies_jour(conn, LUNDI)
    assert {ligne["gars"]: ligne["equipe"] for ligne in lignes} == {
        "Karim": "Équipe 1",
        "Samir": "Équipe 1",
    }


def test_gars_supprime_retire_de_la_saisie_en_cours() -> None:
    """Un gars supprimé dans Admin pendant une saisie est retiré (la page ne plante pas)."""
    assert saisie.retirer_gars_inconnus([1, 2, 3], ids_connus=[1, 3, 4]) == [1, 3]
