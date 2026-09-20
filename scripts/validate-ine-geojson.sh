#!/usr/bin/env bash
# Validate INE GeoJSON files before import (FeatureCollection + non-empty geometry).
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required." >&2
  exit 1
fi

fail=0
for file in "$@"; do
  if [[ ! -f "$file" ]]; then
    echo "FAIL missing file: $file"
    fail=1
    continue
  fi
  if ! jq -e '.type == "FeatureCollection" and (.features | length) > 0' "$file" >/dev/null; then
    echo "FAIL not a non-empty FeatureCollection: $file"
    fail=1
    continue
  fi
  if ! jq -e '.features[0].geometry.coordinates != null' "$file" >/dev/null; then
    echo "FAIL missing geometry: $file"
    fail=1
    continue
  fi
  count="$(jq '.features | length' "$file")"
  echo "OK $file ($count features)"
done

exit "$fail"
