#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  echo "Tip: copy deploy/.env.example to deploy/.env and set OPENROUTER_API_KEY (optional)." >&2
fi
docker compose -f docker-compose.yml up --build "$@"
