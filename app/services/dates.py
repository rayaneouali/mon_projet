"""Dates : jour courant à Paris, semaines du lundi au dimanche, affichage « lun. 9 nov. »."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

FUSEAU = ZoneInfo("Europe/Paris")
JOURS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin"]
MOIS += ["juil.", "août", "sept.", "oct.", "nov.", "déc."]
SAMEDI = 5  # date.weekday() : lundi = 0 … samedi = 5, dimanche = 6


def aujourdhui() -> date:
    """Date du jour à Paris (le serveur en ligne, lui, est à l'heure UTC)."""
    return datetime.now(FUSEAU).date()


def lundi_de(jour: date) -> date:
    """Lundi de la semaine qui contient ce jour."""
    return jour - timedelta(days=jour.weekday())


def jours_de_la_semaine(lundi: date, avec_dimanche: bool = False) -> list[date]:
    """Les jours du lundi au samedi (ou au dimanche)."""
    nombre = 7 if avec_dimanche else 6
    return [lundi + timedelta(days=i) for i in range(nombre)]


def formater(jour: date) -> str:
    """Affiche une date comme « lun. 9 nov. »."""
    return f"{JOURS[jour.weekday()]} {jour.day} {MOIS[jour.month - 1]}"


def est_jour_ouvre(jour: date) -> bool:
    """Vrai du lundi au vendredi."""
    return jour.weekday() < SAMEDI


def est_samedi(jour: date) -> bool:
    """Vrai si le jour est un samedi."""
    return jour.weekday() == SAMEDI


def prochains_samedis(depuis: date, nombre: int = 8) -> list[date]:
    """Les `nombre` prochains samedis (aujourd'hui compris si c'est un samedi)."""
    premier = depuis + timedelta(days=(SAMEDI - depuis.weekday()) % 7)
    return [premier + timedelta(weeks=i) for i in range(nombre)]
