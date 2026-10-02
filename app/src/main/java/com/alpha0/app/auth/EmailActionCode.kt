package com.alpha0.app.auth

fun normalizeEmailActionCode(value: String): String {
    val compact = value.filterNot { it.isWhitespace() }
    return if (Regex("[0-9]{8}").matches(compact)) compact else value.trim()
}

fun validEmailActionCode(value: String): Boolean {
    val normalized = normalizeEmailActionCode(value)
    return Regex("[0-9]{8}|[A-Za-z0-9_-]{32,512}").matches(normalized)
}
