import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../features/voice_settings/presentation/tts_providers.dart';

enum NavKey { routes, search, home, voice, settings }

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
    NavKey.routes,
    NavKey.search,
    NavKey.home,
    NavKey.voice,
    NavKey.settings,
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
      case NavKey.routes:
        return Icons.alt_route_rounded;
      case NavKey.search:
        return Icons.search_rounded;
      case NavKey.home:
        return Icons.home_rounded;
      case NavKey.voice:
        return ttEnabled ? Icons.volume_up_rounded : Icons.volume_off_rounded;
      case NavKey.settings:
        return Icons.settings_rounded;
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
      case NavKey.routes:
        context.push('/routes');
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
            Positioned(
              left: -MediaQuery.of(context).size.width * 0.25,
              right: -MediaQuery.of(context).size.width * 0.25,
              bottom: bottomSafe - 3,
              child: ClipRRect(
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.elliptical(600, 60),
                  topRight: Radius.elliptical(600, 60),
                ),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
                  child: Container(
                    height: 60,
                    decoration: BoxDecoration(
                      color: AppColors.subGlassBgSoft,
                      border: const Border(
                        top: BorderSide(color: Color(0x472FE6C4), width: 1),
                      ),
                      boxShadow: const [
                        BoxShadow(
                          color: Color(0x80000000),
                          blurRadius: 24,
                          offset: Offset(0, -8),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            Positioned(
              left: _horizontalMargin + 30,
              right: _horizontalMargin + 30,
              bottom: bottomSafe + 20,
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
                      boxShadow: const [
                        BoxShadow(
                          color: Color(0x8C000000),
                          blurRadius: 18,
                          offset: Offset(0, 6),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            Positioned(
              left: _horizontalMargin + 30,
              right: _horizontalMargin + 30,
              bottom: bottomSafe + 14,
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
                        height: 68,
                        child: Center(
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 200),
                            width: isActive ? 50 : 44,
                            height: isActive ? 50 : 44,
                            transform: isActive
                                ? (Matrix4.identity()..translate(0.0, -10.0))
                                : Matrix4.identity(),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: isActive ? AppColors.subAccentGradient : null,
                              color: isActive ? null : Colors.transparent,
                              border: isActive
                                  ? Border.all(color: const Color(0xFF0E1219), width: 4)
                                  : null,
                              boxShadow: isActive
                                  ? [
                                      BoxShadow(
                                        color: AppColors.subAccentB,
                                        blurRadius: 16,
                                        spreadRadius: 1,
                                      )
                                    ]
                                  : null,
                            ),
                            child: Icon(
                              _iconFor(key, ttEnabled),
                              size: isActive ? 28 : 26,
                              color: isMuted
                                  ? AppColors.homeDanger
                                  : (isActive ? Colors.white : const Color(0xFFC7CCD1)),
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
