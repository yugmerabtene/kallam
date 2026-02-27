# kallam

Projet Django open source.

## Demarrage local (sans Docker)

```bash
python3 -m pip install --break-system-packages -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

## Demarrage Docker (conteneur unique)

```bash
docker compose up --build
```

Application disponible sur `http://localhost:8000`.

La base SQLite est stockee dans `./data/db.sqlite3` (volume local monte dans le conteneur).

Variables d'environnement minimales a definir selon l'environnement:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_DB_PATH`

## CI

Le workflow GitHub Actions execute:

- `python3 manage.py check`
- `python3 manage.py test`
