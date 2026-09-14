#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: verify_final_release_acceptance_attestation.sh <repository> <source-sha> <output-dir>" >&2
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

runs="$(gh api --method GET "/repos/$repository/actions/workflows/final-release-acceptance.yml/runs?event=workflow_dispatch&branch=main&per_page=100")"
mapfile -t run_ids < <(printf '%s' "$runs" | jq -er --arg sha "$source_sha" '
  [.workflow_runs[]
    | select(.name == "Final Release Acceptance")
    | select(.path == ".github/workflows/final-release-acceptance.yml")
    | select(.head_branch == "main" and .head_sha == $sha and .event == "workflow_dispatch")
    | select(.status == "completed" and .conclusion == "success")]
  | sort_by(.id) | reverse | .[].id
')
[ "${#run_ids[@]}" -gt 0 ] || { echo "no successful final-acceptance workflow exists for source SHA" >&2; exit 1; }

rm -rf "$output_dir"
mkdir -p "$output_dir"
found=""
for run_id in "${run_ids[@]}"; do
  if gh run download "$run_id" \
    --repo "$repository" \
    --name "sentinel-final-release-acceptance-$source_sha" \
    --dir "$output_dir" >/dev/null 2>&1; then
    found="$run_id"
    break
  fi
  rm -rf "$output_dir"/*
done
[ -n "$found" ] || { echo "final-acceptance artifact is missing" >&2; exit 1; }

mapfile -t files < <(find "$output_dir" -type f -print)
[ "${#files[@]}" -eq 1 ] || { echo "final-acceptance artifact must contain exactly one file" >&2; exit 1; }
[ "$(basename "${files[0]}")" = "final-release-acceptance.json" ] || { echo "unexpected final-acceptance artifact member" >&2; exit 1; }

bash scripts/verify_github_attestation.sh \
  "${files[0]}" \
  "$repository" \
  ".github/workflows/final-release-acceptance.yml" \
  "$source_sha" \
  "refs/heads/main"

echo "final release acceptance attestation PASS"
