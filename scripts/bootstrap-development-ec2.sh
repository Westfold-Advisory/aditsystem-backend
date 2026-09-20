#!/usr/bin/env bash
# Run only through SSM after a successful development deployment.
set -euo pipefail

: "${IMAGE_URI:?IMAGE_URI is required}"
: "${BOOTSTRAP_PASSWORD_SECRET_ID:?BOOTSTRAP_PASSWORD_SECRET_ID is required}"

APP_DIR=/opt/aditsystem
ENV_FILE="$APP_DIR/runtime.env"
KEYS_DIR="$APP_DIR/keys"
BOOTSTRAP_EMAIL=eperez@ervic.pro

if [[ ! -f "$ENV_FILE" || ! -d "$KEYS_DIR" ]]; then
  echo "Bootstrap rejected: deployment runtime files are unavailable." >&2
  exit 1
fi

app_env="$(awk -F= '/^APP_ENV=/{print tolower($2); exit}' "$ENV_FILE")"
if [[ "$app_env" != "development" ]]; then
  echo "Bootstrap rejected: runtime APP_ENV must be development." >&2
  exit 1
fi

if ! docker image inspect "$IMAGE_URI" >/dev/null 2>&1; then
  echo "Bootstrap rejected: requested image is not present on this EC2." >&2
  exit 1
fi

# boto3 uses the EC2 instance profile. The secret value is never written to a
# shell variable, command line, file, or SSM output.
docker run --rm \
  --env-file "$ENV_FILE" \
  -e "BOOTSTRAP_EMAIL=$BOOTSTRAP_EMAIL" \
  -e "BOOTSTRAP_PASSWORD_SECRET_ID=$BOOTSTRAP_PASSWORD_SECRET_ID" \
  -v "$KEYS_DIR:/run/aditsystem/keys:ro" \
  "$IMAGE_URI" aditsystem-bootstrap-admin
