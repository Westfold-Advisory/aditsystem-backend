#!/usr/bin/env bash
# Run only through SSM or an approved manual workflow after deployment.
# Optional SEED_FAKER_ARGS: extra CLI flags (e.g. --fresh-subtree --cg 1).
set -euo pipefail

: "${IMAGE_URI:?IMAGE_URI is required}"

APP_DIR=/opt/aditsystem
ENV_FILE="$APP_DIR/runtime.env"
KEYS_DIR="$APP_DIR/keys"
HOST_EXPORT="$APP_DIR/faker-seed-accounts.json"
CONTAINER_EXPORT="/seed-out/faker-seed-accounts.json"

if [[ ! -f "$ENV_FILE" || ! -d "$KEYS_DIR" ]]; then
  echo "Faker seed rejected: deployment runtime files are unavailable." >&2
  exit 1
fi

app_env="$(awk -F= '/^APP_ENV=/{print tolower($2); exit}' "$ENV_FILE")"
if [[ "$app_env" != "development" ]]; then
  echo "Faker seed rejected: runtime APP_ENV must be development." >&2
  exit 1
fi

if ! docker image inspect "$IMAGE_URI" >/dev/null 2>&1; then
  echo "Faker seed rejected: requested image is not present on this EC2." >&2
  exit 1
fi

docker_env=(--env-file "$ENV_FILE")
if [[ -n "${BOOTSTRAP_PASSWORD_SECRET_ID:-}" ]]; then
  docker_env+=(
    -e "BOOTSTRAP_PASSWORD_SECRET_ID=$BOOTSTRAP_PASSWORD_SECRET_ID"
    -e "AWS_REGION=${AWS_REGION:-${AWS_DEFAULT_REGION:-}}"
    -e "AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-${AWS_REGION:-}}"
  )
elif [[ -n "${BOOTSTRAP_PASSWORD:-}" ]]; then
  docker_env+=(-e "BOOTSTRAP_PASSWORD=$BOOTSTRAP_PASSWORD")
else
  echo "Faker seed rejected: set BOOTSTRAP_PASSWORD_SECRET_ID or BOOTSTRAP_PASSWORD." >&2
  exit 1
fi

seed_args=()
if [[ -n "${SEED_FAKER_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  seed_args=($SEED_FAKER_ARGS)
fi
seed_args+=(--export-json "$CONTAINER_EXPORT")

docker run --rm \
  "${docker_env[@]}" \
  -v "$KEYS_DIR:/run/aditsystem/keys:ro" \
  -v "$APP_DIR:/seed-out:rw" \
  "$IMAGE_URI" aditsystem-seed-faker "${seed_args[@]}"

echo "Faker seed accounts written to $HOST_EXPORT on this instance (not in git)."
