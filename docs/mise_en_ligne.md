# Mise en ligne — checklist (environ 15 minutes)

Coche chaque étape dans l'ordre. Ce que tu fais dans un navigateur est décrit ici.
Le code, lui, est déjà prêt.

> Les libellés des boutons Supabase et Streamlit peuvent changer un peu avec le temps.
> Si un bouton n'a pas exactement le même nom, cherche le plus proche.

---

## A. Le code sur GitHub, dans son propre dépôt (5 min, sur ton Mac)

Le code est aujourd'hui sur la branche `claude/vigilant-archimedes-fqtvk9` du dépôt
`rayaneouali/mon_projet`. Ce dépôt contient aussi **un autre projet** sur une autre branche
(`claude/relaxed-bell-oepx9e`). Ne le renomme donc pas : crée un dépôt propre.

1. [ ] Ouvre le Terminal dans le dossier où tu ranges tes projets (par exemple `~/projets`).
2. [ ] Crée le dépôt privé :
   ```bash
   gh repo create rayaneouali/suivi-equipes --private
   ```
3. [ ] Récupère uniquement la branche du projet :
   ```bash
   git clone --branch claude/vigilant-archimedes-fqtvk9 --single-branch https://github.com/rayaneouali/mon_projet.git suivi-equipes
   ```
4. [ ] Entre dans le dossier :
   ```bash
   cd suivi-equipes
   ```
5. [ ] Pointe le dossier vers le nouveau dépôt :
   ```bash
   git remote set-url origin https://github.com/rayaneouali/suivi-equipes.git
   ```
6. [ ] Envoie le code sur la branche `main` du nouveau dépôt :
   ```bash
   git push -u origin claude/vigilant-archimedes-fqtvk9:main
   ```
7. [ ] Passe ton dossier local sur `main` :
   ```bash
   git checkout -b main origin/main
   ```
8. [ ] Sur github.com/rayaneouali/suivi-equipes, onglet **Actions** : le workflow **Tests** doit devenir vert ✅.

## B. Supabase : l'adresse de la base (3 min, navigateur)

Ton projet Supabase existe déjà (créé le 9 nov.).

1. [ ] supabase.com → ton projet.
2. [ ] Si tu n'as plus le mot de passe de la base, régénère-le : **Project Settings** → **Database** → **Reset database password**. Range-le tout de suite.
3. [ ] En haut de la page, bouton **Connect** → partie **Session pooler** → copie l'adresse :
   `postgresql://postgres.<ref>:[YOUR-PASSWORD]@aws-…pooler.supabase.com:5432/postgres`
4. [ ] Remplace `[YOUR-PASSWORD]` par le mot de passe. Ne colle cette adresse **nulle part ailleurs** que dans les cases indiquées ci-dessous.

**Pourquoi le Session pooler ?** La connexion « directe » de Supabase ne marche qu'en IPv6,
une version récente des adresses internet. Streamlit Cloud et GitHub Actions ne parlent qu'IPv4.
Le **pooler** est un relais compatible IPv4. Le mode « session » garde une vraie session
PostgreSQL, comme une connexion directe.

## C. Essai sur ton Mac (3 min, facultatif mais conseillé)

1. [ ] Dans le dossier `suivi-equipes`, crée ton fichier de configuration local :
   ```bash
   cp .env.example .env
   ```
2. [ ] Ouvre `.env` dans VS Code/Cursor et remplis-le : `DATABASE_URL` (l'adresse du B.3), `CODE_CHEFS`, `CODE_ADMIN`. Les codes sont dans le récapitulatif final de la session.
3. [ ] Installe les dépendances :
   ```bash
   uv sync
   ```
4. [ ] Lance l'app :
   ```bash
   uv run streamlit run app/Accueil.py
   ```
5. [ ] Ouvre http://localhost:8501 : la page de connexion affiche « Base connectée » en vert. Les tables sont créées toutes seules au premier démarrage.
6. [ ] Pour tester avec des exemples (2 équipes, 6 gars, 2 dossiers) :
   ```bash
   uv run python scripts/seed.py
   ```
7. [ ] **Avant de donner l'app aux chefs**, retire les exemples :
   ```bash
   uv run python scripts/seed.py --effacer
   ```
8. [ ] Lance les tests sur ton Mac, si tu veux :
   ```bash
   uv run pytest
   ```
   Ils travaillent dans un schéma temporaire, sans toucher aux vraies données.

## D. Streamlit Community Cloud (5 min, navigateur)

1. [ ] Va sur **share.streamlit.io** → **Continue with GitHub**. Accepte que Streamlit accède à tes dépôts **privés**.
2. [ ] Bouton **Create app** (ou **New app**) → « Deploy a public app from GitHub » (c'est le nom du bouton, ton dépôt reste privé).
3. [ ] Remplis :
   - **Repository** : `rayaneouali/suivi-equipes`
   - **Branch** : `main`
   - **Main file path** : `app/Accueil.py`
   - **App URL** : par exemple `suivi-equipes-mdc` (c'est le lien que les chefs utiliseront).
4. [ ] **Advanced settings** :
   - **Python version** : **3.12**
   - **Secrets** : colle ce bloc (au format TOML : `NOM = "valeur"`, guillemets obligatoires) :
     ```toml
     DATABASE_URL = "postgresql://postgres.<ref>:MOT_DE_PASSE@aws-…pooler.supabase.com:5432/postgres"
     CODE_CHEFS = "le code chefs à 6 chiffres"
     CODE_ADMIN = "le code admin à 6 chiffres"
     LOG_LEVEL = "INFO"
     ```
5. [ ] **Deploy**. La première installation prend 2 à 5 minutes. Les dépendances sont lues dans `requirements.txt` (ou `uv.lock`).
6. [ ] Si la plateforme demande aux visiteurs de se connecter, rends l'app visible par les chefs : bouton **Share** → *Who can view this app* → **public**. Ton code reste privé, et l'app reste protégée par les codes d'accès.
7. [ ] Pour changer un secret plus tard : sur l'app, **Manage app** → **⋮** → **Settings** → **Secrets**.

## E. Vérification en ligne (5 min, depuis ton téléphone en 4G)

1. [ ] Ouvre le lien de l'app : la page de connexion affiche « Base connectée ».
2. [ ] **Admin** (code admin) : crée les vraies équipes, puis les gars, puis les dossiers.
3. [ ] **Saisie du jour** (code chefs, dans un autre navigateur) : fais une saisie avec un absent et un renfort. Le message « Enregistré : N gars ✔ » doit s'afficher.
4. [ ] Dans Supabase → **Table Editor** → table `saisies` : les lignes sont là.
5. [ ] **Semaine** : la saisie apparaît, l'export Excel s'ouvre.
6. [ ] **Samedis** : crée une demande, puis la même une 2e fois → message « Déjà demandé », sans erreur rouge.
7. [ ] Avec le code chefs, la page **Admin** n'apparaît pas dans le menu.
8. [ ] Envoie aux chefs : le lien + le code chefs + `docs/guide_chefs.md` (ou une capture).

## F. Filets de sécurité GitHub Actions (3 min, navigateur)

Sur github.com/rayaneouali/suivi-equipes → **Settings** → **Secrets and variables** →
**Actions** → **New repository secret**. Crée ces deux secrets :

| Nom du secret | Valeur | Sert à |
|---|---|---|
| `DATABASE_URL` | la même adresse Session pooler qu'au B.3 | Sauvegarde du dimanche soir (`sauvegarde.yml`) |
| `APP_URL` | le lien de l'app, par ex. `https://suivi-equipes-mdc.streamlit.app` | Réveil en semaine (`reveil.yml`) |

Tant qu'un secret manque, son workflow ne fait rien : il affiche juste un message.

1. [ ] Onglet **Actions** → « Sauvegarde hebdomadaire » → **Run workflow**. Une fois le run vert, ouvre-le : en bas, la sauvegarde est téléchargeable dans **Artifacts**. Dézippe-la : un fichier CSV par table, qui s'ouvre dans Excel.
2. [ ] Onglet **Actions** → « Réveil de l'app » → **Run workflow**. Le résumé du run dit si l'app dormait ou était déjà réveillée.

**Restaurer une sauvegarde** (si un jour tout est perdu) : télécharge l'artifact, dézippe-le
dans `sauvegardes/AAAA-MM-JJ/`, puis lance :
```bash
uv run python scripts/restauration.py sauvegardes/AAAA-MM-JJ --oui
```
La base de `DATABASE_URL` (celle de ton `.env`) est **vidée** puis remplie. Pour t'entraîner sans
risque, mets dans `.env` l'adresse d'un 2e projet Supabase vide avant de lancer la commande.

## G. Rester gratuit et en forme

- **Streamlit Cloud** : l'app s'endort après 12 h sans visite. Le workflow de réveil la relance en semaine. Si quelqu'un la trouve endormie : bouton « Yes, get this app back up! », puis environ 30 s d'attente.
- **Supabase** : un projet gratuit **sans activité pendant une semaine** est mis en pause. L'usage quotidien et la sauvegarde du dimanche l'évitent. S'il est en pause : **Restore project** dans Supabase.
- Garde la version Google Apps Script en service **tant que cette version n'a pas tourné une semaine complète** avec les chefs.
