package com.alpha0.app.update

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertNotNull
import org.junit.Test
import java.nio.charset.StandardCharsets
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.Base64

class SignedUpdateFeedTest {
    private val pair: KeyPair = KeyPairGenerator.getInstance("EC").run {
        initialize(ECGenParameterSpec("secp256r1"))
        generateKeyPair()
    }
    private val feedUrl = "https://updates.example.org/android/latest.feed"
    private val pkg = "com.alpha0.app.physicaltest"
    private val signer = "a".repeat(64)
    private val sha256 = "b".repeat(64)
    private val notes = "Исправлен аварийный Stop.\nДанные сохраняются."
    private val b64 = Base64.getUrlEncoder().withoutPadding()
    private val keyPin = Base64.getEncoder().encodeToString(pair.public.encoded)

    private fun manifest(
        app: String = pkg,
        version: String = "100000895",
        cert: String = signer,
        apkUrl: String = "https://updates.example.org/android/sentinel-v2.apk",
        digest: String = sha256,
        message: String = notes,
    ) = (
        "SENTINEL-UPDATE-v1\n" +
            "package=" + app + "\n" +
            "versionCode=" + version + "\n" +
            "certificateSha256=" + cert + "\n" +
            "apkUrl=" + apkUrl + "\n" +
            "apkSha256=" + digest + "\n" +
            "whatsNewBase64=" + b64.encodeToString(message.toByteArray(StandardCharsets.UTF_8)) + "\n"
        ).toByteArray(StandardCharsets.UTF_8)

    private fun envelope(payload: ByteArray = manifest(), tamperSignature: Boolean = false): ByteArray {
        val sign = Signature.getInstance("SHA256withECDSA")
        sign.initSign(pair.private)
        sign.update(payload)
        val signature = sign.sign()
        if (tamperSignature) signature[signature.lastIndex] =
            (signature.last().toInt() xor 1).toByte()
        return ("SENTINEL-SIGNED-FEED-v1\n" +
            b64.encodeToString(payload) + "\n" +
            b64.encodeToString(signature) + "\n").toByteArray(StandardCharsets.UTF_8)
    }

    private fun verify(
        document: ByteArray = envelope(),
        key: String = keyPin,
        source: String = feedUrl,
        app: String = pkg,
        installedVersion: Long = 100000894,
        installedSigner: String = signer,
    ) = SignedUpdateFeed.verify(document, key, source, app, installedVersion, installedSigner)

    @Test fun validSameCertificateNewerVersionHasVerifiedRussianReleaseNotes() {
        val ready = assertNotNull(verify())
        assertEquals(pkg, ready.packageName)
        assertEquals(100000895L, ready.versionCode)
        assertEquals(notes, ready.whatsNew)
        assertEquals(sha256, ready.apkSha256)
    }

    @Test fun missingOrIncorrectPinnedKeyIsRejected() {
        assertNull(verify(key = ""))
        val different = KeyPairGenerator.getInstance("EC").run {
            initialize(ECGenParameterSpec("secp256r1"))
            generateKeyPair()
        }
        assertNull(verify(key = Base64.getEncoder().encodeToString(different.public.encoded)))
    }

    @Test fun modifiedBytesOrSignatureCannotPass() {
        assertNull(verify(document = envelope(tamperSignature = true)))
        val tampered = envelope().copyOf()
        val index = tampered.indexOf('A'.code.toByte())
        if (index > 0) tampered[index] = 'B'.code.toByte()
        assertNull(verify(document = tampered))
    }

    @Test fun differentPackageSignerOrNonIncreasingVersionCannotPass() {
        assertNull(verify(document = envelope(manifest(app = "com.attacker.app"))))
        assertNull(verify(document = envelope(manifest(cert = "c".repeat(64)))))
        assertNull(verify(document = envelope(manifest(version = "100000894"))))
        assertNull(verify(document = envelope(manifest(version = "100000893"))))
        assertNull(verify(installedSigner = "c".repeat(64)))
        assertNull(verify(installedVersion = 100000895))
    }

    @Test fun nonHttpsCrossOriginAndRedirectableUrlAreRejected() {
        assertNull(verify(source = "http://updates.example.org/android/latest.feed"))
        assertNull(verify(source = "https://user:password@updates.example.org/android/latest.feed"))
        assertNull(verify(document = envelope(manifest(apkUrl = "http://updates.example.org/android/a.apk"))))
        assertNull(verify(document = envelope(manifest(apkUrl = "https://elsewhere.example.org/android/a.apk"))))
        assertNull(verify(document = envelope(manifest(apkUrl = "https://updates.example.org/../a.apk"))))
        assertNull(verify(document = envelope(manifest(apkUrl = "https://updates.example.org/android/a.apk?tag=v2"))))
    }

    @Test fun malformedUnknownFieldsDuplicateFieldsAndTooLargeFeedsAreRejected() {
        assertNull(verify(document = envelope(manifest() + "extra=true\n".toByteArray())))
        assertNull(verify(document = envelope(manifest().toString(StandardCharsets.UTF_8)
            .replace("apkSha256=", "otherField=").toByteArray())))
        assertNull(verify(document = ("SENTINEL-SIGNED-FEED-v1\n\n\n").toByteArray()))
        assertNull(verify(document = ByteArray(8193) { 'A'.code.toByte() }))
        assertNull(verify(document = envelope(manifest(message = "\u0000bad"))))
    }

    @Test fun unsignedOrMissingReleaseNotesCannotBeTreatedAsVerified() {
        assertNull(verify(document = envelope(manifest(message = ""))))
        assertNull(verify(document = envelope(manifest(message = "  "))))
        assertNull(verify(document = envelope(manifest(message = "a".repeat(1025)))))
    }
}
