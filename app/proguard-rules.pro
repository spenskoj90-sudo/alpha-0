# SENTINEL release keep rules — minimize surface while preserving Compose/Kotlin/reflection needs.

-keepattributes *Annotation*, Signature, InnerClasses, EnclosingMethod
-keep class com.alpha0.app.** { *; }
-keep class androidx.compose.** { *; }
-dontwarn com.google.android.play.core.**
-keep class com.google.android.play.core.integrity.** { *; }
