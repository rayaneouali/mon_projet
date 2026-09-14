from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager


class User(db.Model, UserMixin):
    """Un utilisateur : soit un ouvrier, soit l'admin (le patron)."""

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mot_de_passe_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="ouvrier")  # "ouvrier" ou "admin"
    actif = db.Column(db.Boolean, nullable=False, default=True)

    def set_password(self, mot_de_passe):
        self.mot_de_passe_hash = generate_password_hash(mot_de_passe)

    def check_password(self, mot_de_passe):
        return check_password_hash(self.mot_de_passe_hash, mot_de_passe)

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Chantier(db.Model):
    """Un chantier sur lequel les ouvriers peuvent pointer."""

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    adresse = db.Column(db.String(255))
    date = db.Column(db.Date, nullable=False)
    horaire_prevu_debut = db.Column(db.Time)
    horaire_prevu_fin = db.Column(db.Time)

    def __repr__(self):
        return f"<Chantier {self.nom} le {self.date}>"


class Pointage(db.Model):
    """Un événement horodaté : un ouvrier fait une action sur un chantier."""

    TYPES = ("arrivee", "pause", "reprise", "depart")

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    chantier_id = db.Column(db.Integer, db.ForeignKey("chantier.id"), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", backref="pointages")
    chantier = db.relationship("Chantier", backref="pointages")

    def __repr__(self):
        return f"<Pointage {self.type} user={self.user_id} chantier={self.chantier_id}>"


class ReglePrime(db.Model):
    """Configuration globale des seuils de la prime d'assiduité.

    V1 : une seule ligne de configuration valable pour tout le monde.
    On pourra la décliner par salarié plus tard si besoin.
    """

    id = db.Column(db.Integer, primary_key=True)
    tolerance_retard_min = db.Column(db.Integer, nullable=False, default=10)
    duree_pause_max_min = db.Column(db.Integer, nullable=False, default=45)
    jours_requis_mois = db.Column(db.Integer, nullable=False, default=20)

    def __repr__(self):
        return "<ReglePrime config>"
