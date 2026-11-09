"""Aides d'affichage partagées par toutes les pages (erreurs, messages, mémoire de l'équipe).

Ici, pas de règle métier ni de SQL : seulement la façon de montrer les choses à l'écran.
"""

import logging
from collections.abc import Callable
from typing import Any

import streamlit as st

from erreurs import ErreurMetier
from services import base
from services.references import References, charger_references

logger = logging.getLogger("suivi.interface")

MESSAGE_TECHNIQUE = (
    "Problème technique inattendu. Réessaie ; si ça continue, préviens Rayane "
    "(le détail est dans les logs)."
)


def essayer(fonction: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[bool, Any]:
    """Appelle un service ; si erreur : message en français à l'écran et (False, None)."""
    try:
        return True, fonction(*args, **kwargs)
    except ErreurMetier as erreur:
        logger.warning("Refusé : %s", erreur)
        st.error(str(erreur))
    except Exception:
        logger.exception("Erreur inattendue dans %s", getattr(fonction, "__name__", fonction))
        st.error(MESSAGE_TECHNIQUE)
    return False, None


@st.cache_resource(show_spinner="Préparation de la base…")
def _base_prete() -> bool:
    """Applique schema.sql une seule fois par démarrage du serveur (résultat mémorisé)."""
    base.preparer_base()
    return True


def preparer_base_ou_arreter() -> None:
    """Prépare la base au démarrage ; si elle est injoignable, affiche l'erreur et s'arrête."""
    ok, _ = essayer(_base_prete)
    if not ok:
        st.stop()


@st.cache_data(ttl=60, show_spinner=False)
def references() -> References:
    """Équipes, gars et dossiers, gardés 60 s en mémoire (moins d'allers-retours vers la base)."""
    return charger_references()


def oublier_references() -> None:
    """Force la relecture des listes (après une modification dans Admin)."""
    references.clear()


def noter_message(cle: str, texte: str) -> None:
    """Garde un message de succès pour l'afficher après le rechargement de la page."""
    st.session_state[cle] = texte


def afficher_message(cle: str) -> None:
    """Affiche (une seule fois) le message gardé par noter_message."""
    texte = st.session_state.pop(cle, None)
    if texte:
        st.success(texte)
        st.toast(texte)  # visible même si la page est descendue (téléphone)


def equipe_memorisee(ids_equipes: list[int]) -> int:
    """Équipe lue dans l'adresse de la page (?equipe=…), sinon la première de la liste."""
    try:
        equipe_id = int(st.query_params.get("equipe", ""))
    except ValueError:
        return ids_equipes[0]
    return equipe_id if equipe_id in ids_equipes else ids_equipes[0]


def memoriser_equipe(equipe_id: int) -> None:
    """Écrit l'équipe dans l'adresse : un favori ou l'icône d'écran d'accueil la retiendra."""
    if st.query_params.get("equipe") != str(equipe_id):
        st.query_params["equipe"] = str(equipe_id)
