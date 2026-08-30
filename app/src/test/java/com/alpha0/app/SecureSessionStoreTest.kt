package com.alpha0.app

import com.alpha0.app.security.SecureSessionStore
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class SecureSessionStoreTest {
    @Test
    fun persistedSessionIsRestoredAfterStoreRecreation() {
        val preferences = InMemoryPreferences()
        val firstStore = SecureSessionStore(preferences)

        firstStore.saveSession("access-token", "refresh-token")

        val recreatedStore = SecureSessionStore(preferences)
        val session = recreatedStore.loadSession()

        assertEquals("access-token", session?.accessToken)
        assertEquals("refresh-token", session?.refreshToken)
    }

    @Test
    fun missingSessionLoadsAsNull() {
        val store = SecureSessionStore(InMemoryPreferences())

        assertNull(store.loadSession())
    }

    @Test
    fun clearedSessionIsNotRestored() {
        val preferences = InMemoryPreferences()
        val store = SecureSessionStore(preferences)

        store.saveSession("access-token", "refresh-token")
        store.clearSession()

        val recreatedStore = SecureSessionStore(preferences)
        assertNull(recreatedStore.loadSession())
    }
}
