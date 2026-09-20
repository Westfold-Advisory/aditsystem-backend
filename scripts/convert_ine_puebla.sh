#!/usr/bin/env bash
# Convierte capas INE (UTM 14N) a GeoJSON WGS84 listo para import_geocercas.py
set -euo pipefail

SRC_DIR="${1:-../puebla}"
OUT_DIR="${2:-${SRC_DIR}/geojson-wgs84/import-ready}"

if ! command -v ogr2ogr >/dev/null 2>&1; then
  echo "ogr2ogr no encontrado (instalar GDAL)." >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

for layer in DISTRITO_LOCAL DISTRITO_FEDERAL SECCION; do
  echo "Convirtiendo ${layer}..."
  ogr2ogr -t_srs EPSG:4326 -f GeoJSON "${TMP_DIR}/${layer}.geojson" "${SRC_DIR}/${layer}.shp"
  python3 "$(dirname "$0")/normalize_ine_geojson.py" \
    --layer "${layer}" \
    --input "${TMP_DIR}/${layer}.geojson" \
    --output "${OUT_DIR}/${layer}.geojson"
done

echo "Listo: ${OUT_DIR}"
