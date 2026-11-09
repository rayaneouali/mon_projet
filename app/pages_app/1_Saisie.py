"""Page « Saisie du jour » : le chef d'équipe note qui est là, depuis son téléphone.

Rappel Streamlit : tout ce fichier est ré-exécuté de haut en bas à CHAQUE interaction.
- st.session_state garde la mémoire entre deux exécutions (la saisie en cours) ;
- st.form regroupe les menus « Présent / Absent » : la page ne se recharge qu'au clic
  sur « Enregistrer », pas à chaque menu touché.
"""

from datetime import date

import streamlit as st

import interface
from services import acces, dates, saisie
from services.references import References

AUCUN_DOSSIER = 0  # valeur du menu pour « Aucun dossier » (aucun id de la base ne vaut 0)

role = acces.exiger(acces.ROLE_CHEFS)
st.title("📝 Saisie du jour")
interface.afficher_message("saisie_message")


def cle_choix(contexte: str, gars_id: int) -> str:
    """Nom unique du menu Présent/Absent d'un gars pour ce jour et cette équipe."""
    return f"choix-{contexte}-{gars_id}"


def libelle_gars(refs: References, gars_id: int, equipe_id: int) -> str:
    """Nom du gars, avec son équipe s'il vient en renfort."""
    gars = refs.un_gars(gars_id)
    if not gars["actif"]:
        return f"{gars['nom']} (inactif)"
    if gars["equipe_id"] != equipe_id:
        return f"{gars['nom']} ({gars['equipe']})"
    return gars["nom"]


def preparer_widgets(contexte: str, etat: saisie.EtatSaisie) -> None:
    """Remplit la mémoire de la page avec la saisie chargée (avant d'afficher les menus)."""
    st.session_state["saisie_contexte"] = contexte
    st.session_state["saisie_etat"] = etat
    st.session_state["saisie_gars"] = [ligne.gars_id for ligne in etat.lignes]
    st.session_state["saisie_dossier"] = etat.dossier_id or AUCUN_DOSSIER
    for ligne in etat.lignes:
        st.session_state[cle_choix(contexte, ligne.gars_id)] = saisie.ligne_vers_choix(ligne)
    st.session_state.pop("saisie_confirmer", None)


def enregistrer(
    jour: date, equipe_id: int, dossier_id: int | None, lignes: list[saisie.LigneSaisie]
) -> None:
    """Enregistre via le service, puis recharge la page avec un message de succès."""
    ok, nombre = interface.essayer(
        saisie.enregistrer_saisie,
        jour,
        equipe_id,
        dossier_id,
        lignes,
        dates.aujourdhui(),
        qui=role,
        nom_equipe=refs.nom_equipe(equipe_id),
    )
    if ok:
        interface.noter_message("saisie_message", f"Enregistré : {nombre} gars ✔")
        st.session_state.pop("saisie_contexte", None)  # force le rechargement depuis la base
        st.session_state.pop("saisie_confirmer", None)
        st.rerun()


# ------------------------------------------------------------------ données de base
ok, refs = interface.essayer(interface.references)
if not ok:
    st.stop()
if not refs.equipes:
    st.info("Aucune équipe pour l'instant : il faut d'abord en créer dans la page Admin.")
    st.stop()

# ------------------------------------------------------------------ date et équipe
aujourdhui = dates.aujourdhui()
ids_equipes = [e["id"] for e in refs.equipes]
if st.session_state.get("saisie_equipe") not in ids_equipes:
    st.session_state["saisie_equipe"] = interface.equipe_memorisee(ids_equipes)

jour = st.date_input(
    "Date", value=aujourdhui, max_value=aujourdhui, format="DD/MM/YYYY", key="saisie_jour"
)
equipe_id = st.selectbox("Équipe", ids_equipes, format_func=refs.nom_equipe, key="saisie_equipe")
interface.memoriser_equipe(equipe_id)

contexte = f"{jour.isoformat()}-{equipe_id}"
if st.session_state.get("saisie_contexte") != contexte:
    actifs = [g["id"] for g in refs.gars_actifs_de(equipe_id)]
    ok, etat_charge = interface.essayer(saisie.charger_saisie, jour, equipe_id, actifs)
    if not ok:
        st.stop()
    preparer_widgets(contexte, etat_charge)
etat: saisie.EtatSaisie = st.session_state["saisie_etat"]

if etat.deja_saisi:
    st.success("Déjà saisi pour ce jour : tu peux corriger puis ré-enregistrer.", icon="✔")
else:
    st.info(f"Pas encore de saisie pour {refs.nom_equipe(equipe_id)} le {dates.formater(jour)}")

# ------------------------------------------------------------------ qui est dans la saisie
# Un gars supprimé dans Admin entre-temps est retiré de la liste (sinon la page planterait).
st.session_state["saisie_gars"] = saisie.retirer_gars_inconnus(
    st.session_state["saisie_gars"], [g["id"] for g in refs.gars]
)
options = [g["id"] for g in refs.gars_actifs()]
options += [gid for gid in st.session_state["saisie_gars"] if gid not in options]
gars_ids: list[int] = st.multiselect(
    "Gars de la saisie (ajoute un renfort ou retire quelqu'un)",
    options,
    format_func=lambda gid: libelle_gars(refs, gid, equipe_id),
    placeholder="Choisis les gars…",
    key="saisie_gars",
)
if not gars_ids:
    st.warning("Aucun gars : ajoute au moins un gars dans la liste ci-dessus.")

# ------------------------------------------------------------------ le formulaire
dossiers = [AUCUN_DOSSIER] + [d["id"] for d in refs.dossiers_actifs()]
if st.session_state.get("saisie_dossier") not in dossiers:
    dossiers.append(st.session_state["saisie_dossier"])  # dossier fermé depuis, mais déjà saisi

# Après un premier « Enregistrer » sans dossier, un 2e bouton apparaît DANS le formulaire :
# ainsi, c'est bien la saisie affichée (avec les dernières corrections) qui est enregistrée.
attente_confirmation = st.session_state.get("saisie_confirmer") == contexte

with st.form("form_saisie"):
    st.selectbox(
        "Dossier / chantier", dossiers, format_func=refs.libelle_dossier, key="saisie_dossier"
    )
    st.markdown("**Qui est là ?**")
    for gars_id in gars_ids:
        st.selectbox(refs.un_gars(gars_id)["nom"], saisie.CHOIX, key=cle_choix(contexte, gars_id))
        if gars_id in etat.ailleurs:
            st.warning(
                f"Déjà noté dans {etat.ailleurs[gars_id]} ce jour-là : enregistrer le déplace ici.",
                icon="⚠️",
            )
    confirme = False
    if attente_confirmation:
        st.warning("Aucun dossier choisi alors qu'il y a des présents. Choisis un dossier, ou :")
        confirme = st.form_submit_button(
            "Oui, enregistrer sans dossier", type="primary", width="stretch"
        )
    envoye = st.form_submit_button(
        "Enregistrer", type="secondary" if attente_confirmation else "primary", width="stretch"
    )

if envoye or confirme:
    lignes = [
        saisie.choix_vers_ligne(gid, st.session_state.get(cle_choix(contexte, gid), saisie.PRESENT))
        for gid in gars_ids
    ]
    dossier_id = st.session_state["saisie_dossier"] or None  # AUCUN_DOSSIER (0) → None
    if envoye and saisie.besoin_confirmation(dossier_id, lignes):
        st.session_state["saisie_confirmer"] = contexte
        st.rerun()
    else:
        enregistrer(jour, equipe_id, dossier_id, lignes)
