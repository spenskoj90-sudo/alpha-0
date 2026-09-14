#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: verify_release_upstream_attestations.sh <release-evidence.json> <work-dir>" >&2
  exit 2
fi

manifest="$1"
work_dir="$2"
[ -s "$manifest" ] || { echo "release evidence is missing or empty" >&2; exit 2; }
command -v gh >/dev/null 2>&1 || { echo "gh CLI is required" >&2; exit 2; }
command -v jq >/dev/null 2>&1 || { echo "jq is required" >&2; exit 2; }
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required" >&2; exit 2; }

repository="$(jq -er '.source.repository' "$manifest")"
source_sha="$(jq -er '.source.sha' "$manifest")"
event="$(jq -er '.source.event' "$manifest")"
[ "$event" = "push" ] || { echo "attestation gate requires protected-main push evidence" >&2; exit 1; }

supply_run="$(jq -er '.workflows[] | select(.name == "Supply Chain Evidence") | .runId' "$manifest")"
package_run="$(jq -er '.workflows[] | select(.name == "Packaged Companion Host") | .runId' "$manifest")"

rm -rf "$work_dir"
mkdir -p "$work_dir/supply-chain" "$work_dir/packaged-companion"

gh run download "$supply_run" \
  --repo "$repository" \
  --name "sentinel-supply-chain-evidence-$source_sha" \
  --dir "$work_dir/supply-chain"
gh run download "$package_run" \
  --repo "$repository" \
  --name "packaged-companion-host-$source_sha" \
  --dir "$work_dir/packaged-companion"

find_one() {
  local root="$1"
  local name="$2"
  mapfile -t matches < <(find "$root" -type f -name "$name" -print)
  [ "${#matches[@]}" -eq 1 ] || {
    echo "expected exactly one $name under $root" >&2
    exit 1
  }
  printf '%s\n' "${matches[0]}"
}

supply_manifest="$(find_one "$work_dir/supply-chain" supply-chain-evidence.json)"
supply_dir="$(dirname "$supply_manifest")"
python scripts/supply_chain_evidence.py verify \
  --input-dir "$supply_dir" \
  --expected-repository "$repository" \
  --expected-sha "$source_sha"

for subject in \
  "$supply_manifest" \
  "$(find_one "$work_dir/supply-chain" sentinel-application.cdx.json)" \
  "$(find_one "$work_dir/supply-chain" sentinel-core-container.cdx.json)"
do
  bash scripts/verify_github_attestation.sh \
    "$subject" \
    "$repository" \
    ".github/workflows/supply-chain-evidence.yml" \
    "$source_sha" \
    "refs/heads/main"
done

package_zip="$(find_one "$work_dir/packaged-companion" sentinel-companion-win32-x64.zip)"
build_evidence="$(find_one "$work_dir/packaged-companion" build-evidence.json)"
package_manifest="$(find_one "$work_dir/packaged-companion" package-manifest.sha256)"
smoke_evidence="$(find_one "$work_dir/packaged-companion" smoke-evidence.json)"
archive_sha_file="$(find_one "$work_dir/packaged-companion" archive-sha256.txt)"

jq -e --arg sha "$source_sha" '.status == "pass" and .sourceSha == $sha and .signed == false' "$build_evidence" >/dev/null
jq -e --arg sha "$source_sha" '.status == "pass" and .sourceSha == $sha and .signed == false' "$smoke_evidence" >/dev/null
expected_archive_sha="$(tr -d '[:space:]' < "$archive_sha_file" | tr '[:upper:]' '[:lower:]')"
case "$expected_archive_sha" in
  *[!0-9a-f]*|'') echo "invalid packaged archive SHA-256 evidence" >&2; exit 1 ;;
esac
[ "${#expected_archive_sha}" -eq 64 ] || { echo "invalid packaged archive SHA-256 length" >&2; exit 1; }
actual_archive_sha="$(sha256sum "$package_zip" | awk '{print $1}')"
[ "$actual_archive_sha" = "$expected_archive_sha" ] || { echo "packaged archive SHA-256 mismatch" >&2; exit 1; }

for subject in \
  "$package_zip" \
  "$build_evidence" \
  "$package_manifest" \
  "$smoke_evidence" \
  "$archive_sha_file"
do
  bash scripts/verify_github_attestation.sh \
    "$subject" \
    "$repository" \
    ".github/workflows/packaged-companion.yml" \
    "$source_sha" \
    "refs/heads/main"
done

echo "protected-main upstream artifact attestations PASS"
