"""Toutes les requêtes SQL du projet, une fonction par requête.

Règles :
- les valeurs sont TOUJOURS passées avec %s (jamais de f-string dans du SQL) ;
- chaque fonction reçoit la connexion `conn` ouverte par le service appelant ;
- avec LOG_LEVEL=DEBUG, chaque requête exécutée est écrite dans les logs.
"""

import logging
from datetime import date
from typing import Any, BinaryIO

import psycopg
from psycopg import sql

logger = logging.getLogger("suivi.db.requetes")

Ligne = dict[str, Any]


def _executer(conn: psycopg.Connection, requete: str, params: tuple = ()) -> psycopg.Cursor:
    """Exécute une requête et l'écrit dans les logs (niveau DEBUG)."""
    logger.debug("SQL : %s | paramètres : %s", " ".join(requete.split()), params)
    return conn.execute(requete, params)


# ---------------------------------------------------------------- équipes


def lister_equipes(conn: psycopg.Connection) -> list[Ligne]:
    """Toutes les équipes, triées par nom."""
    return _executer(conn, "SELECT id, nom, chef FROM equipes ORDER BY nom").fetchall()


def ajouter_equipe(conn: psycopg.Connection, nom: str, chef: str) -> int:
    """Crée une équipe et renvoie son id."""
    curseur = _executer(
        conn, "INSERT INTO equipes (nom, chef) VALUES (%s, %s) RETURNING id", (nom, chef)
    )
    return curseur.fetchone()["id"]


def modifier_equipe(conn: psycopg.Connection, equipe_id: int, nom: str, chef: str) -> None:
    """Change le nom et le chef d'une équipe."""
    _executer(conn, "UPDATE equipes SET nom = %s, chef = %s WHERE id = %s", (nom, chef, equipe_id))


def supprimer_equipe(conn: psycopg.Connection, equipe_id: int) -> None:
    """Supprime une équipe (refusé par la base si elle a des gars ou des saisies)."""
    _executer(conn, "DELETE FROM equipes WHERE id = %s", (equipe_id,))


def equipe_a_historique(conn: psycopg.Connection, equipe_id: int) -> bool:
    """Vrai si l'équipe a des gars ou des saisies."""
    requete = """
        SELECT EXISTS (SELECT 1 FROM gars WHERE equipe_id = %s)
            OR EXISTS (SELECT 1 FROM saisies WHERE equipe_id = %s) AS reponse
    """
    return _executer(conn, requete, (equipe_id, equipe_id)).fetchone()["reponse"]


# ---------------------------------------------------------------- gars


def lister_gars(conn: psycopg.Connection) -> list[Ligne]:
    """Tous les gars (actifs et inactifs) avec le nom de leur équipe."""
    requete = """
        SELECT g.id, g.nom, g.equipe_id, e.nom AS equipe, g.actif
        FROM gars g
        JOIN equipes e ON e.id = g.equipe_id
        ORDER BY e.nom, g.nom
    """
    return _executer(conn, requete).fetchall()


def ajouter_gars(conn: psycopg.Connection, nom: str, equipe_id: int, actif: bool = True) -> int:
    """Crée un gars et renvoie son id."""
    curseur = _executer(
        conn,
        "INSERT INTO gars (nom, equipe_id, actif) VALUES (%s, %s, %s) RETURNING id",
        (nom, equipe_id, actif),
    )
    return curseur.fetchone()["id"]


def modifier_gars(
    conn: psycopg.Connection, gars_id: int, nom: str, equipe_id: int, actif: bool
) -> None:
    """Change le nom, l'équipe et l'état actif d'un gars."""
    _executer(
        conn,
        "UPDATE gars SET nom = %s, equipe_id = %s, actif = %s WHERE id = %s",
        (nom, equipe_id, actif, gars_id),
    )


def desactiver_gars(conn: psycopg.Connection, gars_id: int) -> None:
    """Passe un gars en inactif (il garde son historique)."""
    _executer(conn, "UPDATE gars SET actif = FALSE WHERE id = %s", (gars_id,))


def supprimer_gars(conn: psycopg.Connection, gars_id: int) -> None:
    """Supprime définitivement un gars (refusé par la base s'il a de l'historique)."""
    _executer(conn, "DELETE FROM gars WHERE id = %s", (gars_id,))


def gars_a_historique(conn: psycopg.Connection, gars_id: int) -> bool:
    """Vrai si le gars apparaît dans une saisie ou une demande de samedi."""
    requete = """
        SELECT EXISTS (SELECT 1 FROM saisies WHERE gars_id = %s)
            OR EXISTS (SELECT 1 FROM demandes_samedi WHERE gars_id = %s) AS reponse
    """
    return _executer(conn, requete, (gars_id, gars_id)).fetchone()["reponse"]


# ---------------------------------------------------------------- dossiers


def lister_dossiers(conn: psycopg.Connection) -> list[Ligne]:
    """Tous les dossiers (actifs et inactifs), triés par code."""
    return _executer(
        conn, "SELECT id, code, client, lieu, actif FROM dossiers ORDER BY code"
    ).fetchall()


def ajouter_dossier(
    conn: psycopg.Connection, code: str, client: str, lieu: str, actif: bool = True
) -> int:
    """Crée un dossier et renvoie son id."""
    curseur = _executer(
        conn,
        "INSERT INTO dossiers (code, client, lieu, actif) VALUES (%s, %s, %s, %s) RETURNING id",
        (code, client, lieu, actif),
    )
    return curseur.fetchone()["id"]


def modifier_dossier(
    conn: psycopg.Connection, dossier_id: int, code: str, client: str, lieu: str, actif: bool
) -> None:
    """Change les informations d'un dossier."""
    _executer(
        conn,
        "UPDATE dossiers SET code = %s, client = %s, lieu = %s, actif = %s WHERE id = %s",
        (code, client, lieu, actif, dossier_id),
    )


def desactiver_dossier(conn: psycopg.Connection, dossier_id: int) -> None:
    """Passe un dossier en inactif (il garde son historique)."""
    _executer(conn, "UPDATE dossiers SET actif = FALSE WHERE id = %s", (dossier_id,))


def supprimer_dossier(conn: psycopg.Connection, dossier_id: int) -> None:
    """Supprime définitivement un dossier (refusé par la base s'il a de l'historique)."""
    _executer(conn, "DELETE FROM dossiers WHERE id = %s", (dossier_id,))


def dossier_a_historique(conn: psycopg.Connection, dossier_id: int) -> bool:
    """Vrai si le dossier apparaît dans une saisie ou une demande de samedi."""
    requete = """
        SELECT EXISTS (SELECT 1 FROM saisies WHERE dossier_id = %s)
            OR EXISTS (SELECT 1 FROM demandes_samedi WHERE dossier_id = %s) AS reponse
    """
    return _executer(conn, requete, (dossier_id, dossier_id)).fetchone()["reponse"]


# ---------------------------------------------------------------- saisies


def lire_saisies_periode(conn: psycopg.Connection, debut: date, fin: date) -> list[Ligne]:
    """Toutes les saisies entre deux dates incluses (une semaine, par exemple)."""
    requete = """
        SELECT s.date, s.equipe_id, e.nom AS equipe, s.dossier_id, d.code AS dossier,
               s.gars_id, g.nom AS gars, s.statut, s.motif
        FROM saisies s
        JOIN equipes e ON e.id = s.equipe_id
        JOIN gars g ON g.id = s.gars_id
        LEFT JOIN dossiers d ON d.id = s.dossier_id
        WHERE s.date BETWEEN %s AND %s
        ORDER BY s.date, e.nom, g.nom
    """
    return _executer(conn, requete, (debut, fin)).fetchall()


def lire_saisies_jour(conn: psycopg.Connection, jour: date) -> list[Ligne]:
    """Toutes les saisies d'un jour, toutes équipes confondues."""
    return lire_saisies_periode(conn, jour, jour)


def dernier_dossier_equipe(conn: psycopg.Connection, equipe_id: int, avant: date) -> int | None:
    """Dossier de la dernière saisie de l'équipe avant une date (None s'il n'y en a pas)."""
    requete = """
        SELECT dossier_id FROM saisies
        WHERE equipe_id = %s AND date < %s AND dossier_id IS NOT NULL
        ORDER BY date DESC
        LIMIT 1
    """
    ligne = _executer(conn, requete, (equipe_id, avant)).fetchone()
    return ligne["dossier_id"] if ligne else None


def remplacer_saisie(
    conn: psycopg.Connection,
    jour: date,
    equipe_id: int,
    dossier_id: int | None,
    lignes: list[tuple[int, str, str | None]],
) -> int:
    """Remplace la saisie d'une équipe pour un jour, en UNE transaction (tout ou rien).

    `lignes` : liste de (gars_id, statut, motif). Supprime les lignes de l'équipe ce jour-là
    ET celles des gars saisis qui étaient notés dans une autre équipe, puis insère.
    """
    gars_ids = [gars_id for gars_id, _statut, _motif in lignes]
    with conn.transaction():
        # Verrou : si deux chefs enregistrent en même temps, le second attend que le premier
        # ait fini (au plus 10 s). Ça évite les conflits « un gars à deux endroits ».
        _executer(conn, "SET LOCAL lock_timeout = '10s'")
        _executer(conn, "LOCK TABLE saisies IN SHARE ROW EXCLUSIVE MODE")
        _executer(
            conn,
            "DELETE FROM saisies WHERE date = %s AND (equipe_id = %s OR gars_id = ANY(%s))",
            (jour, equipe_id, gars_ids),
        )
        for gars_id, statut, motif in lignes:
            _executer(
                conn,
                """
                INSERT INTO saisies (date, equipe_id, dossier_id, gars_id, statut, motif)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (jour, equipe_id, dossier_id, gars_id, statut, motif),
            )
    return len(lignes)


# ---------------------------------------------------------------- demandes de samedi


def lister_demandes_samedi(conn: psycopg.Connection, depuis: date, jusqua: date) -> list[Ligne]:
    """Demandes de samedi entre deux dates incluses, triées par samedi puis par gars."""
    requete = """
        SELECT ds.id, ds.samedi, ds.gars_id, g.nom AS gars, e.nom AS equipe,
               ds.dossier_id, d.code AS dossier, ds.statut, ds.note
        FROM demandes_samedi ds
        JOIN gars g ON g.id = ds.gars_id
        JOIN equipes e ON e.id = g.equipe_id
        LEFT JOIN dossiers d ON d.id = ds.dossier_id
        WHERE ds.samedi BETWEEN %s AND %s
        ORDER BY ds.samedi, g.nom
    """
    return _executer(conn, requete, (depuis, jusqua)).fetchall()


def ajouter_demande_samedi(
    conn: psycopg.Connection, samedi: date, gars_id: int, dossier_id: int | None, note: str
) -> int:
    """Crée une demande de samedi (statut « demande ») et renvoie son id."""
    curseur = _executer(
        conn,
        """
        INSERT INTO demandes_samedi (samedi, gars_id, dossier_id, note)
        VALUES (%s, %s, %s, %s) RETURNING id
        """,
        (samedi, gars_id, dossier_id, note),
    )
    return curseur.fetchone()["id"]


def changer_statut_demande(conn: psycopg.Connection, demande_id: int, statut: str) -> bool:
    """Change le statut d'une demande ; renvoie False si elle n'existe plus."""
    curseur = _executer(
        conn, "UPDATE demandes_samedi SET statut = %s WHERE id = %s", (statut, demande_id)
    )
    return curseur.rowcount == 1


def supprimer_demande_samedi(conn: psycopg.Connection, demande_id: int) -> bool:
    """Supprime une demande ; renvoie False si elle n'existait plus."""
    curseur = _executer(conn, "DELETE FROM demandes_samedi WHERE id = %s", (demande_id,))
    return curseur.rowcount == 1


# ---------------------------------------------------------------- données d'exemple


def inserer_equipe_si_absente(conn: psycopg.Connection, nom: str, chef: str) -> int:
    """Crée l'équipe si son nom n'existe pas encore ; renvoie son id dans tous les cas."""
    _executer(
        conn,
        "INSERT INTO equipes (nom, chef) VALUES (%s, %s) ON CONFLICT (nom) DO NOTHING",
        (nom, chef),
    )
    return _executer(conn, "SELECT id FROM equipes WHERE nom = %s", (nom,)).fetchone()["id"]


def inserer_gars_si_absent(conn: psycopg.Connection, nom: str, equipe_id: int) -> None:
    """Crée le gars si son nom n'existe pas encore."""
    _executer(
        conn,
        "INSERT INTO gars (nom, equipe_id) VALUES (%s, %s) ON CONFLICT (nom) DO NOTHING",
        (nom, equipe_id),
    )


def inserer_dossier_si_absent(conn: psycopg.Connection, code: str, client: str, lieu: str) -> None:
    """Crée le dossier si son code n'existe pas encore."""
    _executer(
        conn,
        """
        INSERT INTO dossiers (code, client, lieu) VALUES (%s, %s, %s)
        ON CONFLICT (code) DO NOTHING
        """,
        (code, client, lieu),
    )


def effacer_exemples(
    conn: psycopg.Connection, equipes: list[str], gars: list[str], dossiers: list[str]
) -> None:
    """Efface les données d'exemple (et leur historique) désignées par nom ou code."""
    with conn.transaction():
        requete_gars = "SELECT id FROM gars WHERE nom = ANY(%s)"
        ids = [ligne["id"] for ligne in _executer(conn, requete_gars, (gars,)).fetchall()]
        _executer(conn, "DELETE FROM saisies WHERE gars_id = ANY(%s)", (ids,))
        _executer(conn, "DELETE FROM demandes_samedi WHERE gars_id = ANY(%s)", (ids,))
        _executer(conn, "DELETE FROM gars WHERE id = ANY(%s)", (ids,))
        _executer(
            conn,
            """
            DELETE FROM dossiers WHERE code = ANY(%s)
              AND NOT EXISTS (SELECT 1 FROM saisies WHERE dossier_id = dossiers.id)
              AND NOT EXISTS (SELECT 1 FROM demandes_samedi WHERE dossier_id = dossiers.id)
            """,
            (dossiers,),
        )
        _executer(
            conn,
            """
            DELETE FROM equipes WHERE nom = ANY(%s)
              AND NOT EXISTS (SELECT 1 FROM gars WHERE equipe_id = equipes.id)
              AND NOT EXISTS (SELECT 1 FROM saisies WHERE equipe_id = equipes.id)
            """,
            (equipes,),
        )


# ---------------------------------------------------------------- sauvegarde / restauration

TABLES_DANS_L_ORDRE = ["equipes", "gars", "dossiers", "saisies", "demandes_samedi"]

# Format CSV « à la française » (séparateur ;) pour qu'il s'ouvre directement dans Excel.
# Un nom de table n'est pas une valeur : il s'insère avec sql.Identifier, jamais avec %s.
EXPORT_CSV = sql.SQL("COPY {table} TO STDOUT WITH (FORMAT csv, HEADER true, DELIMITER ';')")
IMPORT_CSV = sql.SQL("COPY {table} FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER ';')")
RECALER_COMPTEUR = sql.SQL(
    "SELECT setval(pg_get_serial_sequence({nom}, 'id'), "
    "COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
)


def exporter_table_csv(conn: psycopg.Connection, table: str, fichier: BinaryIO) -> None:
    """Écrit toute une table dans un fichier CSV (commande COPY de PostgreSQL)."""
    requete = EXPORT_CSV.format(table=sql.Identifier(table))
    logger.debug("SQL : %s", requete.as_string(conn))
    with conn.cursor().copy(requete) as copie:
        for morceau in copie:
            fichier.write(bytes(morceau))


def vider_toutes_les_tables(conn: psycopg.Connection) -> None:
    """Efface TOUTES les données (avant une restauration)."""
    _executer(conn, "TRUNCATE demandes_samedi, saisies, gars, dossiers, equipes RESTART IDENTITY")


def importer_table_csv(conn: psycopg.Connection, table: str, fichier: BinaryIO) -> None:
    """Recharge une table depuis un fichier CSV, puis recale son compteur d'id."""
    requete = IMPORT_CSV.format(table=sql.Identifier(table))
    logger.debug("SQL : %s", requete.as_string(conn))
    with conn.cursor().copy(requete) as copie:
        copie.write(fichier.read())
    # Le prochain id créé doit être plus grand que tous les id restaurés.
    recalage = RECALER_COMPTEUR.format(nom=sql.Literal(table), table=sql.Identifier(table))
    logger.debug("SQL : %s", recalage.as_string(conn))
    conn.execute(recalage)
