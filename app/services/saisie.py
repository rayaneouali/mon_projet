"""Règles métier de la « Saisie du jour » d'une équipe."""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from db import connexion, requetes
from erreurs import ErreurMetier

logger = logging.getLogger("suivi.services.saisie")

MOTIFS = ["Malade", "Congé", "Accident", "Injustifié", "Autre"]
PRESENT = "Présent"
PREFIXE_ABSENT = "Absent · "
# Un seul menu par gars : « Présent » ou « Absent · motif ». Ça marche dans un st.form
# (pas besoin d'afficher le motif seulement après avoir cliqué sur Absent).
CHOIX = [PRESENT] + [PREFIXE_ABSENT + motif for motif in MOTIFS]


@dataclass
class LigneSaisie:
    """Un gars dans la saisie : présent, ou absent avec un motif."""

    gars_id: int
    statut: str = "present"  # 'present' ou 'absent', comme dans la base
    motif: str | None = None


@dataclass
class EtatSaisie:
    """Ce que la page affiche pour une équipe et un jour."""

    lignes: list[LigneSaisie]
    dossier_id: int | None
    deja_saisi: bool
    ailleurs: dict[int, str] = field(default_factory=dict)  # gars_id -> autre équipe ce jour-là


def choix_vers_ligne(gars_id: int, choix: str) -> LigneSaisie:
    """Transforme le choix du menu (« Absent · Malade ») en ligne de saisie."""
    if choix.startswith(PREFIXE_ABSENT):
        return LigneSaisie(gars_id, "absent", choix.removeprefix(PREFIXE_ABSENT))
    return LigneSaisie(gars_id, "present", None)


def ligne_vers_choix(ligne: LigneSaisie) -> str:
    """Transforme une ligne de saisie en choix du menu (inverse de choix_vers_ligne)."""
    if ligne.statut == "absent":
        return PREFIXE_ABSENT + (ligne.motif if ligne.motif in MOTIFS else "Autre")
    return PRESENT


def preparer_etat(
    saisies_du_jour: list[dict[str, Any]],
    equipe_id: int,
    gars_actifs_equipe: list[int],
    dernier_dossier: int | None,
) -> EtatSaisie:
    """Recharge la saisie existante, sinon propose les gars actifs de l'équipe, tous présents."""
    de_l_equipe = [s for s in saisies_du_jour if s["equipe_id"] == equipe_id]
    ailleurs = {s["gars_id"]: s["equipe"] for s in saisies_du_jour if s["equipe_id"] != equipe_id}
    if de_l_equipe:
        lignes = [LigneSaisie(s["gars_id"], s["statut"], s["motif"]) for s in de_l_equipe]
        return EtatSaisie(lignes, de_l_equipe[0]["dossier_id"], deja_saisi=True, ailleurs=ailleurs)
    lignes = [LigneSaisie(gars_id) for gars_id in gars_actifs_equipe]
    return EtatSaisie(lignes, dernier_dossier, deja_saisi=False, ailleurs=ailleurs)


def charger_saisie(jour: date, equipe_id: int, gars_actifs_equipe: list[int]) -> EtatSaisie:
    """Lit la base et prépare l'état de la saisie d'une équipe pour un jour."""
    with connexion.ouvrir_connexion() as conn:
        saisies_du_jour = requetes.lire_saisies_jour(conn, jour)
        dernier = requetes.dernier_dossier_equipe(conn, equipe_id, jour)
    return preparer_etat(saisies_du_jour, equipe_id, gars_actifs_equipe, dernier)


def verifier_saisie(jour: date, lignes: list[LigneSaisie], aujourdhui: date) -> None:
    """Refuse une saisie incohérente avec un message clair (ErreurMetier)."""
    if jour > aujourdhui:
        raise ErreurMetier("On ne peut pas saisir un jour qui n'est pas encore arrivé.")
    if not lignes:
        raise ErreurMetier("Aucun gars dans la saisie : ajoute au moins un gars.")
    ids = [ligne.gars_id for ligne in lignes]
    if len(ids) != len(set(ids)):
        raise ErreurMetier("Un même gars apparaît deux fois dans la saisie.")
    for ligne in lignes:
        if ligne.statut == "absent" and ligne.motif not in MOTIFS:
            raise ErreurMetier("Chaque absent doit avoir un motif.")
        if ligne.statut not in ("present", "absent"):
            raise ErreurMetier("Statut inconnu : choisis Présent ou Absent.")


def retirer_gars_inconnus(gars_ids: list[int], ids_connus: list[int]) -> list[int]:
    """Enlève de la saisie en cours les gars qui n'existent plus (supprimés dans Admin)."""
    connus = set(ids_connus)
    return [gars_id for gars_id in gars_ids if gars_id in connus]


def besoin_confirmation(dossier_id: int | None, lignes: list[LigneSaisie]) -> bool:
    """Vrai s'il y a des présents mais aucun dossier : on demande confirmation."""
    return dossier_id is None and any(ligne.statut == "present" for ligne in lignes)


def enregistrer_saisie(
    jour: date,
    equipe_id: int,
    dossier_id: int | None,
    lignes: list[LigneSaisie],
    aujourdhui: date,
    qui: str = "?",
    nom_equipe: str = "",
) -> int:
    """Vérifie puis remplace la saisie de l'équipe ce jour-là ; renvoie le nombre de gars."""
    verifier_saisie(jour, lignes, aujourdhui)
    a_ecrire = [(ligne.gars_id, ligne.statut, ligne.motif) for ligne in lignes]
    with connexion.ouvrir_connexion() as conn:
        nombre = requetes.remplacer_saisie(conn, jour, equipe_id, dossier_id, a_ecrire)
    absents = sum(1 for ligne in lignes if ligne.statut == "absent")
    logger.info(
        "Saisie enregistrée par %s : %s, %s, %d gars dont %d absent(s), dossier %s",
        qui,
        nom_equipe or f"équipe n°{equipe_id}",
        jour.isoformat(),
        nombre,
        absents,
        dossier_id,
    )
    return nombre
