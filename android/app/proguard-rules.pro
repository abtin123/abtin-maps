# Flutter ProGuard Rules
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.util.** { *; }
-keep class io.flutter.view.** { *; }
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }

# Drift (Database) Rules
-keep class * extends androidx.room.RoomDatabase
-keep class * extends com.google.gson.TypeAdapter
-keep class * extends com.google.gson.JsonSerializer
-keep class * extends com.google.gson.JsonDeserializer

# MapLibre Rules
-keep class com.mapbox.** { *; }

# Sherpa ONNX (Voice) Rules
-keep class com.k2fsa.sherpa.onnx.** { *; }
