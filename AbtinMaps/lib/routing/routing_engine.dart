import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

class RoutePoint { const RoutePoint(this.lat, this.lon); final double lat, lon; }
class AbmRoutingEngine {
  Future<List<RoutePoint>> route(File graphFile, RoutePoint origin, RoutePoint destination) async {
    if (!await graphFile.exists()) return const [];
    final bytes = await graphFile.readAsBytes();
    const magic = 'ABMGRAPH1\n';
    if (bytes.length < magic.length + 4 || utf8.decode(bytes.sublist(0, magic.length)) != magic) return const [];
    final n = (bytes[magic.length] << 24) | (bytes[magic.length + 1] << 16) | (bytes[magic.length + 2] << 8) | bytes[magic.length + 3];
    final graph = jsonDecode(utf8.decode(bytes.sublist(magic.length + 4, magic.length + 4 + n))) as Map<String, dynamic>;
    final nodes = <int, RoutePoint>{};
    final rawNodes = graph['nodes'] as Map<String, dynamic>? ?? {};
    for (final e in rawNodes.entries) { final v = e.value as List; nodes[int.parse(e.key)] = RoutePoint((v[0] as num).toDouble(), (v[1] as num).toDouble()); }
    if (nodes.isEmpty) return const [];
    int nearest(RoutePoint p) { var id = nodes.keys.first; var best = double.infinity; for (final e in nodes.entries) { final d = _d(p, e.value); if (d < best) { best = d; id = e.key; } } return id; }
    final start = nearest(origin), goal = nearest(destination);
    final adj = <int, List<int>>{};
    for (final e in (graph['edges'] as List? ?? const [])) { final x = e as Map<String, dynamic>; final a = (x['start'] as num).toInt(), b = (x['end'] as num).toInt(); (adj[a] ??= []).add(b); }
    final prev = <int, int?>{start: null}; final queue = <int>[start];
    for (var i = 0; i < queue.length; i++) { final u = queue[i]; if (u == goal) break; for (final v in adj[u] ?? const []) { if (!prev.containsKey(v)) { prev[v] = u; queue.add(v); } } }
    if (!prev.containsKey(goal)) return const [];
    final path = <RoutePoint>[]; int? cur = goal; while (cur != null) { path.add(nodes[cur]!); cur = prev[cur]; } return path.reversed.toList(growable: false);
  }
  double _d(RoutePoint a, RoutePoint b) { final x=(a.lat-b.lat)*111000, y=(a.lon-b.lon)*111000*math.cos(a.lat*math.pi/180); return math.sqrt(x*x+y*y); }
}
