package com.alpha0.app.game

import com.alpha0.app.ui.SentinelStatus

/** The knowledge consumer has distinct access, lifecycle and loading states.
 * Unknown future states remain unavailable, never implicitly pending or ready.
 * Badges reuse the installed production Design System v3 semantics.
 */
internal fun knowledgeUiStatus(state: String): SentinelStatus = when (state) {
    "READY" -> SentinelStatus.ACTIVE
    "DENIED" -> SentinelStatus.DENIED
    "STOPPED" -> SentinelStatus.STOPPED
    "WAITING_FOR_VERIFIED_PROFILE", "LOADING" -> SentinelStatus.PENDING
    else -> SentinelStatus.UNAVAILABLE
}
