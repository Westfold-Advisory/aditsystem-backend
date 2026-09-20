#!/usr/bin/env bash
# Verify team ADMIN login on development EC2 using bootstrap-admin secret (no password in output).
set -euo pipefail

: "${VERIFY_LOGIN_EMAIL:?VERIFY_LOGIN_EMAIL is required}"

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-mx-central-1}}"
SECRET_ID="${BOOTSTRAP_PASSWORD_SECRET_ID:-aditsystem-dev/bootstrap-admin}"
API_URL="${VERIFY_LOGIN_API_URL:-http://127.0.0.1:8000/api/v1/auth/login}"

password="$(
  aws secretsmanager get-secret-value --region "$REGION" \
    --secret-id "$SECRET_ID" --query SecretString --output text \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["password"])'
)"

payload="$(jq -n --arg e "$VERIFY_LOGIN_EMAIL" --arg p "$password" '{email: $e, password: $p}')"
unset password

response_file="$(mktemp)"
trap 'rm -f "$response_file"' EXIT

http_code="$(
  curl -sS -o "$response_file" -w '%{http_code}' \
    -X POST "$API_URL" \
    -H 'Content-Type: application/json' \
    -d "$payload"
)"

if [[ "$http_code" != "200" ]]; then
  echo "Login verification failed: HTTP $http_code" >&2
  jq -r '.detail // .' "$response_file" >&2 || true
  exit 1
fi

token_len="$(jq -r '.access_token | length' "$response_file")"
if [[ "$token_len" -lt 10 ]]; then
  echo "Login verification failed: access_token missing or too short." >&2
  exit 1
fi

echo "Login verification OK"
echo "  email=$(jq -r '.user.email' "$response_file")"
echo "  rol=$(jq -r '.user.rol' "$response_file")"
echo "  access_token_present=yes"
echo "  access_token_length=$token_len"
echo "  expires_in_seconds=$(jq -r '.expires_in_seconds' "$response_file")"
