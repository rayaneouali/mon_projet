"""Page de connexion : on tape le code d'accès (chefs ou admin)."""

import streamlit as st

from services import acces, base

st.title("🏗️ Suivi des équipes MDC")

ok, message = base.etat_connexion()
if ok:
    st.success(message)
else:
    st.error(message)

probleme = acces.probleme_de_configuration()
if probleme:
    st.error(probleme + " Voir docs/mise_en_ligne.md.")
    st.stop()

with st.form("form_connexion"):
    code = st.text_input("Code d'accès", type="password", max_chars=20)
    entrer = st.form_submit_button("Entrer", type="primary", width="stretch")

if entrer:
    if acces.connecter(code):
        st.rerun()
    else:
        st.error("Code incorrect.")

st.caption(
    "Astuce : une fois entré, ajoute cette page à l'écran d'accueil du téléphone "
    "(menu Partager › « Sur l'écran d'accueil ») : tu n'auras plus à retaper le code."
)
