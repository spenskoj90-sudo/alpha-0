plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.alpha0.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.alpha0.app"
        minSdk = 29
        targetSdk = 35
        versionCode = 10002
        versionName = "1.0.0-RC2"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "SENTINEL_API_BASE_URL", "\"${providers.environmentVariable("SENTINEL_API_BASE_URL").orElse("http://127.0.0.1:8000").get().trimEnd('/')}\"")
        // Sentry DSN: empty by default. CI release jobs inject secrets.SENTRY_DSN.
        // Never hardcode a real DSN in source or debug builds.
        val sentryDsn = providers.environmentVariable("SENTRY_DSN").orElse("")
        buildConfigField("String", "SENTRY_DSN", "\"${sentryDsn.get()}\"")
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    signingConfigs {
        create("ciRelease")
    }

    buildTypes {
        debug { }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("ciRelease")
        }
    }

    // Keep release signing secrets out of ordinary debug/unit-test configuration.
    val androidKeystorePath = providers.environmentVariable("ANDROID_KEYSTORE_PATH")
    val androidKeystorePassword = providers.environmentVariable("ANDROID_KEYSTORE_PASSWORD")
    val androidKeyAlias = providers.environmentVariable("ANDROID_KEY_ALIAS")
    val androidKeyPassword = providers.environmentVariable("ANDROID_KEY_PASSWORD")

    val releaseRequested = gradle.startParameter.taskNames.any { taskName ->
        taskName.substringAfterLast(':').contains("Release", ignoreCase = false)
    }

    if (releaseRequested) {
        val keystorePath = androidKeystorePath.orNull
            ?: error("ANDROID_KEYSTORE_PATH is required for release signing")
        val keystorePassword = androidKeystorePassword.orNull
            ?: error("ANDROID_KEYSTORE_PASSWORD is required for release signing")
        val keyAlias = androidKeyAlias.orNull
            ?: error("ANDROID_KEY_ALIAS is required for release signing")
        val keyPassword = androidKeyPassword.orNull
            ?: error("ANDROID_KEY_PASSWORD is required for release signing")

        val ciRelease = android.signingConfigs.getByName("ciRelease")
        ciRelease.storeFile = file(keystorePath)
        ciRelease.storePassword = keystorePassword
        ciRelease.keyAlias = keyAlias
        ciRelease.keyPassword = keyPassword
    }

    kotlin { jvmToolchain(17) }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2025.01.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.navigation:navigation-compose:2.8.9")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.ui:ui-text-google-fonts")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.material3:material3")
    implementation("com.google.android.play:integrity:1.4.0")
    // Sentry Android SDK — runtime crash / error reporting (issue #7).
    // Initialized only when BuildConfig.SENTRY_DSN is non-empty (release CI).
    implementation("io.sentry:sentry-android:8.54.0")
    debugImplementation("androidx.compose.ui:ui-tooling")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}
