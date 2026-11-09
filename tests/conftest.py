"""Préparation commune des tests.

Les tests qui touchent la base travaillent dans un SCHÉMA TEMPORAIRE (un espace séparé
dans la base, avec ses propres tables) : ils ne voient ni ne modifient jamais les vraies
données. Le schéma est créé au début et effacé à la fin.

Base utilisée : TEST_DATABASE_URL si elle existe, sinon DATABASE_URL.
Sans aucune des deux, les tests de base sont « skipped » (sautés) ; les autres tournent.
"""

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql

import config  # charge le .env
from db import connexion, requetes

URL_TEST = os.environ.get("TEST_DATABASE_URL") or config.database_url()
TABLES = ["demandes_samedi", "saisies", "gars", "dossiers", "equipes"]


@pytest.fixture(scope="session")
def schema_test() -> Iterator[str]:
    """Crée un schéma temporaire avec toutes les tables ; l'efface à la fin des tests."""
    if not URL_TEST:
        pytest.skip("Pas de base de test (DATABASE_URL ou TEST_DATABASE_URL non définie)")
    nom = f"test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(URL_TEST, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(nom)))
    anciens = {cle: os.environ.get(cle) for cle in ("DATABASE_URL", "DB_SCHEMA")}
    os.environ["DATABASE_URL"] = URL_TEST
    os.environ["DB_SCHEMA"] = nom
    connexion.appliquer_schema()
    yield nom
    for cle, valeur in anciens.items():
        if valeur is None:
            os.environ.pop(cle, None)
        else:
            os.environ[cle] = valeur
    with psycopg.connect(URL_TEST, autocommit=True) as conn:
        conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(nom)))


@pytest.fixture
def base_vide(schema_test: str) -> str:
    """Vide toutes les tables avant le test (les compteurs d'id repartent à 1)."""
    with connexion.ouvrir_connexion() as conn:
        conn.execute("TRUNCATE " + ", ".join(TABLES) + " RESTART IDENTITY CASCADE")
    return schema_test


@pytest.fixture
def exemples(base_vide: str) -> dict[str, int]:
    """Base avec 2 équipes, 6 gars, 2 dossiers ; renvoie les ids par nom."""
    with connexion.ouvrir_connexion() as conn:
        ids = {
            "Équipe 1": requetes.ajouter_equipe(conn, "Équipe 1", "Karim"),
            "Équipe 2": requetes.ajouter_equipe(conn, "Équipe 2", "Mehdi"),
        }
        for nom, equipe in [
            ("Karim", "Équipe 1"),
            ("Yanis", "Équipe 1"),
            ("Lucas", "Équipe 1"),
            ("Mehdi", "Équipe 2"),
            ("Samir", "Équipe 2"),
            ("Thomas", "Équipe 2"),
        ]:
            ids[nom] = requetes.ajouter_gars(conn, nom, ids[equipe])
        ids["D-001"] = requetes.ajouter_dossier(conn, "D-001", "Client A", "Orléans")
        ids["D-002"] = requetes.ajouter_dossier(conn, "D-002", "Client B", "Tours")
    return ids
