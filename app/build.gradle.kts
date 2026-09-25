import java.net.URI

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

val releaseRequested = gradle.startParameter.taskNames.any { taskName ->
    taskName.substringAfterLast(':').contains("Release", ignoreCase = false)
}
val physicalTestRequested = gradle.startParameter.taskNames.any { taskName ->
    taskName.substringAfterLast(':').contains("PhysicalTest", ignoreCase = false)
}
val explicitApiBaseUrl = providers.environmentVariable("SENTINEL_API_BASE_URL").orNull
    ?.trim()
    ?.trimEnd('/')
    ?.takeIf { it.isNotEmpty() }
val apiBaseUrl = explicitApiBaseUrl ?: "http://127.0.0.1:8000"
val sentryDsn = providers.environmentVariable("SENTRY_DSN").orElse("").get()
val sourceSha = providers.environmentVariable("SENTINEL_SOURCE_SHA")
    .orElse(providers.environmentVariable("GITHUB_SHA"))
    .orElse("")
    .get()
    .trim()
val githubActions = providers.environmentVariable("GITHUB_ACTIONS").orElse("").get() == "true"
val canonicalVersionCode = 10007
val physicalTestVersionCodeRaw = providers.environmentVariable("SENTINEL_PHYSICAL_TEST_VERSION_CODE")
    .orElse(canonicalVersionCode.toString())
    .get()
    .trim()
val physicalTestVersionCode = physicalTestVersionCodeRaw.toIntOrNull()
    ?: error("SENTINEL_PHYSICAL_TEST_VERSION_CODE must be a positive integer")
if (physicalTestVersionCode <= 0) {
    error("SENTINEL_PHYSICAL_TEST_VERSION_CODE must be a positive integer")
}
val physicalTestKeystorePath = providers.environmentVariable("SENTINEL_PHYSICAL_TEST_KEYSTORE_PATH").orNull?.trim().orEmpty()
val physicalTestKeystorePassword = providers.environmentVariable("SENTINEL_PHYSICAL_TEST_KEYSTORE_PASSWORD").orNull.orEmpty()
val physicalTestKeyAlias = providers.environmentVariable("SENTINEL_PHYSICAL_TEST_KEY_ALIAS").orNull.orEmpty()
val physicalTestKeyPassword = providers.environmentVariable("SENTINEL_PHYSICAL_TEST_KEY_PASSWORD").orNull.orEmpty()
val physicalTestSigningValues = listOf(
    physicalTestKeystorePath,
    physicalTestKeystorePassword,
    physicalTestKeyAlias,
    physicalTestKeyPassword,
)
val physicalTestStableSigningConfigured = physicalTestSigningValues.all { it.isNotEmpty() }
if (physicalTestSigningValues.any { it.isNotEmpty() } && !physicalTestStableSigningConfigured) {
    error("Physical-test signing must provide path, store password, alias, and key password together")
}
val vkClientId = providers.environmentVariable("SENTINEL_VK_CLIENT_ID")
    .orElse("0")
    .get()
    .trim()
if (!Regex("[0-9]+").matches(vkClientId)) {
    error("SENTINEL_VK_CLIENT_ID must contain decimal digits only")
}

val runtimeEnvironment = providers.environmentVariable("SENTINEL_RUNTIME_ENVIRONMENT")
    .orElse(if (sentryDsn.isNotEmpty() && githubActions) "release-candidate" else "")
    .get()
    .trim()

if (releaseRequested || physicalTestRequested) {
    val value = explicitApiBaseUrl
        ?: error("SENTINEL_API_BASE_URL is required for release and physical-test builds")
    val uri = runCatching { URI(value) }
        .getOrElse { error("SENTINEL_API_BASE_URL must be a valid HTTPS URL for release and physical-test builds") }
    if (
        uri.scheme?.lowercase() != "https" ||
        uri.host.isNullOrBlank() ||
        uri.rawUserInfo != null ||
        uri.rawQuery != null ||
        uri.rawFragment != null ||
        (!uri.rawPath.isNullOrEmpty() && uri.rawPath != "/")
    ) {
        error("SENTINEL_API_BASE_URL must be an HTTPS origin without credentials, path, query, or fragment for release and physical-test builds")
    }
    if (physicalTestRequested && uri.host.lowercase() != "sentinel-core-staging.onrender.com") {
        error("Physical-test builds must target the canonical staging Core")
    }
}

if (sourceSha.isNotEmpty() && !Regex("[0-9a-f]{40}").matches(sourceSha)) {
    error("SENTINEL_SOURCE_SHA/GITHUB_SHA must be empty or a 40-character lowercase commit SHA")
}
val allowedRuntimeEnvironments = setOf("development", "ci", "staging", "release-candidate", "production")
if (runtimeEnvironment.isNotEmpty() && runtimeEnvironment !in allowedRuntimeEnvironments) {
    error("SENTINEL_RUNTIME_ENVIRONMENT must be empty or an allowlisted environment")
}
if (physicalTestRequested) {
    if (!Regex("[0-9a-f]{40}").matches(sourceSha)) {
        error("Physical-test builds require an exact SENTINEL_SOURCE_SHA")
    }
    if (runtimeEnvironment != "staging") {
        error("Physical-test builds require SENTINEL_RUNTIME_ENVIRONMENT=staging")
    }
}

android {
    namespace = "com.alpha0.app"

    compileSdk = 37

    defaultConfig {
        applicationId = "com.alpha0.app"
        minSdk = 29
        targetSdk = 36
        // Production remains explicitly versioned in source. Physical-test builds
        // receive a workflow-monotonic code so Android can replace the prior test APK.
        versionCode = if (physicalTestRequested) physicalTestVersionCode else canonicalVersionCode
        versionName = rootProject.file("VERSION").readText().trim()
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        manifestPlaceholders["appLabel"] = "SENTINEL"
        manifestPlaceholders["authCallbackScheme"] = "com.alpha0.app.auth.dev"
        manifestPlaceholders["vkRedirectScheme"] = "vk$vkClientId"
        buildConfigField("String", "SENTINEL_AUTH_CALLBACK_SCHEME", "\"com.alpha0.app.auth.dev\"")
        buildConfigField("String", "SENTINEL_VK_REDIRECT_URI", "\"vk$vkClientId://vk.ru/blank.html\"")
        buildConfigField("String", "SENTINEL_API_BASE_URL", "\"$apiBaseUrl\"")

        buildConfigField("String", "SENTRY_DSN", "\"$sentryDsn\"")
        buildConfigField("String", "SENTINEL_SOURCE_SHA", "\"$sourceSha\"")
        buildConfigField("String", "SENTINEL_RUNTIME_ENVIRONMENT", "\"$runtimeEnvironment\"")
        buildConfigField("int", "SENTINEL_HTTP_READ_TIMEOUT_MS", "15000")
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    signingConfigs {
        create("ciRelease")
        create("physicalTestStable")
    }

    buildTypes {
        debug {
            buildConfigField("String", "SENTINEL_DIAGNOSTICS_MODE", "\"DEVELOPMENT\"")
            buildConfigField("int", "SENTINEL_DIAGNOSTICS_MAX_BYTES", "2097152")
            buildConfigField("boolean", "SENTINEL_DIAGNOSTICS_EXPORT_ENABLED", "true")
            buildConfigField("String", "SENTINEL_DISTRIBUTION_CHANNEL", "\"development\"")
        }
        create("physicalTest") {
            initWith(getByName("debug"))
            applicationIdSuffix = ".physicaltest"
            versionNameSuffix = "-physical-test"
            manifestPlaceholders["appLabel"] = "SENTINEL"
            manifestPlaceholders["authCallbackScheme"] = "com.alpha0.app.physicaltest.auth"
            buildConfigField("String", "SENTINEL_AUTH_CALLBACK_SCHEME", "\"com.alpha0.app.physicaltest.auth\"")
            matchingFallbacks += listOf("debug")
            isDebuggable = true
            isMinifyEnabled = false
            buildConfigField("String", "SENTINEL_DIAGNOSTICS_MODE", "\"FORENSIC_TEST\"")
            buildConfigField("int", "SENTINEL_DIAGNOSTICS_MAX_BYTES", "16777216")
            buildConfigField("boolean", "SENTINEL_DIAGNOSTICS_EXPORT_ENABLED", "true")
            buildConfigField("String", "SENTINEL_DISTRIBUTION_CHANNEL", "\"diagnostic\"")
            if (physicalTestStableSigningConfigured) {
                signingConfig = signingConfigs.getByName("physicalTestStable")
            }
            // Render free-tier staging may need roughly a minute to wake. The
            // physical build must wait for the authoritative POST response so
            // registration cannot succeed server-side while the UI reports a
            // false network failure. Release behavior remains at 15 seconds.
            buildConfigField("int", "SENTINEL_HTTP_READ_TIMEOUT_MS", "75000")
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
            buildConfigField("String", "SENTINEL_DISTRIBUTION_CHANNEL", "\"play\"")
            manifestPlaceholders["authCallbackScheme"] = "com.alpha0.app.auth"
            buildConfigField("String", "SENTINEL_AUTH_CALLBACK_SCHEME", "\"com.alpha0.app.auth\"")
        }
    }

    if (physicalTestStableSigningConfigured) {
        val physicalTestStable = android.signingConfigs.getByName("physicalTestStable")
        physicalTestStable.storeFile = file(physicalTestKeystorePath)
        physicalTestStable.storePassword = physicalTestKeystorePassword
        physicalTestStable.keyAlias = physicalTestKeyAlias
        physicalTestStable.keyPassword = physicalTestKeyPassword
    }

    val androidKeystorePath = providers.environmentVariable("ANDROID_KEYSTORE_PATH")
    val androidKeystorePassword = providers.environmentVariable("ANDROID_KEYSTORE_PASSWORD")
    val androidKeyAlias = providers.environmentVariable("ANDROID_KEY_ALIAS")
    val androidKeyPassword = providers.environmentVariable("ANDROID_KEY_PASSWORD")

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

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlin {
        compilerOptions {
            jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
        }
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.09.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)
    implementation("androidx.core:core-ktx:1.19.1")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.11.0")
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.navigation:navigation-compose:2.10.2")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.ui:ui-text-google-fonts")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.credentials:credentials:1.6.0")
    implementation("androidx.credentials:credentials-play-services-auth:1.6.0")
    implementation("com.google.android.libraries.identity.googleid:googleid:1.2.1")
    implementation("com.google.android.play:integrity:1.6.0")
    implementation("com.google.android.play:app-update:2.1.0")
    implementation("com.google.android.play:app-update-ktx:2.1.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.11.0")
    implementation("io.sentry:sentry-android:8.57.0")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20260719")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
    androidTestImplementation("androidx.test:runner:1.7.0")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.7.0")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}
