package com.alpha0.app.security

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class KeystoreIoTest {
    @Test fun `blocking keystore operation is dispatched away from caller thread`() = runBlocking {
        val callerThread = Thread.currentThread().id
        val operationThread = keystoreIo { Thread.currentThread().id }
        assertNotEquals(callerThread, operationThread)
    }

    @Test fun `return value is propagated unchanged`() = runBlocking {
        assertEquals("session-ready", keystoreIo { "session-ready" })
    }
}
