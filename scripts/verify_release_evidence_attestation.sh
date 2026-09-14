#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: verify_release_evidence_attestation.sh <repository> <source-sha> <output-dir>" >&2
  exit 2
fi

repository="$1"
source_sha="$2"
output_dir="$3"

case "$source_sha" in
  *[!0-9a-f]*|'') echo "source SHA must be lowercase hexadecimal" >&2; exit 2 ;;
esac
[ "${#source_sha}" -eq 40 ] || { echo "source SHA must contain 40 characters" >&2; exit 2; }
command -v gh >/dev/null 2>&1 || { echo "gh CLI is required" >&2; exit 2; }
command -v jq >/dev/null 2>&1 || { echo "jq is required" >&2; exit 2; }

runs="$(gh api --method GET "/repos/$repository/actions/workflows/release-evidence.yml/runs?branch=main&event=push&head_sha=$source_sha&per_page=100")"
run_id="$(printf '%s' "$runs" | jq -er --arg sha "$source_sha" '
  [.workflow_runs[]
    | select(.name == "Release Evidence Preflight")
    | select(.path == ".github/workflows/release-evidence.yml")
    | select(.head_branch == "main" and .head_sha == $sha and .event == "push")
    | select(.status == "completed" and .conclusion == "success")]
  | sort_by(.id)
  | last
  | .id
')"

rm -rf "$output_dir"
mkdir -p "$output_dir"
gh run download "$run_id" \
  --repo "$repository" \
  --name "sentinel-release-evidence-$source_sha" \
  --dir "$output_dir"

mapfile -t files < <(find "$output_dir" -type f -print)
[ "${#files[@]}" -eq 1 ] || { echo "release-evidence artifact must contain exactly one file" >&2; exit 1; }
[ "$(basename "${files[0]}")" = "release-evidence.json" ] || { echo "unexpected release-evidence artifact member" >&2; exit 1; }

bash scripts/verify_github_attestation.sh \
  "${files[0]}" \
  "$repository" \
  ".github/workflows/release-evidence.yml" \
  "$source_sha" \
  "refs/heads/main"

echo "protected-main release-evidence attestation PASS"
