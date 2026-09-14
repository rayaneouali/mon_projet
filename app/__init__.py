import click
from flask import Flask, redirect, url_for
from flask_login import current_user

from config import Config
from app.extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from app.auth.routes import auth_bp
    from app.ouvrier.routes import ouvrier_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(ouvrier_bp)
    app.register_blueprint(admin_bp)

    @app.route("/")
    def index():
        # Page d'accueil : redirige chacun vers son propre espace.
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("ouvrier.home"))

    from app import models  # noqa: F401 (nécessaire pour que SQLAlchemy connaisse les tables)

    register_cli(app)

    return app


def register_cli(app):
    """Commandes à lancer depuis le terminal (flask <commande>)."""

    @app.cli.command("init-db")
    def init_db():
        """Crée les tables dans la base de données (à lancer une seule fois)."""
        db.create_all()
        click.echo("Base de données initialisée.")

    @app.cli.command("seed-admin")
    @click.option("--email", prompt=True)
    @click.option("--nom", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def seed_admin(email, nom, password):
        """Crée le tout premier compte admin (le patron)."""
        from app.models import User

        email = email.strip().lower()
        if User.query.filter_by(email=email).first():
            click.echo("Un compte avec cet email existe déjà.")
            return

        user = User(nom=nom, email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Compte admin créé pour {email}.")
