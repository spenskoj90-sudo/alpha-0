#!/usr/bin/env sh
set -eu

if command -v gradle >/dev/null 2>&1; then
  exec gradle "$@"
fi

VERSION=8.9
DIST="${GRADLE_USER_HOME:-$HOME/.gradle}/wrapper/dists/gradle-${VERSION}-bin.zip"
HOME_DIR="${GRADLE_USER_HOME:-$HOME/.gradle}"
INSTALL="$HOME_DIR/sentinel-gradle/${VERSION}"

if [ ! -x "$INSTALL/bin/gradle" ]; then
  mkdir -p "$INSTALL"
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  command -v curl >/dev/null 2>&1 || { echo "gradle or curl is required" >&2; exit 1; }
  curl -fsSL --retry 3 "https://services.gradle.org/distributions/gradle-${VERSION}-bin.zip" -o "$DIST"
  command -v unzip >/dev/null 2>&1 || { echo "gradle or unzip is required" >&2; exit 1; }
  unzip -q "$DIST" -d "$TMP"
  cp -R "$TMP/gradle-${VERSION}/." "$INSTALL/"
fi

exec "$INSTALL/bin/gradle" "$@"
