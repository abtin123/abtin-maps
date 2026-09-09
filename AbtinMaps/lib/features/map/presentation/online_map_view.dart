import 'dart:async';
import '../../../core/abm_debug_log.dart';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:maplibre_gl/maplibre_gl.dart' as ml;

import '../../../abtinmap/abm_models.dart';
import '../../../core/geo/geo_types.dart';
import '../../../shared/providers/map_style_providers.dart';
import '../../gps/data/location_service.dart';
import '../../vehicle/presentation/nav_arrow_painter.dart';
import '../../vehicle/presentation/car_marker.dart';

/// زاویهٔ مکان‌نما نسبت به صفحه، بر پایهٔ heading جغرافیایی GPS و جهت فعلی
/// دوربین. خروجی در بازهٔ استاندارد ۰ تا کمتر از ۳۶۰ درجه است.
double mapRelativeHeading(double headingDeg, double mapBearingDeg) {
  final heading = headingDeg.isFinite ? headingDeg : 0.0;
  final bearing = mapBearingDeg.isFinite ? mapBearingDeg : 0.0;
  return (heading - bearing) % 360.0;
}

/// MapLibre Android موقعیت را با pixel فیزیکی View برمی‌گرداند، در حالی که
/// Positioned در Flutter با logical pixel کار می‌کند. بدون این تبدیل، marker
/// روی نمایشگرهای با تراکم بالاتر از ۱ به سمت لبهٔ پایین/راست جابه‌جا می‌شد.
const Map<int, List<String>> _offlinePoiClassesByKlass = {
  AbmKlass.poiFuel: ['fuel'],
  AbmKlass.poiParking: ['parking', 'bicycle_parking'],
  AbmKlass.poiHospital: ['hospital', 'clinic', 'doctors'],
  AbmKlass.poiPharmacy: ['pharmacy'],
  AbmKlass.poiPolice: ['police'],
  AbmKlass.poiSchool: ['school', 'college', 'university', 'kindergarten'],
  AbmKlass.poiRestaurant: ['restaurant', 'fast_food', 'food_court'],
  AbmKlass.poiCafe: ['cafe', 'ice_cream'],
  AbmKlass.poiBank: ['bank', 'atm'],
  AbmKlass.poiHotel: ['hotel', 'motel', 'hostel', 'guest_house', 'apartment'],
  AbmKlass.poiSupermarket: [
    'supermarket',
    'convenience',
    'department_store',
    'mall',
    'greengrocer',
  ],
  AbmKlass.poiMosque: ['place_of_worship'],
  AbmKlass.poiToilets: ['toilets'],
  AbmKlass.poiBusStation: ['bus_station', 'bus_stop'],
  AbmKlass.poiAirport: ['aerodrome', 'airport'],
  AbmKlass.poiAttraction: [
    'attraction',
    'museum',
    'viewpoint',
    'zoo',
    'theme_park',
    'monument',
    'memorial',
    'castle',
    'archaeological_site',
  ],
  AbmKlass.poiPark: ['park', 'garden', 'nature_reserve'],
  AbmKlass.poiPitch: ['pitch', 'sports_centre', 'stadium'],
  AbmKlass.poiPlace: [
    'city',
    'town',
    'village',
    'suburb',
    'neighbourhood',
    'quarter',
    'hamlet',
    'locality',
  ],
  AbmKlass.poiSpeedCamera: ['speed_camera'],
  AbmKlass.poiSpeedBump: ['bump', 'hump', 'table', 'cushion', 'chicane'],
  AbmKlass.poiTrafficLight: ['traffic_signals'],
};

List<dynamic> offlinePoiLayerFilter(Set<int>? visibleKlasses) {
  if (visibleKlasses != null && visibleKlasses.isEmpty) {
    return const <dynamic>[
      '==',
      ['get', 'class'],
      '__abtin-hidden-poi__'
    ];
  }
  final enabled = visibleKlasses ?? _offlinePoiClassesByKlass.keys.toSet();
  final classes = <String>{
    for (final klass in enabled) ...?_offlinePoiClassesByKlass[klass],
  }.toList(growable: false);
  // هر دو schema پشتیبانی می‌شود: class متنی در MVT یا klass عددی ABM.
  return <dynamic>[
    'all',
    ['has', 'name'],
    [
      'any',
      [
        'in',
        ['get', 'class'],
        ...classes
      ],
      [
        'in',
        ['get', 'klass'],
        ...enabled
      ],
    ],
  ];
}

bool sameOfflinePoiVisibility(Set<int>? a, Set<int>? b) {
  if (a == null || b == null) return a == null && b == null;
  return a.length == b.length && a.containsAll(b);
}

List<dynamic> roadWidthExpression(double scale, {double base = 1.0}) {
  final safeScale = scale.clamp(0.6, 1.8).toDouble();
  return <dynamic>[
    'interpolate',
    ['linear'],
    ['zoom'],
    6,
    base * safeScale,
    10,
    base * 1.35 * safeScale,
    14,
    base * 3.2 * safeScale,
    18,
    base * 8.0 * safeScale,
    20,
    base * 12.0 * safeScale,
  ];
}

Offset mapScreenPointToFlutterOffset(
  math.Point<dynamic> screenPoint,
  double devicePixelRatio,
) {
  final ratio = devicePixelRatio.isFinite && devicePixelRatio > 0
      ? devicePixelRatio
      : 1.0;
  return Offset(
    screenPoint.x.toDouble() / ratio,
    screenPoint.y.toDouble() / ratio,
  );
}

class OnlineRouteOverlay {
  const OnlineRouteOverlay({
    required this.geometry,
    required this.color,
    required this.width,
  });

  final List<LatLng> geometry;
  final Color color;
  final double width;
}

/// MapLibre Native نمایش نقشهٔ آنلاین را با همان renderer GPU نقشهٔ آفلاین
/// renderer برداری داخلی هم‌راستا نگه می‌دارد. دادهٔ route و خودرو از سرویس‌های محلی آبتین
/// می‌آید و به provider نقشه وابسته نیست.
class OnlineMapView extends StatefulWidget {
  const OnlineMapView({
    super.key,
    required this.vehiclePosition,
    required this.showCarModel,
    required this.modelIndex,
    required this.isDark,
    required this.followVehicle,
    required this.drivingMode,
    required this.markerColor,
    required this.pinSizePercent,
    required this.carSizePercent,
    required this.pinShadowEnabled,
    required this.cameraTiltDegrees,
    required this.carCameraAngleDegrees,
    required this.locationFocusRequest,
    required this.palette,
    required this.visiblePoiKlasses,
    this.localStylePath,
    this.routeGeometry,
    this.routeOverlays,
    this.routeColor = const Color(0xFF2FE6C4),
    this.routeWidth = 7.0,
    this.destination,
    this.onLongPress,
    this.onRouteTap,
    this.onUserGestureStart,
    this.onCameraIdle,
    this.onCameraPositionChanged,
    this.onStyleLoaded,
  });

  /// null یعنی هنوز فیکس زنده و قابل اعتماد دریافت نشده است. در این حالت
  /// نقشه باز می‌ماند، اما marker و follow-camera عمداً فعال نمی‌شوند.
  final VehiclePosition? vehiclePosition;

  /// true یعنی مکان‌نمای سه‌بعدیِ خودرو نمایش داده شود؛ false یعنی فلشِ
  /// استانداردِ ناوبری (معادلِ AppearanceTab.car / AppearanceTab.pin).
  final bool showCarModel;
  final int modelIndex;
  final bool isDark;
  final bool followVehicle;
  final bool drivingMode;
  final Color markerColor;
  final double pinSizePercent;
  final double carSizePercent;
  final bool pinShadowEnabled;
  final double cameraTiltDegrees;

  /// زاویهٔ اختصاصیِ دوربینِ مدلِ سه‌بعدیِ خودرو (۰=از بالا، ۹۰=از پشتِ
  /// خودرو) — مستقل از [cameraTiltDegrees] که کجیِ خودِ نقشه است.
  final double carCameraAngleDegrees;
  final int locationFocusRequest;
  final OfflineMapPalette palette;

  /// null یعنی همهٔ دسته‌های POI، و set خالی یعنی همه پنهان هستند.
  final Set<int>? visiblePoiKlasses;

  /// در حالت آفلاین، داده مستقیماً از ABM Reader داخلی خوانده می‌شود.
  /// null یعنی style آنلاینِ بدون API key استفاده شود.
  final String? localStylePath;
  final List<LatLng>? routeGeometry;
  final List<OnlineRouteOverlay>? routeOverlays;
  final Color routeColor;
  final double routeWidth;
  final LatLng? destination;
  final ValueChanged<LatLng>? onLongPress;
  final ValueChanged<int>? onRouteTap;
  final VoidCallback? onUserGestureStart;
  final VoidCallback? onCameraIdle;
  final ValueChanged<ml.CameraPosition>? onCameraPositionChanged;
  final VoidCallback? onStyleLoaded;

  @override
  State<OnlineMapView> createState() => _OnlineMapViewState();
}

class _OnlineMapViewState extends State<OnlineMapView> {
  static const _dayStyle = 'https://tiles.openfreemap.org/styles/liberty';
  static const _nightStyle = 'https://tiles.openfreemap.org/styles/dark';
  // Camera follow must never queue long animations. A 220ms animation
  // triggered every 100ms made the camera permanently lag behind the car.
  static const _cameraUpdateInterval = Duration(milliseconds: 50);
  static const _fallbackInitialTarget = ml.LatLng(32.5, 54.0);

  ml.MapLibreMapController? _controller;
  ml.CameraPosition? _camera;
  Offset? _vehicleScreen;
  Offset? _destinationScreen;
  bool _styleReady = false;
  bool _onlineStreetLabelsAdded = false;
  bool _screenUpdateRunning = false;
  bool _screenUpdateQueued = false;
  int _screenUpdateGeneration = 0;
  bool _cameraMoveRunning = false;
  ml.CameraPosition? _pendingCameraPosition;
  DateTime _lastCameraUpdate = DateTime.fromMillisecondsSinceEpoch(0);
  final List<ml.Line> _routeLines = <ml.Line>[];
  int _routeRefreshGeneration = 0;
  int _pendingLocationFocusRequest = 0;

  // کشِ پیشرفتِ خودرو روی route.geometry برای هدفِ دوربینِ ناوبری (نگاه کنید
  // به _pointAheadOnRoute). جدا از کشِ مشابه در home_screen است چون این
  // ویجت مستقلاً به geometry دسترسی دارد.
  List<LatLng>? _navRouteGeometry;
  List<double>? _navRouteCumulativeM;
  int? _navRouteLastSegment;

  // MapLibre location puck is intentionally disabled. The app uses its own
  // navigation vehicle marker and must not show the default blue location dot.

  static const double _minMapZoom = 2.0;
  // 18 per user request: allow closer street-level inspection. The offline
  // ABM files use overview zooms so 17–18 fall back to lower-resolution
  // overview tiles rather than showing blank voids.
  static const double _maxMapZoom = 18.0;

  // A bad native ambient tile can survive map-widget recreation. Clear it only
  // once per process for the online renderer, then keep valid tiles cached.
  static bool _onlineAmbientCacheClearedThisProcess = false;

  ml.LatLng _toMapLibrePoint(LatLng point) =>
      ml.LatLng(point.latitude, point.longitude);

  ml.LatLng _toMapLibreVehiclePoint(VehiclePosition point) =>
      ml.LatLng(point.lat, point.lng);

  List<OnlineRouteOverlay> get _routeOverlays =>
      widget.routeOverlays ??
      (widget.routeGeometry == null
          ? const <OnlineRouteOverlay>[]
          : <OnlineRouteOverlay>[
              OnlineRouteOverlay(
                geometry: widget.routeGeometry!,
                color: widget.routeColor,
                width: widget.routeWidth,
              ),
            ]);

  @override
  void initState() {
    super.initState();
    _pendingLocationFocusRequest = widget.locationFocusRequest;
  }

  @override
  void didUpdateWidget(covariant OnlineMapView oldWidget) {
    super.didUpdateWidget(oldWidget);
    final previousPosition = oldWidget.vehiclePosition;
    final nextPosition = widget.vehiclePosition;
    final positionChanged = previousPosition?.lat != nextPosition?.lat ||
        previousPosition?.lng != nextPosition?.lng ||
        previousPosition?.headingDeg != nextPosition?.headingDeg ||
        previousPosition?.speedKmh != nextPosition?.speedKmh;
    final tiltChanged = oldWidget.cameraTiltDegrees != widget.cameraTiltDegrees;
    final paletteChanged =
        oldWidget.palette.serialize() != widget.palette.serialize();
    final poiVisibilityChanged = !sameOfflinePoiVisibility(
      oldWidget.visiblePoiKlasses,
      widget.visiblePoiKlasses,
    );
    final routesChanged = oldWidget.routeOverlays != widget.routeOverlays ||
        oldWidget.routeGeometry != widget.routeGeometry ||
        oldWidget.routeColor != widget.routeColor ||
        oldWidget.routeWidth != widget.routeWidth;

    if (oldWidget.locationFocusRequest != widget.locationFocusRequest) {
      _pendingLocationFocusRequest = widget.locationFocusRequest;
      _focusGpsCamera();
    }
    if (oldWidget.destination != widget.destination &&
        widget.destination != null) {
      _focusDestination(widget.destination!);
    }
    // Follow-camera is a map behavior, not a navigation-only behavior.
    // When the user has not manually taken control, the camera must stay
    // behind the vehicle both with and without an active route.
    if (widget.followVehicle &&
        nextPosition != null &&
        (positionChanged ||
            tiltChanged ||
            oldWidget.followVehicle != widget.followVehicle ||
            oldWidget.drivingMode != widget.drivingMode)) {
      _syncCamera(force: tiltChanged);
    } else if (tiltChanged && !widget.followVehicle) {
      final controller = _controller;
      if (controller != null) {
        unawaited(
          controller.animateCamera(
            ml.CameraUpdate.tiltTo(widget.cameraTiltDegrees.clamp(0, 60)),
            duration: const Duration(milliseconds: 220),
          ),
        );
      }
    }
    if (_styleReady && paletteChanged) {
      unawaited(_applyMapPalette());
    }
    if (_styleReady && poiVisibilityChanged) {
      unawaited(_applyOfflinePoiVisibility());
    }
    if (_styleReady && routesChanged) {
      unawaited(_refreshRouteAnnotations());
    }
    if (positionChanged || oldWidget.destination != widget.destination) {
      unawaited(_refreshScreenPositions());
    }
  }

  void _onMapCreated(ml.MapLibreMapController controller) {
    _controller = controller;
    if (widget.localStylePath == null &&
        !_onlineAmbientCacheClearedThisProcess) {
      _onlineAmbientCacheClearedThisProcess = true;
      unawaited(_clearOnlineAmbientCache(controller));
    }
    _focusGpsCamera();
  }

  Future<void> _clearOnlineAmbientCache(
    ml.MapLibreMapController controller,
  ) async {
    try {
      await controller.clearAmbientCache();
      debugPrint('[ABM ONLINE MAP] ambient tile cache cleared once');
    } catch (error) {
      debugPrint('[ABM ONLINE MAP] ambient cache clear failed: $error');
    }
  }

  Future<void> _applyOfflinePoiVisibility() async {
    final controller = _controller;
    if (controller == null || !_styleReady || widget.localStylePath == null) {
      return;
    }
    final filter = offlinePoiLayerFilter(widget.visiblePoiKlasses);
    for (final layerId in const ['poi-points', 'poi-labels']) {
      try {
        await controller.setFilter(layerId, filter);
      } catch (error) {
        debugPrint('[ABM MAP] POI filter failed for $layerId: $error');
      }
    }
  }

  void _onStyleLoaded() {
    _styleReady = true;
    _routeLines.clear();
    _onlineStreetLabelsAdded = false;
    // Do not add sources/layers to the provider style. We only modify existing
    // paint properties after the style is fully loaded. This keeps the online
    // OpenFreeMap source intact while allowing the user's palette to apply.
    unawaited(_applyMapPalette());
    if (widget.localStylePath == null) {
      unawaited(_ensureOnlineStreetLabels());
    }
    if (widget.localStylePath != null) {
      unawaited(_applyOfflinePoiVisibility());
    }
    widget.onStyleLoaded?.call();
    unawaited(_refreshRouteAnnotations());
    if (_pendingLocationFocusRequest != 0) {
      _focusGpsCamera();
    } else if (widget.drivingMode && widget.vehiclePosition != null) {
      _syncCamera(force: true);
    } else {
      unawaited(_refreshScreenPositions());
    }
  }

  /// OpenFreeMap normally provides road labels, but some native MapLibre
  /// builds load the vector source while dropping the provider label layers.
  /// Re-add one provider-owned layer so both online themes show street names.
  Future<void> _ensureOnlineStreetLabels() async {
    final controller = _controller;
    if (controller == null || _onlineStreetLabelsAdded) return;
    try {
      await controller.addSymbolLayer(
        'openmaptiles',
        'abm-online-street-labels',
        ml.SymbolLayerProperties(
          textField: const [
            'coalesce',
            ['get', 'name'],
            ['get', 'name:latin'],
            ['get', 'name:nonlatin'],
            ['get', 'name_en'],
          ],
          textFont: const ['Noto Sans Regular'],
          textSize: const [
            'interpolate',
            ['linear'],
            ['zoom'],
            11,
            10,
            16,
            14,
          ],
          textColor: _hexColor(widget.palette.label),
          textHaloColor: _hexColor(widget.palette.halo),
          textHaloWidth: 1.0,
          textOpacity: 1.0,
          textRotationAlignment: 'map',
          textPitchAlignment: 'map',
          symbolPlacement: 'line',
          textAllowOverlap: false,
          textIgnorePlacement: false,
        ),
        sourceLayer: 'transportation_name',
        minzoom: 11,
        filter: const [
          'match',
          ['get', 'class'],
          [
            'motorway',
            'trunk',
            'primary',
            'secondary',
            'tertiary',
            'minor',
            'service',
            'track',
          ],
          true,
          false,
        ],
        enableInteraction: false,
      );
      _onlineStreetLabelsAdded = true;
    } catch (error) {
      // A provider style without the openmaptiles source already owns its
      // labels; ignore this optional fallback in that case.
      debugPrint('[ABM ONLINE LABELS] add layer skipped: $error');
    }
  }

  /// Applies the same user-editable palette to both the bundled ABM style and
  /// the current online OpenFreeMap style. For online maps we never add/remove
  /// sources or layers; only existing paint properties are changed after the
  /// provider style has loaded. This is the safe path for MapLibre Native.
  Future<void> _applyMapPalette() async {
    final controller = _controller;
    if (controller == null || !_styleReady) return;

    final palette = widget.palette;
    final background = _hexColor(palette.background);
    final green = _hexColor(palette.green);
    final urban = _hexColor(palette.urban);
    final building = _hexColor(palette.building);
    final water = _hexColor(palette.water);
    final label = _hexColor(palette.label);
    final halo = _hexColor(palette.halo);
    final roadOutline = _hexColor(palette.roadOutline);
    final roadWidth = roadWidthExpression(palette.roadWidthScale);
    final roadCasingWidth = roadWidthExpression(
      palette.roadWidthScale,
      base: 1.35,
    );
    final roadColorExpression = <dynamic>[
      'match',
      ['get', 'class'],
      'motorway',
      _hexColor(palette.roadMotorway),
      'trunk',
      _hexColor(palette.roadTrunk),
      'primary',
      _hexColor(palette.roadPrimary),
      'secondary',
      _hexColor(palette.roadSecondary),
      'tertiary',
      _hexColor(palette.roadSecondary),
      'residential',
      _hexColor(palette.roadLocal),
      'unclassified',
      _hexColor(palette.roadLocal),
      'service',
      _hexColor(palette.roadLocal),
      'track',
      _hexColor(palette.roadLocal),
      _hexColor(palette.roadLocal),
    ];

    // The offline ABM style has stable layer ids, so keep its precise mapping.
    if (widget.localStylePath != null) {
      try {
        await controller.setLayerProperties(
          'background',
          ml.BackgroundLayerProperties(backgroundColor: background),
        );
        await controller.setLayerProperties(
          'land-forest',
          ml.FillLayerProperties(fillColor: green),
        );
        await controller.setLayerProperties(
          'land-urban',
          ml.FillLayerProperties(fillColor: urban),
        );
        await controller.setLayerProperties(
          'land-other',
          ml.FillLayerProperties(fillColor: background),
        );
        await controller.setLayerProperties(
          'water-area',
          ml.FillLayerProperties(fillColor: water),
        );
        await controller.setLayerProperties(
          'road-casing',
          ml.LineLayerProperties(
            lineColor: roadOutline,
            lineWidth: roadCasingWidth,
          ),
        );
        await controller.setLayerProperties(
          'road-fill',
          ml.LineLayerProperties(
              lineColor: roadColorExpression, lineWidth: roadWidth),
        );
        await controller.setLayerProperties(
          'buildings',
          ml.FillLayerProperties(fillColor: building),
        );
      } catch (error) {
        debugPrint('[ABM OFFLINE PALETTE] apply failed: $error');
      }
      return;
    }

    // OpenFreeMap/Liberty uses OpenMapTiles source-layers. We inspect the
    // already-loaded style instead of assuming fixed layer ids; this also keeps
    // the code compatible with Bright/Positron/Dark/Fiord variants whose layer
    // names differ. No source or layer is created here.
    try {
      final ids = await controller.getLayerIds();
      for (final rawId in ids) {
        final id = rawId.toString();
        final props = await controller.getLayerProperties(id);
        if (props == null) continue;
        final type = props['type']?.toString();
        final sourceLayer = props['source-layer']?.toString();
        final idLower = id.toLowerCase();
        final sourceLayerLower = sourceLayer?.toLowerCase() ?? '';

        try {
          if (type == 'background') {
            await controller.setLayerProperties(
              id,
              ml.BackgroundLayerProperties(backgroundColor: background),
            );
            continue;
          }

          if (type == 'fill') {
            if (sourceLayerLower == 'water' || idLower.contains('water')) {
              await controller.setLayerProperties(
                id,
                ml.FillLayerProperties(fillColor: water),
              );
            } else if (sourceLayerLower == 'building' ||
                idLower.contains('building')) {
              await controller.setLayerProperties(
                id,
                ml.FillLayerProperties(fillColor: building),
              );
            } else if (sourceLayerLower == 'landcover' ||
                idLower.contains('landcover') ||
                idLower.contains('park') ||
                idLower.contains('wood') ||
                idLower.contains('grass')) {
              await controller.setLayerProperties(
                id,
                ml.FillLayerProperties(fillColor: green),
              );
            } else if (sourceLayerLower == 'landuse' ||
                idLower.contains('landuse') ||
                idLower.contains('residential') ||
                idLower.contains('urban')) {
              await controller.setLayerProperties(
                id,
                ml.FillLayerProperties(fillColor: urban),
              );
            }
            continue;
          }

          if (type == 'line' && sourceLayerLower == 'transportation') {
            final isCasing =
                idLower.contains('casing') || idLower.contains('outline');
            await controller.setLayerProperties(
              id,
              ml.LineLayerProperties(
                lineColor: isCasing ? roadOutline : roadColorExpression,
                lineWidth: isCasing ? roadCasingWidth : roadWidth,
              ),
            );
            continue;
          }

          // All provider labels keep their layout/icon configuration. Only
          // text paint is changed, so glyphs, sprites and collision behavior
          // remain owned by the provider style.
          if (type == 'symbol') {
            await controller.setLayerProperties(
              id,
              ml.SymbolLayerProperties(
                textColor: label,
                textHaloColor: halo,
              ),
            );
          }
        } catch (error) {
          // Some provider layers expose paint properties that are not mutable
          // on every native backend. Ignore only that layer and keep rendering.
          debugPrint('[ABM ONLINE PALETTE] layer $id skipped: $error');
        }
      }
    } catch (error) {
      debugPrint('[ABM ONLINE PALETTE] style inspection failed: $error');
    }
  }

  Future<void> _refreshRouteAnnotations() async {
    final controller = _controller;
    if (!_styleReady || controller == null) return;
    final generation = ++_routeRefreshGeneration;
    final routes = _routeOverlays
        .where((route) => route.geometry.length >= 2)
        .toList(growable: false);
    final options = <ml.LineOptions>[
      for (final route in routes)
        ml.LineOptions(
          geometry:
              route.geometry.map(_toMapLibrePoint).toList(growable: false),
          lineColor: _hexColor(route.color),
          lineWidth: route.width,
          lineOpacity: 1,
          lineJoin: 'round',
        ),
    ];
    try {
      // در لغو مسیر، حذف را مستقیم و قطعی انجام می‌دهیم. مسیرهای پیشنهادی
      // قبلی ممکن است هم‌زمان با تغییر provider در یک frame باقی مانده باشند؛
      // جایگزینی با لیست خالی نباید منتظر addLines بماند.
      if (options.isEmpty) {
        final previous = List<ml.Line>.from(_routeLines);
        _routeLines.clear();
        if (previous.isNotEmpty) await controller.removeLines(previous);
        return;
      }

      if (_routeLines.length == options.length) {
        for (var index = 0; index < options.length; index++) {
          if (generation != _routeRefreshGeneration) return;
          await controller.updateLine(_routeLines[index], options[index]);
        }
        return;
      }

      // خطوط تازه ابتدا اضافه می‌شوند و فقط پس از موفقیت، خطوط قبلی حذف
      // می‌گردند؛ بنابراین با انتخاب route جدید نقشه حتی یک frame بدون مسیر
      // نمی‌ماند و flicker رخ نمی‌دهد.
      final replacement = options.isEmpty
          ? const <ml.Line>[]
          : await controller.addLines(options);
      if (generation != _routeRefreshGeneration || controller != _controller) {
        if (replacement.isNotEmpty) await controller.removeLines(replacement);
        return;
      }
      final previous = List<ml.Line>.from(_routeLines);
      _routeLines
        ..clear()
        ..addAll(replacement);
      if (previous.isNotEmpty) await controller.removeLines(previous);
    } catch (_) {
      // در لحظهٔ جایگزینی style، annotation manager قدیمی ممکن است آزاد شده
      // باشد. callback بارگذاری style، خطوط route را دوباره ثبت می‌کند.
    }
  }

  String _hexColor(Color color) {
    final argb = color.toARGB32();
    return '#${((argb >> 16) & 0xFF).toRadixString(16).padLeft(2, '0')}${((argb >> 8) & 0xFF).toRadixString(16).padLeft(2, '0')}${(argb & 0xFF).toRadixString(16).padLeft(2, '0')}';
  }

  void _focusGpsCamera() {
    final controller = _controller;
    final position = widget.vehiclePosition;
    if (controller == null || position == null) return;
    _pendingLocationFocusRequest = 0;
    // GPS button is a re-anchor, not a queued animation. First put the map
    // exactly on the current vehicle frame; the next follow tick takes over.
    final zoom =
        widget.drivingMode ? _navigationZoom(position.speedKmh) : _maxMapZoom;
    // In navigation the vehicle is intentionally rendered around 64% down
    // the viewport. Re-anchoring the GPS button must use the same camera
    // target, otherwise the marker briefly jumps to the center and then back
    // to the lower-third follow position.
    final target = widget.drivingMode
        ? _navigationCameraTarget(position, zoom)
        : _toMapLibreVehiclePoint(position);
    unawaited(controller.moveCamera(
      ml.CameraUpdate.newCameraPosition(
        ml.CameraPosition(
          target: target,
          zoom: zoom,
          bearing: widget.drivingMode ? position.headingDeg : 0,
          tilt: widget.drivingMode
              ? widget.cameraTiltDegrees.clamp(42.0, 55.0).toDouble()
              : 0,
        ),
      ),
    ));
  }

  void _focusDestination(LatLng destination) {
    final controller = _controller;
    if (controller == null) return;
    unawaited(
      controller.animateCamera(
        ml.CameraUpdate.newCameraPosition(
          ml.CameraPosition(
            target: _toMapLibrePoint(destination),
            zoom: (_maxMapZoom - 1).clamp(14.0, _maxMapZoom),
            bearing: 0,
            tilt: 0,
          ),
        ),
        duration: const Duration(milliseconds: 320),
      ),
    );
  }

  /// در ناوبری، خودرو نباید وسط صفحه قفل شود؛ باید در نیمهٔ پایین بماند
  /// و بخش بیشتری از مسیرِ جلوی راننده دیده شود، شبیه Google Maps/Waze.
  /// بنابراین مرکز دوربین چند ده متر در امتداد heading جلوتر از خودرو قرار
  /// می‌گیرد. این کار با tilt نیز پایدارتر از دستکاریِ مختصاتِ screen است.
  ml.LatLng _navigationCameraTarget(
    VehiclePosition position,
    double zoom,
  ) {
    // فاصلهٔ جلو با zoom کمی تغییر می‌کند تا در زوم نزدیک خودرو خیلی پایین
    // نیفتد و در سرعت بالا مسیرِ بیشتری در جلو قابل مشاهده باشد.
    // دوربین قبلاً 65 تا 100 متر جلوتر از خودرو قفل می‌شد. در نمای شیب‌دار
    // این مقدار خودرو را بیش از حد به پایین صفحه می‌برد و گاهی زیر لایه‌های
    // HUD قرار می‌داد. هدف باید فقط کمی جلوتر از خودرو باشد تا خودِ خودرو
    // همیشه داخل viewport و نزدیک یک‌سوم پایینی صفحه دیده شود.
    final forwardMeters = (18.0 +
            (17.8 - zoom) * 2.5 +
            position.speedKmh.clamp(0.0, 100.0) * 0.05)
        .clamp(14.0, 28.0)
        .toDouble();

    // در حالتِ ناوبری، مکان‌نمای خودرو روی صفحه ثابت است (نگاه کنید به
    // _refreshScreenPositions: fixedVehicle) و فقط این هدفِ دوربین است که
    // تعیین می‌کند کدام نقطهٔ جغرافیایی زیرِ آن مکان‌نمای ثابت قرار بگیرد.
    // قبلاً این هدف با امتداد خط‌راستِ heading فعلی محاسبه می‌شد؛ توی پیچ‌ها
    // این خط‌راست، وترِ پیچ را می‌برید نه کمانش را، پس دوربین (و مکان‌نمای
    // ثابتِ زیرش) از مسیرِ واقعاً رسم‌شده جدا می‌افتاد و خودرو انگار از جاده
    // بیرون می‌زد. حالا وقتی geometry مسیر در دسترس است، هدف با پیمایشِ
    // forwardMeters روی خودِ همان geometry به دست می‌آید تا کمانِ پیچ را
    // دنبال کند، نه وترش را.
    final route = widget.routeGeometry;
    if (route != null && route.length >= 2) {
      final ahead = _pointAheadOnRoute(
        LatLng(position.lat, position.lng),
        route,
        forwardMeters,
      );
      if (ahead != null) return _toMapLibrePoint(ahead);
    }

    // Fallback (بدون مسیر فعال، یا وقتی خودرو خیلی از geometry دور است):
    // امتدادِ خط‌راستِ heading، مثل قبل.
    final heading = (position.headingDeg.isFinite ? position.headingDeg : 0.0) *
        math.pi /
        180.0;
    const metersPerLatitude = 110540.0;
    final lat =
        position.lat + (math.cos(heading) * forwardMeters) / metersPerLatitude;
    final cosLat =
        math.cos(position.lat * math.pi / 180.0).abs().clamp(0.15, 1.0);
    final metersPerLongitude = 111320.0 * cosLat;
    final lng =
        position.lng + (math.sin(heading) * forwardMeters) / metersPerLongitude;
    return ml.LatLng(lat, lng);
  }

  /// نقطه‌ای [forwardMeters] جلوتر از [position] روی خودِ [geometry] (نه خط‌راستِ
  /// heading). ابتدا [position] روی نزدیک‌ترین قطعه projection می‌شود تا
  /// پیشرفتِ فعلی (متر از ابتدای مسیر) به دست آید، سپس همان مقدار جلوتر روی
  /// geometry پیمایش می‌شود. جست‌وجو حول آخرین قطعهٔ منطبق‌شده پنجره‌ای است
  /// (مثل _matchPositionToRoute در home_screen) تا برای مسیرهای طولانی هر
  /// فریم O(کل مسیر) نشود؛ اگر نتیجهٔ پنجره خیلی دور بود، یک‌بار کل مسیر را
  /// جست‌وجو می‌کند.
  LatLng? _pointAheadOnRoute(
    LatLng position,
    List<LatLng> geometry,
    double forwardMeters,
  ) {
    if (geometry.length < 2) return null;
    if (!identical(_navRouteGeometry, geometry)) {
      _navRouteGeometry = geometry;
      _navRouteCumulativeM = _buildCumulativeDistancesM(geometry);
      _navRouteLastSegment = null;
    }
    final cumulative = _navRouteCumulativeM!;
    final lastSegmentCount = geometry.length - 2;

    const backWindowM = 60.0;
    const aheadWindowM = 300.0;
    var startIdx = 0;
    var endIdx = lastSegmentCount;
    final lastIdx = _navRouteLastSegment;
    if (lastIdx != null && lastIdx >= 0 && lastIdx <= lastSegmentCount) {
      final lastProgress = cumulative[lastIdx];
      final lo = lastProgress - backWindowM;
      final hi = lastProgress + aheadWindowM;
      var s = lastIdx;
      while (s > 0 && cumulative[s] > lo) s--;
      var e = lastIdx;
      while (e < lastSegmentCount && cumulative[e] < hi) e++;
      startIdx = s;
      endIdx = e;
    }

    var match = _bestRouteSegment(position, geometry, startIdx, endIdx);
    if (match.distanceMeters > 45 &&
        (startIdx > 0 || endIdx < lastSegmentCount)) {
      match = _bestRouteSegment(position, geometry, 0, lastSegmentCount);
    }
    if (match.distanceMeters > 80) {
      // خودرو خیلی از این geometry دور است (مثلاً هنوز به مسیر نرسیده)؛
      // امتدادِ خط‌راستِ heading قابل‌اعتمادتر از چسباندنِ زوری به مسیر است.
      return null;
    }

    _navRouteLastSegment = match.segmentIndex;
    final segLen =
        cumulative[match.segmentIndex + 1] - cumulative[match.segmentIndex];
    final progressM = cumulative[match.segmentIndex] + segLen * match.t;
    return _pointAtRouteDistanceM(
        geometry, cumulative, progressM + forwardMeters);
  }

  ({int segmentIndex, double t, double distanceMeters}) _bestRouteSegment(
    LatLng position,
    List<LatLng> geometry,
    int startIdx,
    int endIdx,
  ) {
    var bestDistance = double.infinity;
    var bestIndex = startIdx;
    var bestT = 0.0;
    for (var i = startIdx; i <= endIdx; i++) {
      final projection =
          _projectOnRouteSegment(position, geometry[i], geometry[i + 1]);
      if (projection.distanceMeters < bestDistance) {
        bestDistance = projection.distanceMeters;
        bestIndex = i;
        bestT = projection.t;
      }
    }
    return (segmentIndex: bestIndex, t: bestT, distanceMeters: bestDistance);
  }

  ({double distanceMeters, double t}) _projectOnRouteSegment(
    LatLng point,
    LatLng a,
    LatLng b,
  ) {
    final latRad = point.latitude * math.pi / 180.0;
    final mx = 111320.0 * math.cos(latRad);
    const my = 110540.0;
    final abX = (b.longitude - a.longitude) * mx;
    final abY = (b.latitude - a.latitude) * my;
    final apX = (point.longitude - a.longitude) * mx;
    final apY = (point.latitude - a.latitude) * my;
    final lengthSquared = abX * abX + abY * abY;
    if (lengthSquared <= 1e-6) {
      return (distanceMeters: math.sqrt(apX * apX + apY * apY), t: 0.0);
    }
    final t = ((apX * abX + apY * abY) / lengthSquared).clamp(0.0, 1.0);
    final nearestX = abX * t;
    final nearestY = abY * t;
    final dx = apX - nearestX;
    final dy = apY - nearestY;
    return (distanceMeters: math.sqrt(dx * dx + dy * dy), t: t);
  }

  List<double> _buildCumulativeDistancesM(List<LatLng> geometry) {
    final cumulative = List<double>.filled(geometry.length, 0);
    for (var i = 1; i < geometry.length; i++) {
      cumulative[i] =
          cumulative[i - 1] + _distanceBetweenM(geometry[i - 1], geometry[i]);
    }
    return cumulative;
  }

  LatLng _pointAtRouteDistanceM(
    List<LatLng> geometry,
    List<double> cumulative,
    double meters,
  ) {
    final total = cumulative.last;
    final target = meters.clamp(0.0, total);
    var lo = 0;
    var hi = cumulative.length - 1;
    while (lo < hi - 1) {
      final mid = (lo + hi) >> 1;
      if (cumulative[mid] <= target) {
        lo = mid;
      } else {
        hi = mid;
      }
    }
    final a = geometry[lo];
    final b = geometry[hi];
    final segLen = cumulative[hi] - cumulative[lo];
    final t = segLen <= 0.0001
        ? 0.0
        : ((target - cumulative[lo]) / segLen).clamp(0.0, 1.0);
    return LatLng(
      a.latitude + (b.latitude - a.latitude) * t,
      a.longitude + (b.longitude - a.longitude) * t,
    );
  }

  double _distanceBetweenM(LatLng a, LatLng b) {
    final latRad = ((a.latitude + b.latitude) / 2) * math.pi / 180.0;
    final mx = 111320.0 * math.cos(latRad);
    const my = 110540.0;
    final dx = (b.longitude - a.longitude) * mx;
    final dy = (b.latitude - a.latitude) * my;
    return math.sqrt(dx * dx + dy * dy);
  }

  void _syncCamera({bool force = false}) {
    final controller = _controller;
    final position = widget.vehiclePosition;
    if (controller == null || position == null || !widget.followVehicle) {
      return;
    }
    final now = DateTime.now();
    if (!force && now.difference(_lastCameraUpdate) < _cameraUpdateInterval) {
      return;
    }
    _lastCameraUpdate = now;

    final speed = position.speedKmh.clamp(0.0, 160.0).toDouble();
    final zoom = _navigationZoom(speed);
    final camera = ml.CameraPosition(
      target: _navigationCameraTarget(position, zoom),
      zoom: widget.drivingMode ? zoom : math.max(zoom - 1.2, 14.5),
      bearing: position.headingDeg.isFinite ? position.headingDeg : 0,
      tilt: widget.drivingMode
          ? widget.cameraTiltDegrees.clamp(42.0, 55.0).toDouble()
          : widget.cameraTiltDegrees.clamp(0.0, 60.0).toDouble(),
    );

    // Coalesce native camera commands. Never let several moveCamera calls
    // execute out of order; the newest GPS frame always wins.
    _pendingCameraPosition = camera;
    if (_cameraMoveRunning) return;
    _cameraMoveRunning = true;
    unawaited(_drainCameraMoves(controller));
  }

  Future<void> _drainCameraMoves(ml.MapLibreMapController controller) async {
    try {
      while (mounted && controller == _controller && widget.followVehicle) {
        final camera = _pendingCameraPosition;
        _pendingCameraPosition = null;
        if (camera == null) break;
        try {
          await controller.moveCamera(
            ml.CameraUpdate.newCameraPosition(camera),
          );
        } catch (_) {
          break;
        }
      }
    } finally {
      _cameraMoveRunning = false;
      // A GPS frame may have arrived between the final read and releasing the
      // lock. Consume it once, rather than starting another native queue.
      if (_pendingCameraPosition != null &&
          mounted &&
          controller == _controller &&
          widget.followVehicle) {
        _cameraMoveRunning = true;
        unawaited(_drainCameraMoves(controller));
      }
    }
  }

  double _navigationZoom(double speedKmh) {
    // بازه با درنظر گرفتن maxZoom=18: در سرعت پایین تا 17.5 (نمای خیابانی)
    // و در سرعت بالا به 15.4 نرم می‌رسد. کاربر همچنان می‌تواند با gesture
    // تا 18 zoom کند.
    if (speedKmh < 15) return 17.5;
    if (speedKmh < 40) return 17.0;
    if (speedKmh < 70) return 16.4;
    if (speedKmh < 100) return 15.8;
    return 15.4;
  }

  void _onCameraMove(ml.CameraPosition camera) {
    _camera = camera;
    widget.onCameraPositionChanged?.call(camera);
    unawaited(_refreshScreenPositions());
  }

  Future<void> _refreshScreenPositions() async {
    final requestGeneration = ++_screenUpdateGeneration;

    // In active follow-navigation the vehicle is intentionally anchored in a
    // stable screen position. Projecting it through MapLibre on every native
    // camera callback introduces async stale-frame jitter (old projections can
    // arrive after a newer camera frame). The destination still needs native
    // projection, so only the vehicle projection is skipped.
    final fixedVehicle = widget.followVehicle && widget.drivingMode;
    if (fixedVehicle && mounted) {
      final size = MediaQuery.sizeOf(context);
      setState(() {
        _vehicleScreen = Offset(size.width * 0.5, size.height * 0.66);
      });
    }

    if (_screenUpdateRunning) {
      _screenUpdateQueued = true;
      return;
    }
    final controller = _controller;
    if (controller == null) return;
    _screenUpdateRunning = true;
    try {
      final position = widget.vehiclePosition;
      final vehiclePoint = fixedVehicle || position == null
          ? null
          : await controller
              .toScreenLocation(_toMapLibreVehiclePoint(position));
      final destination = widget.destination;
      final destinationPoint = destination == null
          ? null
          : await controller.toScreenLocation(_toMapLibrePoint(destination));

      // A projection belongs to the camera frame that requested it. Discard
      // it if a newer camera/GPS frame has already been requested.
      if (requestGeneration != _screenUpdateGeneration ||
          !mounted ||
          controller != _controller) {
        return;
      }

      final pixelRatio = MediaQuery.devicePixelRatioOf(context);
      setState(() {
        if (!fixedVehicle) {
          _vehicleScreen = vehiclePoint == null
              ? null
              : mapScreenPointToFlutterOffset(vehiclePoint, pixelRatio);
        }
        _destinationScreen = destinationPoint == null
            ? null
            : mapScreenPointToFlutterOffset(destinationPoint, pixelRatio);
      });
    } catch (_) {
      // During style replacement projection may temporarily be unavailable.
    } finally {
      _screenUpdateRunning = false;
      if (_screenUpdateQueued) {
        _screenUpdateQueued = false;
        unawaited(_refreshScreenPositions());
      }
    }
  }

  void _onMapClick(math.Point<double> _, ml.LatLng point) {
    final tap = LatLng(point.latitude, point.longitude);
    final routeIndex = _hitTestRoute(tap, _routeOverlays);
    if (routeIndex != null) {
      widget.onRouteTap?.call(routeIndex);
    }
  }

  void _onMapLongClick(math.Point<double> _, ml.LatLng point) {
    widget.onLongPress?.call(LatLng(point.latitude, point.longitude));
  }

  int? _hitTestRoute(LatLng tap, List<OnlineRouteOverlay> overlays) {
    const hitRadiusMeters = 30.0;
    var bestDistance = hitRadiusMeters;
    int? bestIndex;
    for (var routeIndex = 0; routeIndex < overlays.length; routeIndex++) {
      final geometry = overlays[routeIndex].geometry;
      for (var pointIndex = 1; pointIndex < geometry.length; pointIndex++) {
        final distance = _distanceToSegmentMeters(
          tap,
          geometry[pointIndex - 1],
          geometry[pointIndex],
        );
        if (distance <= bestDistance) {
          bestDistance = distance;
          bestIndex = routeIndex;
        }
      }
    }
    return bestIndex;
  }

  double _distanceToSegmentMeters(LatLng point, LatLng start, LatLng end) {
    final latitudeRadians = point.latitude * math.pi / 180.0;
    final metersPerLongitude = 111320.0 * math.cos(latitudeRadians);
    final abX = (end.longitude - start.longitude) * metersPerLongitude;
    final abY = (end.latitude - start.latitude) * 110540.0;
    final apX = (point.longitude - start.longitude) * metersPerLongitude;
    final apY = (point.latitude - start.latitude) * 110540.0;
    final lengthSquared = abX * abX + abY * abY;
    if (lengthSquared <= 1e-6) return math.sqrt(apX * apX + apY * apY);
    final projection =
        ((apX * abX + apY * abY) / lengthSquared).clamp(0.0, 1.0);
    final nearestX = abX * projection;
    final nearestY = abY * projection;
    final dx = apX - nearestX;
    final dy = apY - nearestY;
    return math.sqrt(dx * dx + dy * dy);
  }

  double get _markerVisualSize {
    // Keep the map anchor box independent from the car-size preference.
    // The 3D model itself is scaled inside this fixed box.
    if (widget.showCarModel) return 72.0;
    return (40.0 * (widget.pinSizePercent / 100)).clamp(30.0, 82.0).toDouble();
  }

  double _effectiveVehicleHeading(VehiclePosition position) {
    final route = widget.routeGeometry;
    // در سرعت کم، GPS معمولاً heading صفر/نویزدار می‌دهد. در حالت ناوبری
    // جهت نزدیک‌ترین قطعهٔ مسیر پایدارتر است و خودرو روی خط عمودی نمی‌ماند.
    if (route == null || route.length < 2 || position.speedKmh >= 3) {
      return position.headingDeg;
    }
    var bestDistance = double.infinity;
    var bestHeading = position.headingDeg;
    final point = LatLng(position.lat, position.lng);
    for (var i = 0; i < route.length - 1; i++) {
      final distance = _distanceToSegmentMeters(point, route[i], route[i + 1]);
      if (distance < bestDistance) {
        bestDistance = distance;
        bestHeading = _bearingBetween(route[i], route[i + 1]);
      }
    }
    return bestHeading;
  }

  double _bearingBetween(LatLng a, LatLng b) {
    final y = (b.longitude - a.longitude) *
        math.cos((a.latitude + b.latitude) * math.pi / 360.0);
    final x = b.latitude - a.latitude;
    return (math.atan2(y, x) * 180.0 / math.pi + 360.0) % 360.0;
  }

  @override
  Widget build(BuildContext context) {
    final vehiclePosition = _vehicleScreen;
    final destinationPosition = _destinationScreen;
    final markerSize = _markerVisualSize;
    final mapBearing = _camera?.bearing ?? 0;
    // tilt واقعیِ MapLibre مرجع اصلی مدل است؛ نه فقط مقدار تنظیمات اولیه.
    // به این ترتیب اگر کاربر نقشه را با gesture از 2D به هر زاویه‌ای ببرد،
    // نمای خودرو در همان فریم به پرسپکتیؤ نقشه نزدیک می‌شود.
    final actualMapTilt =
        (_camera?.tilt ?? widget.cameraTiltDegrees).clamp(0.0, 60.0).toDouble();
    final effectiveCarCameraAngle = math
        .max(
          widget.carCameraAngleDegrees.clamp(0.0, 90.0),
          (actualMapTilt * 1.5).clamp(0.0, 90.0),
        )
        .toDouble();
    // asset پیکان در حالت پایه رو به بالای صفحه (شمال) است؛ بنابراین تنها
    // چرخش لازم، اختلاف heading جغرافیایی با bearing فعلی نقشه است. offset
    // قبلیِ -90 باعث می‌شد مکان‌نما یک ربع‌گردش از مسیر واقعی منحرف باشد.
    final geographicHeading = widget.vehiclePosition == null
        ? 0.0
        : _effectiveVehicleHeading(widget.vehiclePosition!);
    final screenHeading = mapRelativeHeading(geographicHeading, mapBearing);

    return Listener(
      behavior: HitTestBehavior.translucent,
      onPointerDown: (_) => widget.onUserGestureStart?.call(),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          ml.MapLibreMap(
            key: ValueKey(
              'maplibre-${widget.localStylePath ?? (widget.isDark ? 'online-night' : 'online-day')}',
            ),
            styleString: widget.localStylePath ??
                (widget.isDark ? _nightStyle : _dayStyle),
            initialCameraPosition: ml.CameraPosition(
              target: widget.vehiclePosition == null
                  ? _fallbackInitialTarget
                  : _toMapLibreVehiclePoint(widget.vehiclePosition!),
              zoom: widget.vehiclePosition == null
                  ? 5.1
                  : (widget.drivingMode ? 16 : 14.5),
              bearing: widget.vehiclePosition?.headingDeg ?? 0,
              tilt: widget.drivingMode
                  ? widget.cameraTiltDegrees.clamp(42.0, 55.0).toDouble()
                  : widget.cameraTiltDegrees.clamp(0.0, 60.0).toDouble(),
            ),
            minMaxZoomPreference:
                ml.MinMaxZoomPreference(_minMapZoom, _maxMapZoom),
            compassEnabled: false,
            myLocationEnabled: false,
            myLocationTrackingMode: ml.MyLocationTrackingMode.none,
            logoEnabled: false,
            scaleControlEnabled: false,
            rotateGesturesEnabled: true,
            scrollGesturesEnabled: true,
            zoomGesturesEnabled: true,
            tiltGesturesEnabled: true,
            trackCameraPosition: true,
            annotationOrder: const [ml.AnnotationType.line],
            annotationConsumeTapEvents: const [ml.AnnotationType.line],
            foregroundLoadColor: widget.palette.background,
            onMapCreated: _onMapCreated,
            onStyleLoadedCallback: _onStyleLoaded,
            onMapClick: _onMapClick,
            onMapLongClick: _onMapLongClick,
            onCameraMove: _onCameraMove,
            onCameraIdle: () {
              unawaited(_refreshScreenPositions());
              widget.onCameraIdle?.call();
            },
          ),
          if (destinationPosition != null)
            Positioned(
              left: destinationPosition.dx - 21,
              top: destinationPosition.dy - 42,
              child: const IgnorePointer(
                child: Icon(
                  Icons.location_on_rounded,
                  color: Color(0xFFE84A5F),
                  size: 42,
                  shadows: [Shadow(color: Colors.black54, blurRadius: 5)],
                ),
              ),
            ),
          if (vehiclePosition != null)
            Positioned(
              left: vehiclePosition.dx - markerSize / 2,
              // vehiclePosition is the projected map coordinate of the wheel
              // contact point. The model is anchored at that point in both 2D
              // and tilted map modes; its internal camera follows the actual
              // MapLibre pitch, so changing the map angle does not leave the
              // car visually behind/in front of the road.
              top: vehiclePosition.dy - markerSize * 0.50,
              width: markerSize,
              height: markerSize,
              child: IgnorePointer(
                child: widget.showCarModel
                    ? Transform(
                        alignment: Alignment.bottomCenter,
                        transform: Matrix4.identity()
                          ..setEntry(3, 2, 0.0007)
                          ..rotateX(-actualMapTilt * math.pi / 180.0 * 0.22),
                        child: CarMarker3D(
                          size: markerSize,
                          modelIndex: widget.modelIndex,
                          headingDeg: screenHeading,
                          cameraAngleDegrees: effectiveCarCameraAngle,
                          sizePercent: widget.carSizePercent,
                          interactive: false,
                        ),
                      )
                    : Stack(
                        alignment: Alignment.center,
                        children: [
                          Transform.rotate(
                            angle: screenHeading * math.pi / 180,
                            child: NavArrow(
                              size: markerSize,
                              color: widget.markerColor,
                              glow: widget.pinShadowEnabled,
                            ),
                          ),
                        ],
                      ),
              ),
            ),
        ],
      ),
    );
  }
}
