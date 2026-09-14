from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        mot_de_passe = request.form.get("mot_de_passe", "")

        user = User.query.filter_by(email=email).first()

        if user is None or not user.actif or not user.check_password(mot_de_passe):
            flash("Email ou mot de passe incorrect.", "error")
        else:
            login_user(user)
            return redirect(url_for("index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Tu as été déconnecté.", "info")
    return redirect(url_for("auth.login"))
