#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "usage: verify_final_release_acceptance_live.sh <repository> <source-sha> <signer-sha256> <minimum-profile> <work-dir>" >&2
  exit 2
fi

repository="$1"
source_sha="$2"
signer_sha256="$3"
minimum_profile="$4"
work_dir="$5"

case "$source_sha" in
  *[!0-9a-f]*|'') echo "source SHA must be lowercase hexadecimal" >&2; exit 2 ;;
esac
[ "${#source_sha}" -eq 40 ] || { echo "source SHA must contain 40 characters" >&2; exit 2; }
case "$minimum_profile" in
  publication|deployment|production-traffic) ;;
  *) echo "invalid minimum final-acceptance profile" >&2; exit 2 ;;
esac

rm -rf "$work_dir"
mkdir -p "$work_dir"
version="$(tr -d '[:space:]' < VERSION)"
[ -n "$version" ] || { echo "VERSION is empty" >&2; exit 1; }

bash scripts/verify_release_evidence_attestation.sh \
  "$repository" "$source_sha" "$work_dir/release-evidence"

python scripts/release_lineage.py presecret \
  --repository "$repository" \
  --sha "$source_sha"
bash scripts/write_release_presecret_binding.sh \
  "$repository" "$source_sha" "$version" "$work_dir/release-presecret-binding.json"
python scripts/release_lineage.py verify-binding \
  --input "$work_dir/release-presecret-binding.json" \
  --expected-repository "$repository" \
  --expected-sha "$source_sha" \
  --expected-version "$version"

python scripts/release_lineage.py fetch-candidate \
  --repository "$repository" \
  --sha "$source_sha" \
  --binding "$work_dir/release-presecret-binding.json" \
  --expected-signer-sha256 "$signer_sha256" \
  --output-dir "$work_dir/candidate"

for subject in \
  "$work_dir/candidate/app-release.apk" \
  "$work_dir/candidate/release-candidate.json" \
  "$work_dir/candidate/release-presecret-binding.json"
do
  bash scripts/verify_github_attestation.sh \
    "$subject" \
    "$repository" \
    ".github/workflows/release-candidate.yml" \
    "$source_sha" \
    "refs/heads/main"
done

bash scripts/verify_release_upstream_attestations.sh \
  "$work_dir/release-evidence/release-evidence.json" \
  "$work_dir/upstream"

bash scripts/verify_final_release_acceptance_attestation.sh \
  "$repository" "$source_sha" "$work_dir/final-acceptance"

mapfile -t package_sha_files < <(find "$work_dir/upstream/packaged-companion" -type f -name archive-sha256.txt -print)
[ "${#package_sha_files[@]}" -eq 1 ] || { echo "expected exactly one packaged Companion archive digest" >&2; exit 1; }

python scripts/final_release_acceptance.py verify \
  --input "$work_dir/final-acceptance/final-release-acceptance.json" \
  --candidate "$work_dir/candidate/release-candidate.json" \
  --apk "$work_dir/candidate/app-release.apk" \
  --companion-sha256-file "${package_sha_files[0]}" \
  --minimum-profile "$minimum_profile" \
  --expected-repository "$repository" \
  --expected-sha "$source_sha" \
  --expected-version "$version"

echo "live final release acceptance $minimum_profile: PASS"
