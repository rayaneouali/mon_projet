"""Connexion à PostgreSQL : ouvrir une connexion, la tester, appliquer le schéma."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

import config
from erreurs import ErreurMetier

logger = logging.getLogger("suivi.db.connexion")

FICHIER_SCHEMA = Path(__file__).with_name("schema.sql")
MESSAGE_BASE_INJOIGNABLE = (
    "Impossible de joindre la base de données. Vérifie la connexion internet et réessaie "
    "dans une minute. Si ça continue, préviens Rayane."
)


@contextmanager
def ouvrir_connexion() -> Iterator[psycopg.Connection]:
    """Ouvre une connexion ; valide (commit) à la fin, annule tout (rollback) en cas d'erreur."""
    url = config.database_url()
    if not url:
        raise ErreurMetier("DATABASE_URL n'est pas définie : l'app ne sait pas où est la base.")
    try:
        # prepare_threshold=None : pas de requêtes « préparées » (compatible poolers Supabase)
        conn = psycopg.connect(
            url, row_factory=dict_row, connect_timeout=10, prepare_threshold=None
        )
    except psycopg.OperationalError as erreur:
        logger.error("Connexion à la base impossible : %s", erreur)
        raise ErreurMetier(MESSAGE_BASE_INJOIGNABLE) from erreur
    with conn:  # à la sortie du bloc : commit si tout va bien, rollback sinon, puis fermeture
        _choisir_schema(conn)
        yield conn


def _choisir_schema(conn: psycopg.Connection) -> None:
    """Place la connexion dans le schéma DB_SCHEMA s'il est défini (utilisé par les tests)."""
    schema = config.schema_base()
    if schema:
        # Un nom de schéma n'est pas une valeur : on l'insère avec sql.Identifier, jamais avec %s.
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        conn.commit()


def verifier_connexion() -> tuple[bool, str]:
    """Teste la base avec SELECT 1 ; renvoie (ok, message à afficher)."""
    try:
        with ouvrir_connexion() as conn:
            conn.execute("SELECT 1")
    except ErreurMetier as erreur:
        return False, str(erreur)
    return True, "Base connectée"
