#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${SENTINEL_BASE_URL:-http://127.0.0.1:8080}"
ENROLLMENT_TOKEN="${SENTINEL_ENROLLMENT_TOKEN:?missing enrollment token}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

b64url() { base64 -w0 "$1" | tr '+/' '-_' | tr -d '='; }
json() { python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"; }
decode_b64url() { python3 -c 'import sys,base64; s=sys.stdin.read().strip(); sys.stdout.buffer.write(base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)))'; }

openssl ecparam -name prime256v1 -genkey -noout -out "$TMP/key.pem"
openssl ec -in "$TMP/key.pem" -pubout -outform DER -out "$TMP/pub.der" 2>/dev/null
fingerprint="$(sha256sum "$TMP/pub.der" | cut -d' ' -f1)"
pub="$(b64url "$TMP/pub.der")"

curl -fsS -X POST "$BASE_URL/v1/devices/register" --data-urlencode "fingerprint=$fingerprint" --data-urlencode "publicKey=$pub" >/dev/null
curl -fsS -X POST "$BASE_URL/v1/devices/activate" -H "X-Sentinel-Enrollment-Token: $ENROLLMENT_TOKEN" --data-urlencode "fingerprint=$fingerprint" >/dev/null

challenge="$(curl -fsS -X POST "$BASE_URL/v1/challenges/issue" --data-urlencode "fingerprint=$fingerprint")"
challenge_id="$(printf '%s' "$challenge" | json challengeId)"
nonce="$(printf '%s' "$challenge" | json nonce)"
printf '%s' "$nonce" | decode_b64url > "$TMP/nonce.bin"
openssl dgst -sha256 -sign "$TMP/key.pem" -out "$TMP/signature.der" "$TMP/nonce.bin"
signature="$(b64url "$TMP/signature.der")"

proof="$(curl -fsS -X POST "$BASE_URL/v1/challenges/verify" --data-urlencode "challengeId=$challenge_id" --data-urlencode "publicKey=$pub" --data-urlencode "signature=$signature")"
token="$(printf '%s' "$proof" | json token)"

curl -fsS -H "Authorization: Bearer $token" "$BASE_URL/v1/protected/ping" >/dev/null
rotated="$(curl -fsS -X POST -H "Authorization: Bearer $token" "$BASE_URL/v1/sessions/rotate")"
new_token="$(printf '%s' "$rotated" | json token)"
if curl -sS -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $token" "$BASE_URL/v1/protected/ping" | grep -q '^2'; then
  echo 'old session remained valid after rotation' >&2; exit 1
fi
curl -fsS -H "Authorization: Bearer $new_token" "$BASE_URL/v1/protected/ping" >/dev/null
curl -fsS -X POST -H "Authorization: Bearer $new_token" "$BASE_URL/v1/sessions/revoke" >/dev/null
if curl -sS -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $new_token" "$BASE_URL/v1/protected/ping" | grep -q '^2'; then
  echo 'revoked session remained valid' >&2; exit 1
fi

recovery="$(curl -fsS -X POST "$BASE_URL/v1/devices/recovery/issue" -H "X-Sentinel-Enrollment-Token: $ENROLLMENT_TOKEN" --data-urlencode "fingerprint=$fingerprint")"
code="$(printf '%s' "$recovery" | json code)"
openssl ecparam -name prime256v1 -genkey -noout -out "$TMP/new-key.pem"
openssl ec -in "$TMP/new-key.pem" -pubout -outform DER -out "$TMP/new-pub.der" 2>/dev/null
new_fp="$(sha256sum "$TMP/new-pub.der" | cut -d' ' -f1)"
new_pub="$(b64url "$TMP/new-pub.der")"
curl -fsS -X POST "$BASE_URL/v1/devices/recovery/rotate" --data-urlencode "fingerprint=$fingerprint" --data-urlencode "publicKey=$new_pub" --data-urlencode "recoveryCode=$code" >/dev/null

new_challenge="$(curl -fsS -X POST "$BASE_URL/v1/challenges/issue" --data-urlencode "fingerprint=$new_fp")"
new_id="$(printf '%s' "$new_challenge" | json challengeId)"
new_nonce="$(printf '%s' "$new_challenge" | json nonce)"
printf '%s' "$new_nonce" | decode_b64url > "$TMP/new-nonce.bin"
openssl dgst -sha256 -sign "$TMP/new-key.pem" -out "$TMP/new-signature.der" "$TMP/new-nonce.bin"
new_sig="$(b64url "$TMP/new-signature.der")"
curl -fsS -X POST "$BASE_URL/v1/challenges/verify" --data-urlencode "challengeId=$new_id" --data-urlencode "publicKey=$new_pub" --data-urlencode "signature=$new_sig" >/dev/null

echo 'SENTINEL server E2E: PASS'
