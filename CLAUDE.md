# Voxmail — contexte du projet

Assistant WhatsApp (vocal ou texte) qui rédige et envoie des mails depuis le Gmail de l'utilisateur.
Cible : patrons de PME/TPE, artisans, chefs de chantier, mal à l'aise à l'écrit.

## Qui est le développeur
Rayane, 19 ans, débutant (bootcamp Jedha AI Engineering). Deux objectifs à égalité :
1. un produit fiable, vendable à des PME ;
2. apprendre : Rayane doit comprendre chaque ligne qui part en production.

## Comment travailler avec Rayane
- Expliquer en **français**, simplement, ce qu'on fait et **pourquoi**, avant de le faire. Éviter le jargon inutile.
- Code, noms de variables, commentaires et commits en **anglais**. Docs (README, ce fichier) en français.
- Petites étapes. Jamais de gros bloc de code sans explication.
- Fin de chaque phase : récap des concepts, 3 questions de compréhension, attendre la validation.
- Dire franchement quand une consigne est une mauvaise idée, et proposer mieux.
- Pas d'over-engineering. Garder le workflow git simple (commit + push sur la branche de travail).

## Parcours utilisateur (V1)
1. Message WhatsApp (vocal ou texte) : destinataire, objet, contenu.
2. Transcription puis extraction : destinataire, objet, intention.
3. Recherche du destinataire dans les contacts Google et les « autres contacts ».
4. Question courte si une info manque ou est ambiguë, jusqu'à avoir tout.
5. Rédaction d'un mail pro en français (vouvoiement par défaut) avec signature.
6. Aperçu complet (adresse exacte, objet, corps) + boutons Envoyer / Modifier / Annuler.
7. Modifier : boucle de corrections jusqu'à validation ou annulation.
8. Envoi depuis Gmail avec 30 s d'annulation possible, puis confirmation.

## Règles de sécurité (non négociables)
- Le LLM **ne déclenche jamais l'envoi**. Il extrait, rédige, pose des questions. L'envoi est du code
  déterministe, déclenché uniquement par un choix explicite de l'utilisateur (bouton / choix fermé).
- Zéro double envoi : clé d'idempotence par brouillon validé ; déduplication des webhooks par ID.
- Destinataire : le LLM ne choisit JAMAIS l'adresse et n'en invente jamais. Il rapporte ce qu'il a
  entendu (`RecipientHint`), le code classe les contacts, et c'est TOUJOURS l'humain qui choisit
  dans la liste (même avec un seul contact à 99). Seul `Agent.handle_choice` (numéro / tap)
  sélectionne un contact ; une réponse en texte libre = nouveaux indices, nouvelle recherche.
- Adresse jamais utilisée ou dictée à l'oral : faire confirmer l'orthographe.
- Vocal mal compris : reformuler et demander confirmation, ne pas deviner.
- Machine à états explicite, sauvegardée en base :
  COLLECTING → DRAFT_READY → AWAITING_VALIDATION → PENDING_SEND (30 s) → SENT / CANCELLED / FAILED.
- Chaque état expire (brouillon non validé abandonné après ~23 h, car WhatsApp n'autorise
  les messages libres que 24 h après le dernier message de l'utilisateur).

## Google
- Scopes minimaux : `gmail.send`, `contacts.readonly`, `contacts.other.readonly`, `openid`, `email`.
- **Aucun scope Gmail restreint** (readonly, modify, compose, metadata…) : audit CASA payant.
  Donc pas de brouillon côté Gmail, le brouillon vit dans notre base.
- Mode test Google pendant le développement (jetons valables 7 jours seulement), vérification
  Google des scopes sensibles avant la commercialisation (phase 4).
- Jeton expiré : envoyer un lien de reconnexion, ne jamais échouer en silence.

## Stack
Python 3.12+ avec uv · FastAPI · PostgreSQL + SQLAlchemy 2 + Alembic (Docker Compose en local) ·
API Anthropic avec sorties validées par Pydantic · transcription derrière une interface ·
WhatsApp Cloud API (vérifier `X-Hub-Signature-256`) · file d'attente + worker (SQS en prod) ·
pytest, ruff, type hints partout, GitHub Actions · AWS (UE) · Sentry.

## Données et RGPD
- Jetons OAuth chiffrés en base (clé dans Secrets Manager). Aucun secret dans le code.
- Contenu des mails conservé le moins longtemps possible, purge automatique.
- Logs structurés sans contenu de mail ni adresse complète (masquage).
- Hébergement UE.

## Conventions de code
- Code dans `src/voxmail/`, tests dans `tests/`.
- Le cœur (états, règles) ne dépend d'aucun service externe. LLM, contacts, envoi de mail et
  transcription sont derrière de petites interfaces, simulées dans les tests unitaires.
- Configuration uniquement via `voxmail.config.Settings` (variables d'environnement / `.env`).
- Un seul chemin vers l'envoi : `Agent.handle_action(Action.SEND)` depuis AWAITING_VALIDATION,
  puis `Agent.process_due_send` après le délai. Le texte libre ne déclenche jamais d'envoi.
- Tout changement d'état passe par `Conversation.move_to` → `transition()`.
- L'heure est injectée (`clock`) pour que les tests contrôlent le temps.

## Architecture (phase 1)
- `domain/` : `state_machine.py`, `contacts.py` (Contact = 1 adresse, normalisation),
  `phonetic.py` (clé phonétique FRANÇAISE maison, testée), `recipient_search.py`
  (score 0-100 : nom 60 % + contexte 25 % + habitude 15 %, poids dans `Settings`), `models.py`.
- `agent/agent.py` : le LLM extrait (`Extraction`) et rédige (`EmailDraft`) ; le code décide
  de la question suivante et ajoute la signature. Questions posées par du code (texte fixe).
- `llm/` : interface `LLMClient.generate(system, user, output_type)`, `AnthropicLLM`
  (`messages.parse` + Pydantic), `FakeLLM` pour les tests.
- `contacts/` : `ContactDirectory` (JSON factice, Google en phase 2) et `ChoiceMemory`
  (nom entendu → contact choisi, bonus de score, jamais de sélection automatique).
- `mail/` : interface + envoi factice (Gmail en phase 2).
- `evaluation.py` + `evals/scenarios/*.yaml` + `evals/run_evals.py`.

## Recherche du destinataire : règles et décisions
- Un contact n'est proposé que si son NOM (similarité ≥ 0,75) ou son ENTREPRISE (≥ 0,75)
  correspond. L'habitude et les choix appris réordonnent, mais ne qualifient jamais un contact.
- Si une composante manque (pas de nom entendu, ou indice qui ne correspond à personne),
  son poids passe à l'autre ; le poids de l'habitude ne bouge pas.
- Critère : bon contact proposé ≥ 95 %, classé 1er ≥ 80 % (`tests/recipient_cases.py`,
  45 cas sur 36 contacts : 100 % / 98 % actuellement).
- Limite connue : avec nos scopes, Google ne donne ni fréquence ni date d'échange. L'habitude
  sera alimentée par les envois faits via Voxmail et par `ChoiceMemory` (démarre à 0).
- Phase 2 : table `contacts` (user_id, first_name, last_name, full_name, email, company,
  interaction_count, last_interaction_at + champs normalisés) et table des choix appris.
  Synchro proposée : complète à la connexion Google, puis quotidienne (la nuit, incrémentale
  si l'API People le permet — à vérifier), plus une relance à la demande quand une recherche
  ne trouve personne (max 1 fois/heure).
- Phase 3 (transcription) : passer les noms des contacts les plus fréquents comme indice de
  vocabulaire au modèle de transcription. Paramètre et limite de taille À VÉRIFIER dans la
  doc du fournisseur (non accessible depuis cet environnement).

## Commandes
```bash
uv sync                    # installer les dépendances
uv run pytest              # tests
uv run ruff check .        # lint
uv run ruff format .       # formatage
uv run voxmail             # agent dans le terminal (clé Anthropic requise)
uv run python evals/run_evals.py   # évaluation contre le vrai LLM (payant)
```

## Plan
- Phase 0 : initialisation. ✅
- Phase 1 : ✅ code et tests faits ; évaluation réelle à lancer dès qu'une clé API est dispo. Cœur de l'agent en terminal (contacts factices, envoi simulé, machine à états, tests, 30 scénarios d'évaluation, objectif ≥ 90 %).
- Phase 2 : PostgreSQL, OAuth Google, vrais contacts, vrai envoi, idempotence, délai de 30 s.
- Phase 3 : WhatsApp (webhook, signatures, déduplication, boutons, vocaux, file + worker, onboarding).
- Phase 4 : production AWS, Sentry, CI/CD, purge, documents RGPD, runbook.
