"""Point d'entrée de l'application : prépare la base puis affiche le menu des pages.

Streamlit lance CE fichier à chaque interaction ; st.navigation choisit ensuite la page
à exécuter (Saisie, Semaine…).
"""

import streamlit as st

import interface
from log import configurer_logging

st.set_page_config(page_title="Suivi équipes MDC", page_icon="🏗️")
configurer_logging()
interface.preparer_base_ou_arreter()

pages = [st.Page("pages/1_Saisie.py", title="Saisie du jour", icon="📝", default=True)]
navigation = st.navigation(pages, position="top")
st.sidebar.success("Base connectée")
navigation.run()
