#!/usr/bin/env bash
# Manual-only encrypted off-provider PostgreSQL backup. Never print DATABASE_URL.
set -euo pipefail
umask 077

fail() { printf 'backup failure: %s\n' "$1" >&2; exit 1; }

[[ "${GITHUB_REPOSITORY:-}" == "spenskoj90-sudo/alpha-0" ]] || fail "unexpected repository"
[[ "${GITHUB_REF:-}" == "refs/heads/main" ]] || fail "protected main is required"
[[ -n "${DATABASE_URL:-}" ]] || fail "missing unpooled database secret"
[[ "$DATABASE_URL" == postgres://* || "$DATABASE_URL" == postgresql://* ]] || fail "invalid connection scheme"
[[ "$DATABASE_URL" != *-pooler* ]] || fail "pooled URLs cannot be used with pg_dump"
[[ "${BACKUP_AGE_RECIPIENT:-}" =~ ^age1[0-9a-z]{30,}$ ]] || fail "missing or invalid age public recipient"
[[ "${BACKUP_S3_BUCKET:-}" =~ ^[a-z0-9][a-z0-9.-]{2,62}$ ]] || fail "missing or invalid bucket"
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
aws s3 cp --only-show-errors --sse AES256 "$ciphertext" "$remote"
# Read the copy back from the independent provider and verify byte-for-byte.
aws s3 cp --only-show-errors "$remote" "$download"
cmp -s "$ciphertext" "$download" || fail "remote ciphertext mismatch"

{
  printf 'Encrypted offsite backup uploaded and ciphertext compared successfully.\n\n'
  printf 'Location: s3://%s/%s\n' "$BACKUP_S3_BUCKET" "$obj"
  printf 'Encrypted size: %s bytes\n' "$size"
  printf 'Encrypted SHA-256: %s\n' "$digest"
  printf 'Source: Neon sentinel/staging (read-only pg_dump)\n'
  printf 'Restore status: NOT VERIFIED; offline age identity and isolated pg_restore required.\n'
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
printf 'Backup ciphertext uploaded and verified against remote copy. Restore drill remains pending.\n'
