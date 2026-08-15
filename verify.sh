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
check 'Web Dockerfile' test -f web/Dockerfile
check 'Android manifest' test -f app/src/main/AndroidManifest.xml
check 'CI build workflow' test -f .github/workflows/build.yml
check 'CI security workflow' test -f .github/workflows/security.yml
check 'CI deploy workflow' test -f .github/workflows/deploy.yml
check 'CI release workflow' test -f .github/workflows/release.yml
check 'API docs' test -f docs/API.md
check 'Security docs' test -f docs/SECURITY.md
check 'Architecture docs' test -f docs/ARCHITECTURE.md
check 'Deployment docs' test -f docs/DEPLOYMENT.md
check 'Contributing docs' test -f docs/CONTRIBUTING.md
check 'Changelog' test -f docs/CHANGELOG.md

if command -v python >/dev/null 2>&1; then
  check 'Python compile' python -m compileall -q server/app server/migrate.py
fi

if command -v grep >/dev/null 2>&1; then
  if grep -RInE '(AKIA[0-9A-Z]{16}|-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9_]{20,})' . --exclude-dir=.git --exclude='*.md' >/dev/null; then
    printf 'FAIL  obvious credential pattern scan\n'; fail=$((fail+1))
  else
    printf 'PASS  obvious credential pattern scan\n'; pass=$((pass+1))
  fi
fi

printf '\nPASSED=%s FAILED=%s\n' "$pass" "$fail"
if [ "$fail" -ne 0 ]; then exit 1; fi
