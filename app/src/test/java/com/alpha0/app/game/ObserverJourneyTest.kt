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
            lastCompletedFrameSequence = 1L, lastCompletedFrameAt = 110L,
            lastCompletedOcrAt = 111L, lastOcrLatencyMs = 1L,
        )
        assertEquals(HudEvidenceState.RECENT_UNVERIFIED, hudEvidenceState(observation, 111L))
        assertEquals(HudEvidenceState.RECENT_UNVERIFIED, hudEvidenceState(observation, 5110L))
        assertEquals(HudEvidenceState.HISTORICAL, hudEvidenceState(observation, 5111L))
        assertEquals(HudEvidenceState.HISTORICAL, hudEvidenceState(observation.copy(health = null), 111L))
        assertEquals(HudEvidenceState.HISTORICAL, hudEvidenceState(observation.copy(status = ObservationStatus.PAUSED, health = null), 111L))
    }

    @Test fun `missing or mismatched completed OCR provenance cannot be called recent`() {
        val health = HealthCandidate(12, 20, 0)
        val base = ObservationSnapshot(
            status = ObservationStatus.OBSERVING, captureId = "capture-a",
            frames = 2, lastFrameAt = 110L, health = health,
            lastHealth = HealthObservation(health, 110L), lastRecognizedFrameAt = 110L,
            lastCompletedFrameSequence = 2L, lastCompletedFrameAt = 110L,
            lastCompletedOcrAt = 111L, lastOcrLatencyMs = 1L,
        )
        assertEquals(HudEvidenceState.RECENT_UNVERIFIED, hudEvidenceState(base, 112L))
        val incomplete = listOf(
            base.copy(lastCompletedFrameSequence = null),
            base.copy(lastCompletedFrameSequence = 1L),
            base.copy(lastCompletedFrameAt = null),
            base.copy(lastCompletedFrameAt = 109L),
            base.copy(lastCompletedOcrAt = null),
            base.copy(lastCompletedOcrAt = 109L),
            base.copy(lastCompletedOcrAt = 113L),
            base.copy(lastOcrLatencyMs = null),
            base.copy(lastOcrLatencyMs = 0L),
            base.copy(lastOcrLatencyMs = 6000L),
        )
        incomplete.forEach { snapshot ->
            assertEquals(HudEvidenceState.HISTORICAL, hudEvidenceState(snapshot, 112L))
        }
        assertEquals(HudEvidenceState.HISTORICAL, hudEvidenceState(base, 5111L))
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
