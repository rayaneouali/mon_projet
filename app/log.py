"""Configuration du logging : une ligne lisible par événement, niveau réglé par LOG_LEVEL."""

import logging

import config

FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
NIVEAUX_VALIDES = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def configurer_logging() -> None:
    """Configure le logger « suivi » (une seule fois, même si Streamlit relance le script)."""
    logger = logging.getLogger("suivi")
    if not logger.handlers:
        sortie = logging.StreamHandler()
        sortie.setFormatter(logging.Formatter(FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(sortie)
        logger.propagate = False
    niveau = config.log_level()
    if niveau not in NIVEAUX_VALIDES:
        logger.setLevel("INFO")
        logger.warning("LOG_LEVEL=%s inconnu, j'utilise INFO", niveau)
        return
    logger.setLevel(niveau)
