# SENTINEL release keep rules — minimize surface while preserving Compose/Kotlin/reflection needs.

-keepattributes *Annotation*, Signature, InnerClasses, EnclosingMethod
-keep class com.alpha0.app.** { *; }
-keep class androidx.compose.** { *; }
-dontwarn com.google.android.play.core.**
-keep class com.google.android.play.core.integrity.** { *; }

# Sentry Android SDK (issue #7) — preserve line numbers and required reflection surfaces.
-keepattributes SourceFile,LineNumberTable
-keep class io.sentry.** { *; }
-dontwarn io.sentry.**
