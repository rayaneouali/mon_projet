"""Page « Admin » : gérer les équipes, les gars et les dossiers (réservée au code admin)."""

import streamlit as st

import interface
from services import acces, admin

role = acces.exiger(acces.ROLE_ADMIN)

st.set_page_config(layout="wide")
st.title("⚙️ Administration")
interface.afficher_message("admin_message")

ok, refs = interface.essayer(interface.references)
if not ok:
    st.stop()

# Change à chaque enregistrement : les tableaux repartent alors des données de la base.
version = st.session_state.setdefault("admin_version", 0)


def apres_enregistrement(bilan: str) -> None:
    """Message de succès, listes rafraîchies, tableaux remis à zéro."""
    interface.oublier_references()
    st.session_state["admin_version"] += 1
    interface.noter_message("admin_message", bilan)
    st.rerun()


st.caption(
    "Modifie directement dans les tableaux (double-clic sur une case). Pour ajouter une "
    "ligne : « + » en haut à droite du tableau, ou la ligne vide du bas. Puis clique sur "
    "Enregistrer. Supprimer un gars ou un dossier qui a déjà servi le passe en **inactif** "
    "(son historique est gardé)."
)
onglet_equipes, onglet_gars, onglet_dossiers = st.tabs(["Équipes", "Gars", "Dossiers"])

with onglet_equipes:
    avant = admin.tableau_equipes(refs)
    apres = st.data_editor(
        avant,
        key=f"editeur-equipes-{version}",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "id": None,  # colonne cachée : elle sert à reconnaître les lignes
            "Nom": st.column_config.TextColumn("Nom"),
            "Chef": st.column_config.TextColumn("Chef"),
        },
    )
    if st.button("Enregistrer les équipes", type="primary"):
        ok, bilan = interface.essayer(admin.enregistrer_equipes, avant, apres, qui=role)
        if ok:
            apres_enregistrement(bilan)

with onglet_gars:
    if not refs.equipes:
        st.info("Crée d'abord une équipe dans l'onglet « Équipes ».")
    avant = admin.tableau_gars(refs)
    apres = st.data_editor(
        avant,
        key=f"editeur-gars-{version}",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "id": None,
            "Nom": st.column_config.TextColumn("Nom"),
            "Équipe": st.column_config.SelectboxColumn(
                "Équipe", options=[e["nom"] for e in refs.equipes]
            ),
            "Actif": st.column_config.CheckboxColumn("Actif", default=True),
        },
    )
    if st.button("Enregistrer les gars", type="primary"):
        ok, bilan = interface.essayer(admin.enregistrer_gars, avant, apres, refs, qui=role)
        if ok:
            apres_enregistrement(bilan)

with onglet_dossiers:
    avant = admin.tableau_dossiers(refs)
    apres = st.data_editor(
        avant,
        key=f"editeur-dossiers-{version}",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "id": None,
            "Code": st.column_config.TextColumn("Code"),
            "Client": st.column_config.TextColumn("Client"),
            "Lieu": st.column_config.TextColumn("Lieu"),
            "Actif": st.column_config.CheckboxColumn("Actif", default=True),
        },
    )
    if st.button("Enregistrer les dossiers", type="primary"):
        ok, bilan = interface.essayer(admin.enregistrer_dossiers, avant, apres, qui=role)
        if ok:
            apres_enregistrement(bilan)
