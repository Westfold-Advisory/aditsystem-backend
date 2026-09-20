#!/usr/bin/env bash
set -euo pipefail

PS4='+ [${BASH_SOURCE##*/}:${LINENO}] '

log() {
  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"
}

set -x

: "${AWS_REGION:?AWS_REGION is required}"
: "${IMAGE_URI:?IMAGE_URI is required}"
: "${RUNTIME_SECRET_ARN:?RUNTIME_SECRET_ARN is required}"
: "${DB_SECRET_ARN:?DB_SECRET_ARN is required}"
: "${DB_HOST:?DB_HOST is required}"
DB_PORT="${DB_PORT:-5432}"

APP_DIR=/opt/aditsystem
KEYS_DIR="$APP_DIR/keys"
ENV_FILE="$APP_DIR/runtime.env"
CONTAINER_NAME=aditsystem-backend
LOG_GROUP=/aditsystem/dev/backend

log "Ensuring python3 is available"
command -v python3 >/dev/null 2>&1 || dnf install -y -q python3

log "Ensuring Docker is installed and running"
if ! command -v docker >/dev/null 2>&1; then
  dnf install -y docker
  systemctl enable --now docker
  usermod -aG docker ssm-user || true
fi
systemctl is-active --quiet docker || systemctl start docker

log "Creating application directories"
# Owned by the container's non-root "app" user (uid/gid 10001, see Dockerfile)
# so it can traverse the directory once bind-mounted read-only at
# /run/aditsystem/keys; root-owned 0700 blocked that traversal entirely.
install -d -m 0700 -o 10001 -g 10001 "$KEYS_DIR"

log "Authenticating to ECR"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "${IMAGE_URI%%/*}"

log "Pulling image: $IMAGE_URI"
docker pull "$IMAGE_URI"

log "Retrieving runtime secret"
aws secretsmanager get-secret-value --region "$AWS_REGION" \
  --secret-id "$RUNTIME_SECRET_ARN" --query SecretString --output text > "$APP_DIR/runtime.json"

log "Retrieving RDS credentials"
aws secretsmanager get-secret-value --region "$AWS_REGION" \
  --secret-id "$DB_SECRET_ARN" --query SecretString --output text > "$APP_DIR/database.json"

log "Generating runtime configuration"
python3 - "$APP_DIR" "$DB_HOST" "$DB_PORT" <<'PY'
import json
import os
import pathlib
import sys
from urllib.parse import quote

app_dir = pathlib.Path(sys.argv[1])
db_host = sys.argv[2]
db_port = sys.argv[3]

runtime = json.loads((app_dir / "runtime.json").read_text())
database = json.loads((app_dir / "database.json").read_text())
for key in ("jwt_private_key", "jwt_public_key"):
    if not runtime.get(key):
        raise SystemExit(f"runtime secret must contain {key}")

keys_dir = app_dir / "keys"
for source, filename in (("jwt_private_key", "jwt-private.pem"), ("jwt_public_key", "jwt-public.pem")):
    destination = keys_dir / filename
    destination.write_text(runtime[source], encoding="utf-8")
    os.chmod(destination, 0o600)
    os.chown(destination, 10001, 10001)

database_url = (
    "postgresql+asyncpg://"
    f"{quote(database['username'], safe='')}:{quote(database['password'], safe='')}"
    f"@{db_host}:{db_port}/{runtime.get('database_name', 'aditsystem')}"
)
env = {
    "APP_ENV": "development", "DEBUG": "false", "DATABASE_URL": database_url,
    "JWT_PRIVATE_KEY_PATH": "/run/aditsystem/keys/jwt-private.pem",
    "JWT_PUBLIC_KEY_PATH": "/run/aditsystem/keys/jwt-public.pem",
    "CORS_ALLOWED_ORIGINS": runtime.get("cors_allowed_origins", ""),
}
(app_dir / "runtime.env").write_text("".join(f"{key}={value}\n" for key, value in env.items()), encoding="utf-8")
os.chmod(app_dir / "runtime.env", 0o600)
PY
rm -f "$APP_DIR/runtime.json" "$APP_DIR/database.json"

docker run --rm --env-file "$ENV_FILE" -v "$KEYS_DIR:/run/aditsystem/keys:ro" "$IMAGE_URI" alembic upgrade head

start_container() {
  docker run -d --name "$CONTAINER_NAME" --restart unless-stopped \
    --env-file "$ENV_FILE" --log-driver awslogs \
    --log-opt awslogs-region="$AWS_REGION" --log-opt awslogs-group="$LOG_GROUP" \
    --log-opt awslogs-stream="$CONTAINER_NAME" \
    -v "$KEYS_DIR:/run/aditsystem/keys:ro" -p 8000:8000 "$1"
}

previous_image=""
if docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  previous_image=$(docker inspect --format '{{.Config.Image}}' "$CONTAINER_NAME")
  docker rm -f "$CONTAINER_NAME"
fi
start_container "$IMAGE_URI"

for _ in $(seq 1 20); do
  curl --fail --silent http://127.0.0.1:8000/health >/dev/null && exit 0
  sleep 3
done
docker logs "$CONTAINER_NAME" >&2 || true
docker rm -f "$CONTAINER_NAME" || true
if [ -n "$previous_image" ]; then
  start_container "$previous_image"
fi
exit 1
