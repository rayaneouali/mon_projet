from functools import wraps

from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view_func):
    """Décorateur : bloque l'accès à une page si l'utilisateur n'est pas admin."""

    @wraps(view_func)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped


@admin_bp.route("/")
@admin_required
def dashboard():
    # Étape 3 : ici viendra le tableau de bord (heures par chantier/salarié,
    # gestion des chantiers et des comptes ouvriers, config de la prime, export).
    return render_template("admin/dashboard.html", user=current_user)
