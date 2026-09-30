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

## Essayer l'agent dans le terminal (phase 1)

Il faut une clé API Anthropic dans `.env` (`ANTHROPIC_API_KEY=...`, à créer sur
https://console.anthropic.com). Les contacts sont factices (`data/fake_contacts.json`)
et l'envoi est simulé : aucun vrai mail ne part.

```bash
uv run voxmail
```

Exemple : « Envoie un mail à Jean pour lui dire que la réunion est avancée à 9h ».
L'agent propose les contacts les plus proches : tapez le numéro du bon (c'est toujours
vous qui choisissez). Sur l'aperçu, tapez `1` (Envoyer), `2` (Modifier) ou `3` (Annuler).

## Évaluer l'agent

`evals/scenarios/*.yaml` décrit 36 conversations réalistes et le comportement attendu.
Ce script les rejoue avec le vrai Claude et affiche le taux de réussite (objectif ≥ 90 %).
Il coûte un peu d'argent (quelques appels API par scénario).

```bash
uv run python evals/run_evals.py                  # tous les scénarios
uv run python evals/run_evals.py --only homonyms  # une catégorie ou un id
```

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
│   ├── config.py         # lecture de la configuration (.env)
│   ├── domain/           # les règles, sans aucun service externe
│   │   ├── state_machine.py  # états de la conversation et passages autorisés
│   │   ├── contacts.py       # un contact, et la normalisation des noms
│   │   ├── phonetic.py       # « Mauger », « Maugé », « Mojé » → même son
│   │   ├── recipient_search.py  # classe les contacts les plus proches (score 0-100)
│   │   └── models.py         # la « fiche » d'une conversation
│   ├── agent/            # le cerveau : décide quoi faire à chaque message
│   │   ├── agent.py
│   │   └── prompts.py    # les instructions données à Claude
│   ├── llm/              # parler à Claude (et un faux Claude pour les tests)
│   ├── contacts/         # d'où viennent les contacts + mémoire des choix
│   ├── mail/             # comment part le mail (simulé, Gmail plus tard)
│   ├── evaluation.py     # rejoue les scénarios YAML
│   └── cli.py            # l'interface terminal
├── data/fake_contacts.json  # carnet d'adresses factice
├── evals/                # scénarios d'évaluation + script qui les lance
├── tests/                # les tests automatiques (pytest)
├── .github/workflows/    # la CI : tests + lint à chaque push
├── pyproject.toml        # description du projet, dépendances, réglages ruff/pytest
├── uv.lock               # versions exactes installées (ne pas modifier à la main)
├── .python-version       # version de Python utilisée
├── .env.example          # modèle des variables d'environnement (sans secrets)
├── CLAUDE.md             # contexte du projet pour Claude
└── README.md
```
