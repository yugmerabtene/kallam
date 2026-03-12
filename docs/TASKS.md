# Roadmap des taches KALLAM

## Sprint 0 - Foundation (fait / en cours)

- [x] Repo public GitHub initialise
- [x] CI GitHub Actions (check + tests)
- [x] Dockerisation conteneur unique (Django + SQLite)
- [x] Gestion des secrets par variables d'environnement
- [x] Standardiser la convention de nommage et l'arborescence apps

## Sprint 1 - MVP social multilingue

- [x] Creer `apps.accounts` (pseudonyme, profil minimal, langue preferee)
- [x] Creer `apps.posts` (publication, fil public, detail publication)
- [x] Ajouter API REST (Django Ninja ou DRF) pour posts et profils
- [x] Ajouter i18n de base FR/EN/AR pour textes systeme
- [x] Ajouter tests unitaires sur modeles et permissions

## Sprint 2 - Messagerie et securite

- [x] Creer `apps.messaging` (conversation, message, statut lu)
- [x] Chiffrer les champs sensibles au repos (au minimum metadata critique)
- [x] Ajouter politique de retention des messages
- [x] Ajouter endpoint de signalement dans `apps.moderation`
- [x] Ajouter limite anti-spam et anti-abus (rate limit)

## Sprint 3 - Gouvernance et impact FEDE

- [x] Implementer charte communautaire versionnee
- [x] Ajouter listes de confiance cote utilisateur
- [x] Ajouter journal d'actions moderation transparent
- [x] Preparer demo smartphone BYOD (QR code + guide)
- [x] Construire questionnaire anonymise et tableau de synthese

## Sprint 4 - Preparation de soutenance

- [ ] Finaliser feuille de cadrage KALLAM-01 completee
- [ ] Rediger la section limites et modele de menace
- [ ] Produire metriques d'impact (participation, apprentissages, attentes)
- [ ] Stabiliser documentation technique et guide d'exploitation
