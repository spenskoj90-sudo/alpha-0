package com.alpha0.app.game

import android.app.Activity
import android.app.KeyguardManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.alpha0.app.MainActivity
import com.alpha0.app.BuildConfig
import com.alpha0.app.R
import com.alpha0.app.diagnostics.DiagnosticLogger
import com.alpha0.app.security.SecureSessionStore
import com.alpha0.app.ui.AppLanguage
import com.alpha0.app.ui.AppPreferences
import com.alpha0.app.ui.AppStrings
import com.alpha0.app.ui.ENGLISH
import com.alpha0.app.ui.RUSSIAN
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.TextRecognizer
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import java.nio.ByteBuffer
import java.util.UUID

/** Explicit, five-minute, read-only capture. Never restarts or reuses a projection token. */
class GameObservationService : Service() {
    private val handler = Handler(Looper.getMainLooper())
    private var projection: MediaProjection? = null
    private var display: VirtualDisplay? = null
    private var reader: ImageReader? = null
    private var recognizer: TextRecognizer? = null
    private var sessionId: String? = null
    private var deviceId: String? = null
    private var stopping = false
    private var receiverRegistered = false
    private var recognitionBusy = false
    private var lastProcessedAt = -2000L
    private var lastSessionCheckAt = 0L

    private val screenOff = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) = finish("SCREEN_LOCKED")
    }

    private val callback = object : MediaProjection.Callback() {
        override fun onStop() = finish("CAPTURE_REVOKED")

        override fun onCapturedContentVisibilityChanged(isVisible: Boolean) {
            val id = sessionId ?: return
            GameObservationRuntime.session.visibility(id, isVisible, now())
            GameObservationRuntime.publish()
        }

        override fun onCapturedContentResize(width: Int, height: Int) {
            if (stopping) return
            sessionId?.let { GameObservationRuntime.session.invalidate(it); GameObservationRuntime.publish() }
            val size = CaptureSize.fit(width, height) ?: return finish("INVALID_CAPTURE_SIZE")
            try {
                // Android 14 permits one virtual display per consent; resize that same display.
                val current = display ?: return
                current.surface = null
                reader?.close()
                reader = imageReader(size)
                current.resize(size.width, size.height, resources.displayMetrics.densityDpi)
                current.surface = reader!!.surface
            } catch (_: Exception) {
                finish("CAPTURE_RESIZE_FAILED")
            }
        }
    }

    private val heartbeat = object : Runnable {
        override fun run() {
            if (stopping || sessionId == null) return
            val elapsed = now()
            if (!GameObservationRuntime.session.tick(elapsed)) return finish(GameObservationRuntime.session.snapshot.reason)
            if (getSystemService(KeyguardManager::class.java)?.isKeyguardLocked != false) return finish("SCREEN_LOCKED")
            if (elapsed - lastSessionCheckAt >= 30000) {
                lastSessionCheckAt = elapsed
                val current = SecureSessionStore().load(this@GameObservationService)
                if (current?.deviceId != deviceId || current == null) return finish("SESSION_CLOSED")
                if (ShatteredGameProfile.installed(this@GameObservationService) != GameObservationRuntime.state.value.installed) {
                    return finish("GAME_CHANGED")
                }
            }
            GameObservationRuntime.publish()
            handler.postDelayed(this, 1000)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == STOP) {
            finish("USER_STOP")
            return START_NOT_STICKY
        }
        if (sessionId != null || stopping) return START_NOT_STICKY
        if (!BuildConfig.DEBUG || Build.VERSION.SDK_INT < 34) {
            finish("ANDROID_14_REQUIRED")
            return START_NOT_STICKY
        }
        try {
            val consent = intent?.getParcelableExtra(CONSENT, Intent::class.java)
            val current = SecureSessionStore().load(this)
            val install = ShatteredGameProfile.installed(this)
            if (consent == null || current?.deviceId.isNullOrBlank() || install == null ||
                intent?.getLongExtra(VERSION, -1) != install.versionCode) {
                finish("SESSION_OR_GAME_UNAVAILABLE")
                return START_NOT_STICKY
            }
            val strings = notificationStrings()
            val manager = getSystemService(NotificationManager::class.java) ?: throw IllegalStateException("Notification service unavailable")
            manager.createNotificationChannel(NotificationChannel(CHANNEL, strings.text("game_observer_title"), NotificationManager.IMPORTANCE_LOW))
            val stop = PendingIntent.getService(this, 1, Intent(this, javaClass).setAction(STOP), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val open = PendingIntent.getActivity(this, 2, Intent(this, MainActivity::class.java), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val notification = NotificationCompat.Builder(this, CHANNEL)
                .setSmallIcon(R.drawable.ic_sentinel_notification)
                .setContentTitle(strings.text("game_observer_title"))
                .setContentText(strings.text("game_capture_notification"))
                .setContentIntent(open)
                .setOngoing(true)
                .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
                .addAction(0, strings.text("game_capture_stop"), stop)
                .build()
            startForeground(7401, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
            deviceId = current!!.deviceId
            val id = UUID.randomUUID().toString()
            sessionId = id
            GameObservationRuntime.begin(install, id, now())
            ContextCompat.registerReceiver(this, screenOff, IntentFilter(Intent.ACTION_SCREEN_OFF), ContextCompat.RECEIVER_NOT_EXPORTED)
            receiverRegistered = true
            recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
            projection = getSystemService(MediaProjectionManager::class.java)?.getMediaProjection(Activity.RESULT_OK, consent)
                ?: throw IllegalStateException("Projection unavailable")
            projection!!.registerCallback(callback, handler)
            val metrics = resources.displayMetrics
            val size = CaptureSize.fit(metrics.widthPixels, metrics.heightPixels) ?: throw IllegalStateException("Invalid size")
            reader = imageReader(size)
            display = projection!!.createVirtualDisplay(
                "SENTINEL local observer", size.width, size.height, metrics.densityDpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR, reader!!.surface, null, handler,
            )
            handler.post(heartbeat)
            DiagnosticLogger.get(this).info("GAME", "OBSERVATION_STARTED", "OBSERVED", details = mapOf(
                "adapter_id" to ShatteredGameProfile.ADAPTER_ID,
                "game_version" to install.versionName,
                "game_version_code" to install.versionCode,
                "capability_status" to "UNVERIFIED",
            ))
        } catch (_: Exception) {
            finish("CAPTURE_START_FAILED")
        }
        return START_NOT_STICKY
    }

    private fun imageReader(size: CaptureSize): ImageReader = ImageReader.newInstance(size.width, size.height, PixelFormat.RGBA_8888, 2).apply {
        setOnImageAvailableListener({ source ->
            // Always drain latest images, including while recognition is busy or content hidden.
            val image = try { source.acquireLatestImage() } catch (_: IllegalStateException) { null }
            image?.use { frame ->
                val id = sessionId ?: return@use
                val capturedAt = now()
                if (stopping || recognitionBusy || capturedAt - lastProcessedAt < 2000) return@use
                if (!GameObservationRuntime.session.frame(id, capturedAt)) return@use
                lastProcessedAt = capturedAt
                val sequence = GameObservationRuntime.session.snapshot.frames
                GameObservationRuntime.publish()
                try {
                    val crop = hudBitmap(frame)
                    val input = try { Bitmap.createScaledBitmap(crop, crop.width * 2, crop.height * 2, false) }
                        finally { crop.recycle() }
                    recognitionBusy = true
                    val width = frame.width
                    val height = frame.height
                    val task = try { recognizer!!.process(InputImage.fromBitmap(input, 0)) }
                        catch (error: Exception) { input.recycle(); recognitionBusy = false; throw error }
                    task.addOnCompleteListener { result ->
                        try {
                            if (!stopping && result.isSuccessful) {
                                val lines = result.result.textBlocks.flatMap { it.lines }.take(65).mapNotNull { line ->
                                    line.boundingBox?.let { box ->
                                        ScreenTextLine(line.text.take(65), (width * .04f).toInt().toFloat() / width + box.left / (2f * width),
                                            box.top / (2f * height), (width * .04f).toInt().toFloat() / width + box.right / (2f * width), box.bottom / (2f * height))
                                    }
                                }
                                GameObservationRuntime.session.recognized(id, sequence, capturedAt, now(), ShatteredHealthReader.read(lines))
                                GameObservationRuntime.publish()
                            } else if (!stopping) {
                                finish("RECOGNITION_UNAVAILABLE")
                            }
                        } catch (_: Exception) {
                            finish("RECOGNITION_UNAVAILABLE")
                        } finally {
                            input.recycle()
                            recognitionBusy = false
                        }
                    }
                } catch (_: Exception) {
                    finish("RECOGNITION_UNAVAILABLE")
                }
            }
        }, handler)
    }

    /** Copies only the small HUD region; respects pixel/row stride without copying padded pixels. */
    private fun hudBitmap(image: Image): Bitmap {
        require(image.width in 1..1280 && image.height in 1..1280)
        val plane = image.planes.first()
        require(plane.pixelStride == 4)
        val x = (image.width * .04f).toInt()
        val width = maxOf(1, (image.width * .46f).toInt())
        val height = maxOf(1, (image.height * .12f).toInt())
        val input = plane.buffer.duplicate()
        val start = input.position()
        require(plane.rowStride >= image.width * 4)
        require(start.toLong() + (height - 1L) * plane.rowStride + (x + width) * 4L <= input.limit())
        val pixels = ByteArray(width * height * 4)
        repeat(height) { row ->
            input.position(start + row * plane.rowStride + x * 4)
            input.get(pixels, row * width * 4, width * 4)
        }
        return Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888).apply { copyPixelsFromBuffer(ByteBuffer.wrap(pixels)) }
    }

    private fun finish(reason: String) {
        if (stopping) return
        stopping = true
        if (reason != "SERVICE_DESTROYED" || GameObservationRuntime.session.snapshot.status != ObservationStatus.STOPPED) {
            GameObservationRuntime.stop(reason)
        }
        handler.removeCallbacksAndMessages(null)
        if (receiverRegistered) {
            unregisterReceiver(screenOff)
            receiverRegistered = false
        }
        runCatching { display?.release() }; display = null
        runCatching { reader?.close() }; reader = null
        runCatching { projection?.unregisterCallback(callback) }
        runCatching { projection?.stop() }; projection = null
        runCatching { recognizer?.close() }; recognizer = null
        if (sessionId != null) DiagnosticLogger.get(this).info("GAME", "OBSERVATION_STOPPED", "OBSERVED", details = mapOf(
            "reason" to reason, "processed_frames" to GameObservationRuntime.session.snapshot.frames,
        ))
        sessionId = null
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onTaskRemoved(rootIntent: Intent?) = finish("TASK_REMOVED")
    override fun onDestroy() { finish("SERVICE_DESTROYED"); super.onDestroy() }
    private fun now() = SystemClock.elapsedRealtime()

    private fun notificationStrings(): AppStrings {
        val choice = AppPreferences(this).language()
        val russian = choice == AppLanguage.RUSSIAN || (choice == AppLanguage.SYSTEM && resources.configuration.locales[0].language == "ru")
        return AppStrings(if (russian) AppLanguage.RUSSIAN else AppLanguage.ENGLISH, if (russian) RUSSIAN else ENGLISH)
    }

    companion object {
        private const val CHANNEL = "sentinel-game-observation"
        private const val CONSENT = "projection-consent"
        private const val VERSION = "game-version"
        private const val STOP = "com.alpha0.app.game.STOP_OBSERVATION"
        fun start(context: Context, consent: Intent, install: StockGameInstall) {
            try {
                ContextCompat.startForegroundService(context, Intent(context, GameObservationService::class.java)
                    .putExtra(CONSENT, consent).putExtra(VERSION, install.versionCode))
            } catch (_: Exception) {
                GameObservationRuntime.stop("CAPTURE_START_FAILED")
            }
        }
        fun stop(context: Context, reason: String = "USER_STOP") {
            GameObservationRuntime.stop(reason)
            context.stopService(Intent(context, GameObservationService::class.java))
        }
    }
}
