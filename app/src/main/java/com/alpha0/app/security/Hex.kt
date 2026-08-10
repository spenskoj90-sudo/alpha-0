package com.alpha0.app.security

internal object Hex {
    private val HEX_CHARS = "0123456789abcdef".toCharArray()

    fun encode(bytes: ByteArray): String {
        val result = CharArray(bytes.size * 2)

        bytes.forEachIndexed { index, byte ->
            val value = byte.toInt() and 0xff
            result[index * 2] = HEX_CHARS[value ushr 4]
            result[index * 2 + 1] = HEX_CHARS[value and 0x0f]
        }

        return String(result)
    }
}
