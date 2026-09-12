#!/usr/bin/env sh
set -eu

if command -v gradle >/dev/null 2>&1; then
  exec gradle "$@"
fi

GRADLE_VERSION=8.9
GRADLE_DIST_SHA256=d725d707bfabd4dfdc958c624003b3c80accc03f7037b5122c4b1d0ef15cecab
GRADLE_CACHE_HOME="${GRADLE_USER_HOME:-$HOME/.gradle}"
GRADLE_DIST="$GRADLE_CACHE_HOME/wrapper/dists/gradle-${GRADLE_VERSION}-bin.zip"
GRADLE_INSTALL="$GRADLE_CACHE_HOME/sentinel-gradle/${GRADLE_VERSION}"

if [ ! -x "$GRADLE_INSTALL/bin/gradle" ]; then
  mkdir -p "$GRADLE_INSTALL" "$(dirname "$GRADLE_DIST")"
  GRADLE_TMP="$(mktemp -d)"
  trap 'rm -rf "$GRADLE_TMP"' EXIT
  command -v curl >/dev/null 2>&1 || { echo "gradle or curl is required" >&2; exit 1; }
  if [ ! -f "$GRADLE_DIST" ]; then
    curl -fsSL --retry 3 "https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip" -o "$GRADLE_TMP/gradle.zip"
    printf '%s  %s\n' "$GRADLE_DIST_SHA256" "$GRADLE_TMP/gradle.zip" | sha256sum -c -
    mv "$GRADLE_TMP/gradle.zip" "$GRADLE_DIST"
  else
    printf '%s  %s\n' "$GRADLE_DIST_SHA256" "$GRADLE_DIST" | sha256sum -c -
  fi
  command -v unzip >/dev/null 2>&1 || { echo "gradle or unzip is required" >&2; exit 1; }
  unzip -q "$GRADLE_DIST" -d "$GRADLE_TMP"
  cp -R "$GRADLE_TMP/gradle-${GRADLE_VERSION}/." "$GRADLE_INSTALL/"
fi

exec "$GRADLE_INSTALL/bin/gradle" "$@"
