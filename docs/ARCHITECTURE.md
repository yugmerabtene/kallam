# Architecture KALLAM (simple, modulaire, evolutive)

## Objectif

Construire une base propre pour un reseau social centree sur:

- liberte d'expression
- vie privee
- moderation proportionnee

Le MVP tourne dans un seul conteneur Docker.

## Vue d'ensemble

- Runtime: Django + Gunicorn
- Base de donnees: SQLite (fichier `/app/data/db.sqlite3`)
- Deploiement: un seul service Docker
- Persistance: volume Docker monte sur `/app/data`

## Structure modulaire proposee (Django apps)

- `apps.accounts`: comptes, pseudonymes, preferences langue, consentements
- `apps.posts`: publications, commentaires, reactions
- `apps.messaging`: conversations privees, messages, pieces jointes meta
- `apps.moderation`: signalements, actions de moderation, preuves
- `apps.governance`: chartes, listes de confiance, regles communautaires
- `apps.audit`: journaux d'evenements, traces techniques minimales

## Principes de conception

- Privacy by design: minimisation des donnees, retention limitee
- Least privilege: permissions par role et par action
- Modulaire: chaque domaine metier dans son app Django
- Evolutif: migration future possible de SQLite vers PostgreSQL
- Transparence moderation: journalisation explicable des decisions

## Evolution simple vers le scale

- Etape 1: conteneur unique (actuel)
- Etape 2: externaliser la base vers PostgreSQL
- Etape 3: ajouter cache/queue (Redis) pour files de traitement
- Etape 4: separer web / workers / moderation asynchrone
