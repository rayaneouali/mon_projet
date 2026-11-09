"""Règles de la page Admin : équipes, gars et dossiers modifiés dans un tableau éditable.

Principe : on compare le tableau d'origine (« avant ») et le tableau modifié (« après »)
pour savoir quelles lignes ont été ajoutées, modifiées ou supprimées.
Un gars ou un dossier qui a de l'historique n'est jamais effacé : il passe en inactif.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from psycopg import errors

from db import connexion, requetes
from erreurs import ErreurMetier
from services.references import References

logger = logging.getLogger("suivi.services.admin")


@dataclass
class Changements:
    """Différences entre le tableau d'origine et le tableau modifié."""

    ajouts: list[dict[str, Any]] = field(default_factory=list)
    modifications: list[dict[str, Any]] = field(default_factory=list)
    suppressions: list[int] = field(default_factory=list)


@dataclass
class Bilan:
    """Ce qui a été fait, pour le message de confirmation."""

    ajouts: int = 0
    modifications: int = 0
    suppressions: int = 0
    desactivations: list[str] = field(default_factory=list)

    def phrase(self) -> str:
        """Résumé lisible, par ex. « 1 ajout, 2 modifications »."""
        morceaux = []
        if self.ajouts:
            morceaux.append(f"{self.ajouts} ajout(s)")
        if self.modifications:
            morceaux.append(f"{self.modifications} modification(s)")
        if self.suppressions:
            morceaux.append(f"{self.suppressions} suppression(s)")
        if self.desactivations:
            noms = ", ".join(self.desactivations)
            morceaux.append(f"passé(s) en inactif car ils ont un historique : {noms}")
        return "Enregistré : " + ("; ".join(morceaux) if morceaux else "aucun changement") + "."


# ---------------------------------------------------------------- tableaux à éditer


def tableau_equipes(refs: References) -> pd.DataFrame:
    """Tableau des équipes pour l'éditeur."""
    lignes = [{"id": e["id"], "Nom": e["nom"], "Chef": e["chef"]} for e in refs.equipes]
    return pd.DataFrame(lignes, columns=["id", "Nom", "Chef"])


def tableau_gars(refs: References) -> pd.DataFrame:
    """Tableau des gars pour l'éditeur (actifs d'abord)."""
    lignes = [
        {"id": g["id"], "Nom": g["nom"], "Équipe": g["equipe"], "Actif": g["actif"]}
        for g in sorted(refs.gars, key=lambda g: (not g["actif"], g["equipe"], g["nom"]))
    ]
    return pd.DataFrame(lignes, columns=["id", "Nom", "Équipe", "Actif"])


def tableau_dossiers(refs: References) -> pd.DataFrame:
    """Tableau des dossiers pour l'éditeur (actifs d'abord)."""
    lignes = [
        {
            "id": d["id"],
            "Code": d["code"],
            "Client": d["client"],
            "Lieu": d["lieu"],
            "Actif": d["actif"],
        }
        for d in sorted(refs.dossiers, key=lambda d: (not d["actif"], d["code"]))
    ]
    return pd.DataFrame(lignes, columns=["id", "Code", "Client", "Lieu", "Actif"])


# ---------------------------------------------------------------- comparaison avant / après


def _propre(valeur: Any) -> Any:
    """Normalise une cellule : vide → '', texte sans espaces autour, booléens inchangés."""
    if valeur is None or (not isinstance(valeur, (list, dict)) and pd.isna(valeur)):
        return ""
    if isinstance(valeur, str):
        return valeur.strip()
    return valeur


def _ligne_propre(ligne: dict[str, Any]) -> dict[str, Any]:
    """Normalise toutes les cellules d'une ligne (sauf l'id)."""
    return {cle: _propre(valeur) for cle, valeur in ligne.items() if cle != "id"}


def calculer_changements(avant: pd.DataFrame, apres: pd.DataFrame) -> Changements:
    """Compare les deux tableaux grâce à la colonne « id » (vide = nouvelle ligne)."""
    logger.debug("Tableau reçu de l'éditeur : %s", apres.to_dict("records"))
    origine = {int(ligne["id"]): _ligne_propre(ligne) for ligne in avant.to_dict("records")}
    changements = Changements()
    restants = set()
    for ligne in apres.to_dict("records"):
        propre = _ligne_propre(ligne)
        if _propre(ligne.get("id")) == "":
            if any(valeur not in ("", False, True) for valeur in propre.values()):
                changements.ajouts.append(propre)  # ligne neuve non vide
            continue
        identifiant = int(ligne["id"])
        restants.add(identifiant)
        if propre != origine.get(identifiant):
            changements.modifications.append({"id": identifiant, **propre})
    changements.suppressions = sorted(set(origine) - restants)
    return changements


def _obligatoire(valeur: Any, quoi: str) -> str:
    """Refuse un nom ou un code vide."""
    texte = _propre(valeur)
    if not texte:
        raise ErreurMetier(f"{quoi} est obligatoire (une ligne a été laissée vide).")
    return str(texte)


def _actif(valeur: Any) -> bool:
    """Case « Actif » : cochée par défaut pour une nouvelle ligne."""
    return True if _propre(valeur) == "" else bool(valeur)


def _traduire_doublon(erreur: errors.UniqueViolation) -> ErreurMetier:
    """Transforme l'erreur « valeur déjà existante » de la base en message lisible."""
    logger.warning("Doublon refusé par la base : %s", erreur.diag.message_detail)
    return ErreurMetier("Ce nom (ou ce code) existe déjà : choisis-en un autre.")


# ---------------------------------------------------------------- enregistrement


def enregistrer_equipes(avant: pd.DataFrame, apres: pd.DataFrame, qui: str = "?") -> str:
    """Applique les changements d'équipes en une transaction (tout ou rien)."""
    changements = calculer_changements(avant, apres)
    noms = {int(ligne["id"]): ligne["Nom"] for ligne in avant.to_dict("records")}
    bilan = Bilan()
    try:
        with connexion.ouvrir_connexion() as conn, conn.transaction():
            for equipe_id in changements.suppressions:
                if requetes.equipe_a_historique(conn, equipe_id):
                    raise ErreurMetier(
                        f"L'équipe « {noms[equipe_id]} » a des gars ou des saisies : on ne peut "
                        "pas la supprimer. Déplace d'abord ses gars, ou renomme-la."
                    )
                requetes.supprimer_equipe(conn, equipe_id)
                bilan.suppressions += 1
            for ligne in changements.modifications:
                requetes.modifier_equipe(
                    conn, ligne["id"], _obligatoire(ligne["Nom"], "Le nom d'équipe"), ligne["Chef"]
                )
                bilan.modifications += 1
            for ligne in changements.ajouts:
                requetes.ajouter_equipe(
                    conn, _obligatoire(ligne["Nom"], "Le nom d'équipe"), str(ligne["Chef"])
                )
                bilan.ajouts += 1
    except errors.UniqueViolation as erreur:
        raise _traduire_doublon(erreur) from erreur
    logger.info("Admin équipes par %s : %s", qui, bilan.phrase())
    return bilan.phrase()


def enregistrer_gars(
    avant: pd.DataFrame, apres: pd.DataFrame, refs: References, qui: str = "?"
) -> str:
    """Applique les changements de gars ; un gars avec historique est désactivé, pas effacé."""
    changements = calculer_changements(avant, apres)
    noms = {int(ligne["id"]): ligne["Nom"] for ligne in avant.to_dict("records")}
    ids_equipes = {e["nom"]: e["id"] for e in refs.equipes}

    def equipe_id(ligne: dict[str, Any]) -> int:
        """Id de l'équipe choisie dans la ligne (obligatoire)."""
        nom = _propre(ligne["Équipe"])
        if nom not in ids_equipes:
            raise ErreurMetier(f"Choisis une équipe pour « {ligne['Nom'] or 'le nouveau gars'} ».")
        return ids_equipes[nom]

    bilan = Bilan()
    try:
        with connexion.ouvrir_connexion() as conn, conn.transaction():
            for gars_id in changements.suppressions:
                if requetes.gars_a_historique(conn, gars_id):
                    requetes.desactiver_gars(conn, gars_id)
                    bilan.desactivations.append(noms[gars_id])
                else:
                    requetes.supprimer_gars(conn, gars_id)
                    bilan.suppressions += 1
            for ligne in changements.modifications:
                requetes.modifier_gars(
                    conn,
                    ligne["id"],
                    _obligatoire(ligne["Nom"], "Le nom du gars"),
                    equipe_id(ligne),
                    _actif(ligne["Actif"]),
                )
                bilan.modifications += 1
            for ligne in changements.ajouts:
                requetes.ajouter_gars(
                    conn,
                    _obligatoire(ligne["Nom"], "Le nom du gars"),
                    equipe_id(ligne),
                    _actif(ligne["Actif"]),
                )
                bilan.ajouts += 1
    except errors.UniqueViolation as erreur:
        raise _traduire_doublon(erreur) from erreur
    logger.info("Admin gars par %s : %s", qui, bilan.phrase())
    return bilan.phrase()


def enregistrer_dossiers(avant: pd.DataFrame, apres: pd.DataFrame, qui: str = "?") -> str:
    """Applique les changements de dossiers ; un dossier avec historique est désactivé."""
    changements = calculer_changements(avant, apres)
    codes = {int(ligne["id"]): ligne["Code"] for ligne in avant.to_dict("records")}
    bilan = Bilan()
    try:
        with connexion.ouvrir_connexion() as conn, conn.transaction():
            for dossier_id in changements.suppressions:
                if requetes.dossier_a_historique(conn, dossier_id):
                    requetes.desactiver_dossier(conn, dossier_id)
                    bilan.desactivations.append(codes[dossier_id])
                else:
                    requetes.supprimer_dossier(conn, dossier_id)
                    bilan.suppressions += 1
            for ligne in changements.modifications:
                requetes.modifier_dossier(
                    conn,
                    ligne["id"],
                    _obligatoire(ligne["Code"], "Le code dossier"),
                    str(ligne["Client"]),
                    str(ligne["Lieu"]),
                    _actif(ligne["Actif"]),
                )
                bilan.modifications += 1
            for ligne in changements.ajouts:
                requetes.ajouter_dossier(
                    conn,
                    _obligatoire(ligne["Code"], "Le code dossier"),
                    str(ligne["Client"]),
                    str(ligne["Lieu"]),
                    _actif(ligne["Actif"]),
                )
                bilan.ajouts += 1
    except errors.UniqueViolation as erreur:
        raise _traduire_doublon(erreur) from erreur
    logger.info("Admin dossiers par %s : %s", qui, bilan.phrase())
    return bilan.phrase()
