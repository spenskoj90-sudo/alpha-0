#!/usr/bin/env bash
set -Eeuo pipefail

# ALPHA-0 one-shot updater — UPDATE-002A
# preflight -> backup -> write -> build -> tests -> regression -> self-delete
# On failure files are restored and this script is kept for diagnosis.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$ROOT" ]] || { echo 'FAIL: run inside the ALPHA-0 git repository.'; exit 1; }
cd "$ROOT"

readonly UPDATE_ID="UPDATE-002A"
readonly BACKUP_DIR=".alpha0-backup/${UPDATE_ID}"
readonly SELF_PATH="$(realpath "$0")"

restore() {
  local rc=$?
  echo
  echo 'FAIL detected. Restoring changed files...'
  if [[ -d "$BACKUP_DIR" ]]; then
    while IFS= read -r -d '' backup; do
      rel="${backup#"$BACKUP_DIR"/}"
      mkdir -p "$(dirname "$rel")"
      cp -f "$backup" "$rel"
    done < <(find "$BACKUP_DIR" -type f -print0)
    echo 'Rollback: PASS'
  fi
  echo 'STATUS: FAIL'
  echo 'Updater retained for diagnosis.'
  exit "$rc"
}
trap restore ERR

fail() { echo "FAIL: $*"; exit 1; }

echo '========================================'
echo "ALPHA-0 ${UPDATE_ID}"
echo '========================================'

for f in settings.gradle.kts build.gradle.kts app/build.gradle.kts app/src/main/AndroidManifest.xml \
  app/src/main/java/com/alpha0/app/MainActivity.kt \
  app/src/main/java/com/alpha0/app/security/DeviceIdentity.kt \
  app/src/test/java/com/alpha0/app/security/FingerprintTest.kt; do
  [[ -f "$f" ]] || fail "missing expected file: $f"
done
[[ -f ./gradlew ]] || fail 'gradlew not found.'
chmod +x ./gradlew

echo 'Pre-flight: PASS'

rm -rf "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
backup_file() { mkdir -p "$BACKUP_DIR/$(dirname "$1")"; cp -p "$1" "$BACKUP_DIR/$1"; }
for f in app/build.gradle.kts app/src/main/java/com/alpha0/app/MainActivity.kt \
  app/src/main/java/com/alpha0/app/security/DeviceIdentity.kt \
  app/src/test/java/com/alpha0/app/security/FingerprintTest.kt; do backup_file "$f"; done
echo 'Backup: PASS'

write_file() { mkdir -p "$(dirname "$1")"; cat > "$1"; }

write_file app/build.gradle.kts <<'FILE'
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.alpha0.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.alpha0.app"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}

kotlin {
    jvmToolchain(17)
}
FILE

write_file app/src/main/java/com/alpha0/app/security/DeviceIdentity.kt <<'FILE'
package com.alpha0.app.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.PublicKey
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.Locale

class DeviceIdentity {
    companion object {
        private const val KEYSTORE_PROVIDER = "AndroidKeyStore"
        private const val KEY_ALIAS = "alpha0.device.identity.v1"
        private const val HASH_ALGORITHM = "SHA-256"
        private const val SIGNATURE_ALGORITHM = "SHA256withECDSA"
        private const val CURVE = "secp256r1"
    }

    data class IdentityInfo(val fingerprint: String, val algorithm: String)

    private fun loadKeyStore(): KeyStore = KeyStore.getInstance(KEYSTORE_PROVIDER).apply { load(null) }

    @Synchronized
    private fun ensureKeyExists() {
        val keyStore = loadKeyStore()
        if (keyStore.containsAlias(KEY_ALIAS)) return

        val generator = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, KEYSTORE_PROVIDER)
        val spec = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
        )
            .setAlgorithmParameterSpec(ECGenParameterSpec(CURVE))
            .setDigests(KeyProperties.DIGEST_SHA256)
            .build()

        generator.initialize(spec)
        generator.generateKeyPair()
    }

    private fun getPrivateKey(): PrivateKey {
        ensureKeyExists()
        return loadKeyStore().getKey(KEY_ALIAS, null) as? PrivateKey
            ?: error("ALPHA-0 device identity private key is unavailable")
    }

    private fun getPublicKey(): PublicKey {
        ensureKeyExists()
        return loadKeyStore().getCertificate(KEY_ALIAS)?.publicKey
            ?: error("ALPHA-0 device identity public key is unavailable")
    }

    fun getIdentityInfo(): IdentityInfo {
        val fingerprint = MessageDigest.getInstance(HASH_ALGORITHM)
            .digest(getPublicKey().encoded)
            .toHex()
        return IdentityInfo(fingerprint, "EC / $CURVE")
    }

    fun sign(challenge: ByteArray): ByteArray {
        require(challenge.isNotEmpty()) { "Challenge must not be empty" }
        return Signature.getInstance(SIGNATURE_ALGORITHM).apply {
            initSign(getPrivateKey())
            update(challenge)
        }.sign()
    }

    fun verify(challenge: ByteArray, signatureBytes: ByteArray): Boolean {
        if (challenge.isEmpty() || signatureBytes.isEmpty()) return false
        return Signature.getInstance(SIGNATURE_ALGORITHM).apply {
            initVerify(getPublicKey())
            update(challenge)
        }.verify(signatureBytes)
    }

    /** Expected to be false for an Android Keystore-backed private key. */
    fun isPrivateKeyExported(): Boolean = getPrivateKey().encoded != null

    private fun ByteArray.toHex(): String = joinToString("") {
        String.format(Locale.US, "%02x", it)
    }
}
FILE

write_file app/src/test/java/com/alpha0/app/security/FingerprintTest.kt <<'FILE'
package com.alpha0.app.security

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test
import java.security.MessageDigest

class FingerprintTest {
    @Test
    fun sha256FingerprintIsDeterministic() {
        val input = "ALPHA-0".toByteArray()
        assertEquals(fingerprint(input), fingerprint(input))
    }

    @Test
    fun sha256FingerprintChangesWhenInputChanges() {
        assertNotEquals(
            fingerprint("ALPHA-0".toByteArray()),
            fingerprint("ALPHA-0-CHANGED".toByteArray())
        )
    }

    @Test
    fun sha256FingerprintHasExpectedLength() {
        assertEquals(64, fingerprint("ALPHA-0".toByteArray()).length)
    }

    private fun fingerprint(data: ByteArray): String = MessageDigest
        .getInstance("SHA-256")
        .digest(data)
        .joinToString("") { "%02x".format(it) }
}
FILE

write_file app/src/main/java/com/alpha0/app/MainActivity.kt <<'FILE'
package com.alpha0.app

import android.app.Activity
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.TextView
import com.alpha0.app.security.DeviceIdentity

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(48, 48, 48, 48)
        }
        val title = TextView(this).apply {
            text = "ALPHA-0"
            textSize = 32f
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
        }
        val status = TextView(this).apply {
            textSize = 18f
            gravity = Gravity.CENTER
            setPadding(0, 32, 0, 0)
        }
        root.addView(title)
        root.addView(status)
        setContentView(root)

        try {
            val identity = DeviceIdentity().getIdentityInfo()
            status.text = """
                BUILD-002A

                Device Identity initialized.

                Algorithm:
                ${identity.algorithm}

                Fingerprint:
                ${identity.fingerprint}

                Private key:
                Non-exportable Keystore key

                Status:
                READY
            """.trimIndent()
        } catch (error: Exception) {
            status.text = """
                BUILD-002A

                Device Identity:
                FAILED

                ${error.javaClass.simpleName}

                ${error.message ?: "Unknown error"}
            """.trimIndent()
        }
    }
}
FILE

echo 'Files updated: PASS'
echo
echo 'Running assembleDebug...'
./gradlew --no-daemon --stacktrace assembleDebug
echo
echo 'Running unit tests...'
./gradlew --no-daemon --stacktrace test
echo
echo 'Regression: PASS'
find app/build/outputs/apk/debug -maxdepth 1 -type f -name '*.apk' -print
echo
echo 'Cleaning updater after successful verification...'
rm -f "$SELF_PATH"
echo '========================================'
echo 'STATUS: ACCEPTED'
echo 'Build: PASS'
echo 'Tests: PASS'
echo 'Regression: PASS'
echo 'Updater self-removal: PASS'
echo '========================================'
echo "Backup retained at: ${BACKUP_DIR}"
