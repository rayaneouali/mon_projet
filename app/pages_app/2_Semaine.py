"""Page « Semaine » : la vue agenda (qui était où, absences, samedis, saisies manquantes)."""

from datetime import timedelta

import streamlit as st

import interface
from services import acces, dates, semaine

acces.exiger(acces.ROLE_CHEFS)
st.set_page_config(layout="wide")  # tableau large : on prend toute la largeur sur ordinateur
st.title("📅 Semaine")

ok, refs = interface.essayer(interface.references)
if not ok:
    st.stop()

if "semaine_lundi" not in st.session_state:
    st.session_state["semaine_lundi"] = dates.lundi_de(dates.aujourdhui())


def decaler(semaines: int) -> None:
    """Avance ou recule d'un certain nombre de semaines."""
    st.session_state["semaine_lundi"] += timedelta(weeks=semaines)


def revenir_a_cette_semaine() -> None:
    """Revient à la semaine en cours."""
    st.session_state["semaine_lundi"] = dates.lundi_de(dates.aujourdhui())


# ------------------------------------------------------------------ navigation et filtre
avant, maintenant, apres = st.columns(3)
avant.button("◀ Précédente", on_click=decaler, args=(-1,), width="stretch")
maintenant.button("Cette semaine", on_click=revenir_a_cette_semaine, width="stretch")
apres.button("Suivante ▶", on_click=decaler, args=(1,), width="stretch")

lundi = st.session_state["semaine_lundi"]
st.subheader(f"Du {dates.formater(lundi)} au {dates.formater(lundi + timedelta(days=5))}")

TOUTES = 0
equipe_filtre = st.selectbox(
    "Équipe",
    [TOUTES] + [e["id"] for e in refs.equipes],
    format_func=lambda i: "Toutes les équipes" if i == TOUTES else refs.nom_equipe(i),
    key="semaine_filtre",
)

ok, donnees = interface.essayer(semaine.charger_semaine, lundi)
if not ok:
    st.stop()
saisies, demandes = donnees
vue = semaine.construire_vue(
    lundi, refs, saisies, demandes, dates.aujourdhui(), equipe_filtre or None
)

# ------------------------------------------------------------------ suivi des saisies
st.markdown("#### Saisies des chefs")
st.dataframe(vue.suivi.style.map(semaine.style_suivi, subset=vue.jours), hide_index=True)

# ------------------------------------------------------------------ planning par équipe
st.markdown("#### Planning")
for equipe in semaine.equipes_affichees(refs, equipe_filtre or None):
    chef = f" · chef {equipe['chef']}" if equipe["chef"] else ""
    st.markdown(f"**{equipe['nom']}**{chef}")
    lignes = vue.grille[vue.grille["Équipe"] == equipe["nom"]].drop(columns="Équipe")
    if lignes.empty:
        st.caption("Aucun gars dans cette équipe.")
        continue
    st.dataframe(
        lignes.style.map(semaine.style_case, subset=vue.jours),
        hide_index=True,
        column_config={"Gars": st.column_config.Column(pinned=True)},
    )

# ------------------------------------------------------------------ résumé
st.markdown("#### Résumé de la semaine")
nb_absences = int(vue.absences["Jours"].sum()) if not vue.absences.empty else 0
st.markdown(f"**Absences** ({nb_absences} jour{'s' if nb_absences > 1 else ''})")
if vue.absences.empty:
    st.caption("Aucune absence notée.")
else:
    st.dataframe(vue.absences, hide_index=True)

st.markdown("**Jours-homme par dossier**")
if vue.jours_homme.empty:
    st.caption("Rien de saisi.")
else:
    st.dataframe(vue.jours_homme, hide_index=True)

st.markdown("**Demandes de samedi**")
if vue.samedis.empty:
    st.caption("Aucune demande pour ce samedi.")
else:
    st.dataframe(vue.samedis, hide_index=True)

st.download_button(
    "📥 Exporter la semaine en Excel",
    data=semaine.exporter_excel(vue),
    file_name=f"semaine-{lundi.isoformat()}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    width="stretch",
)
