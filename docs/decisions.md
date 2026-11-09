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

## Saisie du jour

- **Un seul menu par gars : « Présent » ou « Absent · motif »** — dans un `st.form`, on ne peut pas faire apparaître le menu « motif » après un clic sur « Absent ». Avec un seul menu, c'est un geste au lieu de deux, et le motif est toujours rempli.
- **Une liste à cocher (multiselect) pour ajouter un renfort ou retirer un gars** — un seul outil fait les deux. Elle est placée au-dessus du formulaire, donc on règle la liste d'abord, puis les présences.
- **Équipe mémorisée dans l'adresse (`?equipe=2`)** — remplace le stockage du téléphone de la version Google. Si le chef ajoute l'app à son écran d'accueil après avoir choisi son équipe, elle est déjà sélectionnée à chaque ouverture.
- **Pas de saisie dans le futur** — le calendrier s'arrête à aujourd'hui, et le service refuse une date future, au cas où.
- **Listes (équipes, gars, dossiers) gardées 60 s en mémoire (`st.cache_data`)** — moins d'allers-retours vers Supabase. La page Admin vide ce cache après chaque modification.
- **« Aucun dossier » = valeur 0 dans le menu** — sinon Streamlit affiche « Choose an option » en anglais. Le 0 redevient « vide » (NULL) avant d'aller en base.
- **Dossier `app/pages_app/` au lieu de `app/pages/`** — avec un dossier nommé `pages/`, Streamlit crée tout seul l'ancien menu automatique. Ouvrir directement l'adresse `/Semaine` exécutait alors la page sans passer par `Accueil.py`, donc sans contrôle d'accès. Je l'ai vu en test : avec un autre nom, toutes les pages passent obligatoirement par `Accueil.py`.

## Semaine

- **Un tableau par équipe + un tableau « Saisies des chefs »** — plus lisible sur téléphone qu'un seul grand tableau avec des lignes d'en-tête mélangées.
- **Un gars inactif reste visible s'il a des saisies cette semaine-là** — son historique ne disparaît pas. C'était le groupe « Autres » de la version Google, rangé ici dans sa propre équipe.
- **Couleur du dossier calculée avec `zlib.crc32`** — `hash()` de Python change à chaque démarrage, alors qu'il faut toujours la même couleur pour le même dossier.
- **Export Excel avec le `Styler` de pandas** — les couleurs du planning sont conservées dans le fichier, sans code en plus.
- **Page Semaine en mode « large »** — sur ordinateur, le tableau prend toute la largeur. Sur téléphone, ça ne change rien.
