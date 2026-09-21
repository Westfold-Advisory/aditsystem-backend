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
HOST_DOCUMENT_STORAGE="$APP_DIR/demo-document-storage"
CONTAINER_DOCUMENT_STORAGE="/seed-document-storage"

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

# The seed image runs as uid 10001. Keep generated demo assets outside the
# disposable container so their Documento storage keys resolve to real objects
# in development until they are copied to the private S3 bucket.
install -d -m 0750 -o 10001 -g 10001 "$HOST_DOCUMENT_STORAGE"

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
seed_args+=(--document-storage-dir "$CONTAINER_DOCUMENT_STORAGE")

docker run --rm \
  "${docker_env[@]}" \
  -v "$KEYS_DIR:/run/aditsystem/keys:ro" \
  -v "$APP_DIR:/seed-out:rw" \
  -v "$HOST_DOCUMENT_STORAGE:$CONTAINER_DOCUMENT_STORAGE:rw" \
  "$IMAGE_URI" aditsystem-seed-faker "${seed_args[@]}"

echo "Faker seed accounts written to $HOST_EXPORT on this instance (not in git)."
echo "Faker demo assets written to $HOST_DOCUMENT_STORAGE on this instance."
