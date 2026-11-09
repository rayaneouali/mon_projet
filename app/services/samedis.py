"""Règles métier des demandes de travail le samedi."""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from psycopg import errors

from db import connexion, requetes
from erreurs import ErreurMetier
from services import dates

logger = logging.getLogger("suivi.services.samedis")

# Statut en base -> libellé affiché
LIBELLES_STATUT = {
    "demande": "Demandé",
    "accepte": "Accepté",
    "refuse": "Refusé",
    "fait": "Fait",
}


@dataclass
class ResultatDemandes:
    """Bilan d'une création : pour qui c'est créé, pour qui ça existait déjà."""

    crees: list[str] = field(default_factory=list)
    deja_demandes: list[str] = field(default_factory=list)


def creer_demandes(
    samedi: date,
    gars: list[tuple[int, str]],
    dossier_id: int | None,
    note: str,
    qui: str = "?",
) -> ResultatDemandes:
    """Crée une demande « demandé » par gars ; un doublon est signalé, pas une erreur.

    `gars` : liste de (gars_id, nom).
    """
    if not gars:
        raise ErreurMetier("Coche au moins un gars.")
    if not dates.est_samedi(samedi):
        raise ErreurMetier("La date choisie n'est pas un samedi.")
    resultat = ResultatDemandes()
    with connexion.ouvrir_connexion() as conn:
        for gars_id, nom in gars:
            try:
                # Sous-transaction (« savepoint ») : si CE gars est un doublon, on annule
                # seulement son insertion et on continue avec les autres.
                with conn.transaction():
                    requetes.ajouter_demande_samedi(conn, samedi, gars_id, dossier_id, note.strip())
                resultat.crees.append(nom)
            except errors.UniqueViolation:
                # C'est la contrainte UNIQUE (samedi, gars_id) de la base qui détecte le doublon.
                logger.info("Demande déjà existante : %s le %s", nom, samedi.isoformat())
                resultat.deja_demandes.append(nom)
    logger.info(
        "Demandes de samedi par %s pour le %s : %d créée(s), %d déjà existante(s)",
        qui,
        samedi.isoformat(),
        len(resultat.crees),
        len(resultat.deja_demandes),
    )
    return resultat


def message_resultat(resultat: ResultatDemandes) -> tuple[str, str]:
    """Phrases à afficher : (succès, avertissement), l'une ou l'autre pouvant être vide."""
    succes = ""
    if resultat.crees:
        succes = (
            f"Demande enregistrée pour {len(resultat.crees)} gars : {', '.join(resultat.crees)}."
        )
    avertissement = ""
    if resultat.deja_demandes:
        avertissement = (
            "Déjà demandé ce samedi-là (rien de changé) pour : "
            + ", ".join(resultat.deja_demandes)
            + "."
        )
    return succes, avertissement


def lister_demandes(aujourdhui: date) -> list[dict[str, Any]]:
    """Demandes à partir de la semaine dernière (8 samedis à venir compris)."""
    depuis = aujourdhui - timedelta(days=7)
    jusqua = aujourdhui + timedelta(weeks=52)
    with connexion.ouvrir_connexion() as conn:
        return requetes.lister_demandes_samedi(conn, depuis, jusqua)


def grouper_par_samedi(demandes: list[dict[str, Any]]) -> dict[date, list[dict[str, Any]]]:
    """Range les demandes par samedi (dans l'ordre des dates)."""
    groupes: dict[date, list[dict[str, Any]]] = {}
    for demande in sorted(demandes, key=lambda d: (d["samedi"], d["gars"])):
        groupes.setdefault(demande["samedi"], []).append(demande)
    return groupes


def changer_statut(demande_id: int, statut: str, qui: str = "?") -> None:
    """Change le statut d'une demande (demandé / accepté / refusé / fait)."""
    if statut not in LIBELLES_STATUT:
        raise ErreurMetier("Statut inconnu.")
    with connexion.ouvrir_connexion() as conn:
        if not requetes.changer_statut_demande(conn, demande_id, statut):
            raise ErreurMetier("Cette demande n'existe plus (supprimée entre-temps ?).")
    logger.info("Demande de samedi n°%d passée à « %s » par %s", demande_id, statut, qui)


def supprimer_demande(demande_id: int, qui: str = "?") -> None:
    """Supprime une demande de samedi."""
    with connexion.ouvrir_connexion() as conn:
        supprimee = requetes.supprimer_demande_samedi(conn, demande_id)
    logger.info(
        "Demande de samedi n°%d supprimée par %s (existait : %s)", demande_id, qui, supprimee
    )
