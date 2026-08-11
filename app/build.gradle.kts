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

        versionCode = 2
        versionName = "0.2.0"
    }

    signingConfigs {
        create("ciRelease") {
            val keystorePath = System.getenv("ALPHA0_KEYSTORE_PATH")
            val keystorePassword = System.getenv("ALPHA0_KEYSTORE_PASSWORD")
            val keyAlias = System.getenv("ALPHA0_KEY_ALIAS")
            val keyPassword = System.getenv("ALPHA0_KEY_PASSWORD")

            if (
                !keystorePath.isNullOrBlank() &&
                !keystorePassword.isNullOrBlank() &&
                !keyAlias.isNullOrBlank() &&
                !keyPassword.isNullOrBlank()
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
            // Use the standard Android debug keystore. CI must not require
            // release-signing secrets for ordinary debug validation.
        }

        release {
            isMinifyEnabled = false

            val ciSigningConfigured = listOf(
                System.getenv("ALPHA0_KEYSTORE_PATH"),
                System.getenv("ALPHA0_KEYSTORE_PASSWORD"),
                System.getenv("ALPHA0_KEY_ALIAS"),
                System.getenv("ALPHA0_KEY_PASSWORD")
            ).all { !it.isNullOrBlank() }

            if (ciSigningConfigured) {
                signingConfig = signingConfigs.getByName("ciRelease")
            }
        }
    }
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
