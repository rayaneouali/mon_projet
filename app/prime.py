"""Calcul du statut de la prime d'assiduité d'un ouvrier pour un mois donné.

Quatre critères, tous configurables par l'admin via ReglePrime :
1. Ponctualité   : pas plus de N retards (arrivée après horaire prévu + tolérance)
2. Pauses        : aucune pause au-delà de la durée maximale autorisée
3. Régularité    : au moins X jours travaillés dans le mois

Simplification V1 : comme il n'y a pas de planning d'absences dans l'app,
le critère "présence complète" du brief est fusionné avec la "régularité"
(le nombre de jours travaillés suffisant sert de proxy pour les deux).
"""

from datetime import datetime, timedelta

from app.extensions import db
from app.models import Pointage, ReglePrime
from app.pointage import heures_travaillees_mois


def get_regle_prime():
    """Retourne la configuration de la prime, en la créant avec des valeurs
    par défaut si l'admin ne l'a encore jamais configurée."""
    regle = ReglePrime.query.first()
    if regle is None:
        regle = ReglePrime()
        db.session.add(regle)
        db.session.commit()
    return regle


def statut_prime_mois(user_id, annee, mois):
    """Calcule si la prime d'assiduité est acquise pour un ouvrier sur un
    mois donné, avec le détail de chaque critère (pour affichage)."""
    regle = get_regle_prime()

    debut_mois = datetime(annee, mois, 1)
    fin_mois = datetime(annee + 1, 1, 1) if mois == 12 else datetime(annee, mois + 1, 1)

    pointages = (
        Pointage.query.filter_by(user_id=user_id)
        .filter(Pointage.timestamp >= debut_mois, Pointage.timestamp < fin_mois)
        .order_by(Pointage.timestamp.asc())
        .all()
    )

    # 1. Ponctualité : une arrivée est un retard si elle dépasse l'horaire
    # prévu du chantier + la tolérance.
    nb_retards = 0
    for p in pointages:
        if p.type != "arrivee":
            continue
        if p.chantier is None or p.chantier.horaire_prevu_debut is None:
            continue
        heure_prevue = datetime.combine(p.timestamp.date(), p.chantier.horaire_prevu_debut)
        limite = heure_prevue + timedelta(minutes=regle.tolerance_retard_min)
        if p.timestamp > limite:
            nb_retards += 1
    ok_ponctualite = nb_retards <= regle.nb_retards_autorises

    # 2. Pauses raisonnables : une pause est excessive si elle dépasse la
    # durée maximale ; aucune pause excessive n'est tolérée.
    nb_pauses_excessives = 0
    debut_pause = None
    for p in pointages:
        if p.type == "pause":
            debut_pause = p.timestamp
        elif p.type in ("reprise", "depart") and debut_pause is not None:
            duree_min = (p.timestamp - debut_pause).total_seconds() / 60
            if duree_min > regle.duree_pause_max_min:
                nb_pauses_excessives += 1
            debut_pause = None
    ok_pauses = nb_pauses_excessives == 0

    # 3. Régularité (+ présence complète, simplifiée) : assez de jours travaillés.
    heures_totales, jours_travailles = heures_travaillees_mois(user_id, annee, mois)
    ok_regularite = jours_travailles >= regle.jours_requis_mois

    acquise = ok_ponctualite and ok_pauses and ok_regularite

    return {
        "acquise": acquise,
        "heures_totales": heures_totales,
        "jours_travailles": jours_travailles,
        "jours_requis": regle.jours_requis_mois,
        "ok_regularite": ok_regularite,
        "nb_retards": nb_retards,
        "retards_autorises": regle.nb_retards_autorises,
        "ok_ponctualite": ok_ponctualite,
        "nb_pauses_excessives": nb_pauses_excessives,
        "duree_pause_max_min": regle.duree_pause_max_min,
        "ok_pauses": ok_pauses,
    }
