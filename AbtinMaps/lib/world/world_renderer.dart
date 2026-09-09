import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class WorldRenderer extends StatefulWidget {
  const WorldRenderer({super.key, required this.center, required this.zoom, required this.isDark});
  final Offset center;
  final double zoom;
  final bool isDark;

  @override
  State<WorldRenderer> createState() => _WorldRendererState();
}

class _WorldRendererState extends State<WorldRenderer> {
  List<List<List<double>>> _land = const [];
  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    final raw = await rootBundle.loadString('assets/world/world.json');
    final json = jsonDecode(raw) as Map<String, dynamic>;
    final out = <List<List<double>>>[];
    for (final f in (json['features'] as List? ?? const [])) {
      final g = (f as Map<String, dynamic>)['geometry'];
      if (g is List) {
        final ring = <List<double>>[];
        for (final p in g) {
          if (p is List && p.length >= 2 && p[0] is num && p[1] is num) {
            ring.add([(p[0] as num).toDouble(), (p[1] as num).toDouble()]);
          }
        }
        if (ring.length >= 3) out.add(ring);
      }
    }
    if (mounted) setState(() => _land = out);
  }

  @override
  Widget build(BuildContext context) => CustomPaint(
    painter: _WorldPainter(_land, widget.center, widget.zoom, widget.isDark),
    size: Size.infinite,
  );
}

class _WorldPainter extends CustomPainter {
  _WorldPainter(this.land, this.center, this.zoom, this.isDark);
  final List<List<List<double>>> land;
  final Offset center;
  final double zoom;
  final bool isDark;

  Offset project(double lon, double lat, Size size) {
    final scale = math.pow(2, zoom).toDouble() * 0.45;
    var dx = lon - center.dx;
    if (dx > 180) dx -= 360;
    if (dx < -180) dx += 360;
    return Offset(size.width / 2 + dx * scale, size.height / 2 - (lat - center.dy) * scale);
  }

  @override
  void paint(Canvas canvas, Size size) {
    final bg = isDark ? const Color(0xFF101418) : const Color(0xFFEAF1F4);
    final landPaint = Paint()..color = (isDark ? const Color(0xFF35433B) : const Color(0xFFD7E1D5))..style = PaintingStyle.fill;
    final border = Paint()..color = (isDark ? const Color(0xFF56655C) : const Color(0xFFB7C2BA))..style = PaintingStyle.stroke..strokeWidth = 0.7;
    canvas.drawRect(Offset.zero & size, Paint()..color = bg);

    for (final ring in land) {
      final path = Path();
      for (var i = 0; i < ring.length; i++) {
        final q = project(ring[i][0], ring[i][1], size);
        if (i == 0) path.moveTo(q.dx, q.dy); else path.lineTo(q.dx, q.dy);
      }
      path.close();
      canvas.drawPath(path, landPaint);
      canvas.drawPath(path, border);
    }

    final grid = Paint()..color = (isDark ? Colors.white : Colors.black).withOpacity(0.055)..strokeWidth = 0.6;
    for (var lon = -180; lon <= 180; lon += 30) {
      final a = project(lon.toDouble(), -85, size), b = project(lon.toDouble(), 85, size);
      canvas.drawLine(a, b, grid);
    }
    for (var lat = -60; lat <= 60; lat += 30) {
      final a = project(-180, lat.toDouble(), size), b = project(180, lat.toDouble(), size);
      canvas.drawLine(a, b, grid);
    }
  }

  @override
  bool shouldRepaint(covariant _WorldPainter old) => old.center != center || old.zoom != zoom || old.isDark != isDark || old.land != land;
}
