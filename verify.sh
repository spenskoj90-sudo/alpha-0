#!/usr/bin/env bash
set -euo pipefail

fail=0
pass=0
check() {
  local name="$1"; shift
  if "$@"; then
    printf 'PASS  %s\n' "$name"; pass=$((pass+1))
  else
    printf 'FAIL  %s\n' "$name"; fail=$((fail+1))
  fi
}

check 'README' test -f README.md
check 'LICENSE' test -f LICENSE
check '.gitignore' test -f .gitignore
check '.editorconfig' test -f .editorconfig
check '.env.example' test -f .env.example
check 'Gradle settings' test -f settings.gradle.kts
check 'Gradle build' test -f build.gradle.kts
check 'Gradle wrapper properties' test -f gradle/wrapper/gradle-wrapper.properties
check 'Core package' test -f server/pyproject.toml
check 'Core migration runner' test -f server/migrate.py
check 'Core migrations' test -d server/migrations
check 'Docker Core' test -f server/Dockerfile
check 'Docker Compose' test -f docker-compose.yml
check 'Web package' test -f web/package.json
check 'Web lockfile' test -f web/package-lock.json
check 'Web Dockerfile' test -f web/Dockerfile
check 'Canonical version' test -s VERSION
check 'Android manifest' test -f app/src/main/AndroidManifest.xml
check 'CI build workflow' test -f .github/workflows/build.yml
check 'CI security workflow' test -f .github/workflows/security.yml
check 'CI deploy workflow' test -f .github/workflows/deploy.yml
check 'CI release workflow' test -f .github/workflows/release.yml
check 'CI release-candidate workflow' test -f .github/workflows/release-candidate.yml
check 'CI release evidence workflow' test -f .github/workflows/release-evidence.yml
check 'CI final release acceptance workflow' test -f .github/workflows/final-release-acceptance.yml
check 'API docs' test -f docs/API.md
check 'Security docs' test -f docs/SECURITY.md
check 'Architecture docs' test -f docs/ARCHITECTURE.md
check 'Deployment docs' test -f docs/DEPLOYMENT.md
check 'Contributing docs' test -f docs/CONTRIBUTING.md
check 'Changelog' test -f docs/CHANGELOG.md
check 'Document authority map' test -f docs/DOCUMENT_STATUS.md
check 'Design system contract' test -f docs/DESIGN_SYSTEM_V1.md
check 'Design system manifest' test -f design/sentinel-design-system.v1.json
check 'Design system tests' test -f scripts/test_design_system.py
check 'Platform baseline tests' test -f scripts/test_platform_baseline.py
check 'Telemetry contract' test -f docs/OBSERVABILITY.md
check 'Telemetry manifest' test -f observability/telemetry-contract.v1.json
check 'Telemetry contract tests' test -f scripts/test_telemetry_contract.py
check 'Provider runtime state tests' test -f scripts/test_provider_runtime_state.py
check 'Repository policy verifier' test -f scripts/verify_repository.py
check 'Release evidence verifier' test -f scripts/release_evidence.py
check 'Release evidence policy entrypoint' test -f scripts/release_evidence_entrypoint.py
check 'Release evidence tests' test -f scripts/test_release_evidence.py
check 'Release supply-chain evidence tests' test -f scripts/test_release_evidence_supply_chain.py
check 'Release lineage verifier' test -f scripts/release_lineage.py
check 'Release lineage tests' test -f scripts/test_release_lineage.py
check 'Artifact attestation tests' test -f scripts/test_artifact_attestations.py
check 'Final release acceptance verifier' test -f scripts/final_release_acceptance.py
check 'Final release acceptance tests' test -f scripts/test_final_release_acceptance.py
check 'Physical-test artifact verifier' test -f scripts/physical_test_artifact.py
check 'Physical-test artifact verifier tests' test -f scripts/test_physical_test_artifact.py
check 'Android product shell contract' test -f docs/ANDROID_PRODUCT_SHELL_V1.md
check 'Android product shell tests' test -f scripts/test_android_product_shell.py
check 'GitHub attestation verifier' test -f scripts/verify_github_attestation.sh
check 'Protected-main release attestation verifier' test -f scripts/verify_release_evidence_attestation.sh
check 'Release upstream attestation verifier' test -f scripts/verify_release_upstream_attestations.sh
check 'Final acceptance attestation verifier' test -f scripts/verify_final_release_acceptance_attestation.sh
check 'Live final acceptance verifier' test -f scripts/verify_final_release_acceptance_live.sh
check 'Release evidence contract' test -f docs/RELEASE_EVIDENCE_PREFLIGHT_V1.md
check 'Release lineage contract' test -f docs/RELEASE_LINEAGE_V1.md
check 'Final release acceptance contract' test -f docs/FINAL_RELEASE_ACCEPTANCE_V1.md

check 'Artifact and acceptance shell syntax' bash -n \
  scripts/verify_github_attestation.sh \
  scripts/verify_release_evidence_attestation.sh \
  scripts/verify_release_upstream_attestations.sh \
  scripts/verify_final_release_acceptance_attestation.sh \
  scripts/verify_final_release_acceptance_live.sh

if command -v python >/dev/null 2>&1; then
  check 'Python compile' python -m compileall -q \
    server/app server/migrate.py \
    scripts/release_evidence.py scripts/release_evidence_entrypoint.py \
    scripts/test_release_evidence.py scripts/test_release_evidence_supply_chain.py \
    scripts/release_lineage.py scripts/test_release_lineage.py \
    scripts/test_artifact_attestations.py scripts/test_design_system.py scripts/test_platform_baseline.py \
    scripts/test_telemetry_contract.py scripts/test_provider_runtime_state.py \
    scripts/final_release_acceptance.py scripts/test_final_release_acceptance.py \
    scripts/physical_test_artifact.py scripts/test_physical_test_artifact.py
  check 'Android product shell invariants' python scripts/test_android_product_shell.py
  check 'Repository policy invariants' python scripts/verify_repository.py
  check 'Release evidence invariants' python scripts/test_release_evidence.py
  check 'Release supply-chain evidence invariants' python scripts/test_release_evidence_supply_chain.py
  check 'Release lineage invariants' python scripts/test_release_lineage.py
  check 'Artifact attestation invariants' python scripts/test_artifact_attestations.py
  check 'Design system invariants' python scripts/test_design_system.py
  check 'Platform baseline invariants' python scripts/test_platform_baseline.py
  check 'Telemetry contract invariants' python scripts/test_telemetry_contract.py
  check 'Provider runtime state invariants' python scripts/test_provider_runtime_state.py
  check 'Final release acceptance invariants' python scripts/test_final_release_acceptance.py
  check 'Physical-test artifact invariants' python scripts/test_physical_test_artifact.py
fi

if command -v grep >/dev/null 2>&1; then
  if grep -RInE '(AKIA[0-9A-Z]{16}|-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9_]{20,})' . \
      --exclude-dir=.git --exclude-dir=.gradle --exclude-dir=.next --exclude-dir=.venv --exclude-dir=build \
      --exclude-dir=node_modules --exclude='*.md' >/dev/null; then
    printf 'FAIL  obvious credential pattern scan\n'; fail=$((fail+1))
  else
    printf 'PASS  obvious credential pattern scan\n'; pass=$((pass+1))
  fi
fi

printf '\nPASSED=%s FAILED=%s\n' "$pass" "$fail"
if [ "$fail" -ne 0 ]; then exit 1; fi
