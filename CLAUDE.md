# CLAUDE.md — Suivi équipes MDC

Ce fichier est relu automatiquement par Claude Code à chaque session.
Il décrit le projet, la stack, ma façon de travailler et les règles de code.

---

## 1. Contexte

- Je gère le suivi des dossiers chez **MDC**, une entreprise familiale de montage
  de rayonnage industriel (~14 salariés, plusieurs équipes de monteurs).
- Chaque semaine, je dois savoir :
  - qui est dans quelle équipe ;
  - qui est absent, et pourquoi ;
  - sur quel dossier / chantier chaque équipe travaille ;
  - à qui on a demandé de travailler un samedi.
- **Objectif** : une app web simple qui remplace mon agenda, remplie chaque jour
  par les chefs d'équipe depuis leur téléphone.
  - Elle doit être **fiable**, **gratuite** et **rester simple** :
    pas d'heures de pointage, pas de pauses.
- **Version de référence** : une première version existe en Google Apps Script
  (`Code.gs` et `Index.html`), rangée dans `docs/reference_apps_script/`.
  C'est le **cahier des charges fonctionnel** : on reprend ses **règles métier**,
  pas sa technique.

## 2. Stack (décidée — ne pas changer sans me demander)

**Principe : le plus simple possible.** Le moins d'outils à installer et à faire
tourner. Pas de Docker : la seule base est sur Supabase.

| Brique | Choix |
|---|---|
| Langage | Python 3.12, environnement géré avec **uv** |
| Interface | **Streamlit** (multipage) |
| Base de données | **PostgreSQL sur Supabase** (offre gratuite), la même en local et en ligne. Requêtes SQL écrites en clair avec **psycopg 3**, toutes regroupées dans un seul module. **Pas d'ORM.** |
| En local | `uv run streamlit run app/Accueil.py` sur mon Mac, branché sur la base Supabase |
| En ligne | App sur **Streamlit Community Cloud**, déployée depuis GitHub |
| Tests | **pytest**. Les tests qui touchent la base travaillent dans un **schéma séparé** qu'ils créent puis effacent : ils ne touchent jamais aux vraies données. Ils tournent aussi sur GitHub Actions à chaque push. |
| Configuration | Variables d'environnement (`.env` en local, **jamais commité** ; `st.secrets` en ligne) |
| Code | GitHub `rayaneouali/mon_projet` (sera renommé `suivi-equipes`) |

Contrainte machine : MacBook Pro M2, 8 Go de RAM, peu d'espace disque
→ rester léger, ne rien installer d'inutile.

**Sécurité Supabase** : le projet a été créé avec la « Data API » activée.
Donc **chaque table** créée dans `schema.sql` doit avoir
`ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` (aucune policy) : ça bloque l'accès
par la Data API, sans gêner l'app (propriétaire des tables).

## 3. Qui je suis et comment on travaille

- Je suis en formation **Jedha Fullstack IA**. Ce projet sert à apprendre.
- Je ne vise pas à devenir expert codeur : je veux **comprendre le système**,
  savoir **superviser**, **repérer une erreur** dans le code et **débugger**.

### Avant chaque étape
- Donne-moi un **plan court** : fichiers créés / modifiés, et ce que fait chacun.
- **Attends mon OK** avant de coder.

### Après chaque étape, explique simplement ce que tu as fait
- Définis chaque terme technique **la première fois** que tu l'utilises,
  sans empiler le jargon.
- Montre-moi les **3 à 5 lignes clés** à savoir reconnaître (pas tout le code).
- Donne-moi **une commande** pour vérifier moi-même que ça marche.
- Termine par **une seule question** de compréhension.

### À la fin de chaque étape validée
- Un **commit** avec un message clair **en français**, puis un **push**.

### Mode autonome (quand je le demande explicitement)
Quand je lance une session en écrivant « MODE AUTONOME », le fonctionnement change
**pour cette session seulement** :
- tu enchaînes les étapes demandées **sans attendre mon OK** entre elles ;
- après chaque étape : `uv run pytest` et `uv run ruff check .` doivent passer, et l'app
  doit démarrer ; puis un commit « Étape N : … » et un push. Pas d'étape suivante si un test est rouge ;
- si une commande échoue, tu diagnostiques et corriges toi-même ;
- tu ne m'arrêtes que pour une action physique (me connecter à un service,
  installer un outil qui demande mon mot de passe) : commande exacte, puis tu attends ;
- pour un choix de bibliothèque ou de détail technique : l'option la plus simple et la plus
  lisible, notée dans `docs/decisions.md` (une ligne : quoi, pourquoi) ;
- interdit : changer la stack ci-dessous, effacer un fichier que tu n'as pas créé, force-push ;
- à la fin seulement : récapitulatif court + `docs/apprendre.md` (pour réviser) +
  liste de ce qu'il me reste à faire.
Sans « MODE AUTONOME », la règle normale s'applique : plan court, puis attendre mon OK.

## 4. Règles de code (pour que je puisse lire et débugger)

- **Clair plutôt que malin.** Fonctions courtes.
- **Noms explicites en français** pour le métier : `gars`, `equipe`, `dossier`,
  `saisie`, `samedi`.
- **Type hints partout.** Une **docstring d'une ligne** par fonction.
- **Séparation stricte en trois couches** :
  - interface → pages Streamlit ;
  - logique métier → `services` ;
  - accès base → `db`.
  - **Aucune requête SQL dans les pages.**
- **Logging** avec le module `logging` (jamais de `print`).
  Niveau réglable via la variable `LOG_LEVEL`.
- **Erreurs** : message en **français simple** pour l'utilisateur,
  **détail technique dans les logs**.
- **Aucun secret dans le code.** Un fichier `.env.example` documenté.
- **Un test pytest pour chaque règle métier.**
