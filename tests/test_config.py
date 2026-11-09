"""Tests de la lecture de configuration et du logging."""

import logging

import pytest

import config
import log


def test_lire_prend_la_variable_d_environnement(monkeypatch: pytest.MonkeyPatch) -> None:
    """Une variable d'environnement définie est renvoyée telle quelle (sans espaces)."""
    monkeypatch.setenv("LOG_LEVEL", "  debug ")
    assert config.log_level() == "DEBUG"


def test_lire_renvoie_le_defaut_si_absente(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sans variable ni secret, on obtient la valeur par défaut."""
    monkeypatch.delenv("VARIABLE_QUI_N_EXISTE_PAS", raising=False)
    assert config.lire("VARIABLE_QUI_N_EXISTE_PAS", "defaut") == "defaut"


def test_log_level_inconnu_retombe_sur_info(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un LOG_LEVEL invalide ne fait pas planter l'app : on passe en INFO."""
    monkeypatch.setenv("LOG_LEVEL", "BAVARD")
    log.configurer_logging()
    assert logging.getLogger("suivi").level == logging.INFO
