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
        versionName = rootProject.file("VERSION").readText().trim()
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "SENTINEL_API_BASE_URL", "\"${providers.environmentVariable("SENTINEL_API_BASE_URL").orElse("http://127.0.0.1:8000").get().trimEnd('/')}\"")

        val sentryDsn = providers.environmentVariable("SENTRY_DSN").orElse("").get()
        val sourceSha = providers.environmentVariable("SENTINEL_SOURCE_SHA")
            .orElse(providers.environmentVariable("GITHUB_SHA"))
            .orElse("")
            .get()
            .trim()
        val githubActions = providers.environmentVariable("GITHUB_ACTIONS").orElse("").get() == "true"
        val runtimeEnvironment = providers.environmentVariable("SENTINEL_RUNTIME_ENVIRONMENT")
            .orElse(if (sentryDsn.isNotEmpty() && githubActions) "release-candidate" else "")
            .get()
            .trim()
        if (sourceSha.isNotEmpty() && !Regex("[0-9a-f]{40}").matches(sourceSha)) {
            error("SENTINEL_SOURCE_SHA/GITHUB_SHA must be empty or a 40-character lowercase commit SHA")
        }
        val allowedRuntimeEnvironments = setOf("development", "ci", "release-candidate", "production")
        if (runtimeEnvironment.isNotEmpty() && runtimeEnvironment !in allowedRuntimeEnvironments) {
            error("SENTINEL_RUNTIME_ENVIRONMENT must be empty or an allowlisted environment")
        }
        buildConfigField("String", "SENTRY_DSN", "\"$sentryDsn\"")
        buildConfigField("String", "SENTINEL_SOURCE_SHA", "\"$sourceSha\"")
        buildConfigField("String", "SENTINEL_RUNTIME_ENVIRONMENT", "\"$runtimeEnvironment\"")
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    signingConfigs {
        create("ciRelease")
    }

    buildTypes {
        debug {
            buildConfigField("String", "SENTINEL_DIAGNOSTICS_MODE", "\"DEVELOPMENT\"")
            buildConfigField("int", "SENTINEL_DIAGNOSTICS_MAX_BYTES", "2097152")
            buildConfigField("boolean", "SENTINEL_DIAGNOSTICS_EXPORT_ENABLED", "true")
        }
        create("physicalTest") {
            initWith(getByName("debug"))
            applicationIdSuffix = ".physicaltest"
            versionNameSuffix = "-physical-test"
            matchingFallbacks += listOf("debug")
            isDebuggable = true
            isMinifyEnabled = false
            buildConfigField("String", "SENTINEL_DIAGNOSTICS_MODE", "\"FORENSIC_TEST\"")
            buildConfigField("int", "SENTINEL_DIAGNOSTICS_MAX_BYTES", "16777216")
            buildConfigField("boolean", "SENTINEL_DIAGNOSTICS_EXPORT_ENABLED", "true")
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("ciRelease")
            buildConfigField("String", "SENTINEL_DIAGNOSTICS_MODE", "\"PRODUCTION\"")
            buildConfigField("int", "SENTINEL_DIAGNOSTICS_MAX_BYTES", "524288")
            buildConfigField("boolean", "SENTINEL_DIAGNOSTICS_EXPORT_ENABLED", "false")
        }
    }

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
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.navigation:navigation-compose:2.8.9")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.ui:ui-text-google-fonts")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.material3:material3")
    implementation("com.google.android.play:integrity:1.4.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("io.sentry:sentry-android:8.54.0")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20250517")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}
