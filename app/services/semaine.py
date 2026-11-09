"""Vue « Semaine » : construit les tableaux (pandas DataFrame) à partir des saisies.

Tout ici est du calcul pur (sauf charger_semaine) : facile à tester avec des données
fabriquées à la main, et la page n'a plus qu'à afficher.
"""

import zlib
from dataclasses import dataclass
from datetime import date, timedelta
from io import BytesIO
from typing import Any

import pandas as pd

from db import connexion, requetes
from services import dates
from services.references import References
from services.samedis import LIBELLES_STATUT

VIDE = "—"
SAISI = "✔ saisi"
MANQUANT = "✗ manquant"
# Paires (fond, texte) : un dossier garde toujours la même couleur.
COULEURS = [
    ("#e6f0ff", "#1f4e8c"),
    ("#e7f6ee", "#17663b"),
    ("#fff1dc", "#8a5a00"),
    ("#f3e8fd", "#6b2fa3"),
    ("#e2f6f8", "#0d6670"),
    ("#fde9f1", "#a12a5e"),
    ("#eef0d9", "#5c6410"),
    ("#ececec", "#444444"),
]
COULEURS_SAMEDI = {
    "Demandé": ("#fff4dc", "#b7791f"),
    "Accepté": ("#e3f4ea", "#1d8a4e"),
    "Refusé": ("#fde8e6", "#c0392b"),
    "Fait": ("#e6ecf7", "#1f4e8c"),
}
Ligne = dict[str, Any]


@dataclass
class VueSemaine:
    """Tous les tableaux de la page Semaine."""

    jours: list[str]  # en-têtes des colonnes jour : « lun. 9 nov. »…
    grille: pd.DataFrame  # une ligne par gars : Équipe, Gars, puis un jour par colonne
    suivi: pd.DataFrame  # une ligne par équipe : saisi / manquant par jour
    absences: pd.DataFrame
    jours_homme: pd.DataFrame
    samedis: pd.DataFrame


def charger_semaine(lundi: date) -> tuple[list[Ligne], list[Ligne]]:
    """Lit les saisies et les demandes de samedi du lundi au dimanche."""
    dimanche = lundi + timedelta(days=6)
    with connexion.ouvrir_connexion() as conn:
        saisies = requetes.lire_saisies_periode(conn, lundi, dimanche)
        demandes = requetes.lister_demandes_samedi(conn, lundi, dimanche)
    return saisies, demandes


# ---------------------------------------------------------------- petites règles


def colonnes_jours(lundi: date, saisies: list[Ligne]) -> list[date]:
    """Lundi → samedi, plus le dimanche seulement si quelqu'un a été saisi ce jour-là."""
    dimanche = lundi + timedelta(days=6)
    avec_dimanche = any(s["date"] == dimanche for s in saisies)
    return dates.jours_de_la_semaine(lundi, avec_dimanche)


def texte_case(saisie: Ligne | None, equipe_du_gars: int, demande: Ligne | None) -> str:
    """Contenu d'une case : code dossier, « ABS · motif », « — », + statut du samedi."""
    if saisie is None:
        texte = VIDE
    elif saisie["statut"] == "absent":
        texte = f"ABS · {saisie['motif']}" if saisie["motif"] else "ABS"
    else:
        texte = saisie["dossier"] or "Présent"
        if saisie["equipe_id"] != equipe_du_gars:
            texte += f" · avec {saisie['equipe']}"
    if demande:
        statut = f"Samedi : {LIBELLES_STATUT[demande['statut']]}"
        texte = statut if texte == VIDE else f"{texte} · {statut}"
    return texte


def gars_a_afficher(refs: References, equipe_id: int, saisies: list[Ligne]) -> list[Ligne]:
    """Gars actifs de l'équipe + gars devenus inactifs mais présents dans la semaine."""
    vus_cette_semaine = {s["gars_id"] for s in saisies}
    return [
        g
        for g in refs.gars
        if g["equipe_id"] == equipe_id and (g["actif"] or g["id"] in vus_cette_semaine)
    ]


def equipes_affichees(refs: References, equipe_filtre: int | None) -> list[Ligne]:
    """Toutes les équipes, ou seulement celle du filtre."""
    return [e for e in refs.equipes if equipe_filtre in (None, e["id"])]


# ---------------------------------------------------------------- tableaux


def construire_grille(
    lundi: date,
    refs: References,
    saisies: list[Ligne],
    demandes: list[Ligne],
    equipe_filtre: int | None = None,
) -> pd.DataFrame:
    """Tableau gars × jours, regroupé par équipe."""
    jours = colonnes_jours(lundi, saisies)
    samedi = lundi + timedelta(days=dates.SAMEDI)
    par_gars_et_jour = {(s["gars_id"], s["date"]): s for s in saisies}
    demande_du_gars = {d["gars_id"]: d for d in demandes if d["samedi"] == samedi}
    lignes = []
    for equipe in equipes_affichees(refs, equipe_filtre):
        for gars in gars_a_afficher(refs, equipe["id"], saisies):
            ligne = {"Équipe": equipe["nom"], "Gars": gars["nom"]}
            for jour in jours:
                demande = demande_du_gars.get(gars["id"]) if jour == samedi else None
                saisie = par_gars_et_jour.get((gars["id"], jour))
                ligne[dates.formater(jour)] = texte_case(saisie, equipe["id"], demande)
            lignes.append(ligne)
    colonnes = ["Équipe", "Gars"] + [dates.formater(jour) for jour in jours]
    return pd.DataFrame(lignes, columns=colonnes)


def etat_saisie_equipe(
    equipe_id: int, jour: date, saisies: list[Ligne], aujourdhui: date, a_des_gars: bool
) -> str:
    """« ✔ saisi », « ✗ manquant » (jour ouvré passé sans saisie) ou vide."""
    if any(s["equipe_id"] == equipe_id and s["date"] == jour for s in saisies):
        return SAISI
    if a_des_gars and dates.est_jour_ouvre(jour) and jour <= aujourdhui:
        return MANQUANT
    return ""


def construire_suivi(
    lundi: date,
    refs: References,
    saisies: list[Ligne],
    aujourdhui: date,
    equipe_filtre: int | None = None,
) -> pd.DataFrame:
    """Une ligne par équipe : qui a fait sa saisie, quel jour (pour savoir qui relancer)."""
    jours = colonnes_jours(lundi, saisies)
    lignes = []
    for equipe in equipes_affichees(refs, equipe_filtre):
        a_des_gars = bool(refs.gars_actifs_de(equipe["id"]))
        ligne = {"Équipe": equipe["nom"], "Chef": equipe["chef"]}
        for jour in jours:
            ligne[dates.formater(jour)] = etat_saisie_equipe(
                equipe["id"], jour, saisies, aujourdhui, a_des_gars
            )
        lignes.append(ligne)
    return pd.DataFrame(lignes, columns=["Équipe", "Chef"] + [dates.formater(j) for j in jours])


def filtrer(saisies: list[Ligne], equipe_filtre: int | None) -> list[Ligne]:
    """Garde les saisies faites dans l'équipe filtrée (toutes si pas de filtre)."""
    return [s for s in saisies if equipe_filtre in (None, s["equipe_id"])]


def resume_absences(saisies: list[Ligne], equipe_filtre: int | None = None) -> pd.DataFrame:
    """Absences de la semaine par gars : dates et motifs."""
    par_gars: dict[str, list[str]] = {}
    for s in filtrer(saisies, equipe_filtre):
        if s["statut"] == "absent":
            detail = dates.formater(s["date"]) + (f" ({s['motif']})" if s["motif"] else "")
            par_gars.setdefault(s["gars"], []).append(detail)
    lignes = [
        {"Gars": gars, "Jours": len(details), "Absences": ", ".join(details)}
        for gars, details in sorted(par_gars.items())
    ]
    return pd.DataFrame(lignes, columns=["Gars", "Jours", "Absences"])


def jours_homme_par_dossier(saisies: list[Ligne], equipe_filtre: int | None = None) -> pd.DataFrame:
    """Nombre de jours-homme (présents) par dossier, du plus gros au plus petit."""
    compte: dict[str, int] = {}
    for s in filtrer(saisies, equipe_filtre):
        if s["statut"] == "present" and s["dossier"]:
            compte[s["dossier"]] = compte.get(s["dossier"], 0) + 1
    lignes = [{"Dossier": code, "Jours-homme": n} for code, n in compte.items()]
    tableau = pd.DataFrame(lignes, columns=["Dossier", "Jours-homme"])
    return tableau.sort_values(
        ["Jours-homme", "Dossier"], ascending=[False, True], ignore_index=True
    )


def tableau_samedis(
    demandes: list[Ligne], refs: References, equipe_filtre: int | None = None
) -> pd.DataFrame:
    """Demandes de samedi de la semaine (gars de l'équipe filtrée)."""
    nom_filtre = refs.nom_equipe(equipe_filtre) if equipe_filtre else None
    lignes = [
        {
            "Samedi": dates.formater(d["samedi"]),
            "Gars": d["gars"],
            "Équipe": d["equipe"],
            "Dossier": d["dossier"] or "",
            "Statut": LIBELLES_STATUT[d["statut"]],
            "Note": d["note"],
        }
        for d in demandes
        if nom_filtre in (None, d["equipe"])
    ]
    return pd.DataFrame(lignes, columns=["Samedi", "Gars", "Équipe", "Dossier", "Statut", "Note"])


def construire_vue(
    lundi: date,
    refs: References,
    saisies: list[Ligne],
    demandes: list[Ligne],
    aujourdhui: date,
    equipe_filtre: int | None = None,
) -> VueSemaine:
    """Assemble tous les tableaux de la page Semaine."""
    return VueSemaine(
        jours=[dates.formater(jour) for jour in colonnes_jours(lundi, saisies)],
        grille=construire_grille(lundi, refs, saisies, demandes, equipe_filtre),
        suivi=construire_suivi(lundi, refs, saisies, aujourdhui, equipe_filtre),
        absences=resume_absences(saisies, equipe_filtre),
        jours_homme=jours_homme_par_dossier(saisies, equipe_filtre),
        samedis=tableau_samedis(demandes, refs, equipe_filtre),
    )


# ---------------------------------------------------------------- couleurs et export


def couleur_dossier(code: str) -> tuple[str, str]:
    """Couleur (fond, texte) stable d'un dossier : le même code donne toujours la même couleur."""
    # zlib.crc32 donne toujours le même nombre pour le même texte (hash() de Python, non).
    return COULEURS[zlib.crc32(code.encode("utf-8")) % len(COULEURS)]


def style_case(texte: str) -> str:
    """Style CSS d'une case du planning (rouge pour ABS, couleur du dossier…)."""
    if texte.startswith("ABS"):
        return "background-color: #fde8e6; color: #c0392b; font-weight: bold"
    if texte in ("", VIDE):
        return "color: #c3c9d3"
    if texte.startswith("Samedi : "):
        fond, encre = COULEURS_SAMEDI.get(texte.removeprefix("Samedi : "), COULEURS[-1])
        return f"background-color: {fond}; color: {encre}"
    if texte.startswith("Présent"):
        return "background-color: #e3f4ea; color: #1d8a4e"
    fond, encre = couleur_dossier(texte.split(" · ")[0])
    return f"background-color: {fond}; color: {encre}; font-weight: bold"


def style_suivi(texte: str) -> str:
    """Style CSS d'une case du suivi des saisies (vert = saisi, rouge = manquant)."""
    if texte == SAISI:
        return "color: #1d8a4e"
    if texte == MANQUANT:
        return "background-color: #fde8e6; color: #c0392b; font-weight: bold"
    return ""


def exporter_excel(vue: VueSemaine) -> bytes:
    """Fichier Excel de la semaine (un onglet par tableau, couleurs du planning conservées)."""
    tampon = BytesIO()
    with pd.ExcelWriter(tampon, engine="openpyxl") as classeur:
        planning = vue.grille.style.map(style_case, subset=vue.jours)
        planning.to_excel(classeur, sheet_name="Planning", index=False)
        vue.suivi.style.map(style_suivi, subset=vue.jours).to_excel(
            classeur, sheet_name="Saisies des chefs", index=False
        )
        vue.absences.to_excel(classeur, sheet_name="Absences", index=False)
        vue.jours_homme.to_excel(classeur, sheet_name="Jours-homme", index=False)
        vue.samedis.to_excel(classeur, sheet_name="Samedis", index=False)
        for feuille in classeur.sheets.values():
            for colonne in feuille.columns:
                feuille.column_dimensions[colonne[0].column_letter].width = 22
    return tampon.getvalue()
