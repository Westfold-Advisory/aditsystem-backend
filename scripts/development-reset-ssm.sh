#!/usr/bin/env bash
# Guarded development schema reset for EC2 via SSM. Never run on merge.
set -euo pipefail

: "${RESET_CHANGE_ID:?RESET_CHANGE_ID is required}"
: "${RESET_CONFIRMATION:?RESET_CONFIRMATION is required}"

if [[ "$RESET_CONFIRMATION" != "RESET_DEVELOPMENT_DATA" ]]; then
  echo "Reset rejected: confirmation must be RESET_DEVELOPMENT_DATA." >&2
  exit 2
fi

APP_DIR=/opt/aditsystem
CONTAINER=aditsystem-backend

test -f "$APP_DIR/runtime.env"
grep -qx 'APP_ENV=development' "$APP_DIR/runtime.env"
docker inspect "$CONTAINER" >/dev/null

RESET_DATABASE_HOST="$(python3 - "$APP_DIR/runtime.env" <<'PY'
from pathlib import Path
from urllib.parse import urlsplit

for line in Path(__import__("sys").argv[1]).read_text().splitlines():
    if line.startswith("DATABASE_URL="):
        print(urlsplit(line.split("=", 1)[1]).hostname)
        break
else:
    raise SystemExit("DATABASE_URL is missing from runtime.env")
PY
)"

case "$RESET_DATABASE_HOST" in
  *.rds.amazonaws.com) ;;
  *) echo "Reset rejected: expected an RDS hostname." >&2; exit 2 ;;
esac
case "$RESET_DATABASE_HOST" in
  *prod*) echo "Reset rejected: production-like hostname." >&2; exit 2 ;;
esac

IMAGE_URI="$(docker inspect --format '{{.Config.Image}}' "$CONTAINER")"
docker stop "$CONTAINER"

if ! docker run --rm --env-file "$APP_DIR/runtime.env" \
  -e RESET_CONFIRMATION=RESET_DEVELOPMENT_DATA \
  -e "RESET_DATABASE_HOST=$RESET_DATABASE_HOST" \
  -e "RESET_CHANGE_ID=$RESET_CHANGE_ID" \
  "$IMAGE_URI" aditsystem-reset-development; then
  echo "Reset or guards failed; API remains stopped." >&2
  exit 1
fi

docker run --rm --env-file "$APP_DIR/runtime.env" \
  -v "$APP_DIR/keys:/run/aditsystem/keys:ro" \
  "$IMAGE_URI" alembic upgrade head
docker start "$CONTAINER"
curl --fail --silent http://127.0.0.1:8000/health
echo
echo "Development reset completed."
