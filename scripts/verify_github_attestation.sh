#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "usage: verify_github_attestation.sh <artifact> <repository> <workflow-path> <source-sha> <source-ref>" >&2
  exit 2
fi

artifact="$1"
repository="$2"
workflow_path="$3"
source_sha="$4"
source_ref="$5"

case "$repository" in
  */*) ;;
  *) echo "repository must be owner/name" >&2; exit 2 ;;
esac
case "$repository" in
  *$'\n'*|*$'\r'*|*' '*) echo "repository contains unsafe characters" >&2; exit 2 ;;
esac
case "$workflow_path" in
  .github/workflows/*.yml|.github/workflows/*.yaml) ;;
  *) echo "workflow path must be under .github/workflows" >&2; exit 2 ;;
esac
case "$source_sha" in
  *[!0-9a-f]*|'') echo "source SHA must be lowercase hexadecimal" >&2; exit 2 ;;
esac
[ "${#source_sha}" -eq 40 ] || { echo "source SHA must contain 40 characters" >&2; exit 2; }
case "$source_ref" in
  refs/heads/*|refs/tags/*) ;;
  *) echo "source ref must be an explicit heads/tags ref" >&2; exit 2 ;;
esac
[ -f "$artifact" ] && [ -s "$artifact" ] || { echo "attestation subject is missing or empty" >&2; exit 2; }
command -v gh >/dev/null 2>&1 || { echo "gh CLI is required" >&2; exit 2; }

gh attestation verify "$artifact" \
  --repo "$repository" \
  --signer-workflow "$repository/$workflow_path" \
  --source-digest "$source_sha" \
  --source-ref "$source_ref" \
  --deny-self-hosted-runners \
  >/dev/null

echo "artifact attestation PASS"
