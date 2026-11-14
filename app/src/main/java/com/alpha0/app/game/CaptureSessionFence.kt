package com.alpha0.app.game

/** Exact user session bound to one explicit MediaProjection chooser request.
 * Token refresh preserves the epoch; logout/login and session replacement advance it.
 * This does not establish the identity of the captured game/window. */
internal data class CaptureSessionBinding(val deviceId: String, val epoch: Long)

internal object CaptureSessionFence {
    fun snapshot(deviceId: String?, epoch: Long?): CaptureSessionBinding? =
        if (deviceId.isNullOrBlank() || epoch == null || epoch < 0L) null
        else CaptureSessionBinding(deviceId, epoch)

    fun isCurrent(expected: CaptureSessionBinding?, actualDeviceId: String?, actualEpoch: Long?): Boolean =
        expected != null && expected.deviceId == actualDeviceId && expected.epoch == actualEpoch
}
