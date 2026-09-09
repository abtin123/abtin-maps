import 'package:flutter/services.dart';

/// مسیرِ فایل GLB هر مدلِ خودرو در assets/models.
///
/// هر دو لیستِ [vehicleModels] و [vehicleModelNames] هم‌تراز هستند — یعنی
/// ایندکسِ i در یکی همان مدلِ ایندکسِ i در دیگری است. هر چهار فایلِ GLB
/// موجود در assets/models اینجا استفاده می‌شوند.
final vehicleModels = <String>[
  'assets/models/bmw_i8.glb',
  'assets/models/acura_rsx.glb',
  'assets/models/nissan_patrol.glb',
  'assets/models/ford_mustang_gt500.glb',
];

/// نام نمایشیِ فارسیِ هر مدل — هم‌ترازِ ایندکسِ [vehicleModels].
final vehicleModelNames = <String>[
  'بی‌ام‌و i8',
  'آکورا RSX',
  'نیسان پاترول',
  'فورد موستانگ GT500',
];


/// Warm the selected GLB into Flutter's asset pipeline before the map/3D
/// marker needs it. This does not replace the real 3D car; it only removes
/// the first asset-read delay from the navigation start path.
final Set<String> _warmedVehicleModels = <String>{};

Future<void> warmUpVehicleModel(int modelIndex) async {
  if (vehicleModels.isEmpty) return;
  final index = modelIndex.clamp(0, vehicleModels.length - 1);
  final asset = vehicleModels[index];
  if (!_warmedVehicleModels.add(asset)) return;
  try {
    await rootBundle.load(asset);
  } catch (_) {
    _warmedVehicleModels.remove(asset);
  }
}
