# Décisions techniques

Une ligne par décision : **quoi** — pourquoi.

## Organisation

- **Pas de Docker, Supabase est la seule base** — tu as demandé le projet le plus simple possible (9 nov.) : rien à installer à part uv, pas de RAM prise sur le Mac 8 Go. `CLAUDE.md` fait foi, même si le prompt autonome mentionnait encore Docker.
- **Dépôt `rayaneouali/mon_projet`, branche `claude/vigilant-archimedes-fqtvk9`** — c'est le dépôt de cette session. Je ne peux pas créer un nouveau dépôt depuis ici. Tu le renommes `suivi-equipes` sur GitHub, puis tu fusionnes la branche dans `main`.
- **Imports « courts » (`from services import saisie`)** — Streamlit ajoute le dossier `app/` au chemin Python. Pytest fait pareil grâce à `pythonpath = ["app"]`, donc aucun paquet à installer.
- **Étape 2 sans Dockerfile ni docker-compose** — conséquence directe de « pas de Docker ». L'étape garde le reste : config, connexion, page « Base connectée ».
- **Une connexion ouverte par action (pas de « pool » de connexions)** — c'est le plus simple à lire. Pour 14 personnes, c'est largement suffisant.
- **`prepare_threshold=None` dans psycopg** — évite les erreurs de « requêtes préparées » avec les poolers Supabase. Le coût est négligeable ici.
- **La page passe par `services/base.py` pour tester la base** — respecte la règle pages → services → db, même pour un simple test de connexion.
