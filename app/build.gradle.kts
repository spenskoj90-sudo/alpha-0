plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.alpha0.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.alpha0.app"
        minSdk = 29
        targetSdk = 35

        versionCode = 3
        versionName = "0.3.0"
    }

    signingConfigs {
        create("ciRelease") {
            val keystorePath = System.getenv("ALPHA0_KEYSTORE_PATH")
            val keystorePassword = System.getenv("ALPHA0_KEYSTORE_PASSWORD")
            val keyAlias = System.getenv("ALPHA0_KEY_ALIAS")
            val keyPassword = System.getenv("ALPHA0_KEY_PASSWORD")

            if (
                keystorePath != null &&
                keystorePassword != null &&
                keyAlias != null &&
                keyPassword != null
            ) {
                storeFile = file(keystorePath)
                storePassword = keystorePassword
                this.keyAlias = keyAlias
                this.keyPassword = keyPassword
            }
        }
    }

    buildTypes {
        debug {
            // Debug builds use the standard Android debug keystore.
            // Production signing material must never be required for local/CI debug builds.
        }

        release {
            // Release signing is intentionally secret-backed. A release build without
            // all required CI secrets must fail instead of silently producing a release artifact.
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("ciRelease")
        }
    }

    lint {
        abortOnError = true
        checkReleaseBuilds = true
    }
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
