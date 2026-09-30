# Voxmail — Bilan complet du projet

> **Date du bilan** : 30 septembre 2026
> **Auteur du projet** : Rayane Ouali, 19 ans, débutant, bootcamp Jedha AI Engineering.
> **Rédigé par** : Claude (assistant de code), pour être transmis tel quel à un autre LLM
> ou à une personne qui reprend le suivi du projet.
> **Dépôt** : `github.com/rayaneouali/mon_projet`, branche de travail `claude/relaxed-bell-oepx9e`.

---

## 0. Résumé en 10 lignes

1. **Voxmail** est un assistant WhatsApp : un patron de PME ou un artisan dicte un vocal, l'agent rédige un mail professionnel et l'envoie depuis son Gmail, après validation.
2. Le projet suit 5 phases (0 à 4). **La phase 0 est finie, la phase 1 est codée à environ 95 %.**
3. Aujourd'hui, l'agent fonctionne **dans le terminal**, avec des contacts factices et un envoi simulé.
4. **180 tests automatiques passent.** Ils utilisent un faux Claude, donc sans réseau et sans frais.
5. **Point bloquant** : l'agent n'a **jamais été testé avec le vrai Claude**, faute de clé API. L'évaluation (36 scénarios, objectif ≥ 90 %) reste à lancer.
6. Le système de choix du destinataire est terminé : score de proximité, phonétique française, et c'est toujours l'humain qui choisit.
7. Il reste : la base de données et le vrai Gmail (phase 2), WhatsApp (phase 3), la production sur AWS et le RGPD (phase 4).
8. **Coût jusqu'ici : 0 €.** Il faut environ 10 à 20 € de crédit Anthropic pour finir la phase 1.
9. **Coût estimé en production** : environ 40 à 95 $/mois d'infrastructure, plus environ 4 à 20 $ par utilisateur et par mois selon le modèle de Claude choisi.
10. Plusieurs points n'ont pas pu être vérifiés dans la documentation officielle, parce que le réseau de l'environnement la bloquait (voir la section 8).

---

## 1. Le produit

### 1.1 Pour qui
Des gens lents ou mal à l'aise à l'écrit, souvent sur le terrain : patrons de PME et de TPE, artisans, chefs de chantier. Ils veulent envoyer des mails **sans les taper**.

### 1.2 Parcours utilisateur cible (V1)
1. L'utilisateur envoie un vocal ou un texte WhatsApp : à qui il écrit, l'objet, ce que le mail doit dire.
2. L'agent transcrit le vocal et extrait le destinataire, l'objet et l'intention.
3. Il propose les contacts les plus proches. **L'humain choisit toujours** dans la liste.
4. S'il manque une info ou si elle est ambiguë, il pose une question courte, et recommence jusqu'à avoir tout.
5. Il rédige un mail professionnel en français : vouvoiement par défaut, tutoiement si demandé, avec la signature de l'utilisateur.
6. Il envoie un aperçu complet (adresse exacte, objet, corps) avec trois boutons : **Envoyer / Modifier / Annuler**.
7. « Modifier » ouvre une boucle de corrections, jusqu'à validation ou annulation.
8. Après « Envoyer », le mail part depuis le Gmail de l'utilisateur avec **30 s pour annuler**, puis l'agent confirme l'envoi.

### 1.3 Définition de « terminé » pour la V1
Un utilisateur inconnu peut, seul et depuis WhatsApp, connecter son Gmail, dicter un mail par vocal, le corriger, l'envoyer et recevoir une confirmation. Conditions :
- **aucun double envoi** ;
- **aucune perte de conversation** ;
- **une alerte sur le téléphone de Rayane** en cas d'erreur.

---

## 2. Règles non négociables (à faire respecter par tout LLM qui reprend)

### 2.1 Sécurité
- **Le LLM ne déclenche JAMAIS l'envoi.** Il extrait, rédige et pose des questions. L'envoi est du code déterministe, déclenché seulement par un choix fermé de l'utilisateur (bouton ou numéro) sur un aperçu précis.
- **Le LLM ne choisit JAMAIS le destinataire** et n'invente jamais d'adresse. Il rapporte ce qu'il a entendu. Le code classe les contacts, **l'humain choisit**, même s'il n'y a qu'un seul contact avec un score de 99.
- **Zéro double envoi** : une clé d'idempotence par brouillon validé. Les webhooks WhatsApp sont dédupliqués par leur identifiant, parce que Meta renvoie parfois le même.
- **Adresse nouvelle ou dictée** : elle est réécrite lettre par lettre et doit être confirmée explicitement.
- **Vocal mal compris** : l'agent reformule et demande confirmation, il ne devine pas.
- **Machine à états explicite**, sauvegardée en base à partir de la phase 2 :
  `COLLECTING → DRAFT_READY → AWAITING_VALIDATION → PENDING_SEND (30 s) → SENT / CANCELLED / FAILED`.
- **Expiration** : une conversation non validée est abandonnée après **23 h**, pas 24 h. WhatsApp n'autorise les messages libres que dans les 24 h qui suivent le dernier message de l'utilisateur. Il faut donc pouvoir le prévenir avant la fermeture de cette fenêtre.

### 2.2 Google
- Scopes OAuth minimaux : `gmail.send`, `contacts.readonly`, `contacts.other.readonly`, `openid`, `email`.
- **Aucun scope Gmail « restreint »** (readonly, modify, compose, metadata…), parce qu'ils imposent un audit CASA annuel et payant. Conséquence : pas de brouillon côté Gmail, le brouillon vit dans notre base.
- Mode test Google pendant le développement. **Attention**, les jetons n'y durent que 7 jours (à vérifier). Il faudra la vérification Google des scopes sensibles avant de commercialiser : elle est gratuite, contrairement à un audit CASA.
- Si le jeton Google expire, l'agent envoie un lien de reconnexion. Il ne doit jamais échouer en silence.

### 2.3 Données et RGPD
- Jetons OAuth chiffrés en base, avec une clé dans AWS Secrets Manager. Aucun secret dans le code.
- Contenu des mails conservé le moins longtemps possible, avec une purge automatique.
- Logs structurés, sans contenu de mail ni adresse complète en clair (masquage).
- Hébergement dans l'Union européenne.

### 2.4 Façon de travailler avec Rayane (très important pour le LLM suivant)
- Expliquer **en français, simplement**, ce qu'on fait et **pourquoi**, avant de le faire. Éviter le jargon.
- Le code, les noms de variables, les commentaires et les commits sont **en anglais**. La documentation est en français.
- Avancer par petites étapes. Rayane a demandé qu'on enchaîne les étapes sans pause dans une phase. Il faut quand même expliquer à la fin.
- **En fin de phase** : un récap des concepts, **3 questions de compréhension**, puis attendre sa validation.
- Dire franchement quand une consigne est une mauvaise idée, et proposer mieux.
- Pas d'over-engineering. Workflow git simple : commit puis push sur la branche de travail. Rayane ne veut pas de jargon « pull request ».
- Rayane est débutant : il ne connaissait pas `uv.lock` ni `SecretStr`. Il faut vérifier sa compréhension sans le noyer.

---

## 3. Stack technique

| Domaine | Choix | Statut |
|---|---|---|
| Langage | Python 3.12+ (Rayane a Python 3.14 sur son Mac, `uv` installe la 3.12) | ✅ en place |
| Gestion du projet | `uv` (dépendances, environnement, `uv.lock`) | ✅ |
| Qualité | `ruff` (lint et format), `pytest`, type hints partout | ✅ |
| CI | GitHub Actions : lint, format et tests à chaque push | ✅ (`.github/workflows/ci.yml`) |
| LLM | API Anthropic (Claude), sorties structurées validées par Pydantic | ✅ code écrit, ❌ jamais appelé en vrai |
| Similarité de noms | `rapidfuzz` (Jaro-Winkler, token_set_ratio) plus une phonétique française maison | ✅ |
| Serveur web | FastAPI | ⏳ phase 3 |
| Base de données | PostgreSQL, SQLAlchemy 2, Alembic, Docker Compose en local | ⏳ phase 2 |
| Messagerie | API officielle Meta WhatsApp Cloud (webhooks, boutons, listes) | ⏳ phase 3 |
| Transcription | Derrière une interface ; fournisseur à choisir (voir 8.3) | ⏳ phase 3 |
| File d'attente | Simple en local, AWS SQS en production | ⏳ phase 3 |
| Production | AWS (Docker, RDS, SQS, Secrets Manager, CloudWatch), région UE | ⏳ phase 4 |
| Alertes | Sentry | ⏳ phase 4 |

Dépendances actuelles (`pyproject.toml`) : `anthropic`, `pydantic`, `pydantic-settings`, `pyyaml`, `rapidfuzz`. Pour le développement : `pytest`, `ruff`, `types-pyyaml`.

---

## 4. Ce qui a été fait, en détail

### 4.1 Historique des commits (branche `claude/relaxed-bell-oepx9e`)

| Commit | Date | Contenu |
|---|---|---|
| `abc2ed1` | 25/09 | Phase 0 : squelette uv, config, ruff, pytest, CI, `.env.example`, CLAUDE.md, README |
| `acd89ae` | 25/09 | Machine à états et délais d'expiration |
| `0220263` | 25/09 | Première recherche de contacts (remplacée depuis) |
| `8a46f14` | 25/09 | Modèles de conversation ; interfaces LLM, contacts et mail |
| `77a56ae` | 25/09 | Agent (orchestration) et interface terminal |
| `d762af3` | 25/09 | 30 scénarios d'évaluation et script qui les rejoue |
| `f01a294` | 30/09 | Score de proximité des contacts et phonétique française |
| `8d3f0df` | 30/09 | L'humain choisit toujours le destinataire ; 36 scénarios |

Défaut cosmétique connu : dans 3 commits du 25/09, les lignes d'attribution se trouvent au milieu du message au lieu de la fin. C'est sans conséquence, et la réécriture de l'historique a été refusée par l'environnement. On laisse tel quel.

### 4.2 Arborescence et rôle de chaque fichier

```
mon_projet/
├── CLAUDE.md                  # contexte + règles pour toute session d'IA (À LIRE EN PREMIER)
├── README.md                  # installation, commandes, structure (pour humains)
├── docs/BILAN.md              # ce document
├── pyproject.toml / uv.lock   # dépendances (uv.lock = versions exactes, jamais à la main)
├── .python-version            # 3.12
├── .env.example               # toutes les variables de config, documentées, sans secret
├── .github/workflows/ci.yml   # CI : ruff check, ruff format --check, pytest
├── data/fake_contacts.json    # carnet factice de 36 contacts (cas difficiles inclus)
├── src/voxmail/
│   ├── config.py              # Settings (pydantic-settings) : lit .env ; SecretStr pour la clé
│   ├── cli.py                 # interface terminal de la phase 1 (`uv run voxmail`)
│   ├── evaluation.py          # modèle des scénarios YAML + rejoue un scénario + vérifications
│   ├── domain/                # RÈGLES PURES, aucun appel réseau ni base
│   │   ├── state_machine.py   # 7 états, table des passages autorisés, expiration 23 h
│   │   ├── models.py          # Conversation, Extraction (sortie LLM), EmailDraft, Draft,
│   │   │                      #   Action (SEND/EDIT/CANCEL), ReplyKind, AgentReply
│   │   ├── contacts.py        # Contact (1 contact = 1 adresse), normalize(), entreprise
│   │   │                      #   déduite du domaine (sauf gmail, orange…)
│   │   ├── phonetic.py        # clé phonétique FRANÇAISE (Mauger = Maugé = Mojé)
│   │   └── recipient_search.py# RecipientHint (sortie LLM) + score 0-100 + suggestions
│   ├── agent/
│   │   ├── agent.py           # le cerveau : décide la question suivante, seul chemin d'envoi
│   │   └── prompts.py         # instructions données à Claude (extraction, rédaction)
│   ├── llm/                   # base.py (interface), anthropic_client.py (vrai), fake.py (tests)
│   ├── contacts/              # directory.py (source des contacts), memory.py (choix appris)
│   └── mail/sender.py         # interface d'envoi + FakeMailSender idempotent
├── tests/                     # 180 tests (voir 4.6)
│   └── recipient_cases.py     # 45 cas « ce que le LLM a entendu → bon contact »
└── evals/
    ├── scenarios/*.yaml       # 36 scénarios réalistes (9 fichiers)
    └── run_evals.py           # rejoue tout contre le VRAI Claude, affiche le taux de réussite
```

Taille : environ 1 500 lignes de code applicatif et 1 000 lignes de tests.

### 4.3 Comment l'agent fonctionne (flux d'un message)

```
message texte ─► Agent.handle_text
                  ├─ si une liste de contacts attend et que le message est un NUMÉRO
                  │     → Agent.handle_choice (aucun LLM)  ← SEUL moyen de choisir un contact
                  ├─ sinon : Claude EXTRAIT → Extraction (Pydantic)
                  │     recipient: RecipientHint (noms entendus, entreprise, indices, email)
                  │     subject, intent, tone, confirmation, cancel, wants_to_send,
                  │     edit_instruction, unclear + reformulation
                  └─ le CODE décide (_next_step) :
                        pas de destinataire  → liste de suggestions (humain choisit)
                                             → ou « donnez plus d'indices »
                                             → ou confirmation lettre par lettre (adresse nouvelle)
                        pas d'intention      → « Que voulez-vous dire à X ? »
                        tout est là          → Claude RÉDIGE → EmailDraft → aperçu + 3 boutons

bouton ─► Agent.handle_action
            SEND   (seulement depuis AWAITING_VALIDATION) → PENDING_SEND + clé d'idempotence
            EDIT   → « Que voulez-vous modifier ? » (le texte suivant = modification)
            CANCEL → CANCELLED

minuterie ─► Agent.process_due_send  (après 30 s) → envoi → SENT ou FAILED
```

Invariants garantis par le code et testés :
- Tout changement d'état passe par `Conversation.move_to()`, puis par `transition()`. Un passage interdit lève une erreur.
- `PENDING_SEND` n'est accessible que depuis `AWAITING_VALIDATION`, et `SENT` que depuis `PENDING_SEND`.
- Si l'utilisateur écrit « ok envoie », l'agent répond « choisissez Envoyer ». Le texte n'envoie jamais.
- La signature est ajoutée **par le code**, jamais par le LLM.
- L'heure est injectée (`clock`), ce qui permet aux tests de contrôler le temps (30 s, 23 h).
- Une erreur du LLM (réseau, refus, JSON invalide) devient `LLMError`. L'agent répond « problème technique » et la conversation n'est pas perdue.

### 4.4 Le système de choix du destinataire (le module le plus élaboré)

**Ce que Claude renvoie** (`RecipientHint`) :
- `heard_names` : plusieurs hypothèses possibles, par exemple `["Jacques", "Jack"]` ;
- `company` : l'entreprise mentionnée ;
- `other_clues` : les autres indices (« mon comptable ») ;
- `email` : une adresse donnée ou dictée.

**Score de 0 à 100** (`domain/recipient_search.py`) :

| Composante | Poids initial | Calcul |
|---|---|---|
| Nom | 60 % | Meilleur score entre chaque hypothèse et le prénom, le nom, le nom complet (dans les deux ordres) et la partie avant @. C'est une moyenne 50/50 entre l'orthographe (Jaro-Winkler) et le son (Jaro-Winkler sur les clés phonétiques françaises). |
| Contexte | 25 % | `token_set_ratio` entre l'entreprise ou les indices et l'entreprise du contact (ou son nom de domaine). |
| Habitude | 15 % | 60 % fréquence (log du nombre d'échanges) et 40 % récence (décroissance sur environ 60 jours). |
| Choix appris | bonus | +8 points par choix passé pour ce nom entendu, plafonné à +20. |

**Règles clés** :
- Un contact n'est proposé que si son **nom** (similarité ≥ 0,75) ou son **entreprise** (≥ 0,75) correspond vraiment. L'habitude et les choix appris **réordonnent** les contacts, mais n'en font **jamais apparaître** un à eux seuls.
- Si une composante manque (pas de nom entendu, ou un indice qui ne correspond à personne), son poids passe à l'autre. Le poids de l'habitude ne change pas.
- Au maximum 5 propositions, triées par score, suivies de « Aucun de ceux-là ».
- Une réponse en **texte libre** à la liste est traitée comme de **nouveaux indices** : une nouvelle recherche est lancée. Seul un numéro (ou un tap WhatsApp) sélectionne un contact.
- Une adresse connue tapée telle quelle est **quand même** présentée dans une liste d'un seul contact, que l'humain doit toucher.
- Les poids, le seuil et le nombre de propositions sont réglables dans `.env` (`RECIPIENT_*`).

**Phonétique française** (`domain/phonetic.py`) : environ 25 règles de prononciation (au et eau → o, ge → je, er ou é final → e, consonnes finales muettes, nasales an/in/on, ph → f, qu → k, w → v…). Soundex et Metaphone ont été écartés parce qu'ils sont conçus pour l'anglais. Résultats : Mauger, Maugé et Mojé donnent `moj` ; Jacques et Jack donnent `jak` ; Dupont et Dupond donnent `dupO` ; Faure et Fort donnent `for`.

**Mesure sur 45 cas réalistes et 36 contacts** (`tests/recipient_cases.py`) :

| Critère | Objectif | Résultat |
|---|---|---|
| Bon contact proposé | ≥ 95 % | **100 %** (45/45) |
| Bon contact classé 1er | ≥ 80 % | **98 %** (44/45) |
| Nom inconnu : rien proposé | — | 4/4 |

Le seul cas classé 2ᵉ est « Stéphanie », où Stéphane Girard passe devant Stéphanie Girardot grâce à l'habitude. C'est une ambiguïté légitime.

### 4.5 Évaluation avec le vrai LLM (préparée, pas encore lancée)
- 36 scénarios YAML : simple (5), infos manquantes (5), homonymes (4), adresses (4), transcription (4), changement d'avis (3), modifications (3), ton (2), destinataires (6).
- Chaque scénario enchaîne des tours de 4 types possibles :
  - `user` : message ;
  - `action` : bouton ;
  - `choose` : l'humain touche un contact ;
  - `wait` : secondes qui passent.
- Chaque tour a des attentes : état, type de réponse, destinataire, proposition en tête ou incluse, mots dans le corps (sans tenir compte des accents), ton…
- Commande : `uv run python evals/run_evals.py` (ou `--only <id ou catégorie>`). Objectif : **≥ 90 % avant de brancher WhatsApp.**

### 4.6 Tests automatiques (180, tous verts)
- Machine à états : chaque passage interdit est testé automatiquement.
- Phonétique, normalisation, entreprise déduite du domaine.
- Score des destinataires : critères 95 % et 80 %, cas un par un, homonymes, entreprise seule, apprentissage, absence de résultat.
- Agent : 26 scénarios avec un faux Claude et une fausse horloge. Ils couvrent :
  - le choix obligatoire et « Aucun de ceux-là » ;
  - la confirmation d'une adresse nouvelle ;
  - le délai de 30 s, l'annulation et l'idempotence ;
  - l'échec d'envoi, l'expiration à 23 h ;
  - les modifications, et « envoie » écrit en texte qui n'envoie pas.
- Client Anthropic testé **sans réseau**, grâce à un faux transport HTTP : sortie valide, refus, erreur 500. Ces tests ont **trouvé et fait corriger un vrai bug** : un JSON invalide faisait planter l'agent.
- Chargement et validité des 36 scénarios, et fonctionnement du script d'évaluation.

### 4.7 Décisions prises (et pourquoi)

| Décision | Raison |
|---|---|
| Expiration à 23 h au lieu de 24 h | Fenêtre WhatsApp de 24 h : on doit pouvoir prévenir l'utilisateur avant qu'elle se ferme. |
| Le brouillon vit dans notre base, pas dans Gmail | `gmail.compose` est un scope restreint, donc audit CASA payant. |
| Les questions sont posées par du code (phrases fixes), pas par le LLM | Plus fiable, moins cher, et testable. |
| L'objet est proposé par Claude s'il n'est pas dicté | Une question de moins pour l'utilisateur ; l'objet reste visible dans l'aperçu validé. |
| Modèle par défaut `claude-opus-5` | Le plus capable, et la valeur par défaut recommandée. **À réévaluer** : voir les coûts en 7.3, Sonnet 5 est probablement suffisant. |
| Pas de « fallback » en cas de refus du modèle | Fonction beta non testable sans clé ; nos contenus sont anodins. Un refus devient une erreur propre. |
| La phonétique française est écrite à la main | Les algorithmes connus sont anglais ; les bibliothèques françaises sont abandonnées ou très lourdes. |
| Un contact = une adresse | Conforme à la table demandée ; un contact avec 2 adresses donne 2 propositions. |

---

## 5. Mode d'emploi de ce qui existe aujourd'hui

### 5.1 Installation (Mac)
```bash
git clone https://github.com/rayaneouali/mon_projet.git
cd mon_projet
git checkout claude/relaxed-bell-oepx9e
uv sync                 # installe Python 3.12 + dépendances
cp .env.example .env    # puis mettre ANTHROPIC_API_KEY=sk-ant-...
```

### 5.2 Commandes
```bash
uv run pytest                        # 180 tests, sans réseau, gratuit
uv run ruff check . && uv run ruff format .
uv run voxmail                       # l'agent dans le terminal (clé API requise)
uv run python evals/run_evals.py     # évaluation contre le vrai Claude (payant)
```

### 5.3 Exemple de session (vérifié avec un faux Claude)
```
vous > mail à Jacques de chez Mecalux pour la livraison des racks
🤖 J'ai compris : « Jacques » ou « Jack », de chez Mecalux.
   À qui voulez-vous écrire ?
   1. Jacques Mauger (jacques.mauger@mecalux.fr)
   2. Jacques Bertin (j.bertin@mecalux.fr)
   ...
   6. Aucun de ceux-là
vous > 2
🤖 À : Jacques Bertin <j.bertin@mecalux.fr>
   Objet : Date de livraison des racks
   Bonjour Monsieur Bertin, ...
   Rayane Ouali
   1) Envoyer   2) Modifier   3) Annuler
vous > 1
🤖 Envoi dans 30 secondes. Vous pouvez encore annuler.
   ⏳ Appuyez sur Entrée pour annuler.
🤖 ✅ Mail envoyé à j.bertin@mecalux.fr.     (simulation : aucun vrai mail)
```

### 5.4 Variables de configuration (`.env`)
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (par défaut `claude-opus-5`)
- `USER_SIGNATURE`, `CONTACTS_FILE`, `SEND_DELAY_SECONDS`
- `RECIPIENT_NAME_WEIGHT`, `RECIPIENT_CONTEXT_WEIGHT`, `RECIPIENT_HABIT_WEIGHT`, `RECIPIENT_MIN_SCORE`, `RECIPIENT_MAX_SUGGESTIONS`
- `APP_ENV`, `LOG_LEVEL`

---

## 6. Ce qu'il reste à faire

### 6.1 Finir la phase 1 (priorité immédiate)
1. **Rayane crée une clé API Anthropic** (console.anthropic.com) et ajoute 10 à 20 € de crédit.
2. Tester à la main avec `uv run voxmail`.
3. Lancer `evals/run_evals.py` et viser **≥ 90 %**. Si ce n'est pas atteint, améliorer les instructions dans `agent/prompts.py`, scénario raté par scénario raté.
4. Comparer `claude-opus-5`, `claude-sonnet-5` et `claude-haiku-4-5` sur l'évaluation, puis choisir selon la qualité, le prix et la latence. Le mieux est sans doute un modèle rapide pour l'extraction et un meilleur modèle pour la rédaction.
5. Mesurer le coût réel par mail (`response.usage`) pour valider les estimations de la section 7.
6. Faire passer à Rayane le récap de fin de phase et les **questions de compréhension restées sans réponse** (section 10).
7. Faire grandir les scénarios : de 36 à l'objectif de 100.

### 6.2 Phase 2 : persistance et vrai Gmail
- PostgreSQL avec Docker Compose, SQLAlchemy 2 et Alembic. Tables envisagées :
  - `users` : jetons OAuth **chiffrés**, signature ;
  - `conversations` : état, données, `state_entered_at`, `send_at`, `idempotency_key` **unique** ;
  - `contacts` : user_id, first_name, last_name, full_name, email, company, interaction_count, last_interaction_at, plus les champs normalisés ;
  - `recipient_choices` : user_id, nom entendu normalisé, email, compteur ;
  - `sent_emails` : minimal, pour l'idempotence et l'historique, avec une purge.
- Une implémentation PostgreSQL de `ConversationRepository`. Un redémarrage ne doit jamais perdre une conversation.
- OAuth Google avec les scopes minimaux, un lien de reconnexion si le jeton expire, et le mode test.
- `GooglePeopleContactDirectory` : contacts et « autres contacts ». Synchronisation complète à la connexion, puis quotidienne (incrémentale si l'API le permet, à vérifier), plus une relance quand une recherche ne trouve personne (au maximum une fois par heure).
- `GmailSender` avec l'API `users.messages.send` et l'idempotence en base (la clé est marquée « envoyée » dans une transaction).
- Un vrai délai de 30 s qui survit à un redémarrage : une tâche planifiée lue en base.
- Mettre à jour `interaction_count` et `last_interaction_at` après chaque envoi.
- Logs structurés avec masquage des adresses et des contenus.

### 6.3 Phase 3 : WhatsApp
- Webhook FastAPI qui répond en moins d'une seconde, vérification de la signature `X-Hub-Signature-256`, déduplication par identifiant de message.
- File d'attente et worker (simple en local, SQS en production).
- Messages interactifs :
  - **boutons** pour Envoyer / Modifier / Annuler (3 au maximum) ;
  - **message liste** pour les propositions de contacts (jusqu'à 10 lignes, à vérifier).
- Transcription des vocaux derrière une interface `Transcriber`, avec un **indice de vocabulaire** contenant les noms des contacts fréquents (paramètre et limite à vérifier chez le fournisseur).
- Un **template** pré-approuvé par Meta, pour prévenir de l'expiration hors de la fenêtre de 24 h.
- Arrivée d'un nouvel utilisateur : premier message WhatsApp → lien de connexion Google → message de bienvenue.

### 6.4 Phase 4 : production
- Déploiement AWS en région UE (Paris `eu-west-3`) : voir les options et les coûts en 7.2.
- Secrets Manager, Sentry avec alerte sur le téléphone, CI/CD (déploiement automatique), purge automatique des données.
- **Vérification Google** des scopes sensibles, pour dépasser 100 utilisateurs et avoir des jetons qui ne périment pas au bout de 7 jours.
- Documents RGPD (brouillons à faire relire) : politique de confidentialité, CGU, registre des traitements, liste des sous-traitants (Anthropic, Meta, Google, AWS, fournisseur de transcription, Sentry).
- Guide de dépannage (runbook) : envoi échoué, accès Google coupé, WhatsApp muet.

### 6.5 Dette technique et points connus
- Le vrai Claude n'a jamais été appelé : le format exact des réponses et la qualité des extractions restent à confirmer.
- Avec `claude-opus-5`, la réflexion (« thinking ») est activée par défaut. Chaque appel peut donc prendre plusieurs secondes et coûter plus cher. À mesurer ; régler `effort` ou changer de modèle.
- `ChoiceMemory` et les conversations sont **en mémoire seulement** : elles sont perdues à l'arrêt, jusqu'à la phase 2.
- Le compte à rebours du terminal utilise `select` : il fonctionne sur Mac et Linux, pas sur Windows. Sans importance, c'est un outil temporaire.
- Pas encore de logs.
- Le scénario `hesitant_voice_message` a des attentes faibles au premier tour.
- Les lignes d'attribution sont mal placées dans 3 anciens commits (cosmétique).

---

## 7. Les coûts

> ⚠️ **Tous les prix sont des estimations** (septembre 2026), faites de mémoire ou à partir de la documentation interne de l'outil de code. La documentation des fournisseurs n'était pas accessible depuis cet environnement. **Il faut les vérifier** sur les pages de tarifs officielles et avec le calculateur AWS avant toute décision commerciale. Les prix des API sont en dollars US.

### 7.1 Ce qui a été dépensé jusqu'ici
**0 €.** Tout a tourné avec un faux Claude. Aucun service payant n'a été utilisé.

### 7.2 Frais de développement (phases 1 à 3)

| Poste | Estimation | Commentaire |
|---|---|---|
| Crédit Anthropic | 10 à 20 $ | Tests manuels, puis évaluations : environ 1 à 4 $ par passage complet des 36 scénarios selon le modèle |
| Transcription (tests) | < 5 $ | Quelques centaines de minutes au maximum |
| WhatsApp Cloud API | 0 € | Meta fournit un numéro de test gratuit en développement |
| Google Cloud (OAuth, People, Gmail API) | 0 € | Gratuit dans les quotas ; vérification des scopes sensibles gratuite |
| GitHub + GitHub Actions | 0 € | Gratuit pour ce volume |
| Docker, PostgreSQL local | 0 € | |
| **Total jusqu'à la phase 3** | **environ 20 à 30 €** | |

> **Correction importante** : j'avais annoncé plus tôt « 1 à 3 centimes par mail » et « 1 à 2 € par évaluation ». En recalculant avec la taille réelle des instructions (environ 2 000 tokens par extraction), plusieurs appels par mail et la réflexion activée par défaut sur Opus 5, **c'est plutôt 4 à 10 centimes par mail avec Opus 5**, et 1 à 4 $ par évaluation. Le détail est en 7.3.

### 7.3 Coût variable par utilisateur (en production)

**Hypothèse** : un utilisateur envoie 10 mails par jour ouvré, soit environ 220 mails par mois, dont 60 % dictés en vocal de 40 s en moyenne. Un mail demande en moyenne 3 à 4 appels à Claude (extraction, éventuelles questions, rédaction, corrections), soit environ 6 000 tokens en entrée et 2 500 en sortie, réflexion comprise.

| Modèle Claude | Prix (entrée / sortie, par million de tokens) | Coût par mail | Coût par utilisateur et par mois |
|---|---|---|---|
| `claude-opus-5` (défaut actuel) | 5 $ / 25 $ | environ 0,09 $ | **environ 20 $** |
| `claude-sonnet-5` | 2 $ / 10 $ | environ 0,04 $ | **environ 9 $** |
| `claude-haiku-4-5` | 1 $ / 5 $ | environ 0,02 $ | **environ 4,5 $** |

| Autre poste | Estimation par utilisateur et par mois |
|---|---|
| Transcription (environ 90 min/mois à 0,001–0,006 $/min selon le fournisseur) | 0,10 à 0,50 $ |
| WhatsApp : conversations ouvertes par l'utilisateur (réponses dans les 24 h) | 0 € (gratuites selon la tarification Meta actuelle, à vérifier) |
| WhatsApp : templates hors fenêtre de 24 h (rappel d'expiration) | quelques centimes chacun ; peu fréquents |
| API Gmail et People | 0 € |

**Recommandation** : tester Sonnet 5, et Haiku pour l'extraction, avec l'évaluation. Si la qualité tient (≥ 90 %), le coût par utilisateur passe d'environ 20 $ à 5–10 $. La mise en cache des instructions peut réduire un peu le coût en entrée, mais nos instructions sont peut-être trop courtes pour être mises en cache (à vérifier).

### 7.4 Coût fixe de l'infrastructure AWS (région Paris, par mois)

**Option A — recommandée pour la fiabilité** : ECS Fargate, avec répartiteur de charge et RDS.

| Service | Estimation par mois |
|---|---|
| ECS Fargate : 2 petites tâches 24h/24 (serveur web et worker, 0,25 vCPU / 0,5 Go) | 20 à 25 $ |
| Application Load Balancer (HTTPS pour le webhook) | 20 à 25 $ |
| RDS PostgreSQL `db.t4g.micro`, une seule zone, 20 Go | 15 à 20 $ (le double en multi-zones) |
| Adresses IPv4 publiques (environ 0,005 $/h chacune) | 7 à 15 $ |
| Secrets Manager (environ 5 secrets à 0,40 $) + une clé KMS (1 $) | environ 3 $ |
| CloudWatch Logs | 1 à 5 $ |
| SQS (1 million de requêtes gratuites par mois) | environ 0 $ |
| ECR (images Docker) | < 1 $ |
| **Total option A** | **environ 70 à 95 $/mois** |

**Option B — la moins chère pour démarrer** : une petite machine EC2 (`t4g.small`) qui fait tourner le serveur et le worker avec Docker Compose, plus RDS.
- EC2 environ 15 $, disque environ 2 $, IPv4 environ 4 $, RDS environ 16 $, divers environ 5 $.
- **Total : environ 40 à 45 $/mois.**
- Moins fiable : une seule machine, et les mises à jour sont à gérer soi-même.

À éviter : le **NAT Gateway** (environ 35 $/mois ou plus), en plaçant les tâches dans des sous-réseaux publics. À vérifier : les crédits d'offre gratuite AWS pour les nouveaux comptes.

### 7.5 Autres frais pour lancer et vendre

| Poste | Estimation |
|---|---|
| Nom de domaine (site, pages CGU et confidentialité, redirection OAuth) | 10 à 15 €/an |
| Numéro de téléphone dédié au WhatsApp de production | 0 à 10 €/mois |
| Vérification Meta Business, vérification Google | 0 € (mais demandent un site, des CGU, une politique de confidentialité et une vidéo de démo pour Google) |
| Sentry (offre gratuite pour développeur) | 0 € au départ |
| Relecture juridique des CGU, de la confidentialité et du registre RGPD | variable, environ 300 à 1 500 € si c'est un professionnel |
| Statut pour facturer (micro-entreprise) | création gratuite ; charges selon le chiffre d'affaires |
| Assurance responsabilité civile professionnelle (conseillée) | environ 100 à 300 €/an |

### 7.6 Exemple de budget total (hypothèses)
- **Phase de test avec 5 clients pilotes, Sonnet 5, option B** : 45 $ + 5 × 9 $ ≈ **90 $/mois**.
- **30 clients, Sonnet 5, option A** : 85 $ + 30 × 9 $ ≈ **355 $/mois**, soit environ 12 $ par client.
- Donc un prix de vente de **29 à 49 € par utilisateur et par mois** laisse une marge confortable, **à condition** d'utiliser Sonnet ou Haiku et de surveiller la consommation. Avec Opus 5 à 20 $ par utilisateur, la marge fond.

---

## 8. Points non vérifiés (à contrôler dans la documentation officielle)

Le réseau de l'environnement de développement a bloqué `developers.google.com` et `docs.mistral.ai`. Pour y accéder, il faut autoriser ces domaines dans les réglages réseau de l'environnement cloud.

1. **Classification des scopes Google**. De mémoire : `gmail.send`, `contacts.readonly` et `contacts.other.readonly` sont « sensibles » ; `gmail.readonly`, `modify`, `compose` et `metadata` sont « restreints ». **À vérifier avant la phase 2.**
2. **Durée de vie des jetons en mode test Google** : 7 jours de mémoire. Et le nombre maximal d'utilisateurs de test (100).
3. **Transcription** : choix du fournisseur et paramètre d'indice de vocabulaire (nom du paramètre, limite de taille, langues). Pistes :
   - Mistral Voxtral : entreprise européenne, intéressant pour le RGPD ;
   - OpenAI `gpt-4o-transcribe` : paramètre `prompt`, limite de taille à vérifier.
4. **API People** : synchronisation incrémentale (`syncToken`) pour les contacts et les « autres contacts ».
5. **WhatsApp** : tarification actuelle (par message, gratuité des réponses dans la fenêtre de 24 h), nombre maximal de lignes d'un message liste, règles des templates.
6. **Anthropic et RGPD** : où sont traitées les données (paramètre `inference_geo`, valeurs disponibles), accord de sous-traitance (DPA), transferts hors UE.
7. **Tous les prix** de la section 7.

---

## 9. Si tout se passe bien : calendrier indicatif
Rayane est débutant et à temps partiel. C'est une estimation grossière.

| Étape | Durée estimée | Résultat |
|---|---|---|
| Fin de phase 1 (clé API, évaluation ≥ 90 %, choix du modèle) | 1 à 2 séances | Agent validé en terminal |
| Phase 2 (PostgreSQL, OAuth, vrais contacts, vrai envoi) | 2 à 3 semaines | Mails réels envoyés depuis le Gmail de Rayane |
| Phase 3 (WhatsApp, vocaux, file et worker, onboarding) | 3 à 4 semaines | Utilisable par Rayane depuis son téléphone |
| Phase 4 (AWS, Sentry, RGPD, runbook, vérification Google) | 2 à 4 semaines, plus les délais de validation Google et Meta (parfois plusieurs semaines) | Premiers clients pilotes |
| **Total jusqu'à la V1 vendable** | **environ 2 à 3 mois** | |

---

## 10. Suivi pédagogique (pour le LLM qui reprend)

Questions posées à Rayane **restées sans réponse** (à reposer, simplement) :

Fin de phase 1 :
1. Pourquoi l'agent reçoit-il un « faux Claude » dans les tests au lieu du vrai ? Deux raisons.
2. L'utilisateur écrit « c'est parfait, envoie-le ». Pourquoi le mail ne part-il pas, et qu'est-ce qui le fait partir ?
3. À quoi sert la clé d'idempotence si le code appelle deux fois l'envoi du même mail ?

Système de choix du destinataire :
4. Pourquoi l'habitude ne peut-elle pas, à elle seule, faire apparaître un contact ?
5. Pourquoi comparer le **son** des noms et pas seulement leur orthographe ?
6. Pourquoi « Jean Martin » tapé au lieu de « 2 » ne sélectionne-t-il pas directement le contact ?

Concepts déjà expliqués :
- `.env` et `.env.example` (Rayane a bien compris) ;
- `uv.lock` (analogie de la liste de courses : « Barilla n°5, 500 g ») ;
- `SecretStr` (le texte qui refuse de s'afficher) ;
- machine à états et `transition()` ;
- Enum ; dataclass (`frozen`) ; type hints ;
- exceptions ; `parametrize` ;
- interfaces (Protocol) ; injection de dépendances ;
- sorties structurées ; idempotence ;
- évaluation d'un LLM ; normalisation ; similarité de chaînes ; phonétique.

---

## 11. Instructions pour le LLM qui reprend le projet
1. Lire `CLAUDE.md` à la racine : c'est la source de vérité des règles et conventions.
2. Lancer `uv sync && uv run pytest` : tout doit être vert (180 tests) avant de modifier quoi que ce soit.
3. Ne jamais affaiblir les invariants de la section 2 et de la section 4.3 :
   - pas d'envoi sans `Action.SEND` ;
   - pas de choix de contact sans `handle_choice` ;
   - tout changement d'état passe par `move_to`.
4. Chaque nouvelle fonctionnalité s'accompagne de tests. Chaque comportement du LLM s'accompagne de scénarios YAML.
5. Parler à Rayane en français simple, expliquer avant de coder, et poser 3 questions en fin de phase.
6. **Prochaine action concrète** : aider Rayane à obtenir une clé API Anthropic, lancer `uv run voxmail`, puis `uv run python evals/run_evals.py`, et analyser les échecs.
