package com.alpha0.app.update

import java.net.URI
import java.nio.ByteBuffer
import java.nio.charset.CharacterCodingException
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets
import java.security.KeyFactory
import java.security.Signature
import java.security.interfaces.ECPublicKey
import java.security.spec.X509EncodedKeySpec
import java.util.Base64

/**
 * Detached, owner-pinned P-256 signature over the exact UTF-8 manifest bytes.
 *
 * No trust-on-first-use, remote key rotation, redirect or unauthenticated fallback.
 * The feed verifying key is PUBLIC and distinct from the Android APK signing key.
 * Actual APK signer and bytes are independently checked before system installation.
 */
internal object SignedUpdateFeed {
    private const val MAX_FEED_BYTES = 8 * 1024
    private const val MAX_MANIFEST_BYTES = 4 * 1024
    private const val MAX_NOTES_BYTES = 1024
    private const val FEED_HEADER = "SENTINEL-SIGNED-FEED-v1"
    private const val MANIFEST_HEADER = "SENTINEL-UPDATE-v1"
    private val hexDigest = Regex("[0-9a-f]{64}")
    private val urlBase64 = Regex("[A-Za-z0-9_-]+")
    private val packagePattern = Regex("[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z][A-Za-z0-9_]*)+")

    data class Release(
        val packageName: String,
        val versionCode: Long,
        val apkUrl: String,
        val apkSha256: String,
        val certificateSha256: String,
        val whatsNew: String,
    )

    private fun strictUtf8(bytes: ByteArray): String =
        StandardCharsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
            .decode(ByteBuffer.wrap(bytes)).toString()

    private fun decodeBase64Url(value: String, maxBytes: Int): ByteArray? {
        if (value.isEmpty() || value.length > maxBytes * 2 || !urlBase64.matches(value)) return null
        val decoded = Base64.getUrlDecoder().decode(value)
        if (decoded.isEmpty() || decoded.size > maxBytes) return null
        if (Base64.getUrlEncoder().withoutPadding().encodeToString(decoded) != value) return null
        return decoded
    }

    private fun httpsUri(value: String): URI? {
        val uri = URI(value)
        if (uri.scheme != "https" || uri.host.isNullOrBlank() || uri.rawUserInfo != null ||
            uri.rawQuery != null || uri.rawFragment != null || (uri.port != -1 && uri.port != 443) ||
            uri.rawPath.isNullOrBlank() || !uri.rawPath.startsWith("/") || uri.normalize() != uri ||
            uri.rawPath != uri.path ||
            uri.path.split('/').any { it == "." || it == ".." } ||
            uri.path.contains('\\') ||
            uri.isOpaque || uri.host.endsWith(".") || uri.host.contains("%")
        ) return null
        return uri
    }

    /** Reject malformed, unsigned, replayed, cross-origin or different-signer offers. */
    fun verify(
        feedBytes: ByteArray,
        verifyingKeyDerBase64: String,
        feedUrl: String,
        installedPackage: String,
        installedVersionCode: Long,
        installedSignerSha256: String,
    ): Release? {
        if (feedBytes.isEmpty() || feedBytes.size > MAX_FEED_BYTES ||
            installedVersionCode <= 0 || !hexDigest.matches(installedSignerSha256) ||
            verifyingKeyDerBase64.isBlank()
        ) return null
        return try {
            val origin = httpsUri(feedUrl) ?: return null
            val envelope = strictUtf8(feedBytes).split('\n')
            if (envelope.size != 4 || envelope[0] != FEED_HEADER || envelope[3].isNotEmpty()) return null
            val manifestBytes = decodeBase64Url(envelope[1], MAX_MANIFEST_BYTES) ?: return null
            val signatureBytes = decodeBase64Url(envelope[2], 256) ?: return null
            val key = KeyFactory.getInstance("EC").generatePublic(
                X509EncodedKeySpec(Base64.getDecoder().decode(verifyingKeyDerBase64)),
            ) as? ECPublicKey ?: return null
            if (key.params.curve.field.fieldSize != 256) return null
            val verifier = Signature.getInstance("SHA256withECDSA")
            verifier.initVerify(key)
            verifier.update(manifestBytes)
            if (!verifier.verify(signatureBytes)) return null

            val lines = strictUtf8(manifestBytes).split('\n')
            if (lines.size != 8 || lines[0] != MANIFEST_HEADER || lines[7].isNotEmpty()) return null
            val names = listOf(
                "package=", "versionCode=", "certificateSha256=", "apkUrl=",
                "apkSha256=", "whatsNewBase64=",
            )
            for (i in names.indices) if (!lines[i + 1].startsWith(names[i])) return null
            val app = lines[1].removePrefix(names[0])
            val version = lines[2].removePrefix(names[1]).toLongOrNull() ?: return null
            val signer = lines[3].removePrefix(names[2])
            val apkUrl = lines[4].removePrefix(names[3])
            val sha256 = lines[5].removePrefix(names[4])
            val notesBytes = decodeBase64Url(lines[6].removePrefix(names[5]), MAX_NOTES_BYTES)
                ?: return null
            val notes = strictUtf8(notesBytes)
            val apkUri = httpsUri(apkUrl) ?: return null
            if (!packagePattern.matches(app) || app != installedPackage ||
                version <= installedVersionCode || version > 2_100_000_000L ||
                signer != installedSignerSha256 || !hexDigest.matches(sha256) ||
                notes.isBlank() || notes.any { it.code < 32 && it != '\n' } ||
                origin.host != apkUri.host || origin.port != apkUri.port ||
                !apkUri.rawPath.endsWith(".apk")
            ) return null
            Release(app, version, apkUrl, sha256, signer, notes)
        } catch (_: IllegalArgumentException) {
            null
        } catch (_: java.security.GeneralSecurityException) {
            null
        } catch (_: CharacterCodingException) {
            null
        } catch (_: ClassCastException) {
            null
        } catch (_: java.net.URISyntaxException) {
            null
        }
    }
}
