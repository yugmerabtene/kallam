# Kallam

**Réseau social multilingue, privacy-by-design.**

Kallam est une plateforme de microblogging pensée pour la liberté d'expression, la vie privée et la dignité en ligne. Entièrement pseudonyme, sans collecte de données civiles, avec chiffrement des messages privés et conformité RGPD native.

> Projet pédagogique — INEAD / FEDE, programme d'excellence européen.

---

## Fonctionnalités

| Domaine | Fonctionnalités |
|---|---|
| **Comptes** | Inscription pseudonyme (pseudo + email + mot de passe uniquement), suppression de compte, export RGPD |
| **Publications** | Fil principal, fil de confiance, likes, reposts, pièces jointes (image / URL / YouTube), signalement |
| **Messagerie** | Conversations privées, messages chiffrés au repos (Fernet / AES-128-CBC) |
| **Modération** | Journal horodaté, actions staff (supprimer / ignorer), tableau de bord |
| **Gouvernance** | Charte communautaire versionnée, listes de confiance, enquête anonyme, métriques d'impact |
| **i18n** | Interface disponible en 6 langues : Français, English, العربية, Deutsch, Español, Italiano |
| **API REST** | Endpoints complets via Django Ninja (`/api/docs`) |

---

## Stack technique

- **Backend** : Django 6.0, Django Ninja (REST), SQLite
- **Sécurité** : `cryptography` (Fernet), rate limiting par cache, CSRF
- **Internationalisation** : `django.middleware.locale.LocaleMiddleware`, fichiers `.po`/`.mo`
- **Serveur** : Gunicorn + Whitenoise
- **CI/CD** : GitHub Actions
- **Conteneurisation** : Docker / Docker Compose

---

## Démarrage rapide

### Sans Docker

```bash
python3 -m pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

### Docker

```bash
docker compose up --build
```

Application accessible sur **http://localhost:8000**.

---

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `DJANGO_SECRET_KEY` | *(obligatoire en prod)* | Clé secrète Django |
| `DJANGO_DEBUG` | `False` | Mode debug |
| `DJANGO_ALLOWED_HOSTS` | `localhost` | Hôtes autorisés (virgule) |
| `DJANGO_DB_PATH` | `data/db.sqlite3` | Chemin base SQLite |
| `FERNET_KEY` | auto-généré | Clé de chiffrement des messages privés |
| `KALLAM_PORT` | `8000` | Port exposé par Docker |
| `GUNICORN_WORKERS` | `2` | Workers Gunicorn |
| `GUNICORN_THREADS` | `4` | Threads Gunicorn |

---

## Architecture

```
kallam/               Configuration Django (settings, urls, wsgi)
apps/
  accounts/           Comptes, profils, pseudonymes, follow, export RGPD
  posts/              Publications, likes, reposts, signalements
  messaging/          Conversations privées, messages chiffrés
  moderation/         Journal de modération, actions staff
  governance/         Charte versionnée, listes de confiance, enquête
locale/               Fichiers de traduction (.po / .mo) — fr, en, ar, de, es, it
templates/            Templates HTML (base, home, profil, messagerie…)
```

Toutes les vues HTML sont regroupées sous le namespace `accounts`.
L'API REST est exposée sous `/api/` (documentation Swagger : `/api/docs`).

---

## API REST

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/posts/` | Non | Fil public (50 derniers posts) |
| POST | `/api/posts/` | Oui | Créer une publication |
| POST | `/api/posts/{id}/like/` | Oui | Liker / unliker |
| POST | `/api/posts/{id}/repost/` | Oui | Reposter |
| POST | `/api/posts/{id}/report/` | Oui | Signaler |
| GET | `/api/profiles/{pseudo}/` | Non | Profil public |
| GET | `/api/me/` | Oui | Mon profil |
| POST | `/api/follow/{pseudo}/` | Oui | Suivre / ne plus suivre |
| GET | `/api/conversations/` | Oui | Mes conversations |
| POST | `/api/conversations/` | Oui | Démarrer une conversation |
| GET | `/api/conversations/{id}/messages/` | Oui | Messages d'une conversation |
| POST | `/api/conversations/{id}/messages/` | Oui | Envoyer un message |
| GET | `/api/moderation/reports/` | Staff | Posts signalés |
| POST | `/api/moderation/{id}/delete/` | Staff | Supprimer un post |
| POST | `/api/moderation/{id}/dismiss/` | Staff | Ignorer les signalements |
| GET | `/api/moderation/log/` | Staff | Journal de modération |

---

## Sécurité & vie privée

- **Pseudonymat complet** : l'inscription ne collecte aucune donnée civile (pas de prénom, pas de nom)
- **Chiffrement au repos** : tous les messages privés sont chiffrés avec Fernet (AES-128-CBC + HMAC-SHA256)
- **Rate limiting** : login 5/5 min, publications 20/min, messages 30/min, enquête 3/h
- **RGPD** : export JSON des données personnelles (`/mes-donnees/`), suppression définitive du compte
- **Rétention** : suppression automatique des messages anciens via commande de gestion
- **Modération** : journal horodaté de toutes les actions staff, accessible uniquement aux utilisateurs `is_staff`
- **CSRF** : protection native Django sur toutes les vues POST

---

## Exploitation

### Créer un compte staff

```bash
python3 manage.py createsuperuser
```

### Interfaces de gestion

| URL | Accès | Description |
|---|---|---|
| `/moderation/` | Staff | Posts signalés en attente |
| `/moderation/journal/` | Staff | Journal de toutes les actions |
| `/enquete/synthese/` | Staff | Synthèse des réponses anonymes |
| `/metriques/` | Staff | Métriques d'impact (participation, engagement) |
| `/admin/` | Superuser | Interface d'administration Django |

### Rétention des messages

```bash
# Simulation (dry-run)
python3 manage.py clean_old_messages --days=90 --dry-run

# Suppression effective
python3 manage.py clean_old_messages --days=90
```

Exemple de cron (suppression quotidienne à 3h) :
```
0 3 * * * cd /app && python3 manage.py clean_old_messages --days=90
```

### Publier une nouvelle version de la charte

```python
from apps.governance.models import CharterVersion
CharterVersion.objects.filter(is_current=True).update(is_current=False)
CharterVersion.objects.create(version="1.1")
```

---

## Tests

```bash
python3 manage.py test apps.accounts
```

**167 tests** couvrant :
- Authentification, inscription, profils, suppression de compte
- Publications, likes, reposts, signalements
- Messagerie privée (chiffrement, conversations)
- Modération (actions staff, journal)
- Gouvernance (charte, listes de confiance, enquête)
- API REST (endpoints publics et authentifiés, permissions staff)
- Intégration : `/mentions-legales/`, commutation des 6 langues, pseudonymat, export RGPD

---

## CI/CD

Le workflow GitHub Actions (`.github/workflows/pipeline.yml`) s'exécute à chaque push sur `main` :

1. `python3 manage.py check` — vérification de la configuration
2. `python3 manage.py collectstatic --noinput` — génération des fichiers statiques
3. `python3 manage.py test apps.accounts` — suite de tests complète

---

## Licence

Voir [LICENSE](LICENSE).
