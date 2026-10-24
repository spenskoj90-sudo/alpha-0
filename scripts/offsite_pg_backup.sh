#!/usr/bin/env bash
# Manual-only encrypted off-provider PostgreSQL backup. Never print DATABASE_URL.
set -euo pipefail
umask 077

fail() { printf 'backup failure: %s\n' "$1" >&2; exit 1; }

[[ "${GITHUB_REPOSITORY:-}" == "spenskoj90-sudo/alpha-0" ]] || fail "unexpected repository"
[[ "${GITHUB_REF:-}" == "refs/heads/main" ]] || fail "protected main is required"
[[ -n "${DATABASE_URL:-}" ]] || fail "missing unpooled database secret"
[[ -n "${BACKUP_EXPECTED_HOST:-}" ]] || fail "missing expected Neon branch host"
[[ -n "${BACKUP_EXPECTED_DATABASE:-}" ]] || fail "missing expected database name"
# Validate *which* branch is read, without printing or exposing the DSN.
# Refuse a pooled endpoint, unexpected host or database, or missing TLS.
python3 - <<'PY'
import os
import sys
from urllib.parse import parse_qs, unquote, urlsplit
try:
    u = urlsplit(os.environ["DATABASE_URL"])
    host = u.hostname or ""
    name = unquote(u.path.lstrip("/"))
    q = parse_qs(u.query)
    ssl = (q.get("sslmode") or [""])[0]
    ok = (
        u.scheme in ("postgresql", "postgres")
        and bool(u.username) and bool(u.password)
        and host == os.environ["BACKUP_EXPECTED_HOST"]
        and host.endswith(".neon.tech")
        and "-pooler" not in host
        and name == os.environ["BACKUP_EXPECTED_DATABASE"]
        and ssl in ("require", "verify-ca", "verify-full")
    )
except (KeyError, ValueError):
    ok = False
if not ok:
    print("backup failure: source connection identity/TLS does not match expected Neon branch", file=sys.stderr)
    sys.exit(1)
PY
[[ "$DATABASE_URL" == postgres://* || "$DATABASE_URL" == postgresql://* ]] || fail "invalid connection scheme"
[[ "$DATABASE_URL" != *-pooler* ]] || fail "pooled URLs cannot be used with pg_dump"
[[ "${BACKUP_AGE_RECIPIENT:-}" =~ ^age1[0-9a-z]{30,}$ ]] || fail "missing or invalid age public recipient"
[[ "${BACKUP_S3_BUCKET:-}" =~ ^[a-z0-9][a-z0-9.-]{2,62}$ ]] || fail "missing or invalid bucket"
[[ "${BACKUP_R2_ENDPOINT:-}" =~ ^https://[a-f0-9]{32}(\.(eu|fedramp))?\.r2\.cloudflarestorage\.com/?$ ]] || fail "missing or invalid Cloudflare R2 endpoint"
[[ -n "${AWS_ACCESS_KEY_ID:-}" && -n "${AWS_SECRET_ACCESS_KEY:-}" ]] || fail "R2 limited-scope S3 API credentials not configured"
[[ "${AWS_REGION:-auto}" == "auto" ]] || fail "R2 AWS_REGION must be auto"
export AWS_EC2_METADATA_DISABLED=true
export AWS_DEFAULT_REGION=auto
export AWS_REGION=auto
export AWS_PAGER=""
export AWS_REQUEST_CHECKSUM_CALCULATION=when_required
export AWS_RESPONSE_CHECKSUM_VALIDATION=when_required
command -v docker >/dev/null || fail "Docker unavailable"
command -v age >/dev/null || fail "age unavailable"
command -v aws >/dev/null || fail "AWS CLI unavailable"
command -v sha256sum >/dev/null || fail "sha256sum unavailable"

workdir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/sentinel-offsite-XXXXXXXX")"
trap 'rm -rf -- "$workdir"' EXIT
ts="$(date -u +%Y%m%dT%H%M%SZ)"
run="${GITHUB_RUN_ID:-manual}-${GITHUB_RUN_ATTEMPT:-1}"
name="sentinel-db-$ts-$run.pgdump.age"
obj="sentinel/staging/$name"
ciphertext="$workdir/$name"
download="$workdir/verify-$name"

# Plaintext flows only through a pipe, not through Actions artifacts or the backup disk.
# pipefail prevents uploading an incomplete dump if either pg_dump or age fails.
docker run --rm --pull=always \
  --env DATABASE_URL \
  postgres:18.1-bookworm \
  sh -c 'exec pg_dump --format=custom --no-owner --no-acl --dbname="$DATABASE_URL"' \
  | age --encrypt --recipient "$BACKUP_AGE_RECIPIENT" --output "$ciphertext"

[[ -s "$ciphertext" ]] || fail "no ciphertext generated"
digest="$(sha256sum "$ciphertext" | awk '{print $1}')"
size="$(wc -c < "$ciphertext" | tr -d ' ')"
[[ "$size" -gt 100 ]] || fail "ciphertext unexpectedly small"

remote="s3://$BACKUP_S3_BUCKET/$obj"
# R2 has platform-managed server-side encryption; the payload was already
# encrypted by age. Do not use AWS S3-only --sse AES256 flags with Cloudflare R2.
aws --endpoint-url "$BACKUP_R2_ENDPOINT" s3 cp --only-show-errors "$ciphertext" "$remote"
# Download the ciphertext from R2 and compare it byte-for-byte.
aws --endpoint-url "$BACKUP_R2_ENDPOINT" s3 cp --only-show-errors "$remote" "$download"
cmp -s "$ciphertext" "$download" || fail "remote ciphertext mismatch"

{
  printf 'Encrypted Cloudflare R2 backup uploaded and ciphertext compared successfully.\n\n'
  printf 'Cloudflare R2 object: s3://%s/%s\n' "$BACKUP_S3_BUCKET" "$obj"
  printf 'Encrypted size: %s bytes\n' "$size"
  printf 'Encrypted SHA-256: %s\n' "$digest"
  printf 'Source: Neon sentinel/staging (read-only pg_dump)\n'
  printf 'Restore status: NOT VERIFIED; offline age identity and isolated pg_restore required.\n'
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
printf 'Backup ciphertext uploaded and verified against remote copy. Restore drill remains pending.\n'
