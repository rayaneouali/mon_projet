"""Point d'entrée de l'application Streamlit."""

import streamlit as st

from erreurs import ErreurMetier
from log import configurer_logging
from services import base

st.set_page_config(page_title="Suivi équipes MDC", page_icon="🏗️")
configurer_logging()


@st.cache_resource(show_spinner="Préparation de la base…")
def base_prete() -> bool:
    """Applique schema.sql une seule fois par démarrage du serveur (résultat mémorisé)."""
    base.preparer_base()
    return True


st.title("Suivi des équipes MDC")
try:
    base_prete()
    st.success("Base connectée")
except ErreurMetier as erreur:
    st.error(str(erreur))
