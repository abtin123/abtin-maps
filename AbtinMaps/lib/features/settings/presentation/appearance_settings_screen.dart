import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/localization/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/geo/geo_types.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/route_guidance_card.dart';
import '../../weather/presentation/weather_settings_providers.dart';
import '../../routing/data/routing_service.dart';
import '../../routing/presentation/road_alert_badge.dart';
import 'appearance/shared_widgets.dart';
import 'appearance_settings_providers.dart';

/// پالتِ رنگ‌های پیشنهادیِ صفحهٔ ظاهر — طبق طراحیِ مرجع (۸ رنگِ ثابت +
/// گزینهٔ رنگِ سفارشی). عمداً مستقل از appColorPresets نگه داشته شده،
/// چون آن پالت برای رنگِ مسیر/پیکان است، نه رنگِ اصلیِ اپ.
const List<Color> _themeColorPresets = [
  Color(0xFF8A3FD0), // بنفش (پیش‌فرض)
  Color(0xFFFFFFFF), // سفید
  Color(0xFF14161B), // مشکی
  Color(0xFF2F6FE0), // آبی
  Color(0xFF3FD0E0), // فیروزه‌ای
  Color(0xFF52C24C), // سبز
  Color(0xFFE0A83F), // طلایی
  Color(0xFFE0523F), // قرمز
];

/// صفحهٔ «تنظیمات ظاهر»: رنگ و حالتِ نمایشِ کلیِ اپ، ظاهرِ کارتِ
/// مسیریابی و ظاهرِ ویجتِ شناورِ آب‌وهوا — همه در یک محل، با هدرِ
/// مشترکِ [PageHeader] و رنگِ داینامیکِ [AppColors.primaryAccent].
class AppearanceSettingsScreen extends ConsumerWidget {
  const AppearanceSettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final accent = AppColors.primaryAccent(context);

    return Scaffold(
      backgroundColor: AppColors.background(context),
      appBar: PageHeader(title: AppStrings.literal('تنظیمات ظاهر')),
      body: Container(
        decoration: BoxDecoration(
          gradient: RadialGradient(
            center: Alignment.topCenter,
            radius: 1.12,
            colors: [accent.withOpacity(0.15), AppColors.background(context)],
          ),
        ),
        child: Stack(
          children: [
            Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  child: RouteGuidanceCard(
                    settings: ref.watch(appearanceSettingsProvider),
                    data: _previewRouteCardData(context, ref),
                  ),
                ),
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 112),
                    children: const [
                      _GeneralSettingsCard(),
                      SizedBox(height: 14),
                      _RouteCardSettingsCard(showPreview: false),
                      SizedBox(height: 14),
                      _RouteAlertSettingsCard(),
                      SizedBox(height: 14),
                      SizedBox(height: 14),
                      _SystemInfoWidgetSettingsCard(),
                      SizedBox(height: 14),
                      _FontSettingsCard(),
                    ],
                  ),
                ),
              ],
            ),
            const BottomNav(currentPage: NavKey.settings),
          ],
        ),
      ),
    );
  }
}

// ============================================================
// پوستهٔ مشترکِ کارت‌های شیشه‌ای این صفحه.
// ============================================================

class _GlassCard extends StatelessWidget {
  const _GlassCard({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.child,
    this.headerLeading,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final Widget child;
  final Widget? headerLeading;

  @override
  Widget build(BuildContext context) => ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.glassPanelSoft(context),
              borderRadius: BorderRadius.circular(18),
              border:
                  Border.all(color: AppColors.glassBorder(context), width: 0.7),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    if (headerLeading != null) ...[
                      headerLeading!,
                    ],
                    const Spacer(),
                    Text(
                      title,
                      textAlign: TextAlign.right,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            color: AppColors.textPrimary(context),
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(width: 9),
                    Container(
                      width: 30,
                      height: 30,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: iconColor.withOpacity(0.18),
                      ),
                      child: Icon(icon, color: iconColor, size: 17),
                    ),
                  ],
                ),
                const SizedBox(height: 15),
                child,
              ],
            ),
          ),
        ),
      );
}

// ============================================================
// اجزای عمومیِ سطرها.
// ============================================================

class _RowIcon extends StatelessWidget {
  const _RowIcon({required this.icon, required this.color});
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        width: 27,
        height: 27,
        alignment: Alignment.center,
        decoration:
            BoxDecoration(shape: BoxShape.circle, color: color.withOpacity(0.16)),
        child: Icon(icon, size: 14, color: color),
      );
}

class _SettingHeader extends StatelessWidget {
  const _SettingHeader({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.leading,
    this.iconColor,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Widget? leading;
  final Color? iconColor;

  @override
  Widget build(BuildContext context) {
    final color = iconColor ?? AppColors.primaryAccent(context);
    return Row(
      children: [
        if (leading != null) ...[leading!, const SizedBox(width: 12)],
        _RowIcon(icon: icon, color: color),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                title,
                textAlign: TextAlign.right,
                style: TextStyle(
                  color: AppColors.textPrimary(context),
                  fontWeight: FontWeight.w700,
                  fontSize: 14.5,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                textAlign: TextAlign.right,
                style:
                    TextStyle(color: AppColors.textMuted(context), fontSize: 11.5),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// سطرِ کامل: هدر (آیکون+عنوان+زیرعنوان) + یک اسلایدر، با امکانِ یک
/// کنترلِ کمکی (فلش/چیپ درصد/دکمهٔ بزرگ‌نمایی) سمتِ چپِ اسلایدر.
class _SliderSetting extends StatelessWidget {
  const _SliderSetting({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
    this.min = 0.0,
    this.max = 1.0,
    this.trailing,
    this.iconColor,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final double value;
  final double min;
  final double max;
  final ValueChanged<double> onChanged;
  final Widget? trailing;
  final Color? iconColor;

  @override
  Widget build(BuildContext context) {
    final accent = AppColors.primaryAccent(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _SettingHeader(
          icon: icon,
          title: title,
          subtitle: subtitle,
          iconColor: iconColor,
        ),
        const SizedBox(height: 2),
        Row(
          children: [
            if (trailing != null) ...[trailing!, const SizedBox(width: 10)],
            Expanded(
              child: SliderTheme(
                data: SliderTheme.of(context).copyWith(
                  activeTrackColor: accent,
                  inactiveTrackColor: accent.withOpacity(0.18),
                  thumbColor: accent,
                  overlayColor: accent.withOpacity(0.12),
                  trackHeight: 4,
                ),
                child: Slider(
                  value: value.clamp(min, max).toDouble(),
                  min: min,
                  max: max,
                  onChanged: onChanged,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// سطرِ تک‌خطیِ رنگ: هدر + یک دایرهٔ رنگ که با تپ، شیتِ انتخاب‌گرِ رنگِ
/// کاملِ [ColorPickerSheet] را باز می‌کند.
class _ColorSetting extends StatelessWidget {
  const _ColorSetting({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.onChanged,
    this.iconColor,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final ValueChanged<Color> onChanged;
  final Color? iconColor;

  @override
  Widget build(BuildContext context) => _SettingHeader(
        icon: icon,
        title: title,
        subtitle: subtitle,
        iconColor: iconColor,
        leading: _ColorSwatchButton(color: color, onChanged: onChanged),
      );
}

class _ColorSwatchButton extends StatelessWidget {
  const _ColorSwatchButton({required this.color, required this.onChanged});
  final Color color;
  final ValueChanged<Color> onChanged;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () async {
            final picked = await ColorPickerSheet.show(context, color);
            if (picked != null) onChanged(picked);
          },
          customBorder: const CircleBorder(),
          child: Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white.withOpacity(0.35), width: 1.4),
              boxShadow: [
                BoxShadow(color: Colors.black.withOpacity(0.25), blurRadius: 4),
              ],
            ),
          ),
        ),
      );
}

/// سطرِ سوییچِ روشن/خاموش (هدر + یک Switch سمتِ چپ).
class _SwitchSetting extends StatelessWidget {
  const _SwitchSetting({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
    this.iconColor,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;
  final Color? iconColor;

  @override
  Widget build(BuildContext context) {
    final accent = AppColors.primaryAccent(context);
    return _SettingHeader(
      icon: icon,
      title: title,
      subtitle: subtitle,
      iconColor: iconColor,
      leading: Switch.adaptive(
        value: value,
        onChanged: onChanged,
        activeColor: accent,
      ),
    );
  }
}

/// گروهِ دوتاییِ فلش (بالا/پایین یا چپ/راست) برای پرشِ سریعِ اسلایدر به
/// دو انتها. جهتِ فعلاً‌فعال بر اساسِ مقدارِ جاری هایلایت می‌شود.
class _BiStepper extends StatelessWidget {
  const _BiStepper({
    required this.value,
    required this.onChanged,
    required this.startIcon,
    required this.endIcon,
  });

  final double value; // 0..100
  final ValueChanged<double> onChanged;
  final IconData startIcon;
  final IconData endIcon;

  @override
  Widget build(BuildContext context) {
    final accent = AppColors.primaryAccent(context);
    final secondActive = value > 50;
    return Directionality(
      textDirection: TextDirection.ltr,
      child: Container(
        padding: const EdgeInsets.all(3),
        decoration: BoxDecoration(
          color: AppColors.surfaceMuted(context),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _StepperButton(
              icon: startIcon,
              active: !secondActive,
              color: accent,
              onTap: () => onChanged(0),
            ),
            _StepperButton(
              icon: endIcon,
              active: secondActive,
              color: accent,
              onTap: () => onChanged(100),
            ),
          ],
        ),
      ),
    );
  }
}

/// گروهِ سه‌تاییِ چپ / سوآپ / راست — برای جایگاهِ افقی و راستاچینیِ
/// محتوا. دکمهٔ میانی همیشه به‌عنوانِ ابزارِ فعال نمایش داده می‌شود و با
/// تپ، مقدار را به میانه (۵۰) برمی‌گرداند؛ دو فلشِ کناری مستقیم به
/// انتها می‌پرند.
class _TriStepper extends StatelessWidget {
  const _TriStepper({required this.onLeft, required this.onCenter, required this.onRight});

  final VoidCallback onLeft;
  final VoidCallback onCenter;
  final VoidCallback onRight;

  @override
  Widget build(BuildContext context) {
    final accent = AppColors.primaryAccent(context);
    return Directionality(
      textDirection: TextDirection.ltr,
      child: Container(
        padding: const EdgeInsets.all(3),
        decoration: BoxDecoration(
          color: AppColors.surfaceMuted(context),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _StepperButton(
              icon: Icons.chevron_left_rounded,
              active: false,
              color: accent,
              onTap: onLeft,
            ),
            _StepperButton(
              icon: Icons.swap_horiz_rounded,
              active: true,
              color: accent,
              onTap: onCenter,
            ),
            _StepperButton(
              icon: Icons.chevron_right_rounded,
              active: false,
              color: accent,
              onTap: onRight,
            ),
          ],
        ),
      ),
    );
  }
}

class _StepperButton extends StatelessWidget {
  const _StepperButton({
    required this.icon,
    required this.active,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final bool active;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Container(
            width: 30,
            height: 30,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: active ? color : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon,
                size: 18,
                color: active ? Colors.white : AppColors.textSecondary(context)),
          ),
        ),
      );
}

/// دکمهٔ تکیِ بزرگ‌نمایی — برای بازنشانیِ سریعِ اندازهٔ ویجت به مقدارِ
/// پیش‌فرض.
class _ExpandButton extends StatelessWidget {
  const _ExpandButton({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final accent = AppColors.primaryAccent(context);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          width: 36,
          height: 36,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppColors.surfaceMuted(context),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(Icons.open_in_full_rounded, size: 16, color: accent),
        ),
      ),
    );
  }
}

/// چیپِ نمایشِ درصد — نمایشِ صرفاً بصریِ مقدارِ فعلیِ اسلایدرِ کناری.
class _PercentChip extends StatelessWidget {
  const _PercentChip({required this.value});
  final int value;

  @override
  Widget build(BuildContext context) {
    final accent = AppColors.primaryAccent(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 8),
      decoration: BoxDecoration(
        color: accent.withOpacity(0.15),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: accent.withOpacity(0.4)),
      ),
      child: Text(
        '$value%',
        style: TextStyle(
          color: AppColors.textPrimary(context),
          fontWeight: FontWeight.w700,
          fontSize: 12,
        ),
      ),
    );
  }
}

// ============================================================
// بخش ۱: تنظیمات عمومی — رنگ اصلی اپ + حالت نمایش.
// ============================================================

class _GeneralSettingsCard extends ConsumerWidget {
  const _GeneralSettingsCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appearance = ref.watch(appearanceSettingsProvider);
    final notifier = ref.read(appearanceSettingsProvider.notifier);
    final isCustom = !_themeColorPresets
        .any((c) => c.value == appearance.primaryColor.value);

    Future<void> setColor(Color c) =>
        notifier.update((s) => s.copyWith(primaryColor: c));
    Future<void> setThemeMode(ThemeMode m) =>
        notifier.update((s) => s.copyWith(themeMode: m));

    return _GlassCard(
      icon: Icons.palette_rounded,
      iconColor: AppColors.primaryAccent(context),
      title: AppStrings.literal('تنظیمات عمومی'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Directionality(
            textDirection: TextDirection.ltr,
            child: Wrap(
              spacing: 14,
              runSpacing: 12,
              children: [
                for (final c in _themeColorPresets)
                  AppColorSwatch(
                    color: c,
                    selected: !isCustom && c.value == appearance.primaryColor.value,
                    onTap: () => setColor(c),
                  ),
                RainbowSwatch(
                  selected: isCustom,
                  onTap: () async {
                    final picked =
                        await ColorPickerSheet.show(context, appearance.primaryColor);
                    if (picked != null) await setColor(picked);
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Text(
            AppStrings.literal('حالت نمایش'),
            textAlign: TextAlign.right,
            style: TextStyle(
              color: AppColors.textSecondary(context),
              fontSize: 12.5,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 10),
          Directionality(
            textDirection: TextDirection.ltr,
            child: Row(
              children: [
                Expanded(
                  child: PillChoice(
                    label: AppStrings.literal('روز'),
                    icon: Icons.wb_sunny_rounded,
                    selected: appearance.themeMode == ThemeMode.light,
                    onTap: () => setThemeMode(ThemeMode.light),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: PillChoice(
                    label: AppStrings.literal('شب'),
                    icon: Icons.dark_mode_rounded,
                    selected: appearance.themeMode == ThemeMode.dark,
                    onTap: () => setThemeMode(ThemeMode.dark),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: PillChoice(
                    label: AppStrings.literal('پیروی از سیستم'),
                    icon: Icons.smartphone_rounded,
                    selected: appearance.themeMode == ThemeMode.system,
                    onTap: () => setThemeMode(ThemeMode.system),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================
// بخش ۲: کارتِ مسیریابی.
// ============================================================

/// دادهٔ نمونه برای پیش‌نمایشِ زندهٔ کارتِ مسیریابی در صفحهٔ تنظیمات —
/// همان شکلی که در ناوبریِ واقعی دیده می‌شود، با اعداد ثابتِ دلخواه.
RouteGuidanceCardData _previewRouteCardData(
    BuildContext context, WidgetRef ref) {
  final t = (String key) => AppStrings.get(context, ref, key);
  return RouteGuidanceCardData(
    icon: Icons.turn_right_rounded,
    distanceText: t('route_distance_m').replaceAll('{value}', '300'),
    streetText: t('route_preview_instruction'),
    etaLabel: t('route_eta'),
    etaValue: '14:32',
    remainingLabel: t('route_remaining'),
    remainingValue: t('route_distance_km').replaceAll('{value}', '4.2'),
    durationLabel: t('route_time'),
    durationValue: t('route_duration_minutes').replaceAll('{value}', '9'),
    onClose: null,
  );
}

class _RouteCardSettingsCard extends ConsumerWidget {
  const _RouteCardSettingsCard({this.showPreview = true});

  final bool showPreview;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appearance = ref.watch(appearanceSettingsProvider);
    final notifier = ref.read(appearanceSettingsProvider.notifier);
    const rowColor = Color(0xFFB57BFF);

    return _GlassCard(
      icon: Icons.map_rounded,
      iconColor: rowColor,
      title: AppStrings.literal('کارت مسیریابی'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // پیش‌نمایشِ زنده: همان ویجتی که در ناوبریِ واقعی رندر می‌شود،
          // با دادهٔ نمونه — هر تغییری در اسلایدرها/رنگ‌های زیر بلافاصله
          // این‌جا هم منعکس می‌شود.
          if (showPreview) ...[
            RouteGuidanceCard(
              settings: appearance,
              data: _previewRouteCardData(context, ref),
            ),
            const SizedBox(height: 16),
          ],
          _SliderSetting(
            icon: Icons.height_rounded,
            iconColor: const Color(0xFFB57BFF),
            title: AppStrings.literal('ارتفاع کارت'),
            subtitle: AppStrings.literal('بلندی کارت مسیریابی'),
            value: appearance.routeCardHeight,
            onChanged: (v) =>
                notifier.update((s) => s.copyWith(routeCardHeight: v)),
          ),
          const RowDivider(),
          _SliderSetting(
            icon: Icons.opacity_rounded,
            iconColor: const Color(0xFF5CC8FF),
            title: AppStrings.literal('شفافیت کارت'),
            subtitle: AppStrings.literal('میزان شفافیت پس‌زمینه کارت'),
            value: appearance.routeCardOpacity,
            onChanged: (v) =>
                notifier.update((s) => s.copyWith(routeCardOpacity: v)),
          ),
          const RowDivider(),
          _SliderSetting(
            icon: Icons.rounded_corner_rounded,
            iconColor: const Color(0xFFFF6FA5),
            title: AppStrings.literal('گردی گوشه کارت'),
            subtitle: AppStrings.literal('میزان گردی گوشه‌های کارت'),
            value: appearance.routeCardCornerRadius,
            onChanged: (v) =>
                notifier.update((s) => s.copyWith(routeCardCornerRadius: v)),
          ),
          const RowDivider(),
          _SliderSetting(
            icon: Icons.flare_rounded,
            iconColor: const Color(0xFF8FD14F),
            title: AppStrings.literal('شدت درخشش کارت'),
            subtitle: AppStrings.literal('میزان درخشش حاشیه کارت'),
            value: appearance.routeCardGlowIntensity,
            onChanged: (v) =>
                notifier.update((s) => s.copyWith(routeCardGlowIntensity: v)),
          ),

          // --- کنترلِ جداگانهٔ هر بخشِ کارت ---
          const SizedBox(height: 8),
          _SectionLabel(text: AppStrings.literal('فلش جهت‌نما')),
          _SliderSetting(
            icon: Icons.zoom_out_map_rounded,
            iconColor: const Color(0xFF3DDC84),
            title: AppStrings.literal('اندازه فلش'),
            subtitle: AppStrings.literal('اندازه آیکون جهت‌نما'),
            value: appearance.routeCardArrowSize,
            onChanged: (v) =>
                notifier.update((s) => s.copyWith(routeCardArrowSize: v)),
          ),
          const RowDivider(),
          _ColorSetting(
            icon: Icons.palette_rounded,
            iconColor: const Color(0xFF3DDC84),
            title: AppStrings.literal('رنگ فلش'),
            subtitle: AppStrings.literal('رنگ آیکون جهت‌نما'),
            color: appearance.routeCardArrowColor,
            onChanged: (c) =>
                notifier.update((s) => s.copyWith(routeCardArrowColor: c)),
          ),

          const SizedBox(height: 8),
          _SectionLabel(text: AppStrings.literal('فاصله تا پیچ بعدی')),
          _SliderSetting(
            icon: Icons.text_fields_rounded,
            iconColor: const Color(0xFF4FD1C5),
            title: AppStrings.literal('اندازه فونت فاصله'),
            subtitle: AppStrings.literal('اندازه عددِ فاصله تا پیچ بعدی'),
            value: appearance.routeCardDistanceFontSize,
            onChanged: (v) => notifier
                .update((s) => s.copyWith(routeCardDistanceFontSize: v)),
          ),
          const RowDivider(),
          _ColorSetting(
            icon: Icons.palette_rounded,
            iconColor: const Color(0xFF4FD1C5),
            title: AppStrings.literal('رنگ فاصله'),
            subtitle: AppStrings.literal('رنگ عددِ فاصله تا پیچ بعدی'),
            color: appearance.routeCardDistanceColor,
            onChanged: (c) =>
                notifier.update((s) => s.copyWith(routeCardDistanceColor: c)),
          ),

          const SizedBox(height: 8),
          _SectionLabel(text: AppStrings.literal('نام خیابان / دستور مسیر')),
          _SliderSetting(
            icon: Icons.text_fields_rounded,
            iconColor: const Color(0xFFF2A93C),
            title: AppStrings.literal('اندازه فونت متن راهنما'),
            subtitle: AppStrings.literal('اندازه نام خیابان و دستور مسیر'),
            value: appearance.routeCardStreetFontSize,
            onChanged: (v) =>
                notifier.update((s) => s.copyWith(routeCardStreetFontSize: v)),
          ),
          const RowDivider(),
          _ColorSetting(
            icon: Icons.palette_rounded,
            iconColor: const Color(0xFFF2A93C),
            title: AppStrings.literal('رنگ متن راهنما'),
            subtitle: AppStrings.literal('رنگ نام خیابان و دستور مسیر'),
            color: appearance.routeCardStreetColor,
            onChanged: (c) =>
                notifier.update((s) => s.copyWith(routeCardStreetColor: c)),
          ),

          const SizedBox(height: 8),
          _SectionLabel(
            text: AppStrings.literal('ردیف آمار (رسیدن / باقی‌مانده / زمان)'),
          ),
          _SliderSetting(
            icon: Icons.text_fields_rounded,
            iconColor: const Color(0xFF5CC8FF),
            title: AppStrings.literal('اندازه فونت آمار'),
            subtitle: AppStrings.literal('اندازه نوشته‌های ردیف پایین کارت'),
            value: appearance.routeCardStatsFontSize,
            onChanged: (v) =>
                notifier.update((s) => s.copyWith(routeCardStatsFontSize: v)),
          ),
          const RowDivider(),
          _ColorSetting(
            icon: Icons.palette_rounded,
            iconColor: const Color(0xFF5CC8FF),
            title: AppStrings.literal('رنگ آمار'),
            subtitle: AppStrings.literal('رنگ نوشته‌های ردیف پایین کارت'),
            color: appearance.routeCardStatsColor,
            onChanged: (c) =>
                notifier.update((s) => s.copyWith(routeCardStatsColor: c)),
          ),
        ],
      ),
    );
  }
}

/// برچسبِ کوچکِ جداکنندهٔ گروهِ کنترل‌های هر بخشِ کارت (فلش/فاصله/متنِ
/// راهنما/آمار) — صرفاً یک متنِ خاکستریِ راست‌چین با کمی فاصلهٔ بالا و
/// پایین، بدون هیچ منطقی.
class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Text(
          text,
          textAlign: TextAlign.right,
          style: TextStyle(
            color: AppColors.textMuted(context),
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      );
}

// ============================================================
// بخش ۳: ویجت آب‌وهوا.
// ============================================================

class _RouteAlertSettingsCard extends ConsumerWidget {
  const _RouteAlertSettingsCard();

  static const _previewAlerts = [
    RouteAlert(type: RouteAlertType.trafficLight, location: LatLng(0, 0)),
    RouteAlert(type: RouteAlertType.speedBump, location: LatLng(0, 0)),
    RouteAlert(type: RouteAlertType.policeCheckpoint, location: LatLng(0, 0)),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appearance = ref.watch(appearanceSettingsProvider);
    final notifier = ref.read(appearanceSettingsProvider.notifier);
    final accent = AppColors.primaryAccent(context);

    return _GlassCard(
      icon: Icons.warning_amber_rounded,
      iconColor: accent,
      title: AppStrings.literal('هشدارهای مسیر'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: RoadAlertStack(
              alerts: _previewAlerts,
              sizePercent: appearance.routeAlertSizePercent,
            ),
          ),
          const SizedBox(height: 16),
          _SliderSetting(
            icon: Icons.photo_size_select_small_rounded,
            iconColor: accent,
            title: AppStrings.literal('اندازه هشدارها'),
            subtitle: AppStrings.literal('اندازه کارت‌های هشدار روی نقشه'),
            value: ((appearance.routeAlertSizePercent - 70.0) / 60.0)
                .clamp(0.0, 1.0),
            onChanged: (v) => notifier.update(
              (s) => s.copyWith(routeAlertSizePercent: 70.0 + v * 60.0),
            ),
          ),
        ],
      ),
    );
  }
}

class _SystemInfoWidgetSettingsCard extends ConsumerWidget {
  const _SystemInfoWidgetSettingsCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appearance = ref.watch(appearanceSettingsProvider);
    final notifier = ref.read(appearanceSettingsProvider.notifier);

    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _SwitchSetting(
          icon: Icons.schedule_rounded,
          iconColor: const Color(0xFF62D8FF),
          title: AppStrings.literal('روشن / خاموش'),
          subtitle: AppStrings.literal('نمایش ساعت و درصد باتری روی نقشه'),
          value: appearance.systemInfoEnabled,
          onChanged: (v) =>
              notifier.update((s) => s.copyWith(systemInfoEnabled: v)),
        ),
        const RowDivider(),
        _SliderSetting(
          icon: Icons.swap_vert_rounded,
          iconColor: const Color(0xFF49C7E7),
          title: AppStrings.literal('جایگاه عمودی'),
          subtitle: AppStrings.literal('موقعیت عمودی ساعت و باتری'),
          min: 0,
          max: 100,
          value: appearance.systemInfoVerticalPercent,
          trailing: _BiStepper(
            value: appearance.systemInfoVerticalPercent,
            startIcon: Icons.keyboard_arrow_up_rounded,
            endIcon: Icons.keyboard_arrow_down_rounded,
            onChanged: (v) =>
                notifier.update((s) => s.copyWith(systemInfoVerticalPercent: v)),
          ),
          onChanged: (v) =>
              notifier.update((s) => s.copyWith(systemInfoVerticalPercent: v)),
        ),
        const RowDivider(),
        _SliderSetting(
          icon: Icons.swap_horiz_rounded,
          iconColor: const Color(0xFFB57BFF),
          title: AppStrings.literal('جایگاه افقی'),
          subtitle: AppStrings.literal('موقعیت افقی ساعت و باتری'),
          min: 0,
          max: 100,
          value: appearance.systemInfoHorizontalPercent,
          trailing: _TriStepper(
            onLeft: () => notifier.update(
                (s) => s.copyWith(systemInfoHorizontalPercent: 0)),
            onCenter: () => notifier.update(
                (s) => s.copyWith(systemInfoHorizontalPercent: 50)),
            onRight: () => notifier.update(
                (s) => s.copyWith(systemInfoHorizontalPercent: 100)),
          ),
          onChanged: (v) =>
              notifier.update((s) => s.copyWith(systemInfoHorizontalPercent: v)),
        ),
        const RowDivider(),
        _SliderSetting(
          icon: Icons.crop_free_rounded,
          iconColor: const Color(0xFF8FD14F),
          title: AppStrings.literal('اندازه'),
          subtitle: AppStrings.literal('اندازهٔ ویجت ساعت و باتری'),
          min: 70,
          max: 150,
          value: appearance.systemInfoSize,
          trailing: _ExpandButton(
            onTap: () =>
                notifier.update((s) => s.copyWith(systemInfoSize: 100)),
          ),
          onChanged: (v) =>
              notifier.update((s) => s.copyWith(systemInfoSize: v)),
        ),
        const RowDivider(),
        _SliderSetting(
          icon: Icons.compare_arrows_rounded,
          iconColor: const Color(0xFFF2A93C),
          title: AppStrings.literal('تراز محتوا'),
          subtitle: AppStrings.literal('چپ یا راست بودن نوشته‌ها'),
          min: 0,
          max: 100,
          value: appearance.systemInfoContentAlign,
          trailing: _TriStepper(
            onLeft: () => notifier.update(
                (s) => s.copyWith(systemInfoContentAlign: 0)),
            onCenter: () => notifier.update(
                (s) => s.copyWith(systemInfoContentAlign: 50)),
            onRight: () => notifier.update(
                (s) => s.copyWith(systemInfoContentAlign: 100)),
          ),
          onChanged: (v) =>
              notifier.update((s) => s.copyWith(systemInfoContentAlign: v)),
        ),
        const RowDivider(),
        _ColorSetting(
          icon: Icons.format_color_fill_rounded,
          iconColor: const Color(0xFFFF6FA5),
          title: AppStrings.literal('رنگ پس‌زمینه'),
          subtitle: AppStrings.literal('رنگ پس‌زمینه ویجت'),
          color: appearance.systemInfoBgColor,
          onChanged: (c) =>
              notifier.update((s) => s.copyWith(systemInfoBgColor: c)),
        ),
        const RowDivider(),
        _SliderSetting(
          icon: Icons.opacity_rounded,
          iconColor: const Color(0xFF5CC8FF),
          title: AppStrings.literal('شفافیت پس‌زمینه'),
          subtitle: AppStrings.literal('میزان شفافیت پس‌زمینه'),
          min: 0,
          max: 1,
          value: appearance.systemInfoBgOpacity,
          trailing:
              _PercentChip(value: (appearance.systemInfoBgOpacity * 100).round()),
          onChanged: (v) =>
              notifier.update((s) => s.copyWith(systemInfoBgOpacity: v)),
        ),
        const RowDivider(),
        _ColorSetting(
          icon: Icons.format_color_text_rounded,
          iconColor: const Color(0xFFF2D93C),
          title: AppStrings.literal('رنگ نوشته و باتری'),
          subtitle: AppStrings.literal('رنگ ساعت، درصد و آیکون باتری'),
          color: appearance.systemInfoTextColor,
          onChanged: (c) =>
              notifier.update((s) => s.copyWith(systemInfoTextColor: c)),
        ),
        const RowDivider(),
        _SwitchSetting(
          icon: Icons.battery_std_rounded,
          iconColor: const Color(0xFF6FE0A0),
          title: AppStrings.literal('جهتِ آیکون باتری'),
          subtitle: AppStrings.literal('روشن = عمودی، خاموش = افقی'),
          value: appearance.systemInfoBatteryOrientation ==
              BatteryIconOrientation.vertical,
          onChanged: (v) => notifier.update((s) => s.copyWith(
              systemInfoBatteryOrientation: v
                  ? BatteryIconOrientation.vertical
                  : BatteryIconOrientation.horizontal)),
        ),
        const RowDivider(),
        _SliderSetting(
          icon: Icons.zoom_out_map_rounded,
          iconColor: const Color(0xFF6FE0A0),
          title: AppStrings.literal('اندازهٔ آیکون باتری'),
          subtitle: AppStrings.literal('اندازهٔ اختصاصیِ آیکونِ باتری'),
          min: 60,
          max: 160,
          value: appearance.systemInfoBatterySizePercent,
          trailing: _ExpandButton(
            onTap: () => notifier
                .update((s) => s.copyWith(systemInfoBatterySizePercent: 100)),
          ),
          onChanged: (v) => notifier
              .update((s) => s.copyWith(systemInfoBatterySizePercent: v)),
        ),
        const RowDivider(),
        _ColorSetting(
          icon: Icons.battery_charging_full_rounded,
          iconColor: const Color(0xFF6FE0A0),
          title: AppStrings.literal('رنگ آیکون باتری'),
          subtitle: AppStrings.literal('در صورتِ خاموش‌بودن، رنگِ نوشته استفاده می‌شود'),
          color: appearance.systemInfoBatteryColor.alpha == 0
              ? appearance.systemInfoTextColor
              : appearance.systemInfoBatteryColor,
          onChanged: (c) =>
              notifier.update((s) => s.copyWith(systemInfoBatteryColor: c)),
        ),
      ],
    );

    return _GlassCard(
      icon: Icons.schedule_rounded,
      iconColor: const Color(0xFF62D8FF),
      title: AppStrings.literal('ویجت ساعت و باتری'),
      headerLeading: Switch.adaptive(
        value: appearance.systemInfoEnabled,
        onChanged: (v) =>
            notifier.update((s) => s.copyWith(systemInfoEnabled: v)),
        activeColor: AppColors.primaryAccent(context),
      ),
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 180),
        opacity: appearance.systemInfoEnabled ? 1 : 0.45,
        child: IgnorePointer(
          ignoring: !appearance.systemInfoEnabled,
          child: content,
        ),
      ),
    );
  }
}

/// کارتِ تنظیماتِ فونتِ سراسریِ اپ: اندازه، رنگ و ضخامت. مقادیرِ
/// پیش‌فرض هیچ اوراردایی اعمال نمی‌کنند، پس با نصبِ تازه ظاهر تغییری
/// نمی‌کند.
class _FontSettingsCard extends ConsumerWidget {
  const _FontSettingsCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appearance = ref.watch(appearanceSettingsProvider);
    final notifier = ref.read(appearanceSettingsProvider.notifier);
    final accent = AppColors.primaryAccent(context);

    final weightLabels = {
      AppFontWeightOption.asDesigned: AppStrings.literal('پیش‌فرض'),
      AppFontWeightOption.light: AppStrings.literal('نازک'),
      AppFontWeightOption.regular: AppStrings.literal('معمولی'),
      AppFontWeightOption.medium: AppStrings.literal('متوسط'),
      AppFontWeightOption.semiBold: AppStrings.literal('نیمه‌ضخیم'),
      AppFontWeightOption.bold: AppStrings.literal('ضخیم'),
      AppFontWeightOption.extraBold: AppStrings.literal('خیلی ضخیم'),
    };

    return _GlassCard(
      icon: Icons.text_fields_rounded,
      iconColor: const Color(0xFFF2A93C),
      title: AppStrings.literal('تنظیمات فونت'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _SliderSetting(
            icon: Icons.format_size_rounded,
            iconColor: const Color(0xFFF2A93C),
            title: AppStrings.literal('اندازهٔ فونت'),
            subtitle: AppStrings.literal('اندازهٔ نوشته‌های اپ'),
            min: 80,
            max: 140,
            value: appearance.appFontSizePercent,
            trailing: _ExpandButton(
              onTap: () =>
                  notifier.update((s) => s.copyWith(appFontSizePercent: 100)),
            ),
            onChanged: (v) =>
                notifier.update((s) => s.copyWith(appFontSizePercent: v)),
          ),
          const RowDivider(),
          _ColorSetting(
            icon: Icons.format_color_text_rounded,
            iconColor: const Color(0xFFF2A93C),
            title: AppStrings.literal('رنگ فونت'),
            subtitle: AppStrings.literal('خاموش = رنگِ پیش‌فرضِ هر بخش'),
            color: appearance.appFontColor.alpha == 0
                ? AppColors.textPrimary(context)
                : appearance.appFontColor,
            onChanged: (c) =>
                notifier.update((s) => s.copyWith(appFontColor: c)),
          ),
          const RowDivider(),
          if (appearance.appFontColor.alpha != 0)
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                onPressed: () => notifier.update(
                    (s) => s.copyWith(appFontColor: Colors.transparent)),
                child: Text(AppStrings.literal('بازگشت به رنگِ پیش‌فرض')),
              ),
            ),
          _SettingHeader(
            icon: Icons.line_weight_rounded,
            iconColor: const Color(0xFFF2A93C),
            title: AppStrings.literal('ضخامت فونت'),
            subtitle: AppStrings.literal('ضخامتِ نوشته‌های اپ'),
          ),
          const SizedBox(height: 8),
          Wrap(
            alignment: WrapAlignment.end,
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final option in AppFontWeightOption.values)
                ChoiceChip(
                  label: Text(weightLabels[option] ?? option.name),
                  selected: appearance.appFontWeightOption == option,
                  selectedColor: accent.withOpacity(0.25),
                  onSelected: (_) => notifier
                      .update((s) => s.copyWith(appFontWeightOption: option)),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
