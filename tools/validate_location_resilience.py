#!/usr/bin/env python3
"""Static checks for two-dimensional filtering and short GPS-gap handling."""

from pathlib import Path


root = Path(__file__).resolve().parents[2]
kalman = (root / "lib/features/gps/data/joint_kalman_filter_2d.dart").read_text(encoding="utf-8")
service = (root / "lib/features/gps/data/location_service.dart").read_text(encoding="utf-8")
nav = (root / "lib/features/gps/presentation/navigation_position_controller.dart").read_text(encoding="utf-8")

assert "class JointKalmanFilter2D" in kalman
assert "KalmanLocationSample? predictOnly" in kalman
assert "void _predict(double dt)" in kalman
assert "bool useJointKalman = true;" in service
assert "_gpsGapPredictionTimer" in service
assert "_maxGpsPredictionGap = Duration(seconds: 8)" in service
assert "_predictGpsGap()" in service
assert "_jointKalman.predictOnly" in service
assert "_gpsGapPredictionTimer?.cancel();" in service
assert "_maxAccuracyForSnapM = 30.0" in nav
assert "_maxSnapDistanceM = 25.0" in nav
print("location_resilience_contract_ok")
