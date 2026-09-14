"""Logique métier du pointage : déterminer l'état d'un ouvrier et calculer
ses heures travaillées. Regroupé ici (plutôt que dans les routes) pour que
l'étape 3 (tableau de bord admin) puisse réutiliser les mêmes fonctions.
"""

from datetime import datetime, timedelta

from app.models import Pointage


def etat_actuel(user_id):
    """Retourne (etat, chantier_actif) pour un ouvrier donné.

    etat vaut "pas_arrive", "sur_chantier" ou "en_pause".
    chantier_actif est l'objet Chantier concerné (ou None si pas_arrive).
    """
    dernier = (
        Pointage.query.filter_by(user_id=user_id)
        .order_by(Pointage.timestamp.desc())
        .first()
    )

    if dernier is None or dernier.type == "depart":
        return "pas_arrive", None
    if dernier.type == "pause":
        return "en_pause", dernier.chantier
    # dernier.type est "arrivee" ou "reprise" -> il est sur le chantier
    return "sur_chantier", dernier.chantier


def heures_travaillees_mois(user_id, annee, mois, chantier_id=None):
    """Calcule le nombre d'heures travaillées et de jours travaillés sur un
    mois donné, pauses déduites. Si chantier_id est fourni, ne compte que
    les heures faites sur ce chantier précis.

    Principe : on parcourt les pointages du mois, du plus ancien au plus
    récent. "arrivee" ou "reprise" ouvre un segment de travail ; "pause" ou
    "depart" le referme et on ajoute sa durée au total.
    """
    debut_mois = datetime(annee, mois, 1)
    fin_mois = datetime(annee + 1, 1, 1) if mois == 12 else datetime(annee, mois + 1, 1)

    query = Pointage.query.filter_by(user_id=user_id).filter(
        Pointage.timestamp >= debut_mois, Pointage.timestamp < fin_mois
    )
    if chantier_id:
        query = query.filter_by(chantier_id=chantier_id)

    pointages = query.order_by(Pointage.timestamp.asc()).all()

    total = timedelta()
    jours_travailles = set()
    debut_segment = None

    for p in pointages:
        if p.type in ("arrivee", "reprise"):
            debut_segment = p.timestamp
            jours_travailles.add(p.timestamp.date())
        elif p.type in ("pause", "depart") and debut_segment is not None:
            total += p.timestamp - debut_segment
            debut_segment = None

    heures = round(total.total_seconds() / 3600, 2)
    return heures, len(jours_travailles)
