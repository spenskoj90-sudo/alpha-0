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
        assertEquals(ObserverNextStep.SAVE_COMPARISON, step(status = ObservationStatus.PAUSED, hasFrame = true))
        assertEquals(ObserverNextStep.WAIT_FOR_RECOGNITION, step(status = ObservationStatus.OBSERVING))
        assertEquals(ObserverNextStep.SAVE_COMPARISON, step(status = ObservationStatus.OBSERVING, hasFrame = true))
        assertEquals(ObserverNextStep.REVIEW_CALIBRATION, step(status = ObservationStatus.OBSERVING, hasFrame = true, count = 32))
    }

    @Test fun `unverified recent numeric OCR becomes history without a new frame`() {
        val health = HealthCandidate(12, 20, 0)
        val observation = ObservationSnapshot(
            status = ObservationStatus.OBSERVING,
            captureId = "capture-a", frames = 1,
            lastFrameAt = 110L, health = health,
            lastHealth = HealthObservation(health, 110L),
            lastRecognizedFrameAt = 110L,
        )
        assertEquals(HudEvidenceState.RECENT_UNVERIFIED, hudEvidenceState(observation, 110L))
        assertEquals(HudEvidenceState.RECENT_UNVERIFIED, hudEvidenceState(observation, 5110L))
        assertEquals(HudEvidenceState.HISTORICAL, hudEvidenceState(observation, 5111L))
        assertEquals(HudEvidenceState.HISTORICAL, hudEvidenceState(observation.copy(health = null), 111L))
        assertEquals(HudEvidenceState.HISTORICAL, hudEvidenceState(observation.copy(status = ObservationStatus.PAUSED, health = null), 111L))
    }

    @Test fun `stopped, unknown and invalid timeline never show a health hypothesis`() {
        val health = HealthCandidate(12, 20, 0)
        val snapshot = ObservationSnapshot(
            status = ObservationStatus.OBSERVING, captureId = "capture-a",
            frames = 1, lastFrameAt = 110L, health = health,
            lastHealth = HealthObservation(health, 110L), lastRecognizedFrameAt = 110L,
        )
        assertEquals(HudEvidenceState.UNKNOWN, hudEvidenceState(snapshot.copy(status = ObservationStatus.STOPPED), 120L))
        assertEquals(HudEvidenceState.UNKNOWN, hudEvidenceState(snapshot.copy(status = ObservationStatus.FAILED), 120L))
        assertEquals(HudEvidenceState.UNKNOWN, hudEvidenceState(snapshot.copy(status = ObservationStatus.WAITING), 120L))
        assertEquals(HudEvidenceState.UNKNOWN, hudEvidenceState(snapshot.copy(captureId = null), 120L))
        assertEquals(HudEvidenceState.UNKNOWN, hudEvidenceState(snapshot.copy(lastHealth = null), 120L))
        assertEquals(HudEvidenceState.UNKNOWN, hudEvidenceState(snapshot, 109L))
        assertEquals(HudEvidenceState.UNKNOWN, hudEvidenceState(snapshot, -1L))
    }

    @Test fun `failed observation never advertises sample or action`() {
        assertEquals(ObserverNextStep.CONSENT, step(status = ObservationStatus.FAILED, hasFrame = true))
        assertEquals(ObserverNextStep.CONSENT, step(status = ObservationStatus.STOPPED, hasFrame = true))
    }
}
