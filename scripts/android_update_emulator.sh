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
    python3 scripts/apk_signer_certificate.py --algorithm sha256
}

case "$1" in
  build)
    [[ "$SENTINEL_RUNTIME_ENVIRONMENT" == staging &&
       "$SENTINEL_API_BASE_URL" == https://sentinel-core-staging.onrender.com &&
       "$SENTINEL_SOURCE_SHA" =~ ^[a-f0-9]{40}$ ]] ||
       { echo "Exact-SHA staging build required" >&2; exit 1; }
    mkdir -p "$OUT"
    # Both APKs and their test instrumentation use the runner's isolated
    # ephemeral debug signer. No durable or Owner signing material is involved.
    SENTINEL_PHYSICAL_TEST_VERSION_CODE="$OLD" ./gradlew --no-daemon assemblePhysicalTest
    cp "$SRC" "$BASE"
    SENTINEL_PHYSICAL_TEST_VERSION_CODE="$NEW" ./gradlew --no-daemon assemblePhysicalTest
    cp "$SRC" "$NEXT"
    # Instrumentation is compiled against exactly the updated diagnostic variant.
    SENTINEL_PHYSICAL_TEST_VERSION_CODE="$NEW" ./gradlew --no-daemon assemblePhysicalTestAndroidTest
    mapfile -t test_apks < <(find app/build/outputs/apk/androidTest/physicalTest -maxdepth 1 -type f -name '*.apk')
    [[ "${#test_apks[@]}" -eq 1 ]] || { echo "Expected one upgrade-only instrumentation APK" >&2; exit 1; }
    cp "${test_apks[0]}" "$OUT/instrumentation.apk"
    assert_version "$BASE" "$OLD"
    assert_version "$NEXT" "$NEW"
    f1="$(fingerprint "$BASE")"
    f2="$(fingerprint "$NEXT")"
    echo "Baseline APK certificate SHA-256: $f1"
    echo "Updated APK certificate SHA-256: $f2"
    [[ "$f1" =~ ^[a-f0-9]{64}$ && "$f1" == "$f2" ]] ||
      { echo "Signer extraction failed or APK signing identity changed" >&2; exit 1; }
    # Test APK is also signed by the same disposable debug signer, as required
    # by Android's instrumentation target signature check.
    fixt="$(fingerprint "$OUT/instrumentation.apk")"
    [[ "$fixt" == "$f1" ]] || { echo "Instrumentation signer differs from test target" >&2; exit 1; }
    echo "PASS: APK identities, test instrumentation and ephemeral signer verified"
    ;;
  verify)
    assert_version "$BASE" "$OLD"
    assert_version "$NEXT" "$NEW"
    adb install -r "$BASE"
    package_state="$(adb shell dumpsys package "$PKG")"
    [[ "$package_state" == *"versionCode=$OLD "* ]] || { echo "Baseline version missing" >&2; exit 1; }
    adb install -r "$OUT/instrumentation.apk"
    adb shell "run-as $PKG sh -c 'mkdir -p files && printf SENTINEL_UPDATE_PRESERVED > files/update_contract_marker'"
    adb shell am instrument -w \
      -e class com.alpha0.app.security.UpgradeContinuityInstrumentedTest#seedDeviceState \
      "$PKG.test/androidx.test.runner.AndroidJUnitRunner" | tee "$OUT/seed-instrumentation.txt"
    grep -q '^OK (1 test)' "$OUT/seed-instrumentation.txt" ||
      { echo "Failed to seed synthetic Keystore/session evidence" >&2; exit 1; }
    value="$(adb shell "run-as $PKG cat files/update_contract_marker" | tr -d '\r')"
    [[ "$value" == SENTINEL_UPDATE_PRESERVED ]] || { echo "Seed data missing" >&2; exit 1; }
    # Upload the actual future APK to the target app's private files. No
    # system installer or unknown-sources permission is invoked by this check.
    adb shell "run-as $PKG sh -c 'mkdir -p files && cat > files/synthetic_candidate.apk'" < "$NEXT"
    expected_bytes="$(wc -c < "$NEXT" | tr -d '[:space:]')"
    transferred_bytes="$(adb shell "run-as $PKG wc -c files/synthetic_candidate.apk" | tr -d '\r' | awk '{print $1}')"
    [[ "$transferred_bytes" == "$expected_bytes" ]] ||
      { echo "Transferred upgrade APK length differs from compiled artifact" >&2; exit 1; }
    adb shell am instrument -w \
      -e class com.alpha0.app.update.UpdatePreflightInstrumentedTest#acceptsCompatibleNewerSameSignerApk \
      "$PKG.test/androidx.test.runner.AndroidJUnitRunner" | tee "$OUT/preflight-before.txt"
    grep -q '^OK (1 test)' "$OUT/preflight-before.txt" ||
      { echo "In-app APK preflight rejected a compatible signed upgrade" >&2; exit 1; }
    adb install -r "$NEXT"
    package_state="$(adb shell dumpsys package "$PKG")"
    [[ "$package_state" == *"versionCode=$NEW "* ]] || { echo "Update version missing" >&2; exit 1; }
    value="$(adb shell "run-as $PKG cat files/update_contract_marker" | tr -d '\r')"
    [[ "$value" == SENTINEL_UPDATE_PRESERVED ]] ||
      { echo "Private data lost during in-place update" >&2; exit 1; }
    adb shell am instrument -w \
      -e class com.alpha0.app.security.UpgradeContinuityInstrumentedTest#verifyPreservedDeviceState \
      "$PKG.test/androidx.test.runner.AndroidJUnitRunner" | tee "$OUT/verify-instrumentation.txt"
    grep -q '^OK (1 test)' "$OUT/verify-instrumentation.txt" ||
      { echo "Keystore or encrypted session continuity failed after update" >&2; exit 1; }
    adb shell am instrument -w \
      -e class com.alpha0.app.update.UpdatePreflightInstrumentedTest#rejectsSameVersionAfterUpgrade \
      "$PKG.test/androidx.test.runner.AndroidJUnitRunner" | tee "$OUT/preflight-after.txt"
    grep -q '^OK (1 test)' "$OUT/preflight-after.txt" ||
      { echo "In-app preflight failed to block already installed version" >&2; exit 1; }
    echo "PASS: Same-signer APK upgraded; in-app preflight accepted newer APK and rejected non-increasing version; app-private data, Keystore, session and preferences survived"

    ;;
  *) echo "Usage: bash $0 build|verify" >&2; exit 2 ;;
esac
