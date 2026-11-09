# Apprendre avec ce projet — fiches de révision

Une fiche par étape : **ce qui a été fait**, **les mots à connaître** (définis simplement),
et **les lignes clés** à savoir reconnaître dans le code. Les numéros de ligne peuvent
bouger un peu : cherche le texte avec Cmd+F dans VS Code/Cursor.

Tout le chemin d'un clic, de haut en bas :
```
Écran (app/pages_app)  →  Règles (app/services)  →  SQL (app/db/requetes.py)  →  PostgreSQL
```

---

## Étape 1 — Squelette du projet

**Fait** : projet créé avec uv, dossiers `app/`, `tests/`, `docs/`, `scripts/`, fichiers
`.gitignore` et `.env.example`, configuration (`config.py`) et logs (`log.py`).

**Mots à connaître**
- **uv** : l'outil qui installe Python et les bibliothèques du projet, et les garde à la même version partout. `pyproject.toml` = la liste des bibliothèques ; `uv.lock` = les versions exactes.
- **Dépendance** : une bibliothèque dont le projet a besoin (Streamlit, psycopg, pandas…).
- **Variable d'environnement** : un réglage donné au programme de l'extérieur (par exemple l'adresse de la base), pour ne jamais l'écrire dans le code.
- **`.env`** : le fichier qui contient ces réglages sur ton Mac. Il est dans `.gitignore`, donc il ne part **jamais** sur GitHub.
- **Logging** : écrire ce qui se passe dans un « journal » (les logs), avec un niveau de gravité : DEBUG < INFO < WARNING < ERROR.

**Lignes clés**
- `app/config.py` → `load_dotenv(RACINE_PROJET / ".env")` : charge ton `.env`.
- `app/config.py` → `valeur = os.environ.get(nom, "").strip()` : on lit d'abord l'environnement…
- `app/config.py` → `return str(st.secrets.get(nom, "")).strip()` : …puis les Secrets de Streamlit Cloud.
- `app/log.py` → `logger.setLevel(niveau)` : c'est ici que `LOG_LEVEL` agit.

## Étape 2 — Connexion à la base (sans Docker)

**Fait** : `db/connexion.py` ouvre une connexion PostgreSQL. La page affiche « Base connectée »
ou un message d'erreur en français. Docker a été retiré : la base est Supabase, en local
comme en ligne.

**Mots à connaître**
- **PostgreSQL** : le logiciel de base de données (des tables avec des lignes et des colonnes).
- **Supabase** : un service qui héberge un PostgreSQL pour toi, gratuitement.
- **psycopg** : la bibliothèque Python qui parle à PostgreSQL.
- **Context manager (`with … :`)** : un bloc qui ouvre quelque chose et le referme **toujours** à la fin, même en cas d'erreur.
- **Exception** : une erreur qui « remonte » les fonctions jusqu'à ce qu'un `try/except` l'attrape.

**Lignes clés** (`app/db/connexion.py`)
- `def ouvrir_connexion()` : LA porte d'entrée vers la base, utilisée partout.
- `conn = psycopg.connect(url, …)` : l'ouverture de la connexion.
- `raise ErreurMetier(MESSAGE_BASE_INJOIGNABLE) from erreur` : l'erreur technique devient un message en français. Le détail part dans les logs.
- `with conn:` : à la fin du bloc, **commit** (on valide) si tout va bien, **rollback** (on annule tout) sinon.

## Étape 3 — Schéma, requêtes, transaction

**Fait** : `schema.sql` crée 5 tables (equipes, gars, dossiers, saisies, demandes_samedi).
`requetes.py` contient TOUT le SQL du projet. L'enregistrement d'une saisie se fait en une
transaction. `scripts/seed.py` ajoute ou retire les exemples. Les tests tournent sur une vraie base.

**Mots à connaître**
- **Clé primaire (`id SERIAL PRIMARY KEY`)** : le numéro unique de chaque ligne, donné automatiquement.
- **Clé étrangère (`REFERENCES equipes (id)`)** : « cette colonne doit contenir l'id d'une ligne qui existe dans l'autre table ». La base refuse un gars rattaché à une équipe qui n'existe pas. On relie par id et non par nom : renommer un gars ne casse pas son historique.
- **Contrainte UNIQUE** : la base refuse deux lignes avec la même valeur, par exemple le même gars deux fois le même jour.
- **Contrainte CHECK** : une règle vérifiée par la base, par exemple « la date est un samedi ».
- **Transaction** : un paquet de requêtes qui passe **en entier ou pas du tout**. Si la 3e requête échoue, les 2 premières sont annulées.
- **Injection SQL** : une attaque où l'on glisse du SQL dans une valeur tapée, par exemple un nom de gars. Avec `%s`, psycopg envoie la valeur **séparément** de la requête : elle ne peut jamais être exécutée comme du SQL.
- **Idempotent** : relancer ne change rien de plus (`CREATE TABLE IF NOT EXISTS`).
- **RLS (Row Level Security)** : un verrou par table. Sur Supabase, il bloque la « Data API » restée ouverte.

**Lignes clés**
- `schema.sql` → `CONSTRAINT un_gars_un_endroit_par_jour UNIQUE (date, gars_id)`
- `schema.sql` → `CONSTRAINT samedi_obligatoire CHECK (EXTRACT(ISODOW FROM samedi) = 6)`
- `requetes.py` → `with conn.transaction():` : le début du « tout ou rien ».
- `requetes.py` → `"DELETE FROM saisies WHERE date = %s AND (equipe_id = %s OR gars_id = ANY(%s))"` : les `%s` et les valeurs passées à part.
- `requetes.py` → `LOCK TABLE saisies IN SHARE ROW EXCLUSIVE MODE` : deux chefs qui enregistrent en même temps passent l'un après l'autre.

**Voir tes données** : Supabase → **Table Editor**, ou **SQL Editor** avec par exemple
`SELECT * FROM gars;`.

## Étape 4 — Saisie du jour (le piège de Streamlit)

**Fait** : page téléphone. On choisit la date et l'équipe. La saisie existante est rechargée, sinon
les gars de l'équipe sont proposés présents, avec le dernier dossier. Un menu par gars
(Présent / Absent · motif), des renforts, un avertissement « déjà noté ailleurs », et une
confirmation s'il n'y a pas de dossier.

**Mots à connaître**
- **Ré-exécution (rerun)** : à CHAQUE clic, Streamlit relance tout le fichier de la page, de haut en bas. Les variables Python normales repartent donc de zéro à chaque fois.
- **`st.session_state`** : la mémoire qui survit aux ré-exécutions (la saisie en cours, l'équipe choisie…). C'est un dictionnaire.
- **`st.form`** : regroupe des champs. Toucher un champ du formulaire ne relance PAS la page : seul le bouton « Enregistrer » la relance, avec toutes les valeurs d'un coup.
- **Callback (`on_change`, `on_click`)** : une fonction appelée par Streamlit juste avant la ré-exécution.
- **Paramètre d'adresse (`?equipe=2`)** : une info dans l'URL. Un favori ou une icône d'écran d'accueil la garde.

**Lignes clés** (`app/pages_app/1_Saisie.py`)
- `if st.session_state.get("saisie_contexte") != contexte:` : on ne relit la base que si la date ou l'équipe a changé.
- `with st.form("form_saisie"):` : les menus Présent/Absent ne déclenchent rien tant qu'on n'enregistre pas.
- `st.session_state["saisie_confirmer"] = contexte` : on se souvient qu'une confirmation est demandée.
- `envoye = st.form_submit_button(` : le seul bouton qui relance la page avec les valeurs du formulaire.

## Étape 5 — Semaine

**Fait** : `services/semaine.py` calcule des tableaux pandas (planning, saisies des chefs,
absences, jours-homme, samedis). La page ne fait qu'afficher. Il y a aussi un export Excel coloré.

**Mots à connaître**
- **DataFrame (pandas)** : un tableau en mémoire (lignes × colonnes), comme une feuille Excel.
- **Fonction « pure »** : elle ne lit ni n'écrit dans la base. Même entrée = même sortie, donc facile à tester.
- **Styler** : l'outil pandas qui colore les cases. Ses couleurs sont reprises dans Excel.
- **Hash stable** : `zlib.crc32` donne toujours le même nombre pour un même code dossier, donc toujours la même couleur. `hash()` de Python change à chaque démarrage.

**Lignes clés** (`app/services/semaine.py`)
- `def construire_grille(` : le cœur du calcul, une ligne par gars.
- `return pd.DataFrame(lignes, columns=colonnes)`
- `return COULEURS[zlib.crc32(code.encode("utf-8")) % len(COULEURS)]`
- `planning = vue.grille.style.map(style_case, subset=vue.jours)` : les couleurs du planning.

**Poser un point d'arrêt** (pour inspecter le DataFrame) :
1. Dans VS Code/Cursor : clique à gauche du numéro de ligne de `return pd.DataFrame(…)` (un point rouge apparaît).
2. Lance le test en mode débogage : icône « Testing » (fiole) → clic droit sur `test_semaine.py` → **Debug Test**.
3. Le programme s'arrête sur la ligne. Le panneau **Variables** montre `lignes`, `jours`… Dans la **Debug Console**, tape `pd.DataFrame(lignes)` pour voir le tableau.

Sans éditeur : ajoute `breakpoint()` sur la ligne voulue, puis lance :
```bash
uv run pytest tests/test_semaine.py -s
```
Le terminal s'arrête sur la ligne. Tape `p lignes` pour afficher une variable, `n` pour avancer d'une ligne, `c` pour continuer. **Retire le `breakpoint()` avant de commiter.**

## Étape 6 — Samedis

**Fait** : demandes pour plusieurs gars, statut modifiable, suppression en deux clics.
Un doublon donne un message propre au lieu d'une erreur rouge.

**Mots à connaître**
- **`UniqueViolation`** : l'exception que psycopg lève quand la contrainte UNIQUE refuse une ligne.
- **Savepoint (sous-transaction)** : un `with conn.transaction():` placé DANS une transaction déjà ouverte. S'il échoue, on annule seulement ce morceau, et la suite continue.

**Comment l'exception remonte jusqu'à l'écran**
1. PostgreSQL refuse l'INSERT (contrainte `une_demande_par_gars_et_samedi`).
2. psycopg transforme ce refus en exception Python `errors.UniqueViolation`.
3. Elle remonte de `requetes.ajouter_demande_samedi` jusqu'à `services/samedis.py`, où le `except` l'attrape. Ce gars va dans la liste « déjà demandé », et les autres sont créés.
4. La page affiche le message en français préparé par `message_resultat`.

**Lignes clés** (`app/services/samedis.py`)
- `with conn.transaction():` : un savepoint par gars.
- `except errors.UniqueViolation:` : l'endroit où l'erreur technique devient une info métier.
- `resultat.deja_demandes.append(nom)`

## Étape 7 — Admin et codes d'accès

**Fait** : tableaux éditables (équipes, gars, dossiers). Un gars ou un dossier qui a de
l'historique passe en inactif au lieu d'être effacé. Deux codes (chefs / admin), un menu
construit selon le code, et un jeton dans l'adresse pour ne pas retaper le code.

**Mots à connaître**
- **`st.data_editor`** : un tableau modifiable comme un mini-Excel.
- **`st.navigation`** : la liste des pages qui existent pour cette personne. Une page absente de la liste n'est pas ouvrable, même en tapant son adresse.
- **`hmac.compare_digest`** : compare deux codes en un temps toujours identique. Un `==` normal s'arrête au premier caractère différent, et cette différence de temps peut aider un pirate à deviner le code.
- **Jeton (HMAC)** : une « empreinte » calculée à partir du code. Elle prouve qu'on connaît le code sans le montrer.

**Lignes clés**
- `acces.py` → `if code_admin and hmac.compare_digest(tape, code_admin.encode()):`
- `Accueil.py` → `pages.append(ADMIN)` : seulement pour le rôle admin.
- `Accueil.py` → `navigation = st.navigation(pages, position="top")`
- `acces.py` → `def exiger(…)` puis `st.stop()` : 2e barrière, en haut de chaque page.
- `admin.py` → `if requetes.gars_a_historique(conn, gars_id):` puis `requetes.desactiver_gars(conn, gars_id)`

**Limites d'un code partagé** (à dire au jury)
- On ne sait pas QUI a fait quoi : les logs disent « chefs », pas « Karim ».
- Si un chef quitte l'entreprise, il faut changer le code pour tout le monde (les anciens liens meurent).
- Le jeton est dans l'adresse : quelqu'un qui récupère le lien a l'accès.
- **Pour aller plus loin** : des comptes individuels (Supabase Auth ou `st.login` avec Google), un rôle par personne en base, et une colonne `saisi_par` dans `saisies`.

## Étape 8 — Fiabilité : relecture, tests, CI, logs

**Fait** : relecture critique. 3 vrais défauts corrigés, chacun avec un test (voir
`docs/decisions.md`). ruff, GitHub Actions et `docs/debug.md` ajoutés. Une panne a été
provoquée exprès (base coupée).

**Mots à connaître**
- **Test unitaire (pytest)** : une petite fonction `test_…` qui vérifie une règle. `assert` = « ceci doit être vrai ».
- **Fixture** : une préparation commune aux tests (ici : un schéma temporaire, des équipes d'exemple).
- **Linter / formateur (ruff)** : repère les erreurs probables et uniformise la mise en forme du code.
- **CI (intégration continue)** : à chaque push, GitHub relance ruff et pytest sur une base neuve. Vert = OK, rouge = quelque chose a cassé.
- **Traceback** : la liste des fonctions traversées par une erreur. La DERNIÈRE ligne dit l'erreur.

**Lignes clés**
- `interface.py` → `def essayer(…)` : le point unique où les erreurs deviennent des messages à l'écran.
- `interface.py` → `except ErreurMetier as erreur:` : erreur prévue, on montre le message.
- `interface.py` → `logger.exception("Erreur inattendue…")` : erreur imprévue, le traceback complet part dans les logs.
- `requetes.py` → `logger.debug("SQL : %s | paramètres : %s", …)` : visible avec `LOG_LEVEL=DEBUG`.
- `.github/workflows/ci.yml` → `run: uv run pytest -v`

**Panne provoquée (base coupée)** : l'écran affichait « Impossible de joindre la base de
données… ». Les logs disaient :
`ERROR | suivi.db.connexion | Connexion à la base impossible : … Connection refused`.
L'écran dit QUOI, le log dit POURQUOI.

## Étape 9 — Mise en ligne

**Fait** : `requirements.txt` pour Streamlit Cloud. `config.py` lit les Secrets en ligne.
Le schéma se crée au démarrage. Checklist dans `docs/mise_en_ligne.md`, README avec l'architecture.

**Mots à connaître**
- **Déploiement** : installer l'app sur un serveur accessible par internet.
- **Secrets** : les variables d'environnement de l'app en ligne, saisies dans l'interface Streamlit, jamais dans le code.
- **Pooler (Session pooler)** : un relais devant la base Supabase, compatible IPv4.
- **IPv4 / IPv6** : deux versions des adresses internet. La connexion directe Supabase est en IPv6 ; Streamlit Cloud ne parle qu'IPv4.

**Le chemin d'un clic « Enregistrer »**
1. Le téléphone du chef envoie le formulaire à Streamlit Cloud (HTTPS, via une connexion « websocket » ouverte en permanence).
2. Streamlit ré-exécute `Accueil.py`, qui vérifie l'accès, puis `1_Saisie.py`. `envoye` vaut `True`.
3. La page appelle `saisie.enregistrer_saisie(…)` (services), qui vérifie les règles (pas de date future, des motifs…).
4. Le service ouvre une connexion (`ouvrir_connexion`) et appelle `requetes.remplacer_saisie`.
5. La transaction part vers Supabase via le Session pooler : LOCK, DELETE, puis un INSERT par gars, et COMMIT.
6. Retour à la page : message « Enregistré : 4 gars ✔ », relecture depuis la base, et une ligne INFO dans les logs.

## Étape 10 — Sauvegarde et réveil

**Fait** : chaque dimanche, une copie de toutes les tables en CSV, gardée 90 jours sur GitHub.
Un script de restauration. En semaine, un navigateur automatique réveille l'app.

**Mots à connaître**
- **cron** : un horaire en 5 champs, `minute heure jour-du-mois mois jour-de-semaine`. Par exemple `30 5,8,11,14 * * 1-5` = à la minute 30, à 5h, 8h, 11h et 14h, tous les jours du mois, tous les mois, du lundi (1) au vendredi (5).
- **UTC** : l'heure de référence mondiale. GitHub Actions ne connaît que l'UTC. Paris = UTC+1 en hiver, UTC+2 en été : 6h30 à Paris = 5h30 UTC l'hiver, mais 4h30 UTC l'été. D'où les deux séries de cron, et le tri selon la saison.
- **Artifact** : un fichier produit par un workflow GitHub, téléchargeable pendant N jours.
- **Playwright** : un navigateur piloté par programme (il clique comme un humain).
- **COPY** : la commande PostgreSQL qui exporte ou importe une table entière en CSV, très vite.

**Lignes clés**
- `reveil.yml` → `- cron: "30 5,8,11,14 * * 1-5" # hiver (UTC+1)`
- `reveil.yml` → `decalage=$(TZ=Europe/Paris date +%z)` : `+0100` = hiver, `+0200` = été.
- `sauvegarde.yml` → `retention-days: 90`
- `requetes.py` → `EXPORT_CSV = sql.SQL("COPY {table} TO STDOUT …")` : un nom de table s'insère avec `sql.Identifier`, jamais avec `%s` ni une f-string.
- `restauration.py` → `with connexion.ouvrir_connexion() as conn, conn.transaction():` : la restauration est tout ou rien.

---

## 10 questions pour vérifier que tu as compris

1. Pourquoi `.env` est-il dans `.gitignore`, et où mets-tu les mêmes valeurs en ligne ?
2. Que se passe-t-il dans la base si la 3e insertion de `remplacer_saisie` échoue ?
3. Pourquoi `%s` protège-t-il contre l'injection SQL, alors qu'une f-string non ?
4. Pourquoi la page Saisie utilise-t-elle `st.form` ? Que se passerait-il sans ?
5. Dans quel fichier une `UniqueViolation` devient-elle un message lisible pour les samedis ?
6. Pourquoi la page Admin est-elle inaccessible au code chefs, même en tapant `/Admin` ?
7. Quelle commande lances-tu pour voir chaque requête SQL dans les logs ?
8. Le badge du README est rouge : où regardes-tu, et dans quel ordre ?
9. Pourquoi utilise-t-on le Session pooler de Supabase et pas la connexion directe ?
10. À quelle heure UTC faut-il programmer un cron pour 15h30 à Paris en juillet ?
