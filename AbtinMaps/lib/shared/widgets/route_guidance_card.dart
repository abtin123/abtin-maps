import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';

import '../../features/settings/domain/appearance_settings.dart';

/// دادهٔ نمایشیِ یک کارتِ راهنمای مسیر — مستقل از منبع، چه از
/// ناوبریِ زنده بیاید و چه از دادهٔ نمونهٔ پیش‌نمایشِ تنظیمات.
@immutable
class RouteGuidanceCardData {
  const RouteGuidanceCardData({
    required this.icon,
    required this.distanceText,
    required this.streetText,
    required this.etaLabel,
    required this.etaValue,
    required this.remainingLabel,
    required this.remainingValue,
    required this.durationLabel,
    required this.durationValue,
    this.onClose,
    this.iconWidget,
  });

  final IconData icon;

  /// فاصله تا پیچ بعدی؛ اگر خالی باشد این سطر اصلاً نمایش داده نمی‌شود.
  final String distanceText;

  /// متنِ راهنما (نام خیابان/دستورِ مسیر).
  final String streetText;

  final String etaLabel;
  final String etaValue;
  final String remainingLabel;
  final String remainingValue;
  final String durationLabel;
  final String durationValue;

  /// اگر null باشد دکمهٔ بستن نمایش داده نمی‌شود (برای پیش‌نمایش تنظیمات).
  final VoidCallback? onClose;

  /// رندر سفارشی فقط برای مانورهایی مثل میدان؛ قاب و چیدمان کارت ثابت می‌ماند.
  final Widget? iconWidget;
}

/// کارتِ شناورِ راهنمای مسیر — همان کارتی که هنگام ناوبریِ فعال روی
/// نقشه دیده می‌شود. ظاهرِ کلیِ کارت (بلندی، شفافیت، گردیِ گوشه، درخشش)
/// و همچنین اندازه/رنگِ هر بخش (فلشِ جهت‌نما، فاصله تا پیچ، نام خیابان،
/// ردیفِ آمار پایین) هر کدام مستقلاً از [AppearanceSettings] خوانده
/// می‌شوند — دقیقاً همان مقادیری که در «تنظیمات ظاهر > کارت مسیریابی»
/// تنظیم می‌شوند.
///
/// این ویجت هم در صفحهٔ اصلیِ نقشه هنگامِ ناوبریِ فعال استفاده می‌شود و
/// هم به‌عنوانِ پیش‌نمایشِ زنده در خودِ صفحهٔ تنظیمات (با دادهٔ نمونه).
class RouteGuidanceCard extends StatelessWidget {
  const RouteGuidanceCard({
    super.key,
    required this.settings,
    required this.data,
  });

  final AppearanceSettings settings;
  final RouteGuidanceCardData data;

  static double _lerp(double min, double max, double t) =>
      min + (max - min) * t.clamp(0.0, 1.0);

  double get _arrowBoxSize => _lerp(32, 64, settings.routeCardArrowSize);
  double get _distanceFontSize =>
      _lerp(18, 34, settings.routeCardDistanceFontSize);
  double get _streetFontSize =>
      _lerp(10, 20, settings.routeCardStreetFontSize);
  double get _statsValueFontSize =>
      _lerp(8, 16, settings.routeCardStatsFontSize);
  double get _statsLabelFontSize => _statsValueFontSize * 0.75;
  double get _cornerRadius => _lerp(10, 28, settings.routeCardCornerRadius);
  double get _verticalPadding => _lerp(10, 22, settings.routeCardHeight);

  @override
  Widget build(BuildContext context) {
    final glow = settings.routeCardGlowIntensity;

    return ClipRRect(
      borderRadius: BorderRadius.circular(_cornerRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 25, sigmaY: 25),
        child: Container(
          padding:
              EdgeInsets.fromLTRB(16, _verticalPadding, 16, _verticalPadding - 4),
          decoration: BoxDecoration(
            color: const Color(0x80182541).withOpacity(settings.routeCardOpacity),
            borderRadius: BorderRadius.circular(_cornerRadius),
            border: Border.all(color: Colors.white.withOpacity(.15)),
            boxShadow: [
              const BoxShadow(
                  color: Colors.black45, blurRadius: 26, offset: Offset(0, 10)),
              if (glow > 0)
                BoxShadow(
                  color: settings.routeCardArrowColor.withOpacity(0.35 * glow),
                  blurRadius: 30 * glow,
                  spreadRadius: 2 * glow,
                ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  SizedBox(
                    width: _arrowBoxSize,
                    height: _arrowBoxSize,
                    child: data.iconWidget ??
                        Icon(
                          data.icon,
                          color: settings.routeCardArrowColor,
                          size: _arrowBoxSize * 0.75,
                          shadows: [
                            Shadow(
                              color: settings.routeCardArrowColor.withOpacity(.5),
                              blurRadius: 20,
                            ),
                          ],
                        ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        if (data.distanceText.isNotEmpty)
                          Text(
                            data.distanceText,
                            textAlign: TextAlign.right,
                            style: TextStyle(
                              color: settings.routeCardDistanceColor,
                              fontSize: _distanceFontSize,
                              fontWeight: FontWeight.w900,
                              letterSpacing: -0.5,
                            ),
                          ),
                          Text(
                            data.streetText,
                            textAlign: TextAlign.right,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: settings.routeCardStreetColor,
                              fontSize: _streetFontSize,
                              fontWeight: FontWeight.w600,
                              height: 1.2,
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Container(
                padding:
                    const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          _StatColumn(
                            label: data.etaLabel,
                            value: data.etaValue,
                            color: settings.routeCardStatsColor,
                            valueFontSize: _statsValueFontSize,
                            labelFontSize: _statsLabelFontSize,
                          ),
                          _StatColumn(
                            label: data.remainingLabel,
                            value: data.remainingValue,
                            color: settings.routeCardStatsColor,
                            valueFontSize: _statsValueFontSize,
                            labelFontSize: _statsLabelFontSize,
                          ),
                          _StatColumn(
                            label: data.durationLabel,
                            value: data.durationValue,
                            color: settings.routeCardStatsColor,
                            valueFontSize: _statsValueFontSize,
                            labelFontSize: _statsLabelFontSize,
                          ),
                        ],
                      ),
                    ),
                    if (data.onClose != null) ...[
                      const SizedBox(width: 12),
                      GestureDetector(
                        onTap: data.onClose,
                        child: Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: Colors.white.withOpacity(.1),
                          ),
                          child: const Icon(Icons.close_rounded,
                              color: Colors.white70, size: 16),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class RoundaboutManeuverIcon extends StatelessWidget {
  const RoundaboutManeuverIcon({
    super.key,
    required this.color,
    this.exit,
    this.exitCount,
    this.angleDegrees,
  });

  final Color color;
  final int? exit;
  final int? exitCount;
  final double? angleDegrees;

  @override
  Widget build(BuildContext context) => CustomPaint(
        painter: _RoundaboutManeuverPainter(
          color: color,
          exit: exit,
          exitCount: exitCount,
          angleDegrees: angleDegrees,
        ),
        child: const SizedBox.expand(),
      );
}

class _RoundaboutManeuverPainter extends CustomPainter {
  const _RoundaboutManeuverPainter({
    required this.color,
    required this.exit,
    required this.exitCount,
    required this.angleDegrees,
  });

  final Color color;
  final int? exit;
  final int? exitCount;
  final double? angleDegrees;

  @override
  void paint(Canvas canvas, Size size) {
    final side = math.min(size.width, size.height);
    if (side <= 0) return;
    final center = Offset(size.width / 2, size.height / 2);
    final radius = side * .29;
    final stroke = (side * .065).clamp(2.2, 4.5).toDouble();
    final selectedStroke = stroke * 1.45;

    final count = (exitCount ?? exit ?? 4).clamp(2, 8);
    final selected = exit == null ? null : exit!.clamp(1, count);

    // حلقه‌ی میدان، کم‌رنگ؛ خروجی اصلی بعداً پررنگ می‌شود.
    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..color = color.withOpacity(.30)
        ..style = PaintingStyle.stroke
        ..strokeWidth = stroke
        ..strokeCap = StrokeCap.round,
    );

    // مسیر ورود خودرو از پایین.
    final entryPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = selectedStroke
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(
      Offset(center.dx, center.dy + radius + side * .18),
      Offset(center.dx, center.dy + radius * .78),
      entryPaint,
    );

    // تمام خروجی‌های واقعیِ قابل استفاده‌ی میدان.
    for (var i = 0; i < count; i++) {
      final isSelected = selected != null && i + 1 == selected;
      final angle = math.pi / 2 - (i * 2 * math.pi / count);
      final inner = Offset(
        center.dx + math.cos(angle) * radius,
        center.dy + math.sin(angle) * radius,
      );
      final outerRadius = radius + (isSelected ? side * .18 : side * .13);
      final outer = Offset(
        center.dx + math.cos(angle) * outerRadius,
        center.dy + math.sin(angle) * outerRadius,
      );
      final paint = Paint()
        ..color = isSelected ? color : color.withOpacity(.52)
        ..style = PaintingStyle.stroke
        ..strokeWidth = isSelected ? selectedStroke : stroke * .8
        ..strokeCap = StrokeCap.round;
      canvas.drawLine(inner, outer, paint);

      if (isSelected) {
        final tip = outer;
        final tangent = angle - math.pi / 2;
        final arrowSize = side * .12;
        final left = tip + Offset(
          math.cos(tangent + math.pi * .72) * arrowSize,
          math.sin(tangent + math.pi * .72) * arrowSize,
        );
        final right = tip + Offset(
          math.cos(tangent - math.pi * .72) * arrowSize,
          math.sin(tangent - math.pi * .72) * arrowSize,
        );
        canvas.drawPath(
          Path()
            ..moveTo(tip.dx, tip.dy)
            ..lineTo(left.dx, left.dy)
            ..lineTo(right.dx, right.dy)
            ..close(),
          Paint()..color = color,
        );
      }
    }

    // قوسِ مسیر انتخاب‌شده داخل میدان؛ فقط برای جهت‌یابی خواناتر است و با
    // angle واقعیِ محاسبه‌شده از router می‌چرخد.
    if (angleDegrees != null) {
      final sweep = angleDegrees!.clamp(-330.0, 330.0) * math.pi / 180;
      final rect = Rect.fromCircle(center: center, radius: radius);
      canvas.drawArc(
        rect,
        math.pi / 2,
        -sweep,
        false,
        Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeWidth = selectedStroke
          ..strokeCap = StrokeCap.round,
      );
    }

    // مرکز خالی بماند تا فرم میدان واضح باشد.
    canvas.drawCircle(
      center,
      radius * .34,
      Paint()..color = const Color(0xFF11151B),
    );

    if (exit != null) {
      final text = TextPainter(
        text: TextSpan(
          text: '$exit',
          style: TextStyle(
            color: color,
            fontSize: side * .23,
            fontWeight: FontWeight.w900,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: side * .42);
      text.paint(
        canvas,
        Offset(center.dx - text.width / 2, center.dy - text.height / 2),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _RoundaboutManeuverPainter oldDelegate) =>
      oldDelegate.color != color ||
      oldDelegate.exit != exit ||
      oldDelegate.exitCount != exitCount ||
      oldDelegate.angleDegrees != angleDegrees;
}

class _StatColumn extends StatelessWidget {
  const _StatColumn({
    required this.label,
    required this.value,
    required this.color,
    required this.valueFontSize,
    required this.labelFontSize,
  });

  final String label;
  final String value;
  final Color color;
  final double valueFontSize;
  final double labelFontSize;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      mainAxisSize: MainAxisSize.min,
      children: [
        Flexible(
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              value,
              maxLines: 1,
              style: TextStyle(
                color: color,
                fontSize: valueFontSize,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
        Flexible(
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              label,
              maxLines: 1,
              style: TextStyle(
                  color: color.withOpacity(.6), fontSize: labelFontSize),
            ),
          ),
        ),
      ],
    );
  }
}
