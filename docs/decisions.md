# Décisions techniques

Une ligne par décision : **quoi** — pourquoi.

## Organisation

- **Pas de Docker, Supabase est la seule base** — tu as demandé le projet le plus simple possible (9 nov.) : rien à installer à part uv, pas de RAM prise sur le Mac 8 Go. `CLAUDE.md` fait foi, même si le prompt autonome mentionnait encore Docker.
- **Dépôt `rayaneouali/mon_projet`, branche `claude/vigilant-archimedes-fqtvk9`** — c'est le dépôt de cette session. Je ne peux pas créer un nouveau dépôt depuis ici. Tu le renommes `suivi-equipes` sur GitHub, puis tu fusionnes la branche dans `main`.
- **Imports « courts » (`from services import saisie`)** — Streamlit ajoute le dossier `app/` au chemin Python. Pytest fait pareil grâce à `pythonpath = ["app"]`, donc aucun paquet à installer.
