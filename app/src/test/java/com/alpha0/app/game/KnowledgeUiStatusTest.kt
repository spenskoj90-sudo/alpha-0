package com.alpha0.app.game

import com.alpha0.app.ui.SentinelStatus
import org.junit.Assert.assertEquals
import org.junit.Test

class KnowledgeUiStatusTest {
    @Test fun `loading and unverified target are visibly pending`() {
        assertEquals(SentinelStatus.PENDING, knowledgeUiStatus("LOADING"))
        assertEquals(SentinelStatus.PENDING, knowledgeUiStatus("WAITING_FOR_VERIFIED_PROFILE"))
    }

    @Test fun `verified knowledge is available but access denial is not pending`() {
        assertEquals(SentinelStatus.ACTIVE, knowledgeUiStatus("READY"))
        assertEquals(SentinelStatus.DENIED, knowledgeUiStatus("DENIED"))
    }

    @Test fun `stopped unavailable and unexpected states never masquerade as loading or ready`() {
        assertEquals(SentinelStatus.STOPPED, knowledgeUiStatus("STOPPED"))
        assertEquals(SentinelStatus.UNAVAILABLE, knowledgeUiStatus("UNAVAILABLE"))
        assertEquals(SentinelStatus.UNAVAILABLE, knowledgeUiStatus("ERROR"))
        assertEquals(SentinelStatus.UNAVAILABLE, knowledgeUiStatus(""))
        assertEquals(SentinelStatus.UNAVAILABLE, knowledgeUiStatus("ready"))
    }
}
