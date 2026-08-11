package com.alpha0.app.security

import java.security.MessageDigest
import java.util.concurrent.ConcurrentHashMap

class ReplayProtection(private val maxClockSkewSeconds: Long = 120L) {
    private val consumed = ConcurrentHashMap<String, Long>()

    fun accept(challenge: String, timestampSeconds: Long, nowSeconds: Long): Boolean {
        if (challenge.isBlank()) return false
        if (kotlin.math.abs(nowSeconds - timestampSeconds) > maxClockSkewSeconds) return false
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(challenge.toByteArray())
            .joinToString("") { "%02x".format(it) }
        return consumed.putIfAbsent(digest, timestampSeconds) == null
    }

    fun clearExpired(nowSeconds: Long) {
        consumed.entries.removeIf { (_, timestamp) -> nowSeconds - timestamp > maxClockSkewSeconds * 2 }
    }
}
