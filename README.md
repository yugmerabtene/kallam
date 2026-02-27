# kallam

Projet Django open source.

## Demarrage local

```bash
python3 -m pip install --break-system-packages -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

## CI

Le workflow GitHub Actions execute:

- `python3 manage.py check`
- `python3 manage.py test`
