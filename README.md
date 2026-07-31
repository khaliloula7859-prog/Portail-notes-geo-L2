# Portail de resultats - L2 Geographie UCAD

Application Flask permettant a chaque etudiant de consulter **uniquement
ses propres notes** en saisissant son matricule. Supporte plusieurs
semestres et plusieurs sessions (Normale / Rattrapage) dans la meme base.

## Structure

```
portail/
├── app.py              # Application Flask
├── import_pv.py        # Script d'import d'un PV PDF vers la base
├── schema.sql           # Schema de la base SQLite
├── requirements.txt
├── Procfile              # Pour le deploiement Render
├── data/
│   └── portail.db        # Base SQLite (deja remplie avec le 1er semestre)
├── templates/
│   ├── index.html
│   └── resultats.html
└── static/
    └── style.css
```

## Lancer en local

```bash
pip install -r requirements.txt
python3 app.py
```
Puis ouvrir http://127.0.0.1:5000

## Ajouter un nouveau PV (2e semestre, rattrapage...)

Des que tu recois un nouveau PDF de PV (meme mise en page que le premier) :

```bash
python3 import_pv.py chemin/vers/nouveau_pv.pdf
```

Le script :
- lit automatiquement le semestre, la session et l'annee inscrits en haut du PDF
- detecte les codes d'UE (GEO231, GEO232, etc.)
- insere les notes des etudiants dans la base, **sans toucher** aux
  semestres/sessions deja importes
- si tu relances le meme PV (ex: apres correction/reclamation), il
  remplace proprement les anciennes notes de ce semestre+session

Un etudiant qui se connecte voit alors automatiquement tous les
semestres et sessions disponibles pour lui, du plus recent au plus
ancien.

## Deploiement sur Render

1. Cree un depot GitHub avec ce dossier (le fichier `data/portail.db`
   peut etre inclus pour demarrer avec les donnees deja importees)
2. Sur Render : **New > Web Service**, connecte le depot GitHub
3. Render detecte `requirements.txt` et `Procfile` automatiquement.
   Si besoin, renseigne manuellement :
   - Build Command : `pip install -r requirements.txt`
   - Start Command : `gunicorn app:app`
4. Deploie. L'URL fournie par Render est ton site public.

**Important** : le disque de Render en formule gratuite n'est pas
persistant entre les redeploiements. Pour ajouter un nouveau PV plus
tard, deux options :
- Reimporter en local, pousser le `portail.db` mis a jour sur GitHub,
  et redeployer
- Ou passer a un disque persistant Render (payant) et lancer
  `import_pv.py` directement sur le serveur via un shell Render

## Securite

- Aucune authentification par mot de passe pour l'instant : le
  matricule seul suffit a consulter un releve. C'est deja bien plus
  sur qu'un fichier HTML statique (les donnees des autres etudiants ne
  sont jamais envoyees au navigateur), mais pour une mise en
  production officielle il est recommande d'ajouter une verification
  complementaire (ex: date de naissance, ou mot de passe initial =
  matricule que l'etudiant change a la premiere connexion).
