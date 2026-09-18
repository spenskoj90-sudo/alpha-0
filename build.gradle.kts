buildscript {
    dependencies {
        // AGP 9 built-in Kotlin defaults to KGP 2.2.10. SENTINEL pins the
        // highest KGP version fully supported by the selected AGP/Gradle pair.
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.4.20")
    }
}

plugins {
    id("com.android.application") version "9.3.1" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.4.20" apply false
}
