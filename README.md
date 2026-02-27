# kallam

Projet Django open source.

## Demarrage local (sans Docker)

```bash
python3 -m pip install --break-system-packages -r requirements.txt
cp .env.example .env
python3 manage.py migrate
python3 manage.py runserver
```

## Demarrage Docker (conteneur unique)

```bash
cp .env.example .env
docker compose up --build
```

Application disponible sur `http://localhost:8000`.

La base SQLite est stockee dans `./data/db.sqlite3` (volume local monte dans le conteneur).

## CI

Le workflow GitHub Actions execute:

- `python3 manage.py check`
- `python3 manage.py test`

## Documentation projet

- Architecture: `docs/ARCHITECTURE.md`
- Roadmap des taches: `docs/TASKS.md`
- Feuille de cadrage: `docs/KALLAM-01.md`
