import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import '../../../core/permissions/location_permission_flow.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/deep_link/deep_link_service.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/glass_notice.dart';
import '../../gps/presentation/gps_providers.dart';
import '../../gps/presentation/vehicle_position_animator.dart';
import '../../gps/data/location_service.dart';
import '../../vehicle/presentation/vehicle_marker.dart';
import '../../vehicle/presentation/vehicle_provider.dart';
import '../../routing/presentation/routing_providers.dart';
import '../../routing/data/routing_service.dart';
import '../../voice_settings/presentation/tts_providers.dart';
import '../../voice_settings/data/voice_pack_fa.dart';
import 'destination_provider.dart';
import 'dart:async';
import 'dart:math' as math;
import 'dart:ui';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  MapLibreMapController? _mapController;
  bool _cameraFollowsVehicle = true;
  bool _arrivalHandled = false;
  int _lastSpokenInstructionIndex = -1;
  Line? _routeLine;

  // --- تشخیص انحراف از مسیر و مسیریابی مجدد خودکار ---
  // نکته‌ی مهم (رفع باگ «اگه مسیر اشتباه بری مسیریابی مجدد انجام نمی‌شه»):
  // قبلاً هیچ کدی چک نمی‌کرد که آیا خودرو روی خط مسیرِ فعلی هست یا نه؛
  // _updateNavigationProgress فقط نزدیک‌ترین دستورالعمل را پیدا می‌کرد، ولی
  // اگر کاربر مسیر را عوض می‌کرد، مسیر رسم‌شده و دستورالعمل‌ها همان‌جای
  // قدیمی می‌ماندند. الان فاصله‌ی خودرو تا خط مسیر هر ۲۰۰ میلی‌ثانیه چک
  // می‌شود؛ چند بار پیاپیِ بیش از حد آستانه (برای فیلتر نویز GPS) باعث
  // محاسبه‌ی خودکار یک مسیر تازه از موقعیت فعلی می‌شود.
  int _offRouteStrikeCount = 0;
  bool _isRerouting = false;
  DateTime? _lastRerouteAt;

  bool _styleLoaded = false;
  bool _showMapRetry = false;
  Timer? _mapLoadTimeoutTimer;
  int _mapReloadKey = 0;

  static const String _demoStyleUrl =
      'https://tiles.openfreemap.org/styles/dark';

  static const CameraPosition _initialCamera = CameraPosition(
    target: LatLng(35.6997, 51.3380),
    zoom: 16,
    tilt: 55,
    bearing: 0,
  );

  void _startMapLoadWatchdog() {
    _mapLoadTimeoutTimer?.cancel();
    _showMapRetry = false;
    _mapLoadTimeoutTimer = Timer(const Duration(seconds: 20), () {
      if (mounted && !_styleLoaded) {
        setState(() => _showMapRetry = true);
      }
    });
  }

  void _retryMapLoad() {
    setState(() {
      _styleLoaded = false;
      _showMapRetry = false;
      _mapReloadKey++;
    });
    _startMapLoadWatchdog();
  }

  @override
  void initState() {
    super.initState();
    _startMapLoadWatchdog();
  }

  @override
  Widget build(BuildContext context) {
    final readiness = ref.watch(locationReadinessProvider);
    final vehiclePositionAsync = ref.watch(animatedVehiclePositionProvider);
    final selectedVehicle = ref.watch(selectedVehicleProvider);
    final destination = ref.watch(selectedDestinationProvider);
    final activeNav = ref.watch(activeNavigationProvider);

    ref.listen<AsyncValue<DeepLinkDestination>>(deepLinkDestinationProvider, (prev, next) {
      next.whenData((dest) {
        final point = LatLng(dest.lat, dest.lng);
        ref.read(selectedDestinationProvider.notifier).state =
            SelectedDestination(point, label: dest.label);
        _mapController?.animateCamera(CameraUpdate.newLatLngZoom(point, 15));
        setState(() => _cameraFollowsVehicle = false);
      });
    });

    // نرخِ خامِ GPS برای پیشرفتِ مسیریابی — کافیه و از اجرای حلقه‌ی
    // تطبیقِ دستورالعمل‌ها و چکِ پیامِ صوتی با نرخِ ۶۰fps جلوگیری می‌کند.
    ref.listen<AsyncValue<VehiclePosition>>(vehiclePositionProvider, (prev, next) {
      next.whenData((pos) {
        if (activeNav != null) {
          _updateNavigationProgress(pos, activeNav);
        }
      });
    });

    // نرخِ نرمِ ۶۰fps (درون‌یابی‌شده) فقط برای حرکتِ دوربین — تا پن/چرخشِ
    // نقشه پیوسته باشد و هر ۱-۲ ثانیه (نرخِ فیکسِ خامِ GPS) نپرد.
    ref.listen<AsyncValue<VehiclePosition>>(animatedVehiclePositionProvider, (prev, next) {
      next.whenData((pos) {
        if (_cameraFollowsVehicle && _mapController != null) {
          _mapController!.moveCamera(
            CameraUpdate.newCameraPosition(
              CameraPosition(
                target: LatLng(pos.lat, pos.lng),
                zoom: 17,
                tilt: 55,
                bearing: pos.headingDeg,
              ),
            ),
          );
        }
      });
    });

    final canPopHome = destination == null && activeNav == null;

    return PopScope(
      canPop: canPopHome,
      onPopInvoked: (didPop) {
        if (didPop) return;
        if (activeNav != null) {
          _stopNavigation();
        } else if (destination != null) {
          ref.read(selectedDestinationProvider.notifier).state = null;
        }
      },
      child: Scaffold(
        backgroundColor: AppColors.frameBackground,
        body: Stack(
          children: [
          Positioned.fill(
            child: Listener(
              onPointerDown: (_) => _takeManualCameraControl(),
              child: MapLibreMap(
                key: ValueKey('map-$_mapReloadKey'),
                styleString: _demoStyleUrl,
                initialCameraPosition: _initialCamera,
                myLocationEnabled: false,
                compassEnabled: false,
                rotateGesturesEnabled: true,
                scrollGesturesEnabled: true,
                tiltGesturesEnabled: _cameraFollowsVehicle,
                zoomGesturesEnabled: true,
                onMapCreated: _onMapCreated,
                onMapLongClick: (point, latLng) {
                  ref.read(selectedDestinationProvider.notifier).state =
                      SelectedDestination(latLng);
                  _takeManualCameraControl();
                },
                onCameraTrackingDismissed: _takeManualCameraControl,
                onStyleLoadedCallback: () {
                  _mapLoadTimeoutTimer?.cancel();
                  if (mounted) setState(() { _styleLoaded = true; _showMapRetry = false; });
                },
              ),
            ),
          ),

          if (_showMapRetry && !_styleLoaded)
            Positioned(
              top: MediaQuery.of(context).padding.top + 5 +
                  (activeNav != null
                      ? 118
                      : (destination != null
                          ? 108
                          : (readiness.valueOrNull != null &&
                                  readiness.valueOrNull != LocationReadiness.ready
                              ? 64
                              : 12))),
              left: 24,
              right: 24,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: const Color(0xCC14171F),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Colors.white.withOpacity(.12)),
                      boxShadow: const [
                        BoxShadow(color: Colors.black45, blurRadius: 16, offset: Offset(0, 6)),
                      ],
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.cloud_off_rounded, color: Colors.white70, size: 16),
                        const SizedBox(width: 8),
                        const Expanded(
                          child: Text(
                            'اتصال نقشه کند است…',
                            style: TextStyle(color: Colors.white, fontSize: 12),
                          ),
                        ),
                        GestureDetector(
                          onTap: _retryMapLoad,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            decoration: BoxDecoration(
                              gradient: AppColors.subAccentGradient,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: const Text(
                              'تلاش دوباره',
                              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),

          Builder(
            builder: (_) {
              final pos = vehiclePositionAsync.valueOrNull;
              final markerPos =
                  pos != null ? LatLng(pos.lat, pos.lng) : _initialCamera.target;
              return VehicleMarker(
                mapController: _mapController,
                position: markerPos,
                headingDeg: pos?.headingDeg ?? 0,
                vehicle: selectedVehicle,
                followsCamera: _cameraFollowsVehicle,
              );
            },
          ),

          if (destination != null)
            _DestinationPin(mapController: _mapController, point: destination.point),

          Positioned(
            top: MediaQuery.of(context).padding.top + 5 +
                (activeNav != null
                    ? 118
                    : (destination != null ? 108 : 12)),
            left: 24,
            right: 24,
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              transitionBuilder: (child, anim) => FadeTransition(
                opacity: anim,
                child: SlideTransition(
                  position: Tween<Offset>(
                    begin: const Offset(0, -0.3),
                    end: Offset.zero,
                  ).animate(anim),
                  child: child,
                ),
              ),
              child: readiness.when(
                data: (state) => state == LocationReadiness.ready
                    ? const SizedBox.shrink(key: ValueKey('gps-ok'))
                    : _GpsWarningBanner(key: ValueKey('gps-$state'), state: state),
                loading: () => const SizedBox.shrink(key: ValueKey('gps-loading')),
                error: (_, __) => const SizedBox.shrink(key: ValueKey('gps-error')),
              ),
            ),
          ),

          if (destination != null && activeNav == null)
            Positioned(
              top: MediaQuery.of(context).padding.top + 10,
              left: 16,
              right: 16,
              child: _DestinationCard(
                destination: destination,
                onClear: () {
                  ref.read(selectedDestinationProvider.notifier).state = null;
                  _clearRoute();
                },
                onStartNavigation: () => _startNavigation(),
              ),
            ),

          Positioned(
            top: 190,
            right: 16,
            child: _Compass(headingDeg: vehiclePositionAsync.valueOrNull?.headingDeg ?? 0),
          ),

          Positioned(
            bottom: 130,
            right: 16,
            child: _RoundIconButton(
              icon: Icons.my_location_rounded,
              onTap: () {
                setState(() => _cameraFollowsVehicle = true);
                final pos = vehiclePositionAsync.valueOrNull;
                if (pos != null) {
                  _mapController?.animateCamera(CameraUpdate.newCameraPosition(
                    CameraPosition(target: LatLng(pos.lat, pos.lng), zoom: 17, tilt: 55, bearing: pos.headingDeg),
                  ));
                } else {
                  _mapController?.animateCamera(CameraUpdate.newCameraPosition(_initialCamera));
                }
              },
            ),
          ),

          Positioned(
            bottom: 90,
            left: 16,
            child: _SpeedCluster(
              speedKmh: vehiclePositionAsync.valueOrNull?.speedKmh ?? 0,
              speedLimitKmh: null,
            ),
          ),

          const BottomNav(currentPage: NavKey.home, isHomePage: true),

          if (activeNav != null)
            Positioned(
              top: MediaQuery.of(context).padding.top + 10,
              left: 16,
              right: 16,
              child: _ActiveNavigationCard(
                navigation: activeNav,
                onClose: () => _stopNavigation(),
              ),
            ),
        ],
        ),
      ),
    );
  }

  void _onMapCreated(MapLibreMapController controller) {
    _mapController = controller;
    controller.addListener(_onCameraMoved);
    if (mounted) setState(() {});
  }

  void _onCameraMoved() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _mapController?.removeListener(_onCameraMoved);
    _mapLoadTimeoutTimer?.cancel();
    super.dispose();
  }

  void _showGlassNotice(
    String message, {
    required IconData icon,
    required List<Color> colors,
    Duration duration = const Duration(seconds: 3),
  }) {
    if (!mounted) return;
    showGlassNotice(context, message, icon: icon, colors: colors, duration: duration);
  }

  Future<void> _startNavigation() async {
    final destination = ref.read(selectedDestinationProvider);
    final vehiclePosition = ref.read(vehiclePositionProvider).value;

    if (destination == null || vehiclePosition == null) return;
    _arrivalHandled = false;
    _offRouteStrikeCount = 0;

    final origin = LatLng(vehiclePosition.lat, vehiclePosition.lng);
    final route = await _computeRouteWithFallback(origin, destination.point);

    await _drawRoute(route.geometry);

    ref.read(activeNavigationProvider.notifier).setNavigation(
      ActiveNavigation(
        route: route,
        state: NavigationState.navigating,
        remainingDistanceKm: route.distanceKm,
      ),
    );

    _lastSpokenInstructionIndex = -1;
    if (route.instructions.isNotEmpty && ref.read(ttEnabledProvider)) {
      _lastSpokenInstructionIndex = 0;
      final first = route.instructions.first;
      final voice = ref.read(ttsServiceProvider)
        ..setVolume(ref.read(ttsVolumeProvider))
        ..setPlaybackRate(ref.read(ttsRateProvider));
      voice.playSequence(VoicePackFa.forManeuver(
        type: first.type,
        modifier: first.modifier,
        exit: first.exit,
      ));
    }

    setState(() => _cameraFollowsVehicle = true);
  }

  /// محاسبه‌ی مسیر با زنجیره‌ی fallback (آنلاین → گراف آفلاین استان →
  /// خط‌راست تقریبی) — از _startNavigation و _rerouteOffPath هر دو استفاده
  /// می‌شود تا منطق یکی باشد و رفتار مسیریابی مجدد دقیقاً مثل مسیریابی اولیه
  /// قابل‌اعتماد باشد.
  Future<RouteInfo> _computeRouteWithFallback(LatLng origin, LatLng destination) async {
    final routingService = ref.read(routingServiceProvider);
    var route = await routingService.calculateRoute(origin: origin, destination: destination);

    String? offlineFailReason;
    if (route == null) {
      final graphStore = ref.read(offlineGraphStoreProvider);
      final province = graphStore.provinceContaining(origin.latitude, origin.longitude);
      if (province != null) {
        final graph = await graphStore.loadProvince(province.id);
        if (graph != null) {
          final offlineService = ref.read(offlineRoutingServiceProvider);
          route = offlineService.calculateRoute(
            graph: graph,
            origin: origin,
            destination: destination,
          );
          offlineFailReason = offlineService.lastError;
        }
      }
    }

    if (route == null) {
      route = routingService.straightLineFallback(origin, destination);
      final reason = offlineFailReason ?? routingService.lastError;
      _showGlassNotice(
        reason == null
            ? 'اتصال به سرور مسیریابی برقرار نشد؛ مسیر تقریبی آفلاین نمایش داده می‌شود.'
            : 'مسیریابی ناموفق: $reason\nمسیر تقریبی آفلاین نمایش داده می‌شود.',
        icon: Icons.cloud_off_rounded,
        colors: const [Color(0xFFFFB74D), Color(0xFFE5834B)],
        duration: reason == null ? const Duration(seconds: 3) : const Duration(seconds: 7),
      );
    } else if (offlineFailReason == null && routingService.lastError != null) {
      _showGlassNotice(
        'بدون اینترنت — مسیر از نقشه‌ی آفلاین دانلودشده محاسبه شد.',
        icon: Icons.offline_pin_rounded,
        colors: const [AppColors.homeAccent, AppColors.subAccentA],
        duration: const Duration(seconds: 4),
      );
    }

    return route;
  }

  /// وقتی خودرو مدتی پیوسته از خط مسیر فاصله‌ی زیادی داشته باشد (یعنی
  /// کاربر پیچ اشتباه رفته یا مسیر دیگری را انتخاب کرده)، این متد از
  /// موقعیت فعلی تا همان مقصد یک مسیر تازه محاسبه، رسم، و جایگزین مسیر قبلی
  /// می‌کند و راهنمای صوتی را هم از دستورالعمل اول مسیر جدید ادامه می‌دهد.
  ///
  /// نکته‌ی مهم: VoicePackFa از قبل یک متد offRoute() با فایل صوتی اختصاصیِ
  /// off_route.ogg داشت (هم در پک زن و هم مرد) که تا الان به هیچ‌جا وصل
  /// نبود — یعنی این قابلیت از اول با صدا طراحی شده بود ولی خودِ منطق
  /// تشخیص انحراف هیچ‌وقت نوشته/وصل نشده بود.
  Future<void> _rerouteOffPath(double deviationMeters) async {
    if (_isRerouting) return;
    final destination = ref.read(selectedDestinationProvider);
    final vehiclePosition = ref.read(vehiclePositionProvider).value;
    if (destination == null || vehiclePosition == null) return;

    _isRerouting = true;
    _offRouteStrikeCount = 0;
    _lastRerouteAt = DateTime.now();

    _showGlassNotice(
      'از مسیر منحرف شدید؛ در حال محاسبه‌ی مسیر جدید...',
      icon: Icons.alt_route_rounded,
      colors: const [AppColors.homeAccent, AppColors.subAccentA],
      duration: const Duration(seconds: 3),
    );

    if (ref.read(ttEnabledProvider)) {
      final voice = ref.read(ttsServiceProvider)
        ..setVolume(ref.read(ttsVolumeProvider))
        ..setPlaybackRate(ref.read(ttsRateProvider));
      // بدون await عمداً: نباید صدای «از مسیر خارج شدید» جلوی محاسبه‌ی
      // مسیر جدید (که خودش چند صدم ثانیه تا چند ثانیه طول می‌کشد) را
      // بگیرد؛ هر دو به‌صورت موازی پیش می‌روند.
      voice.playSequence(VoicePackFa.offRoute(deviationMeters));
    }

    try {
      final origin = LatLng(vehiclePosition.lat, vehiclePosition.lng);
      final route = await _computeRouteWithFallback(origin, destination.point);

      // ممکن است حین محاسبه (که async است) کاربر ناوبری را متوقف کرده
      // باشد؛ در آن صورت این نتیجه‌ی دیرهنگام را دور می‌ریزیم.
      if (!mounted || ref.read(activeNavigationProvider) == null) return;

      await _drawRoute(route.geometry);

      ref.read(activeNavigationProvider.notifier).setNavigation(
        ActiveNavigation(
          route: route,
          state: NavigationState.navigating,
          remainingDistanceKm: route.distanceKm,
        ),
      );

      _arrivalHandled = false;
      _lastSpokenInstructionIndex = -1;
      if (route.instructions.isNotEmpty && ref.read(ttEnabledProvider)) {
        _lastSpokenInstructionIndex = 0;
        final first = route.instructions.first;
        final voice = ref.read(ttsServiceProvider)
          ..setVolume(ref.read(ttsVolumeProvider))
          ..setPlaybackRate(ref.read(ttsRateProvider));
        // «مسیر محاسبه شد» قبل از دستورالعملِ اولِ مسیر تازه، تا کاربر
        // بفهمد این یک مسیر جدید است نه ادامه‌ی همان قبلی.
        voice.playSequence([
          'route_calculate.ogg',
          ...VoicePackFa.forManeuver(
            type: first.type,
            modifier: first.modifier,
            exit: first.exit,
          ),
        ]);
      }
    } finally {
      _isRerouting = false;
    }
  }

  Future<void> _drawRoute(List<LatLng> geometry) async {
    if (_mapController == null) return;

    if (_routeLine != null) {
      await _mapController!.removeLine(_routeLine!);
    }

    _routeLine = await _mapController!.addLine(
      LineOptions(
        geometry: geometry,
        lineColor: '#10D15C',
        lineWidth: 6.0,
        lineOpacity: 0.85,
      ),
    );
  }

  Future<void> _clearRoute() async {
    if (_mapController != null && _routeLine != null) {
      await _mapController!.removeLine(_routeLine!);
      _routeLine = null;
    }
  }

  void _takeManualCameraControl() {
    if (!_cameraFollowsVehicle) return;
    setState(() => _cameraFollowsVehicle = false);
    final pos = ref.read(vehiclePositionProvider).value;
    if (_mapController != null && pos != null) {
      _mapController!.moveCamera(
        CameraUpdate.newCameraPosition(
          CameraPosition(target: LatLng(pos.lat, pos.lng), zoom: 17, tilt: 0, bearing: 0),
        ),
      );
    }
  }

  void _stopNavigation() {
    ref.read(activeNavigationProvider.notifier).clear();
    ref.read(selectedDestinationProvider.notifier).state = null;
    _clearRoute();
    ref.read(ttsServiceProvider).stop();
    _offRouteStrikeCount = 0;
    _isRerouting = false;
    _lastRerouteAt = null;
    setState(() {});
  }

  void _updateNavigationProgress(VehiclePosition pos, ActiveNavigation nav) {
    final currentLoc = LatLng(pos.lat, pos.lng);

    // چک انحراف از مسیر — قبل از هر چیز دیگری، چون اگر مسیر عوض شده باشد
    // بقیه‌ی محاسبات (نزدیک‌ترین دستورالعمل و ...) روی مسیر قدیمیِ بی‌ربط
    // بی‌معنی می‌شوند.
    if (nav.state == NavigationState.navigating && !_isRerouting) {
      final distFromRoute = _distanceToRouteMeters(currentLoc, nav.route.geometry);
      const offRouteThresholdM = 45.0;
      if (distFromRoute > offRouteThresholdM) {
        _offRouteStrikeCount++;
      } else {
        _offRouteStrikeCount = 0;
      }

      // با تایمر ۲۰۰ میلی‌ثانیه‌ای، ۵ بار پیاپی یعنی ~۱ ثانیه انحراف پیوسته
      // — این فیلتر برای نادیده‌گرفتن نویز/پرش لحظه‌ای GPS لازم است.
      const requiredStrikes = 5;
      final cooldownOk = _lastRerouteAt == null ||
          DateTime.now().difference(_lastRerouteAt!) > const Duration(seconds: 8);

      if (_offRouteStrikeCount >= requiredStrikes && cooldownOk) {
        _rerouteOffPath(distFromRoute);
        return;
      }
    }

    final lastIndex = nav.route.instructions.length - 1;
    int nearestInstructionIndex = nav.currentInstructionIndex;
    double minDistance = double.infinity;

    for (int i = nav.currentInstructionIndex; i < nav.route.instructions.length; i++) {
      final instruction = nav.route.instructions[i];
      final distance = _calculateDistance(currentLoc, instruction.location);

      if (distance < minDistance) {
        minDistance = distance;
        nearestInstructionIndex = i;
      }

      // پیشرفتِ index فقط برای دستورالعمل‌های میانی مجاز است، نه برای
      // آخرین (مقصد) — قبلاً همین شرط باعث می‌شد به‌محض ۳۰ متری‌شدن به
      // *هر* دستورالعملی (even قبل از آخری)، index بپرد و در پیچ‌های
      // پشتِ‌سرهم عملاً به index آخر برسد و «رسیدن به مقصد» را با چند
      // صد متر فاصله‌ی واقعی اعلام کند.
      if (distance < 30 && i < lastIndex) {
        nearestInstructionIndex = math.min(i + 1, lastIndex);
      }
    }

    double remainingDistance = 0;
    for (int i = nearestInstructionIndex; i < nav.route.instructions.length; i++) {
      remainingDistance += nav.route.instructions[i].distanceMeters;
    }

    final nextLoc = nav.route.instructions[nearestInstructionIndex].location;
    final distToNext = _calculateDistance(currentLoc, nextLoc);
    // فاصله‌ی خطِ‌مستقیم واقعی تا خودِ نقطه‌ی مقصد — remainingDistance
    // مجموع طولِ segmentهای مسیر است که می‌تواند از فاصله‌ی مستقیم بیشتر
    // باشد (مسیر پیچ می‌خورد)، پس معیارِ «رسیدن» باید فاصله‌ی مستقیم تا
    // مقصد باشد، نه remainingDistance.
    final distToDestination = _calculateDistance(currentLoc, nav.route.instructions.last.location);

    ref.read(activeNavigationProvider.notifier).updateProgress(
      nearestInstructionIndex,
      remainingDistance / 1000,
      distanceToNextManeuverM: distToNext,
    );

    if (nearestInstructionIndex != _lastSpokenInstructionIndex) {
      _lastSpokenInstructionIndex = nearestInstructionIndex;
      if (ref.read(ttEnabledProvider)) {
        final instr = nav.route.instructions[nearestInstructionIndex];
        final voice = ref.read(ttsServiceProvider)
          ..setVolume(ref.read(ttsVolumeProvider))
          ..setPlaybackRate(ref.read(ttsRateProvider));
        voice.playSequence(VoicePackFa.forManeuver(
          type: instr.type,
          modifier: instr.modifier,
          exit: instr.exit,
          distanceMeters: distToNext,
        ));
      }
    }

    if (!_arrivalHandled &&
        distToDestination < 20 &&
        nearestInstructionIndex >= lastIndex) {
      _arrivalHandled = true;
      _onArrived();
    }
  }

  /// کمترین فاصله‌ی نقطه‌ی خودرو تا خطِ چندپاره‌ی مسیر (متر) — با تصویر
  /// کردن نقطه روی هر پاره‌خط (segment) به‌صورت point-to-segment، نه فقط
  /// فاصله تا رأس‌های مسیر؛ چون رأس‌ها ممکن است در پاره‌خط‌های طولانی و
  /// مستقیم خیلی از هم فاصله داشته باشند و فاصله-تا-رأس به‌تنهایی می‌توانست
  /// حتی وقتی خودرو دقیقاً روی جاده است، اشتباهاً «منحرف» تشخیص بدهد.
  double _distanceToRouteMeters(LatLng p, List<LatLng> geometry) {
    if (geometry.isEmpty) return double.infinity;
    if (geometry.length == 1) return _calculateDistance(p, geometry.first);

    double minDist = double.infinity;
    for (var i = 0; i < geometry.length - 1; i++) {
      final d = _distanceToSegmentMeters(p, geometry[i], geometry[i + 1]);
      if (d < minDist) minDist = d;
    }
    return minDist;
  }

  /// فاصله‌ی نقطه‌ی p تا پاره‌خط a-b (متر) — با تبدیل مختصات جغرافیایی به
  /// یک صفحه‌ی محلیِ متری (تقریب مسطح، برای فاصله‌های شهری کاملاً کافی است)
  /// و تصویر عمود نقطه روی پاره‌خط.
  double _distanceToSegmentMeters(LatLng p, LatLng a, LatLng b) {
    const metersPerDegLat = 111320.0;
    final metersPerDegLng = 111320.0 * math.cos(degToRad(p.latitude));

    double toX(LatLng q) => (q.longitude - a.longitude) * metersPerDegLng;
    double toY(LatLng q) => (q.latitude - a.latitude) * metersPerDegLat;

    const ax = 0.0, ay = 0.0;
    final bx = toX(b), by = toY(b);
    final px = toX(p), py = toY(p);

    final dx = bx - ax, dy = by - ay;
    final lenSq = dx * dx + dy * dy;
    var t = lenSq == 0 ? 0.0 : ((px - ax) * dx + (py - ay) * dy) / lenSq;
    t = t.clamp(0.0, 1.0);
    final projX = ax + t * dx, projY = ay + t * dy;
    final ddx = px - projX, ddy = py - projY;
    return math.sqrt(ddx * ddx + ddy * ddy);
  }

  double _calculateDistance(LatLng point1, LatLng point2) {
    const earthRadius = 6371000.0;
    
    final lat1 = degToRad(point1.latitude);
    final lat2 = degToRad(point2.latitude);
    final dLat = degToRad(point2.latitude - point1.latitude);
    final dLng = degToRad(point2.longitude - point1.longitude);
    
    final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(lat1) * math.cos(lat2) *
        math.sin(dLng / 2) * math.sin(dLng / 2);
    
    final c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
    
    return earthRadius * c;
  }

  void _onArrived() {
    _showGlassNotice(
      'به مقصد رسیدید!',
      icon: Icons.flag_rounded,
      colors: const [Color(0xFF3DDC84), Color(0xFF10D15C)],
    );
    if (ref.read(ttEnabledProvider)) {
      ref.read(ttsServiceProvider).playSequence(VoicePackFa.arrived);
    }

    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        _stopNavigation();
      }
    });
  }

}

class _GpsWarningBanner extends ConsumerWidget {
  final LocationReadiness state;
  const _GpsWarningBanner({super.key, required this.state});

  String get _message {
    switch (state) {
      case LocationReadiness.serviceDisabled:
        return 'GPS دستگاه خاموش است. لطفاً آن را روشن کنید.';
      case LocationReadiness.permissionDenied:
        return 'برای ناوبری به مجوز موقعیت مکانی نیاز است. (ضربه بزنید تا دوباره بپرسیم)';
      case LocationReadiness.permissionDeniedForever:
        return 'مجوز موقعیت مکانی رد شده. برای فعال‌سازی از تنظیمات، ضربه بزنید.';
      case LocationReadiness.ready:
        return '';
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: state == LocationReadiness.ready
          ? null
          : () => ref.read(retryLocationPermissionProvider)(),
      child: _buildContent(),
    );
  }

  Widget _buildContent() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: Container(
          padding: const EdgeInsets.fromLTRB(10, 10, 16, 10),
          decoration: BoxDecoration(
            color: const Color(0xFF1B1712).withOpacity(.72),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: const Color(0xFFFFB84D).withOpacity(.35)),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFFFF8A00).withOpacity(.22),
                blurRadius: 22,
                spreadRadius: 1,
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [Color(0xFFFFB84D), Color(0xFFFF7A00)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: const Icon(Icons.gps_off_rounded, color: Colors.white, size: 18),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  _message,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    height: 1.3,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DestinationPin extends StatefulWidget {
  final MapLibreMapController? mapController;
  final LatLng point;
  const _DestinationPin({required this.mapController, required this.point});

  @override
  State<_DestinationPin> createState() => _DestinationPinState();
}

class _DestinationPinState extends State<_DestinationPin> {
  math.Point<num>? _screen;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _update();
    _refreshTimer = Timer.periodic(const Duration(milliseconds: 200), (_) => _update());
  }

  @override
  void didUpdateWidget(covariant _DestinationPin oldWidget) {
    super.didUpdateWidget(oldWidget);
    _update();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _update() async {
    final controller = widget.mapController;
    if (controller == null) return;
    try {
      final s = await controller.toScreenLocation(widget.point);
      if (!mounted) return;
      final x = s.x.toDouble();
      final y = s.y.toDouble();
      if (x.isFinite && y.isFinite) {
        setState(() => _screen = s);
      }
    } catch (_) {
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = _screen;
    if (s == null) return const SizedBox.shrink();
    return Positioned(
      left: s.x.toDouble() - 16,
      top: s.y.toDouble() - 32,
      child: const IgnorePointer(
        child: Icon(Icons.location_on_rounded, color: AppColors.subAccentB, size: 32),
      ),
    );
  }
}

class _DestinationCard extends StatelessWidget {
  final SelectedDestination destination;
  final VoidCallback onClear;
  final VoidCallback onStartNavigation;
  const _DestinationCard({
    required this.destination,
    required this.onClear,
    required this.onStartNavigation,
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: Container(
          decoration: BoxDecoration(
            color: const Color(0xFF14171F).withOpacity(.78),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: AppColors.subAccentB.withOpacity(.45)),
            boxShadow: [
              BoxShadow(
                color: AppColors.subAccentB.withOpacity(.25),
                blurRadius: 24,
                spreadRadius: 1,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 14, 8, 10),
                child: Row(
                  children: [
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: AppColors.subAccentGradient,
                      ),
                      child: const Icon(Icons.location_on_rounded, color: Colors.white, size: 20),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            destination.label ?? 'مقصد انتخاب‌شده',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 14.5,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${destination.point.latitude.toStringAsFixed(5)}, ${destination.point.longitude.toStringAsFixed(5)}',
                            style: const TextStyle(color: AppColors.textSecondary, fontSize: 11),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, color: Colors.white54, size: 20),
                      onPressed: onClear,
                      splashRadius: 20,
                    ),
                  ],
                ),
              ),
              GestureDetector(
                onTap: onStartNavigation,
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  decoration: BoxDecoration(
                    gradient: AppColors.subAccentGradient,
                    borderRadius: const BorderRadius.only(
                      bottomLeft: Radius.circular(20),
                      bottomRight: Radius.circular(20),
                    ),
                  ),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.navigation_rounded, color: Colors.white, size: 16),
                      SizedBox(width: 6),
                      Text(
                        'شروع مسیریابی',
                        style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Compass extends StatelessWidget {
  final double headingDeg;
  const _Compass({required this.headingDeg});
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.black.withOpacity(.4),
        border: Border.all(color: Colors.white.withOpacity(.15)),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Transform.rotate(
            angle: -headingDeg * 3.1415926535 / 180,
            child: CustomPaint(size: const Size(56, 56), painter: _CompassTicksPainter()),
          ),
          Transform.rotate(
            angle: -headingDeg * 3.1415926535 / 180,
            child: CustomPaint(size: const Size(30, 30), painter: _CompassNeedlePainter()),
          ),
          Container(
            width: 5,
            height: 5,
            decoration: const BoxDecoration(shape: BoxShape.circle, color: Colors.white),
          ),
        ],
      ),
    );
  }
}

class _CompassNeedlePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final tip = size.height / 2 - 2;
    final tail = size.height / 2 - 2;
    const halfWidth = 4.0;

    final northPaint = Paint()..color = const Color(0xFFE53E3E);
    final southPaint = Paint()..color = const Color(0xFFB8C0CC);

    final northPath = Path()
      ..moveTo(center.dx, center.dy - tip)
      ..lineTo(center.dx - halfWidth, center.dy)
      ..lineTo(center.dx + halfWidth, center.dy)
      ..close();

    final southPath = Path()
      ..moveTo(center.dx, center.dy + tail)
      ..lineTo(center.dx - halfWidth, center.dy)
      ..lineTo(center.dx + halfWidth, center.dy)
      ..close();

    canvas.drawPath(northPath, northPaint);
    canvas.drawPath(southPath, southPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _CompassTicksPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 4;
    final tickPaint = Paint()
      ..color = Colors.white.withOpacity(.6)
      ..strokeWidth = 1.5;

    for (var i = 0; i < 4; i++) {
      final angle = (i * 90) * 3.1415926535 / 180;
      final outer = Offset(
        center.dx + radius * math.sin(angle),
        center.dy - radius * math.cos(angle),
      );
      final inner = Offset(
        center.dx + (radius - 5) * math.sin(angle),
        center.dy - (radius - 5) * math.cos(angle),
      );
      canvas.drawLine(inner, outer, tickPaint);
    }

    final textPainter = TextPainter(
      text: const TextSpan(
        text: 'N',
        style: TextStyle(color: Color(0xFFE53E3E), fontSize: 10, fontWeight: FontWeight.bold),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    textPainter.paint(
      canvas,
      Offset(center.dx - textPainter.width / 2, center.dy - radius - textPainter.height + 2),
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _RoundIconButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  const _RoundIconButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: AppColors.homeAccentDark,
          border: Border.all(color: Colors.white.withOpacity(.08)),
          boxShadow: const [BoxShadow(color: Colors.black45, blurRadius: 14)],
        ),
        child: Icon(icon, color: Colors.white, size: 22),
      ),
    );
  }
}

class _SpeedCluster extends StatelessWidget {
  final double speedKmh;
  final int? speedLimitKmh;
  const _SpeedCluster({required this.speedKmh, this.speedLimitKmh});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 150,
      height: 96,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned(
            left: 0,
            bottom: 0,
            child: _SpeedometerDial(value: speedKmh),
          ),
          if (speedLimitKmh != null)
            Positioned(
              left: 66,
              bottom: 34,
              child: _SpeedLimitSign(value: speedLimitKmh!.toString()),
            ),
        ],
      ),
    );
  }
}

class _SpeedometerDial extends StatelessWidget {
  final double value;
  const _SpeedometerDial({required this.value});

  @override
  Widget build(BuildContext context) {
    const size = 96.0;
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Image.asset(
            'assets/images/speedometer.png',
            width: size,
            height: size,
            fit: BoxFit.cover,
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                value.round().toString(),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 34,
                  fontWeight: FontWeight.w800,
                  shadows: [Shadow(color: Colors.black87, blurRadius: 8, offset: Offset(0, 2))],
                ),
              ),
              const Text(
                'km/h',
                style: TextStyle(
                  color: Color(0xFFDFE3E6),
                  fontSize: 13,
                  shadows: [Shadow(color: Colors.black87, blurRadius: 6, offset: Offset(0, 2))],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SpeedLimitSign extends StatelessWidget {
  final String value;
  const _SpeedLimitSign({required this.value});

  @override
  Widget build(BuildContext context) {
    const size = 64.0;
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Image.asset(
            'assets/images/speed-limit.png',
            width: size,
            height: size,
            fit: BoxFit.cover,
          ),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w800,
              shadows: [Shadow(color: Colors.black87, blurRadius: 6, offset: Offset(0, 2))],
            ),
          ),
        ],
      ),
    );
  }
}

class _ActiveNavigationCard extends StatelessWidget {
  final ActiveNavigation navigation;
  final VoidCallback onClose;
  const _ActiveNavigationCard({required this.navigation, required this.onClose});

  @override
  Widget build(BuildContext context) {
    final instruction = navigation.currentInstruction;
    final remainingKm = navigation.remainingDistanceKm;
    final remainingMin = navigation.route.distanceKm > 0
        ? (navigation.route.durationMin * (remainingKm / navigation.route.distanceKm)).round()
        : 0;
    final dNext = navigation.distanceToNextManeuverM;
    final nextText = dNext >= 1000
        ? '${(dNext / 1000).toStringAsFixed(1)} کیلومتر'
        : '${dNext.round()} متر';

    final eta = DateTime.now().add(Duration(minutes: remainingMin));
    final etaText =
        '${eta.hour.toString().padLeft(2, '0')}:${eta.minute.toString().padLeft(2, '0')}';

    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 10),
      decoration: BoxDecoration(
        color: const Color(0xF0182541),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(.08)),
        boxShadow: const [
          BoxShadow(color: Colors.black54, blurRadius: 26, offset: Offset(0, 10)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              SizedBox(
                width: 52,
                height: 52,
                child: Icon(
                  _getInstructionIcon(instruction.type),
                  color: AppColors.homeAccent,
                  size: 42,
                  shadows: [
                    Shadow(color: AppColors.homeAccent.withOpacity(.65), blurRadius: 18),
                  ],
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    if (dNext > 0)
                      Text(
                        nextText,
                        textAlign: TextAlign.right,
                        style: TextStyle(
                          color: Colors.white.withOpacity(.55),
                          fontSize: 22,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    const SizedBox(height: 2),
                    Text(
                      instruction.text,
                      textAlign: TextAlign.right,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        height: 1.3,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Divider(color: Colors.white.withOpacity(.12), height: 1),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _NavStat(label: 'زمان رسیدن', value: etaText),
                    _NavStat(label: 'مسافت مانده', value: '${remainingKm.toStringAsFixed(1)} کیلومتر'),
                    _NavStat(label: 'زمان باقی‌مانده', value: '$remainingMin دقیقه'),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              GestureDetector(
                onTap: onClose,
                child: Container(
                  width: 26,
                  height: 26,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white.withOpacity(.08),
                  ),
                  child: const Icon(Icons.close_rounded, color: Colors.white70, size: 16),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  IconData _getInstructionIcon(String type) {
    switch (type) {
      case 'turn':
        return Icons.turn_right_rounded;
      case 'arrive':
        return Icons.flag_rounded;
      case 'depart':
        return Icons.navigation_rounded;
      case 'merge':
        return Icons.merge_rounded;
      case 'roundabout':
      case 'rotary':
        return Icons.roundabout_right_rounded;
      default:
        return Icons.arrow_upward_rounded;
    }
  }
}

class _NavStat extends StatelessWidget {
  final String label;
  final String value;
  const _NavStat({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Flexible(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(color: Colors.white.withOpacity(.45), fontSize: 13),
          ),
        ],
      ),
    );
  }
}

