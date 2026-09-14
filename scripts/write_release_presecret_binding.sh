#!/usr/bin/env bash
set -euo pipefail

repository="${1:?repository is required}"
sha="${2:?source SHA is required}"
version="${3:?version is required}"
output="${4:?output path is required}"

case "$repository" in
  */*) ;;
  *) exit 1 ;;
esac
case "$sha" in
  *[!0-9a-f]*|'') exit 1 ;;
esac
test "${#sha}" -eq 40
test -n "$version"

work="$(mktemp)"
trap 'rm -f "$work"' EXIT

jq -n \
  --arg repository "$repository" \
  --arg sha "$sha" \
  --arg version "$version" \
  --arg artifact_name "sentinel-release-evidence-$sha" \
  '{
    schema: "sentinel.release-presecret-binding.v1",
    status: "PASS",
    source: {repository: $repository, sha: $sha, version: $version},
    releaseEvidence: {
      workflow: {
        name: "Release Evidence Preflight",
        path: ".github/workflows/release-evidence.yml",
        event: "push",
        headBranch: "main"
      },
      artifact: {name: $artifact_name, headSha: $sha}
    },
    claims: {
      signingMaterialAccessed: false,
      signedReleaseArtifact: false,
      releasePublished: false,
      productionDeployed: false
    }
  }' > "$work"

digest="sha256:$(jq -cSj '.' "$work" | sha256sum | awk '{print $1}')"
mkdir -p "$(dirname "$output")"
jq --arg digest "$digest" '. + {bindingDigest: $digest}' "$work" > "$output"
