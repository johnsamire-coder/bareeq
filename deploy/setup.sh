#!/usr/bin/env bash
# Bareeq test server, first time (and after every update: it rebuilds).
# Run from the repo folder: bash deploy/setup.sh
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  umask 077
  sed -e "s/^DJANGO_SECRET_KEY=$/DJANGO_SECRET_KEY=$(openssl rand -hex 32)/" \
      -e "s/^DB_PASSWORD=$/DB_PASSWORD=$(openssl rand -hex 16)/" .env.example > .env
  echo "Made deploy/.env with new secrets (save a copy in Bitwarden)."
fi
docker compose up -d --build
for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8020/api/health/ >/dev/null 2>&1; then
    echo "BAREEQ IS RUNNING on 127.0.0.1:8020"; exit 0
  fi
  sleep 3
done
echo "Bareeq did not answer. Logs:"; docker compose logs --tail 60 app; exit 1
