package com.alpha0.app.game

import org.junit.Assert.assertEquals
import org.junit.Test

class ObservationStopReasonTest {
    @Test fun `explicit Stop reason is preserved when service is destroyed afterward`() {
        assertEquals("USER_STOP", observationStopReasonOnDestroy(
            ObservationSnapshot(status = ObservationStatus.STOPPED, reason = "USER_STOP"),
        ))
        assertEquals("SESSION_CLOSED", observationStopReasonOnDestroy(
            ObservationSnapshot(status = ObservationStatus.STOPPED, reason = "SESSION_CLOSED"),
        ))
        assertEquals("TIME_LIMIT", observationStopReasonOnDestroy(
            ObservationSnapshot(status = ObservationStatus.STOPPED, reason = "TIME_LIMIT"),
        ))
    }

    @Test fun `unexpected destruction remains distinct from user Stop`() {
        for (status in listOf(ObservationStatus.WAITING, ObservationStatus.OBSERVING, ObservationStatus.PAUSED)) {
            assertEquals("SERVICE_DESTROYED", observationStopReasonOnDestroy(
                ObservationSnapshot(status = status, reason = "SOURCE_VISIBLE"),
            ))
        }
        assertEquals("SERVICE_DESTROYED", observationStopReasonOnDestroy(
            ObservationSnapshot(status = ObservationStatus.STOPPED, reason = ""),
        ))
    }
}
