"""Contrôle d'accès par code partagé.

- CODE_CHEFS : Saisie, Semaine, Samedis.
- CODE_ADMIN : tout, y compris Admin.
Une fois connecté, un « jeton » est mis dans l'adresse de la page (?acces=…) : en ajoutant
la page à l'écran d'accueil du téléphone, le chef n'a plus à retaper le code.
"""

import hashlib
import hmac
import logging
import time

import streamlit as st

import config

logger = logging.getLogger("suivi.services.acces")

ROLE_CHEFS = "chefs"
ROLE_ADMIN = "admin"
NIVEAU = {ROLE_CHEFS: 1, ROLE_ADMIN: 2}
CLE_ADRESSE = "acces"


# ---------------------------------------------------------------- règles (testables sans Streamlit)


def verifier_code(code_saisi: str, code_chefs: str, code_admin: str) -> str | None:
    """Rôle correspondant au code tapé, ou None. Comparaison à temps constant (hmac)."""
    tape = code_saisi.strip().encode()
    if code_admin and hmac.compare_digest(tape, code_admin.encode()):
        return ROLE_ADMIN
    if code_chefs and hmac.compare_digest(tape, code_chefs.encode()):
        return ROLE_CHEFS
    return None


def fabriquer_jeton(role: str, code: str) -> str:
    """Jeton à mettre dans l'adresse : dérivé du code, sans le révéler."""
    message = f"suivi-equipes:{role}".encode()
    return hmac.new(code.encode(), message, hashlib.sha256).hexdigest()[:24]


def role_depuis_jeton(jeton: str, code_chefs: str, code_admin: str) -> str | None:
    """Rôle correspondant au jeton de l'adresse (None s'il est faux ou si le code a changé)."""
    for role, code in ((ROLE_ADMIN, code_admin), (ROLE_CHEFS, code_chefs)):
        if code and hmac.compare_digest(jeton.encode(), fabriquer_jeton(role, code).encode()):
            return role
    return None


def autorise(role: str | None, role_requis: str) -> bool:
    """Vrai si le rôle donne accès à ce qui demande `role_requis` (l'admin peut tout)."""
    return role is not None and NIVEAU[role] >= NIVEAU[role_requis]


def probleme_de_codes(code_chefs: str, code_admin: str) -> str | None:
    """Message si les codes sont mal configurés (absents ou identiques), sinon None."""
    if not code_chefs or not code_admin:
        return "Les codes d'accès ne sont pas configurés (CODE_CHEFS et CODE_ADMIN)."
    if code_chefs.strip() == code_admin.strip():
        return "CODE_CHEFS et CODE_ADMIN sont identiques : tout le monde serait administrateur."
    return None


def probleme_de_configuration() -> str | None:
    """Vérifie les codes lus dans la configuration (voir probleme_de_codes)."""
    return probleme_de_codes(config.code_chefs(), config.code_admin())


# ---------------------------------------------------------------- côté Streamlit


def _code_du_role(role: str) -> str:
    """Code d'accès correspondant à un rôle."""
    return config.code_admin() if role == ROLE_ADMIN else config.code_chefs()


def role_connecte() -> str | None:
    """Rôle de la personne : mémorisé pour la session, ou retrouvé grâce au jeton de l'adresse."""
    if probleme_de_configuration():
        return None  # codes absents ou identiques : personne n'entre
    role = st.session_state.get("role")
    if role:
        return role
    jeton = st.query_params.get(CLE_ADRESSE, "")
    role = role_depuis_jeton(jeton, config.code_chefs(), config.code_admin()) if jeton else None
    if role:
        st.session_state["role"] = role
        logger.info("Connexion par lien mémorisé : rôle %s", role)
    return role


def connecter(code: str) -> bool:
    """Vérifie le code ; s'il est bon, mémorise le rôle et met le jeton dans l'adresse."""
    if probleme_de_configuration():
        return False
    role = verifier_code(code, config.code_chefs(), config.code_admin())
    if role is None:
        logger.warning("Code d'accès incorrect")
        time.sleep(1)  # ralentit quelqu'un qui essaierait des codes au hasard
        return False
    st.session_state["role"] = role
    garder_jeton_dans_adresse(role)
    logger.info("Connexion : rôle %s", role)
    return True


def garder_jeton_dans_adresse(role: str) -> None:
    """Remet le jeton dans l'adresse (changer de page l'efface)."""
    jeton = fabriquer_jeton(role, _code_du_role(role))
    if st.query_params.get(CLE_ADRESSE) != jeton:
        st.query_params[CLE_ADRESSE] = jeton


def deconnecter() -> None:
    """Oublie le rôle et retire le jeton de l'adresse."""
    logger.info("Déconnexion : rôle %s", st.session_state.get("role"))
    st.session_state.pop("role", None)
    st.query_params.pop(CLE_ADRESSE, None)


def exiger(role_requis: str) -> str:
    """À appeler en haut de chaque page : arrête la page si l'accès n'est pas autorisé."""
    role = role_connecte()
    if not autorise(role, role_requis):
        st.error("Accès réservé : entre le bon code d'accès sur la page de connexion.")
        st.stop()
    return role
