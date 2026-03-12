# KALLAM

Réseau social multilingue privacy-by-design — prototype pour la liberté d'expression, la vie privée et la dignité en ligne.

## Démarrage rapide

### Sans Docker

```bash
python3 -m pip install --break-system-packages -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

### Docker (conteneur unique)

```bash
docker compose up --build
```

Application disponible sur `http://localhost:8000`.

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | — | Clé secrète Django (obligatoire en prod) |
| `DJANGO_DEBUG` | `False` | Mode debug |
| `DJANGO_ALLOWED_HOSTS` | `localhost` | Hôtes autorisés, séparés par des virgules |
| `DJANGO_DB_PATH` | `data/db.sqlite3` | Chemin vers la base SQLite |
| `FERNET_KEY` | auto-généré | Clé de chiffrement Fernet pour les messages privés |

---

## Architecture

```
apps/
  accounts/    Comptes, pseudonymes, profils, follow, export RGPD
  posts/       Publications, likes, reposts, signalements
  messaging/   Conversations privées, messages chiffrés Fernet
  moderation/  Journal de modération, actions staff
  governance/  Charte versionnée, listes de confiance, enquête anonyme
```

Toutes les URLs sont regroupées sous le namespace `accounts` dans `apps/accounts/urls.py`.
L'API REST est exposée sous `/api/` via Django Ninja (`apps/accounts/api.py`).

---

## API REST

Documentation interactive : `http://localhost:8000/api/docs`

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/posts/` | Non | Fil public (50 derniers posts) |
| POST | `/api/posts/` | Oui | Créer une publication |
| POST | `/api/posts/{id}/like/` | Oui | Liker / unliker |
| POST | `/api/posts/{id}/repost/` | Oui | Reposter |
| POST | `/api/posts/{id}/report/` | Oui | Signaler |
| GET | `/api/profiles/{pseudo}/` | Non | Profil utilisateur |
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

## Sécurité

- **Chiffrement** : messages privés chiffrés au repos (Fernet / AES-128-CBC)
- **Pseudonymat** : aucune identité civile requise
- **Rate limiting** : login 5/5 min, posts 20/min, messages 30/min, enquête 3/h
- **Rétention** : `python3 manage.py clean_old_messages --days=90` (cron recommandé)
- **RGPD** : export complet des données (`/mes-donnees/`), suppression de compte (`/supprimer-mon-compte/`)
- **Modération** : journal horodaté de toutes les actions staff

---

## Guide d'exploitation

### Créer un compte staff

```bash
python3 manage.py createsuperuser
```

### Interfaces staff

| URL | Description |
|---|---|
| `/moderation/` | Posts signalés à traiter |
| `/moderation/journal/` | Journal de toutes les actions |
| `/enquete/synthese/` | Tableau de synthèse des réponses anonymes |
| `/metriques/` | Métriques d'impact (participation, engagement) |
| `/admin/` | Interface d'administration Django |

### Rétention des messages

```bash
# Voir ce qui serait supprimé (dry-run)
python3 manage.py clean_old_messages --days=90 --dry-run

# Supprimer les messages de plus de 90 jours
python3 manage.py clean_old_messages --days=90
```

Ajouter en cron (exemple) :
```
0 3 * * * cd /app && python3 manage.py clean_old_messages --days=90
```

### Charte communautaire

La version courante de la charte est stockée en base (`CharterVersion`).
Pour publier une nouvelle version via le shell Django :

```python
from apps.governance.models import CharterVersion
CharterVersion.objects.filter(is_current=True).update(is_current=False)
CharterVersion.objects.create(version="1.1")
```

---

## CI

Le workflow GitHub Actions (`.github/workflows/pipeline.yml`) exécute à chaque push :

```bash
python3 manage.py check
python3 manage.py collectstatic --noinput
python3 manage.py test apps.accounts
```

---

## Tests

```bash
python3 manage.py test apps.accounts
```

55 tests couvrant : auth, profils, posts, messagerie chiffrée, modération, gouvernance, API REST, permissions.
