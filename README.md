# AFRICA INFOS 360

Média numérique généraliste en français — starter Flask avec articles, catégories, recherche, formulaire de contact et administration.

## Lancer en local (Windows)
1. Installer Python 3.12.
2. Ouvrir un terminal dans ce dossier.
3. `py -m venv .venv`
4. `.venv\\Scripts\\activate`
5. `pip install -r requirements.txt`
6. Définir un mot de passe administrateur dans PowerShell :
   `$env:ADMIN_PASSWORD="UnMotDePasseLongEtUnique"`
   `$env:SECRET_KEY="UneCleAleatoireTresLongue"`
7. `python app.py`
8. Ouvrir http://127.0.0.1:5000

Identifiant admin par défaut : `admin`. Le mot de passe n'a volontairement aucune valeur par défaut : configurez ADMIN_PASSWORD avant connexion.

## Mise en production
- Utiliser un hébergeur compatible Python/Flask et Gunicorn.
- Définir `ADMIN_USER`, `ADMIN_PASSWORD`, `SECRET_KEY` et `DATABASE_PATH=/var/data/africa_infos.db` dans les variables d'environnement.
- Ajouter un disque persistant (offre payante Render) monté sur `/var/data`. Sans disque persistant ou base externe durable, les fichiers SQLite du service peuvent être effacés lors des redémarrages/redéploiements.
- Activer HTTPS, sauvegardes automatiques de la base SQLite et journalisation.
- Ne pas utiliser le serveur de développement Flask en production.
- Pour un trafic important ou plusieurs instances, migrer SQLite vers PostgreSQL.
- Renseigner l'identité réelle de l'éditeur, les mentions légales et les coordonnées de contact.
- Ajouter une politique de confidentialité complète et un mécanisme de consentement aux cookies adapté avant toute publicité personnalisée.
- Remplacer les textes de démonstration par des articles originaux, sourcés, relus et régulièrement actualisés.

## Google AdSense
Les blocs « ESPACE PUBLICITAIRE » sont des emplacements visuels, pas des annonces actives. Après publication et approbation du site par Google AdSense :
1. Ajouter le code AdSense fourni par Google dans `templates/base.html`, dans la balise `<head>`.
2. Ajouter les blocs publicitaires autorisés aux emplacements prévus.
3. Publier le fichier `ads.txt` avec le contenu exact fourni dans votre compte AdSense.
4. Configurer la gestion du consentement si elle est requise pour les visiteurs ciblés.
Ne jamais cliquer sur ses propres annonces, inciter les visiteurs à cliquer ou générer du trafic artificiel.

## À faire avant l'ouverture publique
- Vérifier disponibilité et enregistrer le domaine souhaité (non inclus).
- Choisir l'hébergeur et connecter le DNS.
- Compléter les mentions légales et la politique de confidentialité.
- Ajouter des coordonnées réelles et un responsable éditorial.
- Remplacer les articles de démonstration par du contenu substantiel et original.
- Vérifier les sources des annonces d'emploi, concours et actualités ; dater les informations et corriger les contenus périmés.
- Créer les comptes Search Console, Analytics et AdSense.
