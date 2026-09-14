# Pointage & prime d'assiduité

Web app de suivi d'équipe pour chantiers (pointage ouvrier + tableau de bord admin).

## Installation (première fois)

```bash
python3 -m venv venv
source venv/bin/activate      # sous Windows : venv\Scripts\activate
pip install -r requirements.txt
```

## Démarrer le site en local

```bash
source venv/bin/activate
export FLASK_APP=run.py       # sous Windows : set FLASK_APP=run.py

# à faire une seule fois (crée les tables) :
flask init-db

# à faire une seule fois aussi : créer le compte du patron
flask seed-admin

# démarrer le serveur :
python run.py
```

Puis ouvrir http://127.0.0.1:5000 dans le navigateur.

## État du projet

- [x] Étape 1 — Authentification (login/logout) + base de données (comptes, chantiers, pointages, règles de prime)
- [x] Étape 2 — Écran de pointage ouvrier (arrivée/pause/reprise/départ) + résumé mensuel simple
- [x] Étape 3 — Tableau de bord admin (gestion chantiers/ouvriers, filtres, config prime)
- [x] Étape 4 — Calcul des heures et de la prime d'assiduité + export CSV

## Premiers pas pour ton père (l'admin)

1. `flask seed-admin` (une seule fois) crée son compte.
2. Il se connecte, va dans **Chantiers** et crée les chantiers réels (nom, adresse, date, horaires prévus).
3. Il va dans **Ouvriers** et crée un compte par salarié (email + mot de passe qu'il communique de vive voix).
4. Il va dans **Prime d'assiduité** pour ajuster les seuils (tolérance de retard, retards tolérés, durée de pause max, jours requis dans le mois) — les valeurs par défaut sont raisonnables mais modifiables à tout moment.
5. Chaque ouvrier pointe depuis son téléphone (une fois le site déployé en ligne).
6. Le **tableau de bord** centralise heures et statut de prime, avec un export CSV pour la paie.

## Mise en ligne

- [x] Étape 5 — Guide de déploiement (PythonAnywhere, gratuit) : voir [DEPLOY.md](DEPLOY.md)

Le déploiement effectif se fait avec ton propre compte PythonAnywhere (gratuit, sans carte bancaire) — suis le guide pas à pas dans `DEPLOY.md`.
