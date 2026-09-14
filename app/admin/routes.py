import csv
import io
from datetime import date, time
from functools import wraps

from flask import Blueprint, Response, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Chantier, User
from app.pointage import heures_travaillees_mois
from app.prime import statut_prime_mois, get_regle_prime

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


def _mois_courant_ou_parametre():
    """Lit le mois choisi dans l'URL (?mois=YYYY-MM), sinon le mois actuel."""
    mois_str = request.args.get("mois")
    if mois_str:
        annee, mois = map(int, mois_str.split("-"))
    else:
        aujourdhui = date.today()
        annee, mois = aujourdhui.year, aujourdhui.month
    return annee, mois


@admin_bp.route("/")
@admin_required
def dashboard():
    annee, mois = _mois_courant_ou_parametre()
    chantier_id = request.args.get("chantier_id", type=int)
    user_id_filtre = request.args.get("user_id", type=int)

    ouvriers_query = User.query.filter_by(role="ouvrier")
    if user_id_filtre:
        ouvriers_query = ouvriers_query.filter_by(id=user_id_filtre)
    ouvriers = ouvriers_query.order_by(User.nom).all()

    lignes = []
    for ouvrier in ouvriers:
        heures, jours = heures_travaillees_mois(ouvrier.id, annee, mois, chantier_id=chantier_id)
        statut = statut_prime_mois(ouvrier.id, annee, mois)
        lignes.append({"ouvrier": ouvrier, "heures": heures, "jours": jours, "prime": statut})

    mois_precedent = f"{annee - 1:04d}-12" if mois == 1 else f"{annee:04d}-{mois - 1:02d}"
    mois_suivant = f"{annee + 1:04d}-01" if mois == 12 else f"{annee:04d}-{mois + 1:02d}"

    return render_template(
        "admin/dashboard.html",
        lignes=lignes,
        chantiers=Chantier.query.order_by(Chantier.date.desc()).all(),
        tous_ouvriers=User.query.filter_by(role="ouvrier").order_by(User.nom).all(),
        chantier_id=chantier_id,
        user_id_filtre=user_id_filtre,
        mois_str=f"{annee:04d}-{mois:02d}",
        mois_precedent=mois_precedent,
        mois_suivant=mois_suivant,
    )


@admin_bp.route("/chantiers", methods=["GET", "POST"])
@admin_required
def chantiers():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        date_str = request.form.get("date")

        if not nom or not date_str:
            flash("Le nom et la date sont obligatoires.", "error")
        else:
            debut_str = request.form.get("horaire_debut")
            fin_str = request.form.get("horaire_fin")
            chantier = Chantier(
                nom=nom,
                adresse=request.form.get("adresse", "").strip() or None,
                date=date.fromisoformat(date_str),
                horaire_prevu_debut=time.fromisoformat(debut_str) if debut_str else None,
                horaire_prevu_fin=time.fromisoformat(fin_str) if fin_str else None,
            )
            db.session.add(chantier)
            db.session.commit()
            flash(f"Chantier « {nom} » créé.", "info")
            return redirect(url_for("admin.chantiers"))

    return render_template("admin/chantiers.html", chantiers=Chantier.query.order_by(Chantier.date.desc()).all())


@admin_bp.route("/chantiers/<int:chantier_id>/edit", methods=["GET", "POST"])
@admin_required
def chantier_edit(chantier_id):
    chantier = Chantier.query.get_or_404(chantier_id)

    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        date_str = request.form.get("date")

        if not nom or not date_str:
            flash("Le nom et la date sont obligatoires.", "error")
        else:
            debut_str = request.form.get("horaire_debut")
            fin_str = request.form.get("horaire_fin")
            chantier.nom = nom
            chantier.adresse = request.form.get("adresse", "").strip() or None
            chantier.date = date.fromisoformat(date_str)
            chantier.horaire_prevu_debut = time.fromisoformat(debut_str) if debut_str else None
            chantier.horaire_prevu_fin = time.fromisoformat(fin_str) if fin_str else None
            db.session.commit()
            flash("Chantier mis à jour.", "info")
            return redirect(url_for("admin.chantiers"))

    return render_template("admin/chantier_edit.html", chantier=chantier)


@admin_bp.route("/ouvriers", methods=["GET", "POST"])
@admin_required
def ouvriers():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not nom or not email or not password:
            flash("Nom, email et mot de passe sont obligatoires.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Un compte avec cet email existe déjà.", "error")
        else:
            user = User(nom=nom, email=email, role="ouvrier")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f"Compte créé pour {nom}. Communique-lui son email et son mot de passe.", "info")
            return redirect(url_for("admin.ouvriers"))

    tous = User.query.filter_by(role="ouvrier").order_by(User.nom).all()
    return render_template("admin/ouvriers.html", ouvriers=tous)


@admin_bp.route("/ouvriers/<int:user_id>/toggle", methods=["POST"])
@admin_required
def ouvrier_toggle(user_id):
    ouvrier = User.query.get_or_404(user_id)
    if ouvrier.role != "ouvrier":
        abort(404)

    ouvrier.actif = not ouvrier.actif
    db.session.commit()
    flash(f"Compte de {ouvrier.nom} {'réactivé' if ouvrier.actif else 'désactivé'}.", "info")
    return redirect(url_for("admin.ouvriers"))


@admin_bp.route("/regles", methods=["GET", "POST"])
@admin_required
def regles():
    regle = get_regle_prime()

    if request.method == "POST":
        try:
            tolerance = int(request.form.get("tolerance_retard_min"))
            retards_autorises = int(request.form.get("nb_retards_autorises"))
            pause_max = int(request.form.get("duree_pause_max_min"))
            jours_requis = int(request.form.get("jours_requis_mois"))
        except (TypeError, ValueError):
            flash("Merci de saisir des nombres valides.", "error")
        else:
            regle.tolerance_retard_min = tolerance
            regle.nb_retards_autorises = retards_autorises
            regle.duree_pause_max_min = pause_max
            regle.jours_requis_mois = jours_requis
            db.session.commit()
            flash("Règles de la prime mises à jour.", "info")
            return redirect(url_for("admin.regles"))

    return render_template("admin/regles.html", regle=regle)


@admin_bp.route("/export.csv")
@admin_required
def export_csv():
    annee, mois = _mois_courant_ou_parametre()

    buffer = io.StringIO()
    buffer.write("﻿")  # BOM : pour qu'Excel affiche correctement les accents
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Nom", "Email", "Mois", "Jours travailles", "Heures totales", "Prime acquise"])

    for ouvrier in User.query.filter_by(role="ouvrier").order_by(User.nom).all():
        heures, jours = heures_travaillees_mois(ouvrier.id, annee, mois)
        statut = statut_prime_mois(ouvrier.id, annee, mois)
        writer.writerow(
            [ouvrier.nom, ouvrier.email, f"{annee:04d}-{mois:02d}", jours, heures, "Oui" if statut["acquise"] else "Non"]
        )

    response = Response(buffer.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=heures_{annee:04d}-{mois:02d}.csv"
    return response
