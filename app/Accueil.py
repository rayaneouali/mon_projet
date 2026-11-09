"""Point d'entrée de l'application Streamlit."""

import streamlit as st

from log import configurer_logging
from services import base

st.set_page_config(page_title="Suivi équipes MDC", page_icon="🏗️")
configurer_logging()

st.title("Suivi des équipes MDC")
ok, message = base.etat_connexion()
if ok:
    st.success(message)
else:
    st.error(message)
