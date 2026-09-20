#!/usr/bin/env bash
# Invoked on the development EC2 via SSM (GitHub Actions workflow_dispatch or manual).
set -euo pipefail

: "${BOOTSTRAP_CHANGE_ID:?BOOTSTRAP_CHANGE_ID is required}"
: "${BOOTSTRAP_CONFIRMATION:?BOOTSTRAP_CONFIRMATION is required}"

if [[ "$BOOTSTRAP_CONFIRMATION" != "BOOTSTRAP_DEVELOPMENT_ADMIN" ]]; then
  echo "Bootstrap rejected: confirmation must be BOOTSTRAP_DEVELOPMENT_ADMIN." >&2
  exit 2
fi

APP_DIR=/opt/aditsystem
CONTAINER=aditsystem-backend
WRAPPER="$APP_DIR/bootstrap-development-ec2.sh"

test -f "$APP_DIR/runtime.env"
grep -qx 'APP_ENV=development' "$APP_DIR/runtime.env"
docker inspect "$CONTAINER" >/dev/null
test -x "$WRAPPER"

export IMAGE_URI="$(docker inspect --format '{{.Config.Image}}' "$CONTAINER")"
export AWS_REGION="${AWS_REGION:-$(printf '%s' "$IMAGE_URI" | sed -E 's|^[^.]+\.dkr\.ecr\.([^.]+)\.amazonaws.com/.*|\1|')}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_REGION}"

if [[ -z "${BOOTSTRAP_PASSWORD_SECRET_ID:-}" ]]; then
  export BOOTSTRAP_PASSWORD_SECRET_ID='aditsystem-dev/bootstrap-admin'
fi

exec bash "$WRAPPER"
