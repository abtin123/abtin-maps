import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'abm_reader.dart';
import '../styles/style_manager.dart';

class VectorMapRenderer extends StatelessWidget {
  const VectorMapRenderer({super.key, required this.features, required this.style, required this.center, required this.zoom, this.route = const []});
  final List<AbmFeature> features;
  final MapStyle style;
  final Offset center;
  final double zoom;
  final List<List<double>> route;

  @override
  Widget build(BuildContext context) => CustomPaint(painter: _VectorPainter(features, style, center, zoom, route));
}

class _VectorPainter extends CustomPainter {
  _VectorPainter(this.features, this.style, this.center, this.zoom, this.route);
  final List<AbmFeature> features; final MapStyle style; final Offset center; final double zoom; final List<List<double>> route;
  Offset project(double lon, double lat, Size size) {
    final scale = math.pow(2, zoom).toDouble() * 0.45;
    return Offset(size.width / 2 + (lon - center.dx) * scale, size.height / 2 - (lat - center.dy) * scale);
  }
  @override void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = style.background);
    for (final f in features) {
      if (f.geometry.length < 2) continue;
      final cls = '${f.tags['highway'] ?? f.tags['landuse'] ?? f.tags['natural'] ?? ''}'.toLowerCase();
      final paint = Paint()..style = (f.tags['building'] != null || f.tags['landuse'] != null || f.tags['natural'] != null) ? PaintingStyle.fill : PaintingStyle.stroke;
      paint.color = f.tags['building'] != null ? style.building : (f.tags['waterway'] != null || f.tags['natural'] == 'water' ? style.water : (cls == 'motorway' || cls == 'trunk' ? style.motorway : style.road));
      paint.strokeWidth = math.max(0.6, math.min(12, (zoom - 3) * 0.55));
      final path = Path();
      for (var i = 0; i < f.geometry.length; i++) {
        final q = project(f.geometry[i][0], f.geometry[i][1], size);
        if (i == 0) path.moveTo(q.dx, q.dy); else path.lineTo(q.dx, q.dy);
      }
      canvas.drawPath(path, paint);
      final name = '${f.tags['name_fa'] ?? f.tags['name'] ?? f.tags['name_en'] ?? ''}'.trim();
      if (name.isNotEmpty && (f.layer == 'roads' || f.layer == 'places')) {
        final q = project(f.geometry[f.geometry.length ~/ 2][0], f.geometry[f.geometry.length ~/ 2][1], size);
        final tp = TextPainter(text: TextSpan(text:name,style:TextStyle(fontSize:f.layer=='places'?12:9,color:style.label,fontWeight:f.layer=='places'?FontWeight.w600:FontWeight.w400)),textDirection:TextDirection.ltr)..layout(maxWidth:180);
        tp.paint(canvas,q+const Offset(3,-8));
      }
    }
    if (route.length > 1) {
      final p = Paint()..style = PaintingStyle.stroke..strokeWidth = 7..strokeCap = StrokeCap.round..color = const Color(0xFF2FE6C4);
      final path = Path();
      for (var i = 0; i < route.length; i++) { final q = project(route[i][0], route[i][1], size); if (i == 0) path.moveTo(q.dx, q.dy); else path.lineTo(q.dx, q.dy); }
      canvas.drawPath(path, p);
    }
  }
  @override bool shouldRepaint(covariant _VectorPainter old) => true;
}
