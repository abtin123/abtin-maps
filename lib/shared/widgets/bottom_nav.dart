import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../features/voice_settings/presentation/tts_providers.dart';

enum NavKey { settings, voice, home, saved, search }

class BottomNav extends ConsumerStatefulWidget {
  final NavKey currentPage;
  final bool isHomePage;

  const BottomNav({
    super.key,
    required this.currentPage,
    this.isHomePage = false,
  });

  @override
  ConsumerState<BottomNav> createState() => _BottomNavState();
}

class _BottomNavState extends ConsumerState<BottomNav> {
  static const List<NavKey> _defaultOrder = [
    NavKey.settings,
    NavKey.voice,
    NavKey.home,
    NavKey.saved,
    NavKey.search,
  ];
  static const int _centerSlot = 2;

  static const double _barHeight = 96;
  static const double _horizontalMargin = 7;

  List<NavKey> _buildOrder(NavKey current) {
    final order = List<NavKey>.from(_defaultOrder);
    if (current != NavKey.home) {
      final idx = order.indexOf(current);
      if (idx != -1) {
        final tmp = order[idx];
        order[idx] = order[_centerSlot];
        order[_centerSlot] = tmp;
      }
    }
    return order;
  }

  IconData _iconFor(NavKey key, bool ttEnabled) {
    switch (key) {
      case NavKey.settings:
        return Icons.settings_rounded;
      case NavKey.voice:
        return ttEnabled ? Icons.volume_up_rounded : Icons.volume_off_rounded;
      case NavKey.home:
        return Icons.home_rounded;
      case NavKey.saved:
        return Icons.star_rounded;
      case NavKey.search:
        return Icons.search_rounded;
    }
  }

  String _labelFor(NavKey key) {
    switch (key) {
      case NavKey.settings:
        return 'تنظیمات';
      case NavKey.voice:
        return 'صدا';
      case NavKey.home:
        return 'خانه';
      case NavKey.saved:
        return 'علاقه‌مندی‌ها';
      case NavKey.search:
        return 'جستجو';
    }
  }

  void _onTap(NavKey key) {
    if (key == NavKey.voice) {
      final notifier = ref.read(ttEnabledProvider.notifier);
      final newValue = !ref.read(ttEnabledProvider);
      notifier.set(newValue);
      if (!newValue) {
        ref.read(ttsServiceProvider).stop();
      }
      return;
    }
    switch (key) {
      case NavKey.home:
        context.go('/');
        break;
      case NavKey.saved:
        context.push('/saved-places');
        break;
      case NavKey.search:
        context.push('/search');
        break;
      case NavKey.settings:
        context.push('/settings');
        break;
      case NavKey.voice:
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final order = _buildOrder(widget.currentPage);
    final bottomSafe = MediaQuery.of(context).padding.bottom;
    final ttEnabled = ref.watch(ttEnabledProvider);

    return Align(
      alignment: Alignment.bottomCenter,
      child: SizedBox(
        height: _barHeight + bottomSafe,
        child: Stack(
          clipBehavior: Clip.none,
          alignment: Alignment.bottomCenter,
          children: [
            // Main Background with Deeper Curve
            Positioned(
              left: -MediaQuery.of(context).size.width * 0.25,
              right: -MediaQuery.of(context).size.width * 0.25,
              bottom: bottomSafe - 10, // Lowered slightly
              child: ClipPath(
                clipper: _BottomBarClipper(),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
                  child: Container(
                    height: 80, // Increased height for deeper curve
                    decoration: BoxDecoration(
                      color: AppColors.subGlassBgSoft.withOpacity(0.8),
                      border: const Border(
                        top: BorderSide(color: Color(0x472FE6C4), width: 1.5),
                      ),
                    ),
                  ),
                ),
              ),
            ),

            // Inner Glass Bar
            Positioned(
              left: _horizontalMargin + 30,
              right: _horizontalMargin + 30,
              bottom: bottomSafe + 16,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(28),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 22, sigmaY: 22),
                  child: Container(
                    height: 56,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(28),
                      color: AppColors.subGlassBg,
                      border: Border.all(color: AppColors.subGlassBorder, width: 1),
                    ),
                  ),
                ),
              ),
            ),

            // Navigation Items
            Positioned(
              left: _horizontalMargin + 30,
              right: _horizontalMargin + 30,
              bottom: bottomSafe + 10,
              child: Directionality(
                textDirection: TextDirection.ltr,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: order.map((key) {
                    final isActive = order.indexOf(key) == _centerSlot;
                    final isMuted = key == NavKey.voice && !ttEnabled;
                    return GestureDetector(
                      onTap: () => _onTap(key),
                      behavior: HitTestBehavior.opaque,
                      child: SizedBox(
                        width: 55,
                        height: 75,
                        child: Center(
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 200),
                            width: isActive ? 52 : 44,
                            height: isActive ? 52 : 44,
                            transform: isActive
                                ? (Matrix4.identity()..translate(0.0, -12.0))
                                : Matrix4.identity(),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: isActive ? AppColors.subAccentGradient : null,
                              color: isActive ? null : Colors.transparent,
                              border: isActive
                                  ? Border.all(color: const Color(0xFF0E1219), width: 2) // Reduced stroke
                                  : null,
                              // Removed Glow Shadow as requested
                            ),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  _iconFor(key, ttEnabled),
                                  size: isActive ? 26 : 22,
                                  color: isMuted
                                      ? AppColors.homeDanger
                                      : (isActive ? Colors.white : const Color(0xFFC7CCD1)),
                                ),
                                if (!isActive) ...[
                                  const SizedBox(height: 2),
                                  Text(
                                    _labelFor(key),
                                    style: TextStyle(
                                      color: isMuted ? AppColors.homeDanger : const Color(0xFFC7CCD1),
                                      fontSize: 9,
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BottomBarClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final path = Path();
    path.moveTo(0, 30);
    path.quadraticBezierTo(size.width / 2, -20, size.width, 30); // Deeper curve
    path.lineTo(size.width, size.height);
    path.lineTo(0, size.height);
    path.close();
    return path;
  }

  @override
  bool shouldReclip(CustomClipper<Path> oldClipper) => true;
}
