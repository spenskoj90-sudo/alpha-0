package com.alpha0.app.game

import org.junit.Assert.assertEquals
import org.junit.Test

class ObserverJourneyTest {
    private fun step(installed: Boolean = true, supported: Boolean = true,
                     status: ObservationStatus = ObservationStatus.STOPPED,
                     hasFrame: Boolean = false, consent: Boolean = false,
                     pending: Boolean = false, count: Int = 0) = observerNextStep(
        installed, supported, status, hasFrame, consent, pending, count,
    )

    @Test fun `missing game and unsupported build block capture journey`() {
        assertEquals(ObserverNextStep.INSTALL_GAME, step(installed = false, consent = true))
        assertEquals(ObserverNextStep.DIAGNOSTIC_BUILD, step(supported = false, consent = true))
    }

    @Test fun `stopped capture requires renewed consent and system chooser`() {
        assertEquals(ObserverNextStep.CONSENT, step())
        assertEquals(ObserverNextStep.CHOOSE_SOURCE, step(consent = true))
        assertEquals(ObserverNextStep.WAIT_FOR_PERMISSION, step(consent = true, pending = true))
    }

    @Test fun `only completed current frame offers numeric sample`() {
        assertEquals(ObserverNextStep.WAIT_FOR_SOURCE, step(status = ObservationStatus.WAITING))
        assertEquals(ObserverNextStep.SOURCE_HIDDEN, step(status = ObservationStatus.PAUSED, hasFrame = true))
        assertEquals(ObserverNextStep.WAIT_FOR_RECOGNITION, step(status = ObservationStatus.OBSERVING))
        assertEquals(ObserverNextStep.SAVE_COMPARISON, step(status = ObservationStatus.OBSERVING, hasFrame = true))
        assertEquals(ObserverNextStep.REVIEW_CALIBRATION, step(status = ObservationStatus.OBSERVING, hasFrame = true, count = 32))
    }

    @Test fun `failed observation never advertises sample or action`() {
        assertEquals(ObserverNextStep.CONSENT, step(status = ObservationStatus.FAILED, hasFrame = true))
        assertEquals(ObserverNextStep.CONSENT, step(status = ObservationStatus.STOPPED, hasFrame = true))
    }
}
