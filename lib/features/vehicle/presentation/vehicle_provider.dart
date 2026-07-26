import 'package:flutter_riverpod/flutter_riverpod.dart';

enum VehicleType { arrow, bmwI8 }

final selectedVehicleProvider = StateProvider<VehicleType>((ref) => VehicleType.arrow);
