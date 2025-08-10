\
# Staybnb (démo locale)

Un mini clone d'Airbnb (sans la marque) prêt à tourner en local : annonces, recherche, réservations (disponibilité), messagerie, avis, tableau de bord hôte/voyageur. SQLite, Flask, SQLAlchemy, Bootstrap.

## Installation (local)

1) Créer un environnement Python 3.10+ puis installer les dépendances :

```bash
pip install -r requirements.txt
```

2) Lancer le serveur :

```bash
python app.py
```

3) Ouvrir http://localhost:5000

## Fonctionnalités

- Authentification (inscription/connexion)
- CRUD basique d’annonces (création + upload de photos locales)
- Recherche par ville/pays/nombre de voyageurs
- Réservations avec vérification de disponibilité (chevauchement de dates)
- Messagerie 1:1 (invité ↔ hôte)
- Avis (après un séjour terminé)
- Tableau de bord (mes annonces, mes réservations, demandes reçues)
- Paiement **simulé** (statut confirmé)

## Notes

- Les images sont stockées dans `static/uploads`.
- Base SQLite créée automatiquement (`staybnb.sqlite3`). 
- **Attention légale** : ce projet est une démo pédagogique. N’utilise pas la marque, le logo, le design ou le contenu d’Airbnb en production.
