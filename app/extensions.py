# Ce fichier centralise les "outils" partagés par toute l'application
# (base de données, gestion des connexions), pour éviter les imports circulaires
# entre app/__init__.py et app/models.py.

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Merci de te connecter pour accéder à cette page."
