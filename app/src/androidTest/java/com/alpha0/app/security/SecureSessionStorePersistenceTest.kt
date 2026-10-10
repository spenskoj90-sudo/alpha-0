package com.alpha0.app.security

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SecureSessionStorePersistenceTest {
    private val context = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun lateRefreshCannotRestoreClearedSessionOrReplaceNewLogin() {
        val first = SecureSessionStore(); val second = SecureSessionStore()
        first.clear(context); first.save(context, "old-access", "old-refresh", "device-old")
        val old = first.load(context)!!
        second.clear(context)
        assertFalse(first.replaceIfCurrent(context, old, "late-access", "late-refresh"))
        assertNull(second.load(context))
        second.save(context, "fresh-access", "fresh-refresh", "device-new")
        val fresh = second.load(context)!!
        assertFalse(first.clearIfCurrent(context, old))
        assertFalse(first.replaceIfCurrent(context, old, "late-access", "late-refresh"))
        assertEquals(fresh, second.load(context))
        assertTrue(first.replaceIfCurrent(context, fresh, "rotated-access", "rotated-refresh"))
        assertEquals(fresh.epoch, second.load(context)!!.epoch)
        assertEquals("device-new", second.load(context)!!.deviceId)
        second.clear(context)
    }

    @Test
    fun persistedSessionSurvivesStoreRecreation() {
        val firstStore = SecureSessionStore()
        firstStore.clear(context)
        firstStore.save(context, "access-token", "refresh-token", "device-123")

        val recreatedStore = SecureSessionStore()
        val session = recreatedStore.load(context)

        assertEquals("access-token", session?.accessToken)
        assertEquals("refresh-token", session?.refreshToken)
        assertEquals("device-123", session?.deviceId)

        recreatedStore.clear(context)
    }

    @Test
    fun missingSessionLoadsAsNull() {
        val store = SecureSessionStore()
        store.clear(context)

        assertNull(store.load(context))
    }

    @Test
    fun clearedSessionIsNotRestored() {
        val store = SecureSessionStore()
        store.save(context, "access-token", "refresh-token", "device-123")
        store.clear(context)

        val recreatedStore = SecureSessionStore()
        assertNull(recreatedStore.load(context))
    }
}
