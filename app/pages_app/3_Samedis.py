"""Page « Samedis » : demander à des gars de travailler un samedi, et suivre les réponses."""

import streamlit as st

import interface
from services import dates, samedis

AUCUN_DOSSIER = 0

st.title("🗓️ Samedis")
interface.afficher_message("samedis_message")

ok, refs = interface.essayer(interface.references)
if not ok:
    st.stop()
qui = st.session_state.get("role", "?")


def quand_statut_change(demande_id: int) -> None:
    """Enregistre le nouveau statut choisi dans le menu (appelé avant le rechargement)."""
    statut = st.session_state[f"statut-{demande_id}"]
    ok, _ = interface.essayer(samedis.changer_statut, demande_id, statut, qui=qui)
    if ok:
        interface.noter_message("samedis_message", "Statut mis à jour ✔")


def demander_suppression(demande_id: int) -> None:
    """Retient quelle demande attend une confirmation de suppression."""
    st.session_state["samedi_a_supprimer"] = demande_id


def annuler_suppression() -> None:
    """Abandonne la suppression en attente."""
    st.session_state.pop("samedi_a_supprimer", None)


def confirmer_suppression(demande_id: int) -> None:
    """Supprime pour de bon la demande après confirmation."""
    ok, _ = interface.essayer(samedis.supprimer_demande, demande_id, qui=qui)
    st.session_state.pop("samedi_a_supprimer", None)
    if ok:
        interface.noter_message("samedis_message", "Demande supprimée ✔")


# ------------------------------------------------------------------ nouvelle demande
st.subheader("Demander un samedi")
with st.form("form_samedi", clear_on_submit=True):
    samedi = st.selectbox(
        "Samedi", dates.prochains_samedis(dates.aujourdhui(), 8), format_func=dates.formater
    )
    coches: list[tuple[int, str]] = []
    for equipe in refs.equipes:
        gars_equipe = refs.gars_actifs_de(equipe["id"])
        if not gars_equipe:
            continue
        st.markdown(f"**{equipe['nom']}**")
        for gars in gars_equipe:
            if st.checkbox(gars["nom"], key=f"coche-{gars['id']}"):
                coches.append((gars["id"], gars["nom"]))
    dossier = st.selectbox(
        "Dossier",
        [AUCUN_DOSSIER] + [d["id"] for d in refs.dossiers_actifs()],
        format_func=refs.libelle_dossier,
    )
    note = st.text_input("Note", placeholder="ex : finir l'allée 4, 7h-12h")
    envoye = st.form_submit_button("Enregistrer la demande", type="primary", width="stretch")

if envoye:
    ok, resultat = interface.essayer(
        samedis.creer_demandes, samedi, coches, dossier or None, note, qui=qui
    )
    if ok:
        succes, avertissement = samedis.message_resultat(resultat)
        if succes:
            st.success(succes)
            st.toast(succes)
        if avertissement:
            st.warning(avertissement)
            st.toast(avertissement)

# ------------------------------------------------------------------ demandes existantes
st.subheader("Demandes à venir")
ok, demandes = interface.essayer(samedis.lister_demandes, dates.aujourdhui())
if not ok:
    st.stop()
if not demandes:
    st.caption("Aucune demande.")

aujourdhui = dates.aujourdhui()
statuts = list(samedis.LIBELLES_STATUT)
for jour, demandes_du_jour in samedis.grouper_par_samedi(demandes).items():
    passe = " (passé)" if jour < aujourdhui else ""
    st.markdown(f"#### {dates.formater(jour)}{passe}")
    for demande in demandes_du_jour:
        with st.container(border=True):
            details = [demande["equipe"]]
            if demande["dossier"]:
                details.append(demande["dossier"])
            if demande["note"]:
                details.append(demande["note"])
            st.markdown(f"**{demande['gars']}** · " + " · ".join(details))
            cle = f"statut-{demande['id']}"
            st.session_state[cle] = demande["statut"]  # toujours l'état réel de la base
            menu, bouton = st.columns([3, 1], vertical_alignment="bottom")
            menu.selectbox(
                "Statut",
                statuts,
                format_func=samedis.LIBELLES_STATUT.get,
                key=cle,
                on_change=quand_statut_change,
                args=(demande["id"],),
            )
            bouton.button(
                "Supprimer",
                key=f"suppr-{demande['id']}",
                on_click=demander_suppression,
                args=(demande["id"],),
                width="stretch",
            )
            if st.session_state.get("samedi_a_supprimer") == demande["id"]:
                st.warning(f"Supprimer la demande de {demande['gars']} ?")
                oui, non = st.columns(2)
                oui.button(
                    "Oui, supprimer",
                    type="primary",
                    key=f"oui-{demande['id']}",
                    on_click=confirmer_suppression,
                    args=(demande["id"],),
                    width="stretch",
                )
                non.button(
                    "Annuler",
                    key=f"non-{demande['id']}",
                    on_click=annuler_suppression,
                    width="stretch",
                )
