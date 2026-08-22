#!/usr/bin/env python3
"""Static contract checks for optional offline AI Camera and landscape-only HUD."""

from pathlib import Path


root = Path(__file__).resolve().parents[2]
settings = (root / "lib/features/ai_camera/presentation/ai_camera_settings.dart").read_text(encoding="utf-8")
screen = (root / "lib/features/ai_camera/presentation/ai_camera_settings_screen.dart").read_text(encoding="utf-8")
street = (root / "lib/features/ai_camera/presentation/street_view_screen.dart").read_text(encoding="utf-8")
hud = (root / "lib/features/ai_camera/presentation/hud_screen.dart").read_text(encoding="utf-8")
recorder = (root / "lib/features/ai_camera/presentation/ai_dashcam_recorder.dart").read_text(encoding="utf-8")
detector = (root / "lib/features/ai_camera/data/offline_traffic_sign_detector.dart").read_text(encoding="utf-8")
router = (root / "lib/core/router/app_router.dart").read_text(encoding="utf-8")
home = (root / "lib/features/map/presentation/home_screen.dart").read_text(encoding="utf-8")
manifest = (root / "android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
pubspec = (root / "pubspec.yaml").read_text(encoding="utf-8")

assert "this.enabled = false" in settings and "this.hudEnabled = false" in settings
assert "keyAiCameraSettings" in settings
assert "فعال‌سازی AI Camera" in screen
assert "HUD آینه‌ای" in screen
assert "ضبط DashCam" in screen and "دستیار رانندگی آفلاین" in screen
assert "camera: ^" in pubspec and "tflite_flutter: ^" in pubspec
assert "android.permission.CAMERA" in manifest
assert "traffic_sign_gtsrb.lite" in detector
assert "Interpreter.fromAsset" in detector
assert "ImageFormatGroup.yuv420" in detector
assert "AI Camera توسط کاربر فعال نشده" in street
assert "CameraPreview" in street and "_RouteProjection" in street
assert "startVideoRecording" in street and "startImageStream" in street
assert "Orientation.landscape" in hud
assert "Matrix4.identity()..scale(-1.0, 1.0)" in hud
assert "Orientation.landscape" not in street
assert "aiStreetViewOpenProvider" in settings
assert "CameraController" in recorder and "startVideoRecording" in recorder
assert "getApplicationDocumentsDirectory" in recorder and "segmentMinutes" in recorder
assert "/street-view" in router and "/hud" in router
assert "aiCameraSettings.enabled" in home and "aiCameraSettings.hudEnabled" in home
assert "AiDashCamRecorder" in home and "!streetViewOpen" in home
assert (root / "assets/models/traffic_sign_gtsrb.lite").stat().st_size > 1_000_000

print("ai_camera_contract_ok")
