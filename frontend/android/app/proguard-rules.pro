# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.
#
# For more details, see
#   http://developer.android.com/guide/developing/tools/proguard.html

# If your project uses WebView with JS, uncomment the following
# and specify the fully qualified class name to the JavaScript interface
# class:
#-keepclassmembers class fqcn.of.javascript.interface.for.webview {
#   public *;
#}

# Uncomment this to preserve the line number information for
# debugging stack traces.
#-keepattributes SourceFile,LineNumberTable

# If you keep the line number information, uncomment this to
# hide the original source file name.
#-renamesourcefileattribute SourceFile

# ── Capacitor ────────────────────────────────────────────────────────────────
# Los plugins se resuelven por nombre desde capacitor.plugins.json, asi que R8
# no ve ninguna referencia estatica y los eliminaria del APK de release.
-keep public class * extends com.getcapacitor.Plugin
-keep @com.getcapacitor.annotation.CapacitorPlugin public class * { *; }
-keepclassmembers class * extends com.getcapacitor.Plugin {
    @com.getcapacitor.PluginMethod public <methods>;
}
-keep class com.getcapacitor.** { *; }
-keep class com.capacitorjs.plugins.** { *; }
-keep class com.getcapacitor.community.database.sqlite.** { *; }

# El puente JS <-> nativo entra por @JavascriptInterface
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# SQLCipher / androidx.sqlite, que usa @capacitor-community/sqlite
-keep class net.sqlcipher.** { *; }
-dontwarn net.sqlcipher.**

# Firebase Cloud Messaging (@capacitor/push-notifications)
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**

# Cordova, por los plugins puenteados
-keep class org.apache.cordova.** { *; }
-dontwarn org.apache.cordova.**
