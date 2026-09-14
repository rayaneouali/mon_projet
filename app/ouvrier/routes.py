from flask import Blueprint, render_template
from flask_login import login_required, current_user

ouvrier_bp = Blueprint("ouvrier", __name__, url_prefix="/ouvrier")


@ouvrier_bp.route("/")
@login_required
def home():
    # Étape 2 : ici viendra l'écran de pointage (arrivée / pause / reprise / départ)
    # et le résumé mensuel (jours travaillés, heures, statut prime).
    return render_template("ouvrier/home.html", user=current_user)
