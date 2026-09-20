#!/usr/bin/env bash
# Run only through SSM after a successful development deployment.
# TEAM_ADMIN_EMAILS: comma-separated list, or set TEAM_ADMIN_EMAILS_SECRET_ID
# to read {"emails":"a@x.com,b@y.com"} from Secrets Manager (instance profile).
set -euo pipefail

: "${IMAGE_URI:?IMAGE_URI is required}"

APP_DIR=/opt/aditsystem
ENV_FILE="$APP_DIR/runtime.env"
KEYS_DIR="$APP_DIR/keys"

if [[ ! -f "$ENV_FILE" || ! -d "$KEYS_DIR" ]]; then
  echo "Team admin seed rejected: deployment runtime files are unavailable." >&2
  exit 1
fi

app_env="$(awk -F= '/^APP_ENV=/{print tolower($2); exit}' "$ENV_FILE")"
if [[ "$app_env" != "development" ]]; then
  echo "Team admin seed rejected: runtime APP_ENV must be development." >&2
  exit 1
fi

if ! docker image inspect "$IMAGE_URI" >/dev/null 2>&1; then
  echo "Team admin seed rejected: requested image is not present on this EC2." >&2
  exit 1
fi

team_emails="${TEAM_ADMIN_EMAILS:-}"
if [[ -z "$team_emails" && -n "${TEAM_ADMIN_EMAILS_SECRET_ID:-}" ]]; then
  region="${AWS_REGION:-${AWS_DEFAULT_REGION:-}}"
  if [[ -z "$region" ]]; then
    echo "Team admin seed rejected: AWS_REGION required to read TEAM_ADMIN_EMAILS_SECRET_ID." >&2
    exit 1
  fi
  team_emails="$(
    aws secretsmanager get-secret-value --region "$region" \
      --secret-id "$TEAM_ADMIN_EMAILS_SECRET_ID" --query SecretString --output text \
      | python3 -c 'import json, sys; data=json.load(sys.stdin); print(data["emails"])'
  )"
fi

if [[ -z "$team_emails" ]]; then
  echo "Team admin seed rejected: set TEAM_ADMIN_EMAILS or TEAM_ADMIN_EMAILS_SECRET_ID." >&2
  exit 1
fi

docker_env=(--env-file "$ENV_FILE" -e "TEAM_ADMIN_EMAILS=$team_emails")
if [[ -n "${BOOTSTRAP_PASSWORD_SECRET_ID:-}" ]]; then
  docker_env+=(-e "BOOTSTRAP_PASSWORD_SECRET_ID=$BOOTSTRAP_PASSWORD_SECRET_ID")
elif [[ -n "${BOOTSTRAP_PASSWORD:-}" ]]; then
  docker_env+=(-e "BOOTSTRAP_PASSWORD=$BOOTSTRAP_PASSWORD")
else
  echo "Team admin seed rejected: set BOOTSTRAP_PASSWORD_SECRET_ID or BOOTSTRAP_PASSWORD." >&2
  exit 1
fi

docker run --rm \
  "${docker_env[@]}" \
  -v "$KEYS_DIR:/run/aditsystem/keys:ro" \
  "$IMAGE_URI" aditsystem-seed-team-admins
