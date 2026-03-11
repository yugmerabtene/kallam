#!/bin/sh
set -e

mkdir -p /app/data /app/staticfiles /app/media

python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear

exec gunicorn kallam.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-60}"
