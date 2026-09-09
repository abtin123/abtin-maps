import 'dart:math' as math;
import 'package:flutter/material.dart';

/// آیکون اختصاصی میدان: مسیر ورود، قوس حرکت و شماره خروجی را داخل همان
/// فضای آیکون کارت مسیریابی نشان می‌دهد. خود کارت دست‌نخورده می‌ماند.
class RoundaboutManeuverIcon extends StatelessWidget {
  const RoundaboutManeuverIcon({
    super.key,
    this.exit,
    this.angleDegrees,
    required this.color,
  });

  final int? exit;
  final double? angleDegrees;
  final Color color;

  @override
  Widget build(BuildContext context) => CustomPaint(
        painter: _RoundaboutPainter(
          color: color,
          exit: exit,
          angleDegrees: angleDegrees,
        ),
      );
}

class _RoundaboutPainter extends CustomPainter {
  _RoundaboutPainter({
    required this.color,
    required this.exit,
    required this.angleDegrees,
  });

  final Color color;
  final int? exit;
  final double? angleDegrees;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final radius = math.min(size.width, size.height) * .27;
    final stroke = math.max(2.5, size.shortestSide * .075);

    final ring = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, ring);

    final angle = ((angleDegrees ?? 90) - 90) * math.pi / 180;
    final start = Offset(
      center.dx + math.cos(angle) * radius,
      center.dy + math.sin(angle) * radius,
    );
    final endAngle = angle + math.pi * .78;
    final end = Offset(
      center.dx + math.cos(endAngle) * radius,
      center.dy + math.sin(endAngle) * radius,
    );

    final arrow = Paint()
      ..color = color
      ..style = PaintingStyle.fill;
    final tangent = endAngle + math.pi / 2;
    final tip = end;
    final left = Offset(
      tip.dx + math.cos(tangent + 2.55) * stroke * 2.4,
      tip.dy + math.sin(tangent + 2.55) * stroke * 2.4,
    );
    final right = Offset(
      tip.dx + math.cos(tangent - 2.55) * stroke * 2.4,
      tip.dy + math.sin(tangent - 2.55) * stroke * 2.4,
    );
    canvas.drawPath(
      Path()..moveTo(tip.dx, tip.dy)..lineTo(left.dx,left.dy)..lineTo(right.dx,right.dy)..close(),
      arrow,
    );

    final entry = Paint()
      ..color = color
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(
      Offset(center.dx, center.dy + radius + stroke * .35),
      Offset(center.dx, center.dy + radius * .45),
      entry,
    );

    if (exit != null) {
      final textPainter = TextPainter(
        text: TextSpan(
          text: '$exit',
          style: TextStyle(
            color: color,
            fontSize: size.shortestSide * .28,
            fontWeight: FontWeight.w900,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      textPainter.paint(
        canvas,
        Offset(
          center.dx - textPainter.width / 2,
          center.dy - textPainter.height / 2,
        ),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _RoundaboutPainter oldDelegate) =>
      oldDelegate.color != color ||
      oldDelegate.exit != exit ||
      oldDelegate.angleDegrees != angleDegrees;
}
