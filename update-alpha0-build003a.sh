#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$ROOT" ]]; then
  echo "ERROR: not inside a git repository."
  exit 1
fi
cd "$ROOT"

BACKUP_DIR=".alpha0-backup/UPDATE-003A-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

FILES=(
  "app/src/main/java/com/alpha0/app/security/DeviceIdentity.kt"
  "app/src/main/java/com/alpha0/app/MainActivity.kt"
)

for f in "${FILES[@]}"; do
  [[ -f "$f" ]] || { echo "ERROR: missing $f"; exit 1; }
  mkdir -p "$BACKUP_DIR/$(dirname "$f")"
  cp "$f" "$BACKUP_DIR/$f"
done

restore() {
  echo "Restoring previous files..."
  for f in "${FILES[@]}"; do
    cp "$BACKUP_DIR/$f" "$f"
  done
}
trap 'restore' ERR

cat > app/src/main/java/com/alpha0/app/security/DeviceIdentity.kt <<'EOF'
package com.alpha0.app.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
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

    data class IdentityInfo(
        val fingerprint: String,
        val algorithm: String
    )

    private fun loadKeyStore(): KeyStore =
        KeyStore.getInstance(KEYSTORE_PROVIDER).apply {
            load(null)
        }

    private fun ensureKeyExists() {
        val keyStore = loadKeyStore()
        if (keyStore.containsAlias(KEY_ALIAS)) return

        val generator = KeyPairGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_EC,
            KEYSTORE_PROVIDER
        )

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

    private fun getPrivateKey(): java.security.PrivateKey {
        ensureKeyExists()
        return loadKeyStore().getKey(KEY_ALIAS, null) as java.security.PrivateKey
    }

    private fun getPublicKey(): java.security.PublicKey {
        ensureKeyExists()
        return loadKeyStore().getCertificate(KEY_ALIAS).publicKey
    }

    fun getIdentityInfo(): IdentityInfo {
        val publicKey = getPublicKey()
        val fingerprint = MessageDigest
            .getInstance(HASH_ALGORITHM)
            .digest(publicKey.encoded)
            .toHex()

        return IdentityInfo(
            fingerprint = fingerprint,
            algorithm = "$CURVE / $SIGNATURE_ALGORITHM"
        )
    }

    fun sign(challenge: ByteArray): ByteArray =
        Signature.getInstance(SIGNATURE_ALGORITHM).apply {
            initSign(getPrivateKey())
            update(challenge)
        }.sign()

    fun verify(
        challenge: ByteArray,
        signatureBytes: ByteArray
    ): Boolean =
        Signature.getInstance(SIGNATURE_ALGORITHM).apply {
            initVerify(getPublicKey())
            update(challenge)
        }.verify(signatureBytes)

    fun isPrivateKeyExported(): Boolean =
        getPrivateKey().encoded != null

    private fun ByteArray.toHex(): String =
        joinToString("") {
            String.format(Locale.US, "%02x", it.toInt() and 0xff)
        }
}
EOF

cat > app/src/main/java/com/alpha0/app/MainActivity.kt <<'EOF'
package com.alpha0.app

import android.app.Activity
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.TextView
import com.alpha0.app.security.DeviceIdentity
import java.security.SecureRandom

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
            textSize = 17f
            gravity = Gravity.CENTER
            setPadding(0, 32, 0, 0)
        }

        root.addView(title)
        root.addView(status)
        setContentView(root)

        try {
            val identity = DeviceIdentity()
            val info = identity.getIdentityInfo()

            val challenge = ByteArray(32).also {
                SecureRandom().nextBytes(it)
            }

            val signature = identity.sign(challenge)
            val signatureValid = identity.verify(challenge, signature)

            val tamperedChallenge = challenge.clone().also {
                it[0] = (it[0].toInt() xor 0x01).toByte()
            }
            val tamperedRejected = !identity.verify(tamperedChallenge, signature)

            val keyNonExportable = !identity.isPrivateKeyExported()

            val cryptoPassed =
                signatureValid &&
                tamperedRejected &&
                keyNonExportable

            status.text = """
                BUILD-003A

                Device Identity initialized.

                Algorithm:
                ${info.algorithm}

                Fingerprint:
                ${info.fingerprint}

                Private key:
                Android Keystore

                Cryptographic self-test:
                Signature: ${if (signatureValid) "PASS" else "FAIL"}
                Tampered challenge: ${if (tamperedRejected) "REJECTED" else "ACCEPTED"}
                Private key export: ${if (keyNonExportable) "BLOCKED" else "EXPOSED"}

                Status:
                ${if (cryptoPassed) "READY / CRYPTO PASS" else "CRYPTO FAILED"}
            """.trimIndent()
        } catch (error: Exception) {
            status.text = """
                BUILD-003A

                Device Identity:
                FAILED

                ${error.javaClass.simpleName}

                ${error.message ?: "Unknown error"}
            """.trimIndent()
        }
    }
}
EOF

if [[ -x "./gradlew" ]]; then
  ./gradlew --no-daemon --stacktrace assembleDebug
  ./gradlew --no-daemon --stacktrace test
else
  gradle --no-daemon --stacktrace assembleDebug
  gradle --no-daemon --stacktrace test
fi

trap - ERR
echo
echo "PASS: BUILD-003A compiled and unit tests passed."
echo "Backup retained at: $BACKUP_DIR"
