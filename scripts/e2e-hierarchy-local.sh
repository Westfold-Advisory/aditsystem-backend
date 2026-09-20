#!/usr/bin/env bash
# Reproducible local hierarchy E2E: reset, migrate, seed, role chain, media, 403.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.compose}"
API_BASE="${API_BASE:-http://127.0.0.1:8000/api/v1}"
BOOTSTRAP_PASSWORD="${BOOTSTRAP_PASSWORD:-AditDevE2E!2026}"

json_field() {
  python3 -c "import json,sys; data=json.load(sys.stdin); print(data$1)"
}

login() {
  local email="$1"
  curl --fail --silent -X POST "$API_BASE/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"password\":\"$BOOTSTRAP_PASSWORD\"}"
}

auth_get() {
  local token="$1"
  local path="$2"
  curl --silent -o /tmp/e2e-body.json -w '%{http_code}' \
    -H "Authorization: Bearer $token" \
    "$API_BASE$path"
}

echo "== Local reset =="
./scripts/reset-local-db.sh --confirm-local-reset
docker compose --env-file "$ENV_FILE" up --build -d db migrations api
docker compose --env-file "$ENV_FILE" run --rm migrations alembic current

echo "== Seed =="
BOOTSTRAP_PASSWORD="$BOOTSTRAP_PASSWORD" \
  docker compose --env-file "$ENV_FILE" run --rm api aditsystem-seed-development

echo "== Login chain =="
ADMIN_TOKEN="$(login admin@aditsystem.test | json_field "['access_token']")"
GENERAL_TOKEN="$(login general@aditsystem.test | json_field "['access_token']")"
COORD_TOKEN="$(login coordinador@aditsystem.test | json_field "['access_token']")"
ENLACE_TOKEN="$(login enlace@aditsystem.test | json_field "['access_token']")"

GENERAL_ID="$(curl --fail --silent -H "Authorization: Bearer $GENERAL_TOKEN" \
  "$API_BASE/auth/me" | json_field "['persona_id']")"
COORD_ID="$(curl --fail --silent -H "Authorization: Bearer $COORD_TOKEN" \
  "$API_BASE/auth/me" | json_field "['persona_id']")"
ENLACE_ID="$(curl --fail --silent -H "Authorization: Bearer $ENLACE_TOKEN" \
  "$API_BASE/auth/me" | json_field "['persona_id']")"

for token in "$ADMIN_TOKEN" "$GENERAL_TOKEN" "$COORD_TOKEN" "$ENLACE_TOKEN"; do
  code="$(auth_get "$token" "/personas/$GENERAL_ID/metricas")"
  [[ "$code" == "200" ]] || { echo "metricas failed with $code"; cat /tmp/e2e-body.json; exit 1; }
done

echo "== Scoped map =="
code="$(auth_get "$GENERAL_TOKEN" "/personas/$GENERAL_ID/mapa")"
[[ "$code" == "200" ]] || { echo "mapa failed with $code"; cat /tmp/e2e-body.json; exit 1; }

echo "== Document metadata (scoped) =="
curl --fail --silent -X POST "$API_BASE/personas/$ENLACE_ID/documentos" \
  -H "Authorization: Bearer $ENLACE_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "tipo":"FOTO",
    "titulo":"E2E foto",
    "descripcion":"metadata only",
    "s3_key":"development/e2e/foto.bin",
    "mime_type":"image/jpeg",
    "size_bytes":128
  }' >/dev/null

echo "== Cross-hierarchy 403 =="
OTHER_COORD="$(curl --fail --silent -X POST "$API_BASE/personas" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"rol\":\"COORDINADOR\",
    \"parent_persona_id\":\"$GENERAL_ID\",
    \"nombre\":\"Otro\",
    \"apellido_paterno\":\"Coord\",
    \"apellido_materno\":\"Prueba\",
    \"telefono\":\"5550199999\"
  }" | json_field "['id']")"
code="$(auth_get "$COORD_TOKEN" "/personas/$OTHER_COORD/metricas")"
if [[ "$code" != "403" ]]; then
  echo "Expected 403 for sibling branch, got $code"
  cat /tmp/e2e-body.json
  exit 1
fi

echo "== AMIGO has no session =="
if login amigo@aditsystem.test 2>/dev/null; then
  echo "AMIGO must not authenticate"
  exit 1
fi

echo "E2E hierarchy flow completed successfully."
