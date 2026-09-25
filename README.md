# Voxmail

Assistant WhatsApp qui transforme un message vocal ou texte en mail professionnel,
puis l'envoie depuis Gmail après validation de l'utilisateur.

## Installation (macOS)

Prérequis : [uv](https://docs.astral.sh/uv/) installé.

```bash
git clone https://github.com/rayaneouali/mon_projet.git
cd mon_projet
uv sync                  # crée l'environnement virtuel (.venv) et installe tout
cp .env.example .env     # puis remplis les valeurs dans .env
```

`uv` télécharge tout seul la bonne version de Python (3.12, voir `.python-version`).

## Commandes utiles

```bash
uv run pytest            # lancer les tests
uv run ruff check .      # chercher les erreurs et mauvaises pratiques
uv run ruff format .     # formater le code automatiquement
```

À chaque `git push`, GitHub Actions lance ces mêmes vérifications (`.github/workflows/ci.yml`).

## Structure du projet

```
mon_projet/
├── src/voxmail/          # le code de l'application
│   ├── __init__.py       # fait de ce dossier un package Python
│   └── config.py         # lecture de la configuration (.env)
├── tests/                # les tests automatiques (pytest)
├── .github/workflows/    # la CI : tests + lint à chaque push
├── pyproject.toml        # description du projet, dépendances, réglages ruff/pytest
├── uv.lock               # versions exactes installées (ne pas modifier à la main)
├── .python-version       # version de Python utilisée
├── .env.example          # modèle des variables d'environnement (sans secrets)
├── CLAUDE.md             # contexte du projet pour Claude
└── README.md
```

D'autres dossiers (agent, contacts, mail…) apparaîtront au fil des phases.
