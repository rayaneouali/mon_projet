from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Chantier, Pointage
from app.pointage import etat_actuel, heures_travaillees_mois

ouvrier_bp = Blueprint("ouvrier", __name__, url_prefix="/ouvrier")


@ouvrier_bp.route("/")
@login_required
def home():
    etat, chantier_actif = etat_actuel(current_user.id)

    chantiers_du_jour = []
    if etat == "pas_arrive":
        chantiers_du_jour = (
            Chantier.query.filter_by(date=date.today()).order_by(Chantier.nom).all()
        )

    aujourdhui = date.today()
    heures_mois, jours_mois = heures_travaillees_mois(
        current_user.id, aujourdhui.year, aujourdhui.month
    )

    return render_template(
        "ouvrier/home.html",
        etat=etat,
        chantier_actif=chantier_actif,
        chantiers_du_jour=chantiers_du_jour,
        heures_mois=heures_mois,
        jours_mois=jours_mois,
    )


def _enregistrer(type_action, etat_attendu):
    """Enregistre un pointage, après avoir vérifié que l'ouvrier est bien
    dans l'état attendu (protège contre un double clic ou un bouton
    rafraîchi qui n'est plus valable)."""
    etat, chantier_actif = etat_actuel(current_user.id)
    if etat != etat_attendu:
        flash("Action impossible : ta situation a changé, la page a été rafraîchie.", "error")
        return redirect(url_for("ouvrier.home"))

    if type_action == "arrivee":
        chantier_id = request.form.get("chantier_id", type=int)
        if not chantier_id:
            flash("Merci de choisir un chantier.", "error")
            return redirect(url_for("ouvrier.home"))
    else:
        chantier_id = chantier_actif.id

    db.session.add(Pointage(user_id=current_user.id, chantier_id=chantier_id, type=type_action))
    db.session.commit()
    return redirect(url_for("ouvrier.home"))


@ouvrier_bp.route("/arrivee", methods=["POST"])
@login_required
def arrivee():
    return _enregistrer("arrivee", "pas_arrive")


@ouvrier_bp.route("/pause", methods=["POST"])
@login_required
def pause():
    return _enregistrer("pause", "sur_chantier")


@ouvrier_bp.route("/reprise", methods=["POST"])
@login_required
def reprise():
    return _enregistrer("reprise", "en_pause")


@ouvrier_bp.route("/depart", methods=["POST"])
@login_required
def depart():
    return _enregistrer("depart", "sur_chantier")
