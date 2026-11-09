# Décisions techniques

Une ligne par décision : **quoi** — pourquoi.

## Organisation

- **Pas de Docker, Supabase est la seule base** — tu as demandé le projet le plus simple possible (9 nov.) : rien à installer à part uv, pas de RAM prise sur le Mac 8 Go. `CLAUDE.md` fait foi, même si le prompt autonome mentionnait encore Docker.
- **Code poussé sur `rayaneouali/mon_projet`, branche `claude/vigilant-archimedes-fqtvk9`** — c'est le seul dépôt accessible depuis cette session, et je ne peux pas en créer un. Ce dépôt contient aussi un autre projet (branche `claude/relaxed-bell-oepx9e`). Donc pas de renommage : crée `suivi-equipes` et pousse-y cette branche comme `main` (voir `docs/mise_en_ligne.md`, partie A).
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

## Samedis

- **Un doublon n'empêche pas de créer les autres demandes** — chaque gars est inséré dans une sous-transaction (« savepoint »). Si la contrainte UNIQUE refuse un gars, on annule seulement celui-là et on affiche : « Déjà demandé pour : Karim ».
- **Le menu de statut enregistre tout seul (callback `on_change`)** — pas de bouton « Enregistrer » en plus. Le menu affiche toujours l'état réel de la base.
- **Suppression en deux clics (« Supprimer » puis « Oui, supprimer »)** — la confirmation est demandée dans la page elle-même, sans fenêtre surgissante (plus fiable sur téléphone).

## Accès et administration

- **Menu construit selon le code (`st.navigation`)** — avec le code chefs, la page Admin n'est pas dans la liste des pages : elle n'existe pas pour eux, même en tapant son adresse. En plus, chaque page vérifie l'accès en haut (`acces.exiger`), c'est une double sécurité.
- **Jeton dans l'adresse (`?acces=…`) au lieu d'un cookie** — c'est la façon la plus simple de garder la connexion sur le téléphone sans bibliothèque en plus. Le jeton est calculé à partir du code (HMAC) mais ne le révèle pas. Si tu changes le code, tous les anciens liens sont refusés.
- **1 seconde d'attente après un mauvais code** — freine quelqu'un qui essaierait des codes au hasard.
- **Pas de colonnes « obligatoires » dans les tableaux Admin** — sinon, une ligne incomplète disparaît sans prévenir. Vu en test : ça affichait « aucun changement ». Maintenant, le service répond « Le nom du gars est obligatoire ».
- **Une équipe avec des gars ou des saisies ne se supprime pas** — message clair : on déplace d'abord les gars, ou on renomme l'équipe.
- **Données d'exemple jamais créées automatiquement** — elles n'existent que si tu lances `scripts/seed.py`. Tu les retires avec `--effacer`, avant de donner l'app aux chefs.

## Relecture critique (étape 8)

Défauts trouvés et corrigés, chacun avec un test :
- **Confirmation « sans dossier » qui enregistrait d'anciennes valeurs** — si le chef corrigeait un statut après l'avertissement, la correction était perdue. Le bouton « Oui, enregistrer sans dossier » est maintenant DANS le formulaire : c'est la saisie affichée qui part (vérifié dans le navigateur).
- **Gars supprimé dans Admin pendant une saisie en cours** — la page du chef plantait. Il est maintenant retiré de la liste (`retirer_gars_inconnus`).
- **CODE_CHEFS identique à CODE_ADMIN** — tout le monde devenait administrateur. L'app refuse maintenant cette configuration, avec un message clair.
- **Colonnes « obligatoires » de l'Admin** — une ligne incomplète disparaissait sans message (corrigé à l'étape 7).
- **Dossier `pages/`** — il permettait d'ouvrir une page sans passer par le contrôle d'accès (corrigé à l'étape 5).

Cas vérifiés, déjà couverts par des tests : équipe sans gars, gars inactif avec historique (Semaine et Admin), date future, deux chefs qui enregistrent en même temps, demande de samedi en double, nom en double dans Admin, transaction annulée en cas d'erreur.

Limites connues, acceptées pour rester simple :
- **Si deux chefs modifient la MÊME équipe le même jour, le dernier qui enregistre gagne.** C'est le même comportement que dans la version Google.
- **Une page interdite tapée à la main affiche la fenêtre Streamlit « Page not found », en anglais.** Elle mène ensuite à la page autorisée.
- **Le choix « Select all » de la liste des gars reste en anglais.** C'est un texte interne de Streamlit, qu'on ne peut pas traduire.

## Mise en ligne

- **`requirements.txt` généré par uv (`uv export`)** — c'est le format que Streamlit Cloud lit à coup sûr. `pyproject.toml` + `uv.lock` restent la référence, et la CI vérifie que les deux sont d'accord.
- **Python 3.12 choisi dans « Advanced settings » de Streamlit Cloud** — la plateforme ne lit pas `.python-version`.
- **`config.py` lit d'abord les variables d'environnement, puis `st.secrets`** — même code en local (`.env`) et en ligne (Secrets). Rien d'autre à changer.
- **Le schéma est appliqué au démarrage du serveur (`st.cache_resource`)** — sur Supabase comme en local, les tables se créent toutes seules au premier lancement. Aucune donnée d'exemple en production.
- **Lien du badge vers `rayaneouali/suivi-equipes`** — c'est le dépôt final. Le badge s'affichera une fois la partie A de la mise en ligne faite.

## Sauvegarde et réveil

- **Sauvegarde en CSV (séparateur `;`, avec BOM) plutôt qu'avec `pg_dump`** — `pg_dump` doit avoir la même version que le serveur Supabase (source fréquente d'erreurs). Le CSV passe par psycopg, déjà installé, et s'ouvre directement dans Excel, accents compris.
- **Restauration avec `scripts/restauration.py … --oui`** — vide la base puis recharge tout en UNE transaction, et recale les compteurs d'id. Sans `--oui`, le script explique et s'arrête. Pas de base Docker locale : on restaure dans la base de `DATABASE_URL`.
- **Réveil : deux séries de cron (hiver / été) et un tri selon le décalage horaire de Paris** — GitHub ne connaît que l'heure UTC. Le run de « l'autre saison » s'arrête en quelques secondes. Un run en retard (GitHub décale parfois de 10-15 min) reste valable.
- **Playwright fixé à la version 1.63.0, installé seulement dans GitHub Actions** — rien à installer sur le Mac.
- **Workflows inactifs sans leur secret** — ils affichent une note au lieu d'échouer en rouge.
