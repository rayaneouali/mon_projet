# Mettre le site en ligne (PythonAnywhere, gratuit)

Ce guide t'explique comment publier le site sur Internet, avec une vraie
adresse accessible depuis n'importe quel téléphone. Compte prévu pour
la vie du projet : gratuit, sans carte bancaire, avec stockage qui ne
s'efface jamais entre deux mises à jour.

**Limite à connaître** : contrairement à un hébergeur payant, PythonAnywhere
ne se met pas à jour tout seul quand on modifie le code. Après chaque
changement, il faudra refaire les étapes 6 et 7 de ce guide (2 commandes +
un clic). C'est expliqué à la fin.

---

## 1. Créer le compte

Va sur https://www.pythonanywhere.com/, clique sur "Pricing & signup", puis
choisis l'offre **"Create a Beginner account"** (gratuite). Choisis un nom
d'utilisateur simple : ce sera l'adresse de ton site, par exemple
`https://tonpseudo.pythonanywhere.com`.

## 2. Ouvrir une console et récupérer le code

Une fois connecté, va dans l'onglet **"Consoles"** en haut, puis clique sur
**"Bash"** pour ouvrir un terminal (comme celui que j'utilise ici, mais sur
leur serveur).

Dans ce terminal, tape :

```bash
git clone https://github.com/rayaneouali/mon_projet.git
cd mon_projet
git checkout claude/projet-precis-gcwdbe
```

## 3. Créer l'environnement et installer les dépendances

Toujours dans la même console :

```bash
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

(Si `python3.10` n'existe pas, tape `python3 --version` pour voir ce qui est
disponible et adapte la commande — n'importe quelle version 3.9+ convient.)

## 4. Créer la base de données et le compte de ton père

Toujours dans la console, avec l'environnement activé (tu dois voir `(venv)`
au début de la ligne) :

```bash
export FLASK_APP=run.py
flask init-db
flask seed-admin
```

Réponds aux questions (email, nom, mot de passe) : c'est le compte que ton
père utilisera pour se connecter en tant qu'admin.

## 5. Générer une clé secrète

Toujours dans la console :

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Ça affiche une longue suite de lettres/chiffres. **Copie-la**, tu vas t'en
servir juste après (ne la partage à personne, c'est ce qui sécurise les
connexions).

## 6. Configurer l'application web

Va dans l'onglet **"Web"** en haut, puis **"Add a new web app"**.

- Clique "Next", puis choisis **"Manual configuration"** (pas "Flask" dans
  la liste — c'est contre-intuitif mais c'est la bonne option pour garder le
  contrôle total sur notre structure de projet).
- Choisis la version Python correspondant à celle utilisée à l'étape 3
  (ex. Python 3.10).

Une fois le site créé, sur la page qui s'affiche :

- Section **"Virtualenv"** : indique le chemin `/home/tonpseudo/mon_projet/venv`
  (remplace `tonpseudo` par ton nom d'utilisateur PythonAnywhere).
- Section **"Code"** → clique sur le lien **WSGI configuration file**. Un
  éditeur de texte s'ouvre. **Supprime tout le contenu** et remplace-le par :

```python
import sys
import os

# Remplace "tonpseudo" par ton nom d'utilisateur PythonAnywhere
path = "/home/tonpseudo/mon_projet"
if path not in sys.path:
    sys.path.insert(0, path)

# Colle ici la clé générée à l'étape 5, entre les guillemets
os.environ["SECRET_KEY"] = "colle-ta-cle-ici"

from app import create_app
application = create_app()
```

Enregistre (bouton "Save" en haut à droite de l'éditeur).

## 7. Lancer le site

Retourne sur l'onglet **"Web"**, clique sur le gros bouton vert
**"Reload tonpseudo.pythonanywhere.com"**.

Ton site est en ligne à l'adresse `https://tonpseudo.pythonanywhere.com` 🎉

Teste : ouvre cette adresse, connecte-toi avec le compte admin créé à
l'étape 4, va dans "Chantiers" pour créer les premiers vrais chantiers, puis
dans "Ouvriers" pour créer les comptes des salariés.

---

## Mettre à jour le site après un changement de code

Quand le code du projet évolue (une nouvelle étape, une correction), il faut
répéter ces deux choses sur PythonAnywhere :

1. Dans une console Bash : `cd mon_projet && git pull`
2. Onglet **"Web"** → clique sur **"Reload"**

C'est tout. Les données (chantiers, ouvriers, pointages) ne sont jamais
touchées par cette opération : elles vivent dans le fichier
`instance/app.db`, séparé du code.

## Sauvegarder les données régulièrement

La base de données est un simple fichier. Pour ne jamais rien perdre, pense
à le télécharger de temps en temps depuis l'onglet **"Files"** de
PythonAnywhere : dossier `mon_projet/instance/app.db`, bouton de
téléchargement.
