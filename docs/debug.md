# Débugger l'app — les 5 pannes les plus probables

**Règle d'or** : l'écran dit *quoi* en français simple, les **logs** disent *pourquoi*.
Commence toujours par les logs.

| Où tourne l'app | Où lire les logs |
|---|---|
| Sur ton Mac | Le terminal où tu as lancé `uv run streamlit run app/Accueil.py` |
| En ligne (Streamlit Cloud) | Ouvre l'app → bouton **Manage app** en bas à droite → panneau des logs |
| Tests automatiques (GitHub) | Onglet **Actions** du dépôt → le dernier run → étape en rouge |

Pour voir **chaque requête SQL** exécutée : mets `LOG_LEVEL=DEBUG` dans `.env`
(ou dans les Secrets en ligne), puis relance. Remets `INFO` après.

Une ligne de log se lit ainsi :
```
2026-11-09 14:36:51 | ERROR   | suivi.db.connexion | Connexion à la base impossible : …
   date et heure    | gravité | qui parle (module) | le message
```

---

## 1. La base est injoignable

**Symptôme** : à l'écran, « Impossible de joindre la base de données… ».

**Où regarder** : les logs, ligne `ERROR | suivi.db.connexion`. Exemple réel (panne
provoquée en coupant la base) :
```
ERROR   | suivi.db.connexion | Connexion à la base impossible : connection failed:
          connection to server at "127.0.0.1", port 5432 failed: Connection refused
WARNING | suivi.interface | Refusé : Impossible de joindre la base de données…
```

**Causes fréquentes, et quoi faire** :
- **Projet Supabase en pause.** En offre gratuite, un projet sans activité pendant une semaine est mis en pause. Va sur supabase.com → ton projet → **Restore project**.
- **Mauvais mot de passe** dans `DATABASE_URL`. Le log dit `password authentication failed`. Régénère le mot de passe (Project Settings → Database), puis mets à jour `.env` et les Secrets.
- **Connexion directe au lieu du Session pooler.** Le log dit `Network is unreachable` ou `could not translate host name`. Reprends l'adresse **Session pooler** (bouton Connect).
- **Pas d'internet** sur le Mac ou le téléphone.

**Commande utile** (sur le Mac, teste la connexion sans lancer l'app) :
```bash
uv run python -c "import sys; sys.path.insert(0, 'app'); from db.connexion import verifier_connexion; print(verifier_connexion())"
```

## 2. Une variable d'environnement manque

**Symptôme** : « DATABASE_URL n'est pas définie… », ou bien « Les codes d'accès ne sont pas
configurés (CODE_CHEFS et CODE_ADMIN) », ou encore « … sont identiques ».

**Où regarder** : le fichier `.env` sur le Mac (copié depuis `.env.example`), ou les
**Secrets** de l'app sur Streamlit Cloud (Manage app → ⋮ → Settings → Secrets).
Attention aux fautes de frappe dans le NOM de la variable.

**Commande utile** (affiche les variables lues, sans montrer les valeurs) :
```bash
uv run python -c "import sys; sys.path.insert(0, 'app'); import config; print({n: bool(config.lire(n)) for n in ['DATABASE_URL','CODE_CHEFS','CODE_ADMIN','LOG_LEVEL']})"
```
`False` = variable absente ou vide.

## 3. Le port 8501 est déjà utilisé

**Symptôme** : au lancement, `Port 8501 is already in use`, ou l'app s'ouvre sur `:8502`
au lieu de `:8501`.

**Où regarder** : un autre Streamlit tourne déjà (un vieux terminal ouvert).

**Commandes utiles** (Mac) :
```bash
lsof -i :8501
```
Cette commande montre le programme qui occupe le port (colonne PID). Pour l'arrêter :
```bash
kill <PID>
```
Ou lance l'app sur le port suivant :
```bash
uv run streamlit run app/Accueil.py --server.port 8502
```

## 4. Une contrainte de la base est violée

**Symptôme** : « Problème technique inattendu… ». Les cas prévus, eux, ont déjà un message clair :
doublon de demande de samedi, nom déjà pris dans Admin.

**Où regarder** : dans les logs, une ligne `ERROR … Erreur inattendue dans …` suivie d'un
« Traceback ». Lis la **dernière ligne** du traceback, par exemple :
```
psycopg.errors.CheckViolation: new row for relation "demandes_samedi" violates
check constraint "samedi_obligatoire"
```
Le **nom de la contrainte** te dit quelle règle a bloqué. Ces noms sont dans `app/db/schema.sql` :
`un_gars_un_endroit_par_jour`, `samedi_obligatoire`, `une_demande_par_gars_et_samedi`,
`motif_seulement_si_absent`…

**Commande utile** : relance avec `LOG_LEVEL=DEBUG` pour voir la requête SQL exacte et ses
paramètres juste avant l'erreur. Puis reproduis le cas dans un test (`tests/`) :
```bash
uv run pytest -k samedi -v
```

## 5. L'app en ligne est endormie

**Symptôme** : le lien affiche une page Streamlit avec un bouton
« **Yes, get this app back up!** ». Ce n'est pas une panne : sans visite pendant 12 h,
l'app gratuite s'endort.

**Que faire** : clique sur le bouton et attends ~30 secondes. Le workflow
`.github/workflows/reveil.yml` le fait automatiquement en semaine (6h30, 9h30, 12h30, 15h30)
une fois le secret `APP_URL` défini (voir `docs/mise_en_ligne.md`).

**Où regarder** : GitHub → onglet **Actions** → « Réveil de l'app » : chaque passage dit
s'il a trouvé l'app endormie ou déjà réveillée.

---

## Méthode quand tu es seul face à une panne

1. **Lis le message à l'écran** : il dit quelle action a échoué.
2. **Ouvre les logs** et cherche la dernière ligne `ERROR` ou `WARNING`, à l'heure de la panne.
3. **Lis la dernière ligne du Traceback** : le type d'erreur et le fichier où elle naît.
4. **Reproduis** avec `LOG_LEVEL=DEBUG` (tu vois le SQL), puis avec un test pytest.
5. **Une seule hypothèse à la fois** : change une chose, relance, regarde.
