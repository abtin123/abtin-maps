import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../features/voice_settings/presentation/tts_providers.dart';
import '../../core/localization/app_localizations.dart';
import '../../features/search/presentation/search_providers.dart';

enum NavKey { settings, voice, home, saved, routes, search }

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

  // ترتیب دکمه‌ها همیشه ثابت است (هوم همیشه وسط می‌ماند)؛ قبلاً اینجا
  // جای دکمه‌ی صفحه‌ی فعلی با دکمه‌ی وسط (هوم) عوض می‌شد تا صفحه‌ی فعلی
  // وسط بیفتد — یعنی با رفتن به تنظیمات، خودِ آیکون هوم از وسط جابه‌جا
  // می‌شد. حالا فقط استایل (پس‌زمینه‌ی رنگی/برجسته) روی آیکونِ صفحه‌ی
  // فعلی می‌رود، بدون این‌که جای هیچ دکمه‌ای عوض شود.
  List<NavKey> _buildOrder(NavKey current) => _defaultOrder;

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
      case NavKey.routes:
        return Icons.alt_route_rounded;
      case NavKey.search:
        return Icons.search_rounded;
    }
  }

  String _labelFor(NavKey key) {
    switch (key) {
      case NavKey.settings:
        return AppStrings.get(context, ref, 'settings');
      case NavKey.voice:
        return AppStrings.get(context, ref, 'voice');
      case NavKey.home:
        return AppStrings.get(context, ref, 'home');
      case NavKey.saved:
        return AppStrings.get(context, ref, 'favorites');
      case NavKey.routes:
        return AppStrings.get(context, ref, 'routes');
      case NavKey.search:
        return AppStrings.get(context, ref, 'search');
    }
  }

  /// تپ روی دکمهٔ صدا: قطع/وصل سریع صدا.
  /// نگه‌داشتن (long press): صفحهٔ تنظیمات صدا/TTS باز می‌شود.
  void _toggleVoice() {
    final notifier = ref.read(ttEnabledProvider.notifier);
    final newValue = !ref.read(ttEnabledProvider);
    notifier.set(newValue);
    if (!newValue) {
      ref.read(ttsServiceProvider).stop();
    }
  }

  void _onTap(NavKey key) {
    if (key == NavKey.voice) {
      _toggleVoice();
      return;
    }
    if (key == NavKey.search) {
      ref.read(searchActiveProvider.notifier).state = true;
      return;
    }
    switch (key) {
      case NavKey.home:
        // اگر جستجو باز است، دکمهٔ هوم باید اول جستجو را ببندد نه این‌که
        // مسیر را دوباره push/go کند.
        if (ref.read(searchActiveProvider)) {
          ref.read(searchActiveProvider.notifier).state = false;
          return;
        }
        context.go('/');
        break;
      case NavKey.saved:
        context.push('/saved-places');
        break;
      case NavKey.routes:
        // مسیر، مقصد و محاسبهٔ route را از providerهای مشترک می‌خواند؛
        // go باعث می‌شود با هر بار کلیک یک صفحهٔ تکراری روی stack ساخته نشود.
        context.go('/routes');
        break;
      case NavKey.settings:
        context.push('/settings');
        break;
      case NavKey.voice:
        break;
      case NavKey.search:
        break;
    }
  }

  void _onLongPress(NavKey key) {
    if (key == NavKey.voice) {
      context.push('/voice-settings');
    }
  }

  @override
  Widget build(BuildContext context) {
    final order = _buildOrder(widget.currentPage);
    final bottomSafe = MediaQuery.of(context).padding.bottom;
    final ttEnabled = ref.watch(ttEnabledProvider);
    final searchActive = ref.watch(searchActiveProvider);

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
              bottom:
                  bottomSafe - 30, // ۲۰ پیکسل پایین‌تر از قبل (درخواست کاربر)
              child: ClipPath(
                clipper: _BottomBarClipper(),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
                  child: Container(
                    height: 80, // Increased height for deeper curve
                    decoration: BoxDecoration(
                      color:
                          AppColors.subGlassBgSoft(context).withOpacity(0.38),
                      border: Border(
                        top: BorderSide(
                          color: AppColors.primaryAccent(context)
                              .withOpacity(0.28),
                          width: 1.5,
                        ),
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
                      color: AppColors.subGlassBg(context),
                      border: Border.all(
                          color: AppColors.subGlassBorder(context), width: 1),
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
                    // وقتی جستجو باز است: هوم دی‌اکتیو می‌شود و خودِ آیکون
                    // سرچ به‌جایش فعال/برجسته نشان داده می‌شود.
                    final isActive = searchActive
                        ? key == NavKey.search
                        : key == widget.currentPage;
                    final isMuted = key == NavKey.voice && !ttEnabled;
                    // اندازه/جابه‌جایی فقط به این‌که دکمه «هوم» است یا نه
                    // بستگی دارد — نه به این‌که کدام صفحه فعال است. یعنی
                    // دکمه‌ی هوم همیشه (در هر صفحه‌ای) همین‌قدر بزرگ و
                    // بالاآمده می‌ماند و جای هیچ دکمه‌ای عوض نمی‌شود؛ تنها
                    // چیزی که با صفحه‌ی فعال عوض می‌شود «پرشدن/رنگی‌شدنِ
                    // پس‌زمینه»‌ی همان آیکون است.
                    final isHomeKey = key == NavKey.home;
                    final circleSize = isHomeKey ? 52.0 : 44.0;
                    final iconSize = isHomeKey ? 28.0 : 24.0;
                    final liftOffset = isHomeKey ? -12.0 : 0.0;
                    final isFilled = isActive;
                    return GestureDetector(
                      onTap: () => _onTap(key),
                      onLongPress:
                          key == NavKey.voice ? () => _onLongPress(key) : null,
                      behavior: HitTestBehavior.opaque,
                      child: SizedBox(
                        width: 55,
                        height: 75,
                        child: Center(
                          child: Transform.translate(
                            offset: Offset(0, liftOffset),
                            child: SizedBox(
                              width: circleSize,
                              height: circleSize,
                              child: isFilled
                                  ? ClipOval(
                                      child: BackdropFilter(
                                        filter: ImageFilter.blur(
                                            sigmaX: 14, sigmaY: 14),
                                        child: Container(
                                          decoration: BoxDecoration(
                                            shape: BoxShape.circle,
                                            gradient: LinearGradient(
                                              begin: Alignment.topLeft,
                                              end: Alignment.bottomRight,
                                              colors: [
                                                AppColors.primaryAccentLight(
                                                        context)
                                                    .withOpacity(0.78),
                                                AppColors.primaryAccent(context)
                                                    .withOpacity(0.78),
                                                AppColors.primaryAccentDark(
                                                        context)
                                                    .withOpacity(0.78),
                                              ],
                                              stops: const [0, 0.58, 1],
                                            ),
                                            // دکمه‌ی وسط (هوم) وقتی فعال است
                                            // با رنگ تبِ فعلی (accent —
                                            // همان رنگ اپ) حلقه می‌گیرد؛
                                            // بقیه‌ی دکمه‌ها مثل قبل.
                                            border: Border.all(
                                              color: isHomeKey
                                                  ? AppColors.primaryAccent(
                                                      context)
                                                  : AppColors.frameBackground(
                                                          context)
                                                      .withOpacity(0.9),
                                              width: isHomeKey ? 2.5 : 2,
                                            ),
                                          ),
                                          child: Icon(
                                            _iconFor(key, ttEnabled),
                                            size: iconSize,
                                            color: isMuted
                                                ? AppColors.homeDanger
                                                : AppColors.primaryOnAccent(
                                                    context),
                                          ),
                                        ),
                                      ),
                                    )
                                  : DecoratedBox(
                                      decoration: BoxDecoration(
                                        shape: BoxShape.circle,
                                        color: AppColors.subGlassBg(context),
                                        // باگ قبلی: دور دکمه‌ی وسط (هوم)
                                        // وقتی غیرفعال بود اصلاً هیچ حلقه‌ای
                                        // نبود — کاربر خواسته بود همیشه یک
                                        // دایره دورش باشد، فقط رنگش وقتی
                                        // غیرفعاله همرنگ خودِ نوارِ شیشه‌ای
                                        // («سیلندر») باشد تا در حالتِ
                                        // غیرفعال محو/هم‌رنگِ پس‌زمینه به‌نظر
                                        // برسد، نه ناپدید.
                                        border: isHomeKey
                                            ? Border.all(
                                                color: AppColors.subGlassBorder(
                                                    context),
                                                width: 1.5,
                                              )
                                            : null,
                                      ),
                                      child: Icon(
                                        _iconFor(key, ttEnabled),
                                        size: iconSize,
                                        color: isMuted
                                            ? AppColors.homeDanger
                                            : AppColors.textSecondary(context),
                                      ),
                                    ),
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
    // A more pronounced parabolic curve to match the reference image
    path.moveTo(0, size.height);
    path.lineTo(0, 50);
    path.quadraticBezierTo(size.width / 2, -60, size.width, 50);
    path.lineTo(size.width, size.height);
    path.close();
    return path;
  }

  @override
  bool shouldReclip(CustomClipper<Path> oldClipper) => true;
}
