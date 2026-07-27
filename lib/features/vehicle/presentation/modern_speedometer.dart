import 'dart:math' as math;
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../weather/presentation/weather_providers.dart';

class ModernSpeedometer extends ConsumerWidget {
  final double speedKmh;
  final double maxSpeed;

  const ModernSpeedometer({
    super.key,
    required this.speedKmh,
    this.maxSpeed = 240.0,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentSpeed = speedKmh.clamp(0.0, maxSpeed);
    
    // Scale everything down by roughly 0.6x (close to half)
    return Stack(
      alignment: Alignment.center,
      children: [
        // Background Glow
        Container(
          width: 90,
          height: 90,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: _getSpeedColor(currentSpeed).withOpacity(0.1),
                blurRadius: 15,
                spreadRadius: 2,
              ),
            ],
          ),
        ),
        
        // Outer Ring & Ticks
        CustomPaint(
          size: const Size(100, 100),
          painter: _SpeedometerPainter(speed: currentSpeed, maxSpeed: maxSpeed),
        ),
        
        // Speed Text (Digital Style)
        Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              currentSpeed.toInt().toString(),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 28, // Scaled down from 54
                fontWeight: FontWeight.w300,
                letterSpacing: -1,
                fontFamily: 'monospace',
              ),
            ),
            const Text(
              'km/h',
              style: TextStyle(
                color: Colors.white60,
                fontSize: 8, // Scaled down from 12
                fontWeight: FontWeight.w400,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Color _getSpeedColor(double speed) {
    if (speed < 80) return AppColors.speedLow;
    if (speed < 160) return AppColors.speedMid;
    return AppColors.speedHigh;
  }

  IconData _getWeatherIcon(String? code) {
    if (code == null) return Icons.wb_sunny_rounded;
    int c = int.tryParse(code) ?? 0;
    if (c == 0) return Icons.wb_sunny_rounded;
    if (c <= 3) return Icons.wb_cloudy_rounded;
    if (c <= 65) return Icons.umbrella_rounded;
    return Icons.wb_sunny_rounded;
  }
}

class _SpeedometerPainter extends CustomPainter {
  final double speed;
  final double maxSpeed;

  _SpeedometerPainter({required this.speed, required this.maxSpeed});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    
    // Background Arc
    final bgPaint = Paint()
      ..color = Colors.white.withOpacity(0.05)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 12
      ..strokeCap = StrokeCap.round;
      
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius - 10),
      math.pi * 0.75,
      math.pi * 1.5,
      false,
      bgPaint,
    );
    
    // Dynamic Speed Arc
    final speedPercent = (speed / maxSpeed).clamp(0.0, 1.0);
    final speedPaint = Paint()
      ..shader = SweepGradient(
        colors: const [
          AppColors.speedLow,
          AppColors.speedMid,
          AppColors.speedHigh,
        ],
        stops: const [0.0, 0.5, 1.0],
        startAngle: math.pi * 0.75,
        endAngle: math.pi * 2.25,
      ).createShader(Rect.fromCircle(center: center, radius: radius))
      ..style = PaintingStyle.stroke
      ..strokeWidth = 14
      ..strokeCap = StrokeCap.round;
      
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius - 10),
      math.pi * 0.75,
      math.pi * 1.5 * speedPercent,
      false,
      speedPaint,
    );
    
    // Draw Ticks and Numbers (Enhanced for 0-240 مدرج)
    final tickPaint = Paint()
      ..color = Colors.white.withOpacity(0.3)
      ..strokeWidth = 1.5;
      
    for (int i = 0; i <= 240; i += 10) {
      final isMajor = i % 40 == 0;
      final angle = math.pi * 0.75 + (math.pi * 1.5 * (i / 240));
      
      final tickLength = isMajor ? 12.0 : 6.0;
      final start = Offset(
        center.dx + (radius - 10) * math.cos(angle),
        center.dy + (radius - 10) * math.sin(angle),
      );
      final end = Offset(
        center.dx + (radius - 10 - tickLength) * math.cos(angle),
        center.dy + (radius - 10 - tickLength) * math.sin(angle),
      );
      
      canvas.drawLine(start, end, tickPaint..color = isMajor ? Colors.white70 : Colors.white30);
      
      if (isMajor) {
        // Draw Numbers exactly as the image
        final textPainter = TextPainter(
          text: TextSpan(
            text: i.toString(),
            style: TextStyle(
              color: Colors.white.withOpacity(0.8),
              fontSize: 8, // Scaled down from 14
              fontWeight: FontWeight.w400,
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        
        final textOffset = Offset(
          center.dx + (radius - 22) * math.cos(angle) - textPainter.width / 2,
          center.dy + (radius - 22) * math.sin(angle) - textPainter.height / 2,
        );
        textPainter.paint(canvas, textOffset);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _SpeedometerPainter oldDelegate) => oldDelegate.speed != speed;
}
