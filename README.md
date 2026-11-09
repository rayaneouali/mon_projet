# Suivi équipes MDC

[![Tests](https://github.com/rayaneouali/suivi-equipes/actions/workflows/ci.yml/badge.svg)](https://github.com/rayaneouali/suivi-equipes/actions/workflows/ci.yml)

App web qui remplace l'agenda de suivi des équipes de monteurs de MDC. Chaque jour, depuis
leur téléphone, les chefs d'équipe notent qui est **présent**, qui est **absent** (et
pourquoi), sur quel **dossier**, et à qui on a demandé de travailler le **samedi**.

Pages : **Saisie du jour**, **Semaine** (planning, saisies manquantes, export Excel),
**Samedis**, **Admin** (équipes, gars, dossiers). Accès par code : chefs ou admin.

## Architecture

```
  EN LIGNE                                       SUR TON MAC (développement)

  Téléphone d'un chef                            Navigateur → http://localhost:8501
        │  HTTPS                                         │
        ▼                                                ▼
  Streamlit Community Cloud                      uv run streamlit run app/Accueil.py
  (l'app Python, redéployée à chaque push)        (même code, config dans .env)
        │  PostgreSQL (Session pooler, IPv4)             │
        └──────────────┐               ┌─────────────────┘
                       ▼               ▼
                 Supabase : base PostgreSQL (offre gratuite)

  GitHub : code + Actions → tests à chaque push, sauvegarde le dimanche,
                            réveil de l'app en semaine
```

Dans le code, trois couches qui ne se mélangent pas :

```
app/pages_app/*.py   →  app/services/*.py   →  app/db/requetes.py  →  PostgreSQL
  (écrans Streamlit)     (règles métier)         (tout le SQL, en clair)
```

| Dossier / fichier | Rôle |
|---|---|
| `app/Accueil.py` | Point d'entrée : prépare la base, vérifie le code d'accès, construit le menu |
| `app/pages_app/` | Les écrans (Connexion, Saisie, Semaine, Samedis, Admin) |
| `app/services/` | Les règles métier, testées (saisie, semaine, samedis, admin, accès, dates) |
| `app/db/` | Connexion, `schema.sql` (tables), `requetes.py` (toutes les requêtes SQL) |
| `app/config.py`, `app/log.py` | Configuration (`.env` / Secrets) et logs |
| `scripts/` | Données d'exemple, sauvegarde, restauration, réveil |
| `tests/` | Tests pytest (les tests de base tournent dans un schéma temporaire) |
| `docs/` | Guide des chefs, mise en ligne, débogage, décisions, fiches de révision |

## Lancer en local

Prérequis : [uv](https://docs.astral.sh/uv/) (il installe Python 3.12 tout seul).

1. Crée ton fichier de configuration :
   ```bash
   cp .env.example .env
   ```
2. Remplis `.env` : `DATABASE_URL` (Supabase, Session pooler), `CODE_CHEFS`, `CODE_ADMIN`.
3. Installe les dépendances :
   ```bash
   uv sync
   ```
4. Lance l'app :
   ```bash
   uv run streamlit run app/Accueil.py
   ```
   Puis ouvre http://localhost:8501.

Si le port 8501 est déjà pris, Streamlit utilise automatiquement le suivant (8502) et
l'affiche dans le terminal.

Tests et style :
```bash
uv run pytest
```
```bash
uv run ruff check .
```
```bash
uv run ruff format .
```

Données d'exemple (2 équipes, 6 gars, 2 dossiers), et leur retrait :
```bash
uv run python scripts/seed.py
```
```bash
uv run python scripts/seed.py --effacer
```

## Déployer

Tout est décrit pas à pas dans [`docs/mise_en_ligne.md`](docs/mise_en_ligne.md) :
dépôt GitHub, Supabase, Streamlit Community Cloud (point d'entrée `app/Accueil.py`,
Python 3.12, secrets), vérifications, secrets GitHub pour la sauvegarde et le réveil.

Après un `uv add <paquet>`, régénère le fichier lu par Streamlit Cloud (la CI vérifie qu'il est à jour) :
```bash
uv export --no-dev --no-hashes --format requirements-txt --frozen -o requirements.txt
```

## Documentation

- [`docs/guide_chefs.md`](docs/guide_chefs.md) : mode d'emploi d'une page pour les chefs
- [`docs/debug.md`](docs/debug.md) : les 5 pannes probables, et comment les diagnostiquer
- [`docs/decisions.md`](docs/decisions.md) : chaque choix technique, et pourquoi
- [`docs/apprendre.md`](docs/apprendre.md) : fiches de révision, étape par étape
