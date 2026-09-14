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
- [ ] Étape 3 — Tableau de bord admin (gestion chantiers/ouvriers)
- [ ] Étape 4 — Calcul des heures et de la prime d'assiduité + export CSV
