-- Schéma de la base « Suivi équipes MDC ».
-- Idempotent : on peut le relancer autant de fois qu'on veut (IF NOT EXISTS partout).
-- Il est appliqué automatiquement au démarrage de l'app (local et en ligne).
-- Les tables sont reliées par id et non par nom : renommer un gars ne casse pas son historique.

CREATE TABLE IF NOT EXISTS equipes (
    id    SERIAL PRIMARY KEY,
    nom   TEXT NOT NULL UNIQUE CHECK (btrim(nom) <> ''),
    chef  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS gars (
    id         SERIAL PRIMARY KEY,
    nom        TEXT NOT NULL UNIQUE CHECK (btrim(nom) <> ''),
    equipe_id  INTEGER NOT NULL REFERENCES equipes (id),
    actif      BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS dossiers (
    id      SERIAL PRIMARY KEY,
    code    TEXT NOT NULL UNIQUE CHECK (btrim(code) <> ''),
    client  TEXT NOT NULL DEFAULT '',
    lieu    TEXT NOT NULL DEFAULT '',
    actif   BOOLEAN NOT NULL DEFAULT TRUE
);

-- Une ligne = un gars, un jour, dans une équipe (présent ou absent).
CREATE TABLE IF NOT EXISTS saisies (
    id          SERIAL PRIMARY KEY,
    date        DATE NOT NULL,
    equipe_id   INTEGER NOT NULL REFERENCES equipes (id),
    dossier_id  INTEGER REFERENCES dossiers (id),          -- peut être vide
    gars_id     INTEGER NOT NULL REFERENCES gars (id),
    statut      TEXT NOT NULL CHECK (statut IN ('present', 'absent')),
    motif       TEXT,                                       -- seulement si absent
    saisi_le    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT un_gars_un_endroit_par_jour UNIQUE (date, gars_id),
    CONSTRAINT motif_seulement_si_absent CHECK (statut = 'absent' OR motif IS NULL)
);

CREATE INDEX IF NOT EXISTS saisies_par_equipe_et_date ON saisies (equipe_id, date);

-- Une ligne = on a demandé à un gars de travailler un samedi.
CREATE TABLE IF NOT EXISTS demandes_samedi (
    id          SERIAL PRIMARY KEY,
    samedi      DATE NOT NULL,
    gars_id     INTEGER NOT NULL REFERENCES gars (id),
    dossier_id  INTEGER REFERENCES dossiers (id),
    statut      TEXT NOT NULL DEFAULT 'demande'
                CHECK (statut IN ('demande', 'accepte', 'refuse', 'fait')),
    note        TEXT NOT NULL DEFAULT '',
    cree_le     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT samedi_obligatoire CHECK (EXTRACT(ISODOW FROM samedi) = 6),  -- 6 = samedi
    CONSTRAINT une_demande_par_gars_et_samedi UNIQUE (samedi, gars_id)
);

-- Verrou RLS (Row Level Security) sur chaque table.
-- Sur Supabase, il bloque la « Data API » (accès web automatique aux tables) : sans règle
-- d'accès, elle ne voit et ne modifie rien. L'app n'est pas gênée : elle a créé les tables,
-- et le propriétaire d'une table passe toujours ce verrou.
ALTER TABLE equipes ENABLE ROW LEVEL SECURITY;
ALTER TABLE gars ENABLE ROW LEVEL SECURITY;
ALTER TABLE dossiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE saisies ENABLE ROW LEVEL SECURITY;
ALTER TABLE demandes_samedi ENABLE ROW LEVEL SECURITY;
