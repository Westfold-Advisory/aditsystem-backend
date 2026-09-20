#!/usr/bin/env bash
# Invoked on development EC2 via SSM (GitHub Actions workflow_dispatch).
set -euo pipefail

: "${INE_IMPORT_CHANGE_ID:?INE_IMPORT_CHANGE_ID is required}"
: "${INE_IMPORT_CONFIRMATION:?INE_IMPORT_CONFIRMATION is required}"
INE_RELEASE_TAG="${INE_RELEASE_TAG:-tra-128-ine-import}"
INE_RELEASE_REPO="${INE_RELEASE_REPO:-Westfold-Advisory/aditsystem-backend}"

if [[ "$INE_IMPORT_CONFIRMATION" != "IMPORT_INE_DEVELOPMENT" ]]; then
  echo "INE import rejected: confirmation must be IMPORT_INE_DEVELOPMENT." >&2
  exit 2
fi

APP_DIR=/opt/aditsystem
ENV_FILE="$APP_DIR/runtime.env"
KEYS_DIR="$APP_DIR/keys"
CONTAINER=aditsystem-backend
IMPORT_DIR=/tmp/ine-import-tra128
BATCH_ID="${INE_IMPORT_BATCH_ID:-tra-128-ine-dev}"

test -f "$ENV_FILE"
grep -qx 'APP_ENV=development' "$APP_DIR/runtime.env"
docker inspect "$CONTAINER" >/dev/null

IMAGE_URI="$(docker inspect --format '{{.Config.Image}}' "$CONTAINER")"
export AWS_REGION="${AWS_REGION:-$(printf '%s' "$IMAGE_URI" | sed -E 's|^[^.]+\.dkr\.ecr\.([^.]+)\.amazonaws.com/.*|\1|')}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_REGION}"

if [[ ! -d "$KEYS_DIR" ]]; then
  echo "INE import rejected: JWT keys directory missing." >&2
  exit 1
fi

echo "=== Alembic upgrade head (development RDS) ==="
docker run --rm --env-file "$ENV_FILE" -v "$KEYS_DIR:/run/aditsystem/keys:ro" \
  "$IMAGE_URI" alembic upgrade head
docker run --rm --env-file "$ENV_FILE" -v "$KEYS_DIR:/run/aditsystem/keys:ro" \
  "$IMAGE_URI" alembic current

echo "=== Download GeoJSON from GitHub release ${INE_RELEASE_TAG} ==="
rm -rf "$IMPORT_DIR"
mkdir -p "$IMPORT_DIR"
release_base="https://github.com/${INE_RELEASE_REPO}/releases/download/${INE_RELEASE_TAG}"
for asset in ENTIDAD.geojson MUNICIPIO.geojson DISTRITO_LOCAL.geojson DISTRITO_FEDERAL.geojson SECCION.geojson; do
  curl -fsSL "${release_base}/${asset}" -o "${IMPORT_DIR}/${asset}"
done
ls -lh "$IMPORT_DIR"

import_layer() {
  local file="$1" tipo="$2"
  echo "=== Import $tipo from $file ==="
  docker run --rm --env-file "$ENV_FILE" \
    -v "$IMPORT_DIR:/import:ro" \
    "$IMAGE_URI" aditsystem-import-geocercas \
    --file "/import/$(basename "$file")" \
    --tipo "$tipo" \
    --replace \
    --batch-id "$BATCH_ID"
}

import_layer ENTIDAD.geojson ESTADO
import_layer MUNICIPIO.geojson MUNICIPIO
import_layer DISTRITO_LOCAL.geojson DISTRITO_LOCAL
import_layer DISTRITO_FEDERAL.geojson DISTRITO_FEDERAL
import_layer SECCION.geojson SECCION

echo "=== Post-import counts (vigente) ==="
docker run --rm --env-file "$ENV_FILE" "$IMAGE_URI" python - <<'PY'
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from aditsystem_backend.core.config import get_settings

async def main() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    """
                    SELECT tipo::text, count(*)::int
                    FROM geocercas
                    WHERE vigente = true
                      AND tipo IN ('ESTADO','MUNICIPIO','DISTRITO_LOCAL','DISTRITO_FEDERAL','SECCION','DISTRITO')
                    GROUP BY tipo
                    ORDER BY tipo
                    """
                )
            )
        ).all()
        for tipo, count in rows:
            print(f"{tipo}={count}")
        dist = (
            await conn.execute(
                text("SELECT count(*)::int FROM geocercas WHERE tipo = 'DISTRITO'")
            )
        ).scalar_one()
        print(f"DISTRITO_total={dist}")
    await engine.dispose()

asyncio.run(main())
PY

echo "INE Puebla import completed (change ${INE_IMPORT_CHANGE_ID})."
