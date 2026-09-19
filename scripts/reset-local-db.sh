#!/usr/bin/env bash
# Reset only the named Docker Compose database volume for a declared local env.
set -euo pipefail

if [[ "${1:-}" != "--confirm-reset-local-db" ]]; then
  echo "Refusing destructive reset. Pass --confirm-reset-local-db." >&2
  exit 2
fi

env_file="${ENV_FILE:-.env.compose}"
if [[ ! -f "$env_file" ]]; then
  echo "Missing $env_file (copy .env.compose.example first)." >&2
  exit 2
fi

app_env=$(grep -E '^APP_ENV=' "$env_file" | tail -n1 | cut -d= -f2- | tr -d '[:space:]')
if [[ "$app_env" != "local" && "$app_env" != "development" ]]; then
  echo "Refusing reset: APP_ENV must be local or development." >&2
  exit 2
fi

database_url=$(grep -E '^DATABASE_URL=' "$env_file" | tail -n1 | cut -d= -f2- || true)
if [[ -n "$database_url" && ! "$database_url" =~ @((localhost|127\.0\.0\.1|::1|db)(:|/)) ]]; then
  echo "Refusing reset: DATABASE_URL host must be local or the Compose db service." >&2
  exit 2
fi

project=$(docker compose --env-file "$env_file" config --format json | \
  python3 -c 'import json,sys; print(json.load(sys.stdin).get("name", ""))')
if [[ -z "$project" ]]; then
  echo "Unable to resolve the local Compose project." >&2
  exit 2
fi
volume="${project}_aditsystem-postgres-data"
if [[ "$volume" != *"aditsystem-postgres-data" ]]; then
  echo "Refusing unexpected volume target: $volume" >&2
  exit 2
fi

docker compose --env-file "$env_file" down
docker volume rm "$volume" 2>/dev/null || true
docker compose --env-file "$env_file" up -d db
docker compose --env-file "$env_file" run --rm migrations alembic upgrade head
echo "Local database reset and migrated successfully."
