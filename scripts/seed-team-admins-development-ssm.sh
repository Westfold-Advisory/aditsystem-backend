#!/usr/bin/env bash
# Invoked on the development EC2 via SSM (GitHub Actions workflow_dispatch or manual).
set -euo pipefail

: "${TEAM_ADMINS_CHANGE_ID:?TEAM_ADMINS_CHANGE_ID is required}"
: "${TEAM_ADMINS_CONFIRMATION:?TEAM_ADMINS_CONFIRMATION is required}"

if [[ "$TEAM_ADMINS_CONFIRMATION" != "SEED_DEVELOPMENT_TEAM_ADMINS" ]]; then
  echo "Team admin seed rejected: confirmation must be SEED_DEVELOPMENT_TEAM_ADMINS." >&2
  exit 2
fi

APP_DIR=/opt/aditsystem
CONTAINER=aditsystem-backend
WRAPPER="$APP_DIR/seed-team-admins-development-ec2.sh"

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
if [[ -z "${TEAM_ADMIN_EMAILS_SECRET_ID:-}" ]]; then
  export TEAM_ADMIN_EMAILS_SECRET_ID='aditsystem-dev/team-admin-emails'
fi

exec bash "$WRAPPER"
