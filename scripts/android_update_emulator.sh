#!/usr/bin/env bash
# Synthetic, same-runner debug-signed in-place APK update test. Never uses Owner keys.
set -euo pipefail

PKG=com.alpha0.app.physicaltest
OLD=1700000301
NEW=1700000302
OUT="$RUNNER_TEMP/sentinel-update-retention"
SRC=app/build/outputs/apk/physicalTest/app-physicalTest.apk
BASE="$OUT/baseline.apk"
NEXT="$OUT/update.apk"

sdk_tool() {
  find "$ANDROID_SDK_ROOT/build-tools" -type f -name "$1" | sort -V | tail -n 1
}
assert_version() {
  local apk="$1" expected="$2" line
  line="$("$(sdk_tool aapt)" dump badging "$apk")"
  [[ "$line" == *"name='$PKG'"* && "$line" == *"versionCode='$expected'"* ]] ||
    { echo "APK package/version mismatch" >&2; exit 1; }
}
fingerprint() {
  "$(sdk_tool apksigner)" verify --print-certs "$1" |
    sed -n 's/^Signer #1 certificate SHA-256 digest: //p' |
    tr '[:upper:]' '[:lower:]' | tr -d '[:space:]:'
}

case "$1" in
  build)
    [[ "$SENTINEL_RUNTIME_ENVIRONMENT" == staging &&
       "$SENTINEL_API_BASE_URL" == https://sentinel-core-staging.onrender.com &&
       "$SENTINEL_SOURCE_SHA" =~ ^[a-f0-9]{40}$ ]] ||
       { echo "Exact-SHA staging build required" >&2; exit 1; }
    mkdir -p "$OUT"
    # A unique, disposable CI-only certificate is generated per run, and reused
    # for both APKs. It is never published or confused with Owner stable custody.
    local_keystore="$OUT/ci-update-only.p12"
    local_password="$(openssl rand -hex 24)"
    keytool -genkeypair -noprompt -storetype PKCS12 \
      -keystore "$local_keystore" -storepass "$local_password" \
      -alias ci-update -keypass "$local_password" -keyalg RSA -keysize 3072 \
      -validity 1 -dname "CN=SENTINEL isolated update emulator test" >/dev/null 2>&1
    chmod 600 "$local_keystore"
    export SENTINEL_PHYSICAL_TEST_KEYSTORE_PATH="$local_keystore"
    export SENTINEL_PHYSICAL_TEST_KEYSTORE_PASSWORD="$local_password"
    export SENTINEL_PHYSICAL_TEST_KEY_ALIAS=ci-update
    export SENTINEL_PHYSICAL_TEST_KEY_PASSWORD="$local_password"
    SENTINEL_PHYSICAL_TEST_VERSION_CODE="$OLD" ./gradlew --no-daemon assemblePhysicalTest
    cp "$SRC" "$BASE"
    SENTINEL_PHYSICAL_TEST_VERSION_CODE="$NEW" ./gradlew --no-daemon assemblePhysicalTest
    cp "$SRC" "$NEXT"
    assert_version "$BASE" "$OLD"
    assert_version "$NEXT" "$NEW"
    f1="$(fingerprint "$BASE")"
    f2="$(fingerprint "$NEXT")"
    [[ "$f1" =~ ^[a-f0-9]{64}$ && "$f1" == "$f2" ]] ||
      { echo "Debug signer changed across builds" >&2; exit 1; }
    echo "PASS: APK identities and ephemeral test signer verified"
    ;;
  verify)
    assert_version "$BASE" "$OLD"
    assert_version "$NEXT" "$NEW"
    adb install -r "$BASE"
    package_state="$(adb shell dumpsys package "$PKG")"
    [[ "$package_state" == *"versionCode=$OLD "* ]] || { echo "Baseline version missing" >&2; exit 1; }
    adb shell "run-as $PKG sh -c 'mkdir -p files && printf SENTINEL_UPDATE_PRESERVED > files/update_contract_marker'"
    value="$(adb shell "run-as $PKG cat files/update_contract_marker" | tr -d '\r')"
    [[ "$value" == SENTINEL_UPDATE_PRESERVED ]] || { echo "Seed data missing" >&2; exit 1; }
    adb install -r "$NEXT"
    package_state="$(adb shell dumpsys package "$PKG")"
    [[ "$package_state" == *"versionCode=$NEW "* ]] || { echo "Update version missing" >&2; exit 1; }
    value="$(adb shell "run-as $PKG cat files/update_contract_marker" | tr -d '\r')"
    [[ "$value" == SENTINEL_UPDATE_PRESERVED ]] ||
      { echo "Private data lost during in-place update" >&2; exit 1; }
    echo "PASS: Android installed compatible APK over existing app and retained private data"
    ;;
  *) echo "Usage: bash $0 build|verify" >&2; exit 2 ;;
esac
