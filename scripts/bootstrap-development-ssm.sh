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

if [[ ! -f "$APP_DIR/runtime.env" ]]; then
  echo "Bootstrap rejected: missing $APP_DIR/runtime.env; deploy the development backend first." >&2
  exit 1
fi

if ! grep -qx 'APP_ENV=development' "$APP_DIR/runtime.env"; then
  echo "Bootstrap rejected: $APP_DIR/runtime.env must set APP_ENV=development." >&2
  exit 1
fi

if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "Bootstrap rejected: Docker container $CONTAINER is not running; complete a healthy backend deployment first." >&2
  exit 1
fi

if [[ ! -x "$WRAPPER" ]]; then
  echo "Bootstrap rejected: missing executable $WRAPPER; install the EC2 bootstrap wrapper before retrying." >&2
  exit 1
fi

export IMAGE_URI="$(docker inspect --format '{{.Config.Image}}' "$CONTAINER")"
export AWS_REGION="${AWS_REGION:-$(printf '%s' "$IMAGE_URI" | sed -E 's|^[^.]+\.dkr\.ecr\.([^.]+)\.amazonaws.com/.*|\1|')}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_REGION}"

if [[ -z "${BOOTSTRAP_PASSWORD_SECRET_ID:-}" ]]; then
  export BOOTSTRAP_PASSWORD_SECRET_ID='aditsystem-dev/bootstrap-admin'
fi

exec bash "$WRAPPER"
