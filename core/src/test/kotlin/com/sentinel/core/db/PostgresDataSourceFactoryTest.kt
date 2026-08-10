package com.sentinel.core.db

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class PostgresDataSourceFactoryTest {
    @Test
    fun missingCredentialsFailClosed() {
        assertThrows(IllegalStateException::class.java) {
            PostgresDataSourceFactory.fromEnvironment(mapOf("SENTINEL_DB_URL" to "jdbc:postgresql://db/sentinel"))
        }
    }

    @Test
    fun nonPostgresUrlIsRejected() {
        assertThrows(IllegalArgumentException::class.java) {
            PostgresDataSourceFactory.fromEnvironment(
                mapOf(
                    "SENTINEL_DB_URL" to "jdbc:h2:mem:test",
                    "SENTINEL_DB_USER" to "sentinel",
                    "SENTINEL_DB_PASSWORD" to "secret"
                )
            )
        }
    }
}
