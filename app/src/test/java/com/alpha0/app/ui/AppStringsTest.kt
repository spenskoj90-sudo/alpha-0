package com.alpha0.app.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class AppStringsTest {
    @Test
    fun `english and russian catalogs expose the same keys`() {
        assertEquals(ENGLISH.keys, RUSSIAN.keys)
    }

    @Test
    fun `critical product-shell translations are present`() {
        val keys = listOf(
            "settings",
            "updates",
            "help",
            "about",
            "home",
            "games",
            "security",
            "activity",
            "device_setup",
            "bind_device",
            "check_updates",
        )

        keys.forEach { key ->
            assertFalse("English translation missing: $key", ENGLISH.getValue(key).isBlank())
            assertFalse("Russian translation missing: $key", RUSSIAN.getValue(key).isBlank())
        }
    }

    @Test
    fun `observer processing summary formats without implying accuracy`() {
        val english = AppStrings(AppLanguage.ENGLISH, ENGLISH)
        val russian = AppStrings(AppLanguage.RUSSIAN, RUSSIAN)
        for (strings in listOf(english, russian)) {
            val counts = strings.text("game_capture_ocr_counters", 2, 1, 3)
            assertFalse(counts.contains("%d"))
            assertFalse(counts.isBlank())
            val maximum = strings.text("game_capture_ocr_max", 400)
            assertFalse(maximum.contains("%d"))
            assertFalse(maximum.isBlank())
            val warning = strings.text("game_capture_ocr_metrics_note")
            assertFalse(warning.isBlank())
        }
    }

    @Test
    fun `calibration labels separate frame age from OCR and human entry`() {
        for (strings in listOf(AppStrings(AppLanguage.ENGLISH, ENGLISH), AppStrings(AppLanguage.RUSSIAN, RUSSIAN))) {
            for (key in listOf("game_calibration_frame_age", "game_calibration_processing", "game_calibration_since_ocr")) {
                val label = strings.text(key, 7)
                assertFalse("$key must render a duration", label.isBlank() || label.contains("%d"))
            }
            assertFalse(strings.text("game_calibration_timing_note").isBlank())
        }
    }

    @Test
    fun `unknown key has a deterministic fallback`() {
        val strings = AppStrings(AppLanguage.RUSSIAN, RUSSIAN)
        assertEquals("unknown_key", strings.text("unknown_key"))
    }
}
