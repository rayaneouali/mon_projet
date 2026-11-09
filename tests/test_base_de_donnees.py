"""Tests du schéma et des requêtes, sur une vraie base PostgreSQL (schéma temporaire)."""

import threading
from datetime import date

import psycopg
import pytest
from psycopg import errors

from db import connexion, requetes

LUNDI = date(2026, 11, 9)
SAMEDI = date(2026, 11, 14)


def test_schema_relancable_sans_erreur(base_vide: str) -> None:
    """schema.sql peut être appliqué plusieurs fois (idempotent)."""
    connexion.appliquer_schema()
    connexion.appliquer_schema()


def test_verrou_rls_actif_sur_toutes_les_tables(base_vide: str) -> None:
    """Chaque table a le verrou RLS (protection de la Data API Supabase)."""
    with connexion.ouvrir_connexion() as conn:
        lignes = conn.execute(
            """
            SELECT c.relname, c.relrowsecurity FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = current_schema() AND c.relkind = 'r'
            """
        ).fetchall()
    assert len(lignes) == 5
    assert all(ligne["relrowsecurity"] for ligne in lignes)


def test_un_gars_ne_peut_etre_qu_a_un_endroit_par_jour(exemples: dict[str, int]) -> None:
    """Contrainte UNIQUE (date, gars_id) : deux lignes le même jour pour un gars = refus."""
    with pytest.raises(errors.UniqueViolation):
        with connexion.ouvrir_connexion() as conn:
            for equipe in ("Équipe 1", "Équipe 2"):
                conn.execute(
                    "INSERT INTO saisies (date, equipe_id, gars_id, statut) "
                    "VALUES (%s, %s, %s, 'present')",
                    (LUNDI, exemples[equipe], exemples["Yanis"]),
                )


def test_une_demande_de_samedi_doit_tomber_un_samedi(exemples: dict[str, int]) -> None:
    """Contrainte CHECK : une demande « samedi » un lundi est refusée par la base."""
    with pytest.raises(errors.CheckViolation):
        with connexion.ouvrir_connexion() as conn:
            requetes.ajouter_demande_samedi(conn, LUNDI, exemples["Yanis"], None, "")


def test_une_seule_demande_par_gars_et_par_samedi(exemples: dict[str, int]) -> None:
    """Contrainte UNIQUE (samedi, gars_id)."""
    with pytest.raises(errors.UniqueViolation):
        with connexion.ouvrir_connexion() as conn:
            requetes.ajouter_demande_samedi(conn, SAMEDI, exemples["Yanis"], None, "")
            requetes.ajouter_demande_samedi(conn, SAMEDI, exemples["Yanis"], None, "")


def test_motif_interdit_pour_un_present(exemples: dict[str, int]) -> None:
    """Contrainte CHECK : un présent n'a pas de motif d'absence."""
    with pytest.raises(errors.CheckViolation):
        with connexion.ouvrir_connexion() as conn:
            requetes.remplacer_saisie(
                conn, LUNDI, exemples["Équipe 1"], None, [(exemples["Yanis"], "present", "Malade")]
            )


def _saisies(jour: date) -> list[dict]:
    """Lit les saisies d'un jour dans une connexion neuve."""
    with connexion.ouvrir_connexion() as conn:
        return requetes.lire_saisies_jour(conn, jour)


def test_remplacer_saisie_remplace_les_lignes_de_l_equipe(exemples: dict[str, int]) -> None:
    """Ré-enregistrer une équipe le même jour remplace l'ancienne saisie."""
    e1, d1 = exemples["Équipe 1"], exemples["D-001"]
    with connexion.ouvrir_connexion() as conn:
        requetes.remplacer_saisie(
            conn,
            LUNDI,
            e1,
            d1,
            [(exemples["Karim"], "present", None), (exemples["Yanis"], "present", None)],
        )
    with connexion.ouvrir_connexion() as conn:
        requetes.remplacer_saisie(conn, LUNDI, e1, d1, [(exemples["Karim"], "absent", "Malade")])
    lignes = _saisies(LUNDI)
    assert [(ligne["gars"], ligne["statut"], ligne["motif"]) for ligne in lignes] == [
        ("Karim", "absent", "Malade")
    ]


def test_remplacer_saisie_deplace_un_gars_venu_d_une_autre_equipe(exemples: dict[str, int]) -> None:
    """Un gars noté en Équipe 2 puis saisi en renfort en Équipe 1 est déplacé (pas dupliqué)."""
    with connexion.ouvrir_connexion() as conn:
        requetes.remplacer_saisie(
            conn,
            LUNDI,
            exemples["Équipe 2"],
            None,
            [(exemples["Samir"], "present", None), (exemples["Mehdi"], "present", None)],
        )
        requetes.remplacer_saisie(
            conn, LUNDI, exemples["Équipe 1"], None, [(exemples["Samir"], "present", None)]
        )
    par_gars = {ligne["gars"]: ligne["equipe"] for ligne in _saisies(LUNDI)}
    assert par_gars == {"Samir": "Équipe 1", "Mehdi": "Équipe 2"}


def test_transaction_annulee_si_une_ligne_echoue(exemples: dict[str, int]) -> None:
    """Si une insertion échoue au milieu, RIEN n'est modifié (l'ancienne saisie reste)."""
    e1 = exemples["Équipe 1"]
    with connexion.ouvrir_connexion() as conn:
        requetes.remplacer_saisie(conn, LUNDI, e1, None, [(exemples["Karim"], "present", None)])
    with pytest.raises(errors.CheckViolation):
        with connexion.ouvrir_connexion() as conn:
            requetes.remplacer_saisie(
                conn,
                LUNDI,
                e1,
                None,
                [(exemples["Yanis"], "present", None), (exemples["Lucas"], "en_vacances", None)],
            )
    assert [ligne["gars"] for ligne in _saisies(LUNDI)] == ["Karim"]


def test_deux_enregistrements_simultanes_sans_conflit(exemples: dict[str, int]) -> None:
    """Deux chefs enregistrent le même gars en même temps : le verrou évite l'erreur."""
    erreurs: list[Exception] = []
    depart = threading.Barrier(2)

    def enregistrer(equipe: str) -> None:
        """Enregistre Samir dans l'équipe donnée."""
        try:
            depart.wait()
            with connexion.ouvrir_connexion() as conn:
                requetes.remplacer_saisie(
                    conn, LUNDI, exemples[equipe], None, [(exemples["Samir"], "present", None)]
                )
        except psycopg.Error as erreur:
            erreurs.append(erreur)

    fils = [threading.Thread(target=enregistrer, args=(e,)) for e in ("Équipe 1", "Équipe 2")]
    for fil in fils:
        fil.start()
    for fil in fils:
        fil.join()
    assert erreurs == []
    assert len(_saisies(LUNDI)) == 1  # Samir est à un seul endroit


def test_dernier_dossier_de_l_equipe(exemples: dict[str, int]) -> None:
    """On retrouve le dossier de la dernière saisie de l'équipe avant une date."""
    e1 = exemples["Équipe 1"]
    with connexion.ouvrir_connexion() as conn:
        requetes.remplacer_saisie(
            conn, date(2026, 11, 2), e1, exemples["D-001"], [(exemples["Karim"], "present", None)]
        )
        requetes.remplacer_saisie(
            conn, date(2026, 11, 5), e1, exemples["D-002"], [(exemples["Karim"], "present", None)]
        )
        assert requetes.dernier_dossier_equipe(conn, e1, LUNDI) == exemples["D-002"]
        assert requetes.dernier_dossier_equipe(conn, e1, date(2026, 11, 3)) == exemples["D-001"]
        assert requetes.dernier_dossier_equipe(conn, exemples["Équipe 2"], LUNDI) is None


def test_seed_sans_doublon(base_vide: str) -> None:
    """Le script d'exemples peut être relancé : pas de doublon. --effacer les retire."""
    import importlib.util
    from pathlib import Path

    chemin = Path(__file__).resolve().parent.parent / "scripts" / "seed.py"
    spec = importlib.util.spec_from_file_location("seed", chemin)
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    seed.ajouter_exemples()
    seed.ajouter_exemples()
    with connexion.ouvrir_connexion() as conn:
        assert len(requetes.lister_gars(conn)) == 6
        assert len(requetes.lister_equipes(conn)) == 2
        assert len(requetes.lister_dossiers(conn)) == 2
    seed.effacer_exemples()
    with connexion.ouvrir_connexion() as conn:
        assert requetes.lister_gars(conn) == []
        assert requetes.lister_equipes(conn) == []
