package com.alpha0.app.auth

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/** Keystore and one-shot SharedPreferences behavior; not real provider login. */
@RunWith(AndroidJUnit4::class)
class FederatedAuthStateStoreInstrumentedTest {
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private val first = FederatedAuthStateStore()
    private val second = FederatedAuthStateStore()
    private val state = "s".repeat(43)
    private val verifier = "v".repeat(64)

    @Before fun startClean() = first.clear(context)
    @After fun cleanUp() = first.clear(context)

    @Test fun unsolicitedDeepLinkCannotCancelLegitimatePendingLogin() {
        first.save(context, FederatedAuthStateStore.Pending(
            "vk", "login", state, verifier, System.currentTimeMillis(),
        ))
        assertTrue(first.consumeMatching(context, "vk", "login", "x".repeat(43)) is
            FederatedAuthStateStore.ConsumeResult.StateMismatch)
        assertTrue(first.consumeMatching(context, "telegram", "login", state) is
            FederatedAuthStateStore.ConsumeResult.ProviderMismatch)
        assertTrue(first.consumeMatching(context, "vk", "link", state) is
            FederatedAuthStateStore.ConsumeResult.OperationMismatch)
        val accepted = second.consumeMatching(context, "vk", "login", state)
        assertTrue(accepted is FederatedAuthStateStore.ConsumeResult.Matched)
        assertEquals(verifier, (accepted as FederatedAuthStateStore.ConsumeResult.Matched).pending.codeVerifier)
        assertTrue(first.consumeMatching(context, "vk", "login", state) is
            FederatedAuthStateStore.ConsumeResult.Expired)
    }

    @Test fun replacingBrowserFlowRejectsOldStateWithoutConsumingNewState() {
        first.save(context, FederatedAuthStateStore.Pending(
            "vk", "login", state, verifier, System.currentTimeMillis(),
        ))
        second.save(context, FederatedAuthStateStore.Pending(
            "telegram", "login", "t".repeat(43), verifier, System.currentTimeMillis(),
        ))
        assertTrue(first.consumeMatching(context, "vk", "login", state) is
            FederatedAuthStateStore.ConsumeResult.ProviderMismatch)
        assertTrue(second.consumeMatching(context, "telegram", "login", "t".repeat(43)) is
            FederatedAuthStateStore.ConsumeResult.Matched)
        assertTrue(first.consumeMatching(context, "telegram", "login", "t".repeat(43)) is
            FederatedAuthStateStore.ConsumeResult.Expired)
    }

    @Test fun expiredEncryptedEntryCannotBeConsumed() {
        first.save(context, FederatedAuthStateStore.Pending(
            "vk", "login", state, verifier, System.currentTimeMillis() - 700_000L,
        ))
        assertTrue(first.consumeMatching(context, "vk", "login", state) is
            FederatedAuthStateStore.ConsumeResult.Expired)
        first.save(context, FederatedAuthStateStore.Pending(
            "vk", "login", state, verifier, System.currentTimeMillis(),
        ))
        assertTrue(second.consumeMatching(context, "vk", "login", state) is
            FederatedAuthStateStore.ConsumeResult.Matched)
    }
}
