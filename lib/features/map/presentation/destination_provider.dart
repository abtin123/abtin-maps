import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';

class SelectedDestination {
  final LatLng point;
  final String? label;
  const SelectedDestination(this.point, {this.label});
}

final selectedDestinationProvider = StateProvider<SelectedDestination?>((ref) => null);
