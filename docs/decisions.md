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

## Base de données

- **`SERIAL` pour les id** — plus simple à lire que `GENERATED … AS IDENTITY`, et ça marche pareil pour nous.
- **Nom de gars et nom d'équipe uniques** — évite les doublons tapés deux fois dans Admin. Pour deux homonymes, écris « Mohamed B. » et « Mohamed K. ».
- **`gars.equipe_id` obligatoire** — chaque gars appartient à une équipe : un cas « sans équipe » en moins à gérer.
- **Contraintes nommées (`un_gars_un_endroit_par_jour`…)** — le nom apparaît dans les messages d'erreur, donc on comprend tout de suite quelle règle a bloqué.
- **`LOCK TABLE saisies` pendant un enregistrement** — si deux chefs enregistrent en même temps, le second attend (10 s max) au lieu de planter. C'est l'équivalent du `LockService` de la version Google.
- **Verrou RLS sur chaque table** — le projet Supabase a la Data API activée, et ce verrou la bloque (voir `CLAUDE.md`).
- **Tests dans un schéma temporaire `test_xxxx`** — ils ne touchent jamais aux vraies tables, même branchés sur Supabase.
- **`scripts/seed.py --effacer`** — retire proprement les exemples avant la mise en service, sans toucher aux vraies données.
