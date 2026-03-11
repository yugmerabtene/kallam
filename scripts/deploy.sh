#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$HOME/kallam}"
REPO_URL="${REPO_URL:-https://github.com/yugmerabtene/kallam.git}"
BRANCH="${BRANCH:-main}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required on the server"
  exit 1
fi

if [ ! -d "$APP_DIR/.git" ]; then
  mkdir -p "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

docker compose up --build -d --remove-orphans
docker exec kallam python manage.py collectstatic --noinput --clear
chown -R "$(whoami):$(whoami)" "$APP_DIR/staticfiles/" 2>/dev/null || true
chmod -R o+rX "$APP_DIR/staticfiles/" "$APP_DIR/media/" 2>/dev/null || true
docker image prune -f
