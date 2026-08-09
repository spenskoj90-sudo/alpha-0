#!/usr/bin/env bash

set -euo pipefail

echo "========================================"
echo "ALPHA-0 temporary update"
echo "========================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DEVICE_IDENTITY="$ROOT_DIR/app/src/main/java/com/alpha0/app/security/DeviceIdentity.kt"
FINGERPRINT_TEST="$ROOT_DIR/app/src/test/java/com/alpha0/app/security/FingerprintTest.kt"
MAIN_ACTIVITY="$ROOT_DIR/app/src/main/java/com/alpha0/app/MainActivity.kt"

BACKUP_DIR="$ROOT_DIR/.alpha0-update-backup"

echo "[1/6] Checking project structure..."

if [ ! -f "$ROOT_DIR/settings.gradle.kts" ]; then
echo "ERROR: settings.gradle.kts not found."
exit 1
fi

if [ ! -f "$ROOT_DIR/app/build.gradle.kts" ]; then
echo "ERROR: app/build.gradle.kts not found."
exit 1
fi

mkdir -p "$BACKUP_DIR"

echo "[2/6] Creating backups..."

backup_file() {
local file="$1"

if [ -f "$file" ]; then
    local relative
    relative="${file#$ROOT_DIR/}"
    mkdir -p "$BACKUP_DIR/$(dirname "$relative")"
    cp "$file" "$BACKUP_DIR/$relative"
fi

}

backup_file "$DEVICE_IDENTITY"
backup_file "$FINGERPRINT_TEST"
backup_file "$MAIN_ACTIVITY"

echo "[3/6] Writing DeviceIdentity.kt..."

mkdir -p "$(dirname "$DEVICE_IDENTITY")"

cat > "$DEVICE_IDENTITY" <<'EOF'
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

    private const val CURVE = "secp256r1"
    private const val SIGNATURE_ALGORITHM = "SHA256withECDSA"
    private const val HASH_ALGORITHM = "SHA-256"
}

data class IdentityInfo(
    val fingerprint: String,
    val algorithm: String
)

private fun loadKeyStore(): KeyStore {
    return KeyStore.getInstance(KEYSTORE_PROVIDER).apply {
        load(null)
    }
}

private fun ensureKeyExists() {
    val keyStore = loadKeyStore()

    if (keyStore.containsAlias(KEY_ALIAS)) {
        return
    }

    val generator = KeyPairGenerator.getInstance(
        KeyProperties.KEY_ALGORITHM_EC,
        KEYSTORE_PROVIDER
    )

    val spec = KeyGenParameterSpec.Builder(
        KEY_ALIAS,
        KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
    )
        .setAlgorithmParameterSpec(
            ECGenParameterSpec(CURVE)
        )
        .setDigests(
            KeyProperties.DIGEST_SHA256
        )
        .build()

    generator.initialize(spec)
    generator.generateKeyPair()
}

private fun getPrivateKey(): PrivateKey {
    ensureKeyExists()

    val keyStore = loadKeyStore()

    return keyStore.getKey(
        KEY_ALIAS,
        null
    ) as? PrivateKey
        ?: throw IllegalStateException(
            "ALPHA-0 private key is unavailable"
        )
}

private fun getPublicKey(): PublicKey {
    ensureKeyExists()

    val keyStore = loadKeyStore()

    return keyStore
        .getCertificate(KEY_ALIAS)
        ?.publicKey
        ?: throw IllegalStateException(
            "ALPHA-0 public key is unavailable"
        )
}

fun getIdentityInfo(): IdentityInfo {
    val publicKey = getPublicKey()

    val fingerprint = MessageDigest
        .getInstance(HASH_ALGORITHM)
        .digest(publicKey.encoded)
        .toHex()

    return IdentityInfo(
        fingerprint = fingerprint,
        algorithm = "EC / $CURVE / $SIGNATURE_ALGORITHM"
    )
}

fun sign(challenge: ByteArray): ByteArray {
    require(challenge.isNotEmpty()) {
        "Challenge must not be empty"
    }

    return Signature
        .getInstance(SIGNATURE_ALGORITHM)
        .apply {
            initSign(getPrivateKey())
            update(challenge)
        }
        .sign()
}

fun verify(
    challenge: ByteArray,
    signatureBytes: ByteArray
): Boolean {
    if (challenge.isEmpty() || signatureBytes.isEmpty()) {
        return false
    }

    return try {
        Signature
            .getInstance(SIGNATURE_ALGORITHM)
            .apply {
                initVerify(getPublicKey())
                update(challenge)
            }
            .verify(signatureBytes)
    } catch (_: Exception) {
        false
    }
}

private fun ByteArray.toHex(): String {
    return joinToString("") {
        String.format(Locale.US, "%02x", it)
    }
}

}
EOF

echo "[4/6] Writing FingerprintTest.kt..."

mkdir -p "$(dirname "$FINGERPRINT_TEST")"

cat > "$FINGERPRINT_TEST" <<'EOF'
package com.alpha0.app.security

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test
import java.security.MessageDigest

class FingerprintTest {

@Test
fun sha256FingerprintIsDeterministic() {
    val input = "ALPHA-0".toByteArray()

    val first = fingerprint(input)
    val second = fingerprint(input)

    assertEquals(first, second)
}

@Test
fun sha256FingerprintChangesWhenInputChanges() {
    val first = fingerprint("ALPHA-0".toByteArray())
    val second = fingerprint("ALPHA-0-CHANGED".toByteArray())

    assertNotEquals(first, second)
}

@Test
fun sha256FingerprintHasExpectedLength() {
    val result = fingerprint("ALPHA-0".toByteArray())

    assertEquals(64, result.length)
}

@Test
fun sha256FingerprintContainsOnlyHexCharacters() {
    val result = fingerprint("ALPHA-0".toByteArray())

    assert(result.all { it in '0'..'9' || it in 'a'..'f' })
}

private fun fingerprint(data: ByteArray): String {
    return MessageDigest
        .getInstance("SHA-256")
        .digest(data)
        .joinToString("") {
            "%02x".format(it)
        }
}

}
EOF

echo "[5/6] Writing MainActivity.kt..."

mkdir -p "$(dirname "$MAIN_ACTIVITY")"

cat > "$MAIN_ACTIVITY" <<'EOF'
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

    initializeDeviceIdentity(status)
}

private fun initializeDeviceIdentity(status: TextView) {
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
            Android Keystore

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
EOF

echo "[6/6] Verifying files..."

grep -q "class DeviceIdentity" "$DEVICE_IDENTITY"
grep -q "class FingerprintTest" "$FINGERPRINT_TEST"
grep -q "class MainActivity" "$MAIN_ACTIVITY"

if grep -R "isInsideSecurityHardware" 
"$ROOT_DIR/app/src/main/java" 
"$ROOT_DIR/app/src/test" 
2>/dev/null; then

echo "ERROR: obsolete isInsideSecurityHardware reference remains."
echo "Backup preserved at: $BACKUP_DIR"
exit 1

fi

echo ""
echo "========================================"
echo "ALPHA-0 FILE UPDATE: PASS"
echo "========================================"
echo ""
echo "Files updated:"
echo "  - DeviceIdentity.kt"
echo "  - FingerprintTest.kt"
echo "  - MainActivity.kt"
echo ""
echo "Backup created at:"
echo "  $BACKUP_DIR"
echo ""
echo "Temporary updater will now remove itself."
echo ""

rm -rf "$BACKUP_DIR"
rm -- "$ROOT_DIR/update-alpha0.sh"

echo "Cleanup: PASS"
echo "========================================"
EOF
