package com.alpha0.app.ui

import android.content.Context

enum class AppLanguage { SYSTEM, RUSSIAN, ENGLISH }

enum class AppThemeMode { SYSTEM, LIGHT, DARK }

class AppPreferences(context: Context) {
    private val values = context.getSharedPreferences("sentinel_ui_preferences", Context.MODE_PRIVATE)

    fun language(): AppLanguage = enumValue(values.getString(KEY_LANGUAGE), AppLanguage.SYSTEM)

    fun theme(): AppThemeMode = enumValue(values.getString(KEY_THEME), AppThemeMode.SYSTEM)

    fun setLanguage(value: AppLanguage) {
        values.edit().putString(KEY_LANGUAGE, value.name).apply()
    }

    fun setTheme(value: AppThemeMode) {
        values.edit().putString(KEY_THEME, value.name).apply()
    }

    private inline fun <reified T : Enum<T>> enumValue(raw: String?, fallback: T): T =
        enumValues<T>().firstOrNull { it.name == raw } ?: fallback

    private companion object {
        const val KEY_LANGUAGE = "language"
        const val KEY_THEME = "theme"
    }
}
