package com.alpha0.app.auth

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.alpha0.app.security.SecureSessionStore
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.util.Collections
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

@RunWith(AndroidJUnit4::class)
class SessionManagerInstrumentedTest {
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private val store = SecureSessionStore()

    @Before
    fun clearSession() {
        store.clear(context)
    }

    @Test
    fun successfulRefreshReplacesTokensAndPreservesDeviceId() {
        store.save(context, "old-access", "old-refresh", "device-123")
        val client = FakeRefreshClient(
            AuthApi.Result.Success(AuthApi.Session("new-access", "new-refresh", listOf("account:read")))
        )
        val manager = SessionManager(client, store)

        val result = manager.refreshStoredSession(context)

        assertTrue(result is AuthApi.Result.Success)
        assertEquals("old-refresh", client.seenRefreshTokens.single())
        val session = store.load(context)
        assertEquals("new-access", session?.accessToken)
        assertEquals("new-refresh", session?.refreshToken)
        assertEquals("device-123", session?.deviceId)
    }

    @Test
    fun invalidRefreshClearsSession() {
        store.save(context, "old-access", "old-refresh")
        val client = FakeRefreshClient(AuthApi.Result.Failure("INVALID_REFRESH"))
        val manager = SessionManager(client, store)

        val result = manager.refreshStoredSession(context)

        assertEquals("INVALID_REFRESH", (result as AuthApi.Result.Failure).message)
        assertNull(store.load(context))
    }

    @Test
    fun concurrentRefreshesAreSerializedAndEachUsesLatestStoredRefreshToken() {
        store.save(context, "access-0", "refresh-0")
        val client = RecordingRefreshClient()
        val manager = SessionManager(client, store)
        val executor = Executors.newFixedThreadPool(2)
        val start = CountDownLatch(1)
        val done = CountDownLatch(2)

        repeat(2) {
            executor.execute {
                try {
                    start.await()
                    manager.refreshStoredSession(context)
                } finally {
                    done.countDown()
                }
            }
        }
        start.countDown()

        assertTrue(done.await(5, TimeUnit.SECONDS))
        executor.shutdownNow()
        assertEquals(listOf("refresh-0", "refresh-1"), client.seenRefreshTokens.toList())
        val session = store.load(context)
        assertEquals("access-2", session?.accessToken)
        assertEquals("refresh-2", session?.refreshToken)
    }

    private class FakeRefreshClient(private val result: AuthApi.Result) : RefreshClient {
        val seenRefreshTokens = mutableListOf<String>()

        override fun refresh(refreshToken: String): AuthApi.Result {
            seenRefreshTokens += refreshToken
            return result
        }
    }

    private class RecordingRefreshClient : RefreshClient {
        val seenRefreshTokens = Collections.synchronizedList(mutableListOf<String>())

        override fun refresh(refreshToken: String): AuthApi.Result {
            seenRefreshTokens += refreshToken
            val next = seenRefreshTokens.size
            return AuthApi.Result.Success(AuthApi.Session("access-$next", "refresh-$next", emptyList()))
        }
    }
}
