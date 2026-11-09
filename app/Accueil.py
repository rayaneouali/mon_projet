"""Point d'entrée de l'application : prépare la base, vérifie l'accès, affiche le menu.

Streamlit lance CE fichier à chaque interaction ; st.navigation exécute ensuite la page
choisie. Seules les pages autorisées pour le code tapé sont dans le menu : les autres
n'existent tout simplement pas pour cette personne.
"""

import streamlit as st

import interface
from log import configurer_logging
from services import acces

st.set_page_config(page_title="Suivi équipes MDC", page_icon="🏗️")
configurer_logging()
interface.preparer_base_ou_arreter()

SAISIE = st.Page("pages_app/1_Saisie.py", title="Saisie du jour", icon="📝", default=True)
SEMAINE = st.Page("pages_app/2_Semaine.py", title="Semaine", icon="📅")
SAMEDIS = st.Page("pages_app/3_Samedis.py", title="Samedis", icon="🗓️")
ADMIN = st.Page("pages_app/9_Admin.py", title="Admin", icon="⚙️")
CONNEXION = st.Page("pages_app/0_Connexion.py", title="Connexion", icon="🔑", default=True)

role = acces.role_connecte()
if role is None:
    navigation = st.navigation([CONNEXION], position="hidden")
else:
    acces.garder_jeton_dans_adresse(role)
    pages = [SAISIE, SEMAINE, SAMEDIS]
    if acces.autorise(role, acces.ROLE_ADMIN):
        pages.append(ADMIN)
    navigation = st.navigation(pages, position="top")
    with st.sidebar:
        st.success("Base connectée")
        qui = "administrateur" if role == acces.ROLE_ADMIN else "chef d'équipe"
        st.caption(f"Connecté en tant que {qui}")
        if st.button("Se déconnecter"):
            acces.deconnecter()
            st.rerun()

navigation.run()
