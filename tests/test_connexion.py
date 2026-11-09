"""Tests de la connexion à la base."""

import pytest

from db import connexion


def test_sans_database_url_message_clair(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sans DATABASE_URL, on obtient un message en français, pas un plantage."""
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setattr("config._lire_secret_streamlit", lambda nom: "")
    ok, message = connexion.verifier_connexion()
    assert not ok
    assert "DATABASE_URL" in message


def test_base_injoignable_message_clair(monkeypatch: pytest.MonkeyPatch) -> None:
    """Une base injoignable donne le message « Impossible de joindre la base »."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://personne:faux@127.0.0.1:1/rien")
    ok, message = connexion.verifier_connexion()
    assert not ok
    assert "Impossible de joindre la base" in message
