import 'dart:math' as math;
import 'package:maplibre_gl/maplibre_gl.dart';
import 'road_graph.dart';
import 'routing_service.dart' show RouteInfo, RouteInstruction;

class _PQItem {
  final int node;
  final double priority;
  const _PQItem(this.node, this.priority);
}

class _MinHeap {
  final List<_PQItem> _items = [];

  bool get isEmpty => _items.isEmpty;

  void push(_PQItem item) {
    _items.add(item);
    var i = _items.length - 1;
    while (i > 0) {
      final parent = (i - 1) >> 1;
      if (_items[parent].priority <= _items[i].priority) break;
      final tmp = _items[parent];
      _items[parent] = _items[i];
      _items[i] = tmp;
      i = parent;
    }
  }

  _PQItem pop() {
    final top = _items[0];
    final last = _items.removeLast();
    if (_items.isNotEmpty) {
      _items[0] = last;
      var i = 0;
      while (true) {
        final l = 2 * i + 1;
        final r = 2 * i + 2;
        var smallest = i;
        if (l < _items.length && _items[l].priority < _items[smallest].priority) smallest = l;
        if (r < _items.length && _items[r].priority < _items[smallest].priority) smallest = r;
        if (smallest == i) break;
        final tmp = _items[smallest];
        _items[smallest] = _items[i];
        _items[i] = tmp;
        i = smallest;
      }
    }
    return top;
  }
}

class OfflineRoutingService {
  String? lastError;

  RouteInfo? calculateRoute({
    required RoadGraph graph,
    required LatLng origin,
    required LatLng destination,
  }) {
    lastError = null;
    final startNode = graph.nearestNode(origin.latitude, origin.longitude);
    final endNode = graph.nearestNode(destination.latitude, destination.longitude);
    if (startNode == null || endNode == null) {
      lastError = 'این منطقه در گراف مسیریابی آفلاین دانلودشده پوشش داده نشده';
      return null;
    }
    if (startNode == endNode) {
      return RouteInfo(
        geometry: [origin, destination],
        distanceKm: 0,
        durationMin: 0,
        instructions: [
          RouteInstruction(text: 'به مقصد رسیدید', distanceMeters: 0, location: destination, type: 'arrive'),
        ],
      );
    }

    final path = _aStar(graph, startNode, endNode);
    if (path == null) {
      lastError = 'مسیری بین این دو نقطه در گراف آفلاین پیدا نشد';
      return null;
    }

    return _buildRouteInfo(graph, path, origin, destination);
  }

  List<int>? _aStar(RoadGraph graph, int start, int goal) {
    final gScore = <int, double>{start: 0};
    final cameFrom = <int, int>{};
    final visited = <int>{};
    final heap = _MinHeap();

    double h(int node) => RoadGraph.haversineM(
          graph.lats[node], graph.lngs[node], graph.lats[goal], graph.lngs[goal],
        );

    heap.push(_PQItem(start, h(start)));

    while (!heap.isEmpty) {
      final current = heap.pop().node;
      if (visited.contains(current)) continue;
      if (current == goal) {
        final path = <int>[goal];
        var node = goal;
        while (cameFrom.containsKey(node)) {
          node = cameFrom[node]!;
          path.add(node);
        }
        return path.reversed.toList();
      }
      visited.add(current);

      for (final edge in graph.adjacency[current]) {
        if (visited.contains(edge.to)) continue;
        final tentativeG = gScore[current]! + edge.distanceM;
        if (tentativeG < (gScore[edge.to] ?? double.infinity)) {
          gScore[edge.to] = tentativeG;
          cameFrom[edge.to] = current;
          heap.push(_PQItem(edge.to, tentativeG + h(edge.to)));
        }
      }
    }
    return null;
  }

  RouteInfo _buildRouteInfo(RoadGraph graph, List<int> path, LatLng origin, LatLng destination) {
    final geometry = <LatLng>[
      origin,
      for (final n in path) LatLng(graph.lats[n], graph.lngs[n]),
      destination,
    ];

    double totalDistance = 0;
    final instructions = <RouteInstruction>[];
    instructions.add(RouteInstruction(
      text: 'حرکت کنید',
      distanceMeters: 0,
      location: LatLng(graph.lats[path.first], graph.lngs[path.first]),
      type: 'depart',
    ));

    String? prevName;
    double segmentDistance = 0;

    for (var i = 0; i < path.length - 1; i++) {
      final a = path[i];
      final b = path[i + 1];
      final edge = graph.adjacency[a].firstWhere((e) => e.to == b);
      totalDistance += edge.distanceM;
      segmentDistance += edge.distanceM;

      final name = edge.nameIndex >= 0 ? graph.roadNames[edge.nameIndex] : null;

      final turnsNext = i + 2 < path.length ? _turnAt(graph, a, b, path[i + 2]) : null;
      final nameChanged = name != null && name != prevName;

      if (turnsNext != null || (nameChanged && i > 0)) {
        instructions.add(RouteInstruction(
          text: _instructionText(turnsNext, name),
          distanceMeters: segmentDistance,
          location: LatLng(graph.lats[b], graph.lngs[b]),
          type: turnsNext == null ? 'new name' : 'turn',
          modifier: turnsNext,
        ));
        segmentDistance = 0;
      }
      if (name != null) prevName = name;
    }

    instructions.add(RouteInstruction(
      text: 'به مقصد رسیدید',
      distanceMeters: 0,
      location: destination,
      type: 'arrive',
    ));

    return RouteInfo(
      geometry: geometry,
      distanceKm: totalDistance / 1000,
      durationMin: (totalDistance / 1000) / 35 * 60,
      instructions: instructions,
    );
  }

  String? _turnAt(RoadGraph graph, int a, int b, int c) {
    final bearing1 = _bearing(graph.lats[a], graph.lngs[a], graph.lats[b], graph.lngs[b]);
    final bearing2 = _bearing(graph.lats[b], graph.lngs[b], graph.lats[c], graph.lngs[c]);
    var delta = bearing2 - bearing1;
    delta = (delta + 540) % 360 - 180;

    if (delta.abs() < 20) return null;
    if (delta > 120) return 'sharp right';
    if (delta > 45) return 'right';
    if (delta > 20) return 'slight right';
    if (delta < -120) return 'sharp left';
    if (delta < -45) return 'left';
    return 'slight left';
  }

  double _bearing(double lat1, double lng1, double lat2, double lng2) {
    final phi1 = lat1 * math.pi / 180;
    final phi2 = lat2 * math.pi / 180;
    final dLambda = (lng2 - lng1) * math.pi / 180;
    final y = math.sin(dLambda) * math.cos(phi2);
    final x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dLambda);
    return (math.atan2(y, x) * 180 / math.pi + 360) % 360;
  }

  String _instructionText(String? modifier, String? roadName) {
    final nameText = (roadName != null && roadName.isNotEmpty) ? ' به $roadName' : '';
    if (modifier == null) {
      return 'ادامه دهید$nameText';
    }
    String direction;
    switch (modifier) {
      case 'sharp right':
        direction = 'کاملاً به راست';
        break;
      case 'right':
        direction = 'به راست';
        break;
      case 'slight right':
        direction = 'کمی به راست';
        break;
      case 'sharp left':
        direction = 'کاملاً به چپ';
        break;
      case 'left':
        direction = 'به چپ';
        break;
      case 'slight left':
        direction = 'کمی به چپ';
        break;
      default:
        direction = '';
    }
    return 'بپیچید $direction$nameText'.trim();
  }
}
