package com.sentinel.core.db

import org.postgresql.ds.PGSimpleDataSource
import javax.sql.DataSource

/**
 * Builds a PostgreSQL datasource from environment variables without embedding
 * credentials in source. TLS and channel binding are mandatory by default.
 */
object PostgresDataSourceFactory {
    fun fromEnvironment(env: Map<String, String> = System.getenv()): DataSource {
        val url = required(env, "SENTINEL_DB_URL")
        val user = required(env, "SENTINEL_DB_USER")
        val password = required(env, "SENTINEL_DB_PASSWORD")
        require(url.startsWith("jdbc:postgresql://")) { "SENTINEL_DB_URL must be a PostgreSQL JDBC URL" }
        require(!url.contains("sslmode=", ignoreCase = true)) { "SENTINEL_DB_URL must not override sslmode" }
        require(!url.contains("channelBinding=", ignoreCase = true)) { "SENTINEL_DB_URL must not override channelBinding" }

        return PGSimpleDataSource().apply {
            setUrl(withSecurityParameters(url))
            setUser(user)
            setPassword(password)
            applicationName = "sentinel-core"
            connectTimeout = CONNECT_TIMEOUT_SECONDS
            socketTimeout = SOCKET_TIMEOUT_SECONDS
        }
    }

    private fun withSecurityParameters(url: String): String {
        val separator = if ('?' in url) '&' else '?'
        return buildString {
            append(url)
            append(separator)
            append("sslmode=require&channelBinding=require")
        }
    }

    private fun required(env: Map<String, String>, name: String): String =
        env[name]?.takeIf { it.isNotBlank() } ?: error("Missing required environment variable: $name")

    private const val CONNECT_TIMEOUT_SECONDS = 10
    private const val SOCKET_TIMEOUT_SECONDS = 15
}
