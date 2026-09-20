#!/usr/bin/env bash
# Reset only the named Docker Compose volume used for this local project.
set -euo pipefail

if [[ "${1:-}" != "--confirm-local-reset" || $# -ne 1 ]]; then
  echo "Uso: $0 --confirm-local-reset" >&2
  exit 64
fi

env_file=".env.compose"
if [[ ! -f "$env_file" ]]; then
  echo "Falta $env_file; el reset sólo admite el entorno Compose local." >&2
  exit 1
fi

app_env="$(awk -F= '/^[[:space:]]*APP_ENV[[:space:]]*=/{gsub(/[[:space:]#].*$/, "", $2); print tolower($2); exit}' "$env_file")"
if [[ "$app_env" != "local" ]]; then
  echo "Reset rechazado: APP_ENV debe ser exactamente local." >&2
  exit 1
fi

if [[ "${DATABASE_URL:-}" == *"://"* && "${DATABASE_URL}" != *"@localhost:"* && "${DATABASE_URL}" != *"@127.0.0.1:"* && "${DATABASE_URL}" != *"@db:"* ]]; then
  echo "Reset rechazado: DATABASE_URL no apunta a un host local/Compose." >&2
  exit 1
fi

echo "Se eliminarán únicamente los volúmenes del proyecto Compose local aditsystem-backend."
docker compose --env-file "$env_file" down --volumes --remove-orphans
