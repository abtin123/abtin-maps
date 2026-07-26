import 'dart:typed_data' show Float64List;
import 'road_graph.dart';

class RoadGraphBuilder {
  static String overpassQuery({
    required double south,
    required double west,
    required double north,
    required double east,
    int timeoutSec = 55,
  }) {
    return '''
[out:json][timeout:$timeoutSec];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)\$"]($south,$west,$north,$east);
);
(._;>;);
out body;
''';
  }

  static RoadGraph build(Map<String, dynamic> overpassJson) {
    final elements = overpassJson['elements'] as List;

    final osmIdToLat = <int, double>{};
    final osmIdToLng = <int, double>{};
    for (final el in elements) {
      if (el['type'] == 'node') {
        final id = el['id'] as int;
        osmIdToLat[id] = (el['lat'] as num).toDouble();
        osmIdToLng[id] = (el['lon'] as num).toDouble();
      }
    }

    final nodeIndexOf = <int, int>{};
    final lats = <double>[];
    final lngs = <double>[];
    int indexFor(int osmId) {
      final existing = nodeIndexOf[osmId];
      if (existing != null) return existing;
      final idx = lats.length;
      lats.add(osmIdToLat[osmId]!);
      lngs.add(osmIdToLng[osmId]!);
      nodeIndexOf[osmId] = idx;
      return idx;
    }

    final roadNames = <String>[];
    final nameIndexOf = <String, int>{};
    int nameIndexFor(String? name) {
      if (name == null || name.isEmpty) return -1;
      final existing = nameIndexOf[name];
      if (existing != null) return existing;
      final idx = roadNames.length;
      roadNames.add(name);
      nameIndexOf[name] = idx;
      return idx;
    }

    final adjacency = <List<RoadEdge>>[];

    void ensureAdjacencySize(int n) {
      while (adjacency.length < n) {
        adjacency.add(<RoadEdge>[]);
      }
    }

    for (final el in elements) {
      if (el['type'] != 'way') continue;
      final tags = (el['tags'] as Map?)?.cast<String, dynamic>() ?? const {};
      final wayNodes = (el['nodes'] as List).cast<int>();
      if (wayNodes.length < 2) continue;

      final name = (tags['name'] as String?) ?? (tags['name:fa'] as String?);
      final nameIdx = nameIndexFor(name);

      final onewayTag = (tags['oneway'] as String?)?.toLowerCase();
      final isOneway = onewayTag == 'yes' || onewayTag == 'true' || onewayTag == '1';
      final isReversedOneway = onewayTag == '-1';

      for (var i = 0; i < wayNodes.length - 1; i++) {
        final aOsm = wayNodes[i];
        final bOsm = wayNodes[i + 1];
        if (!osmIdToLat.containsKey(aOsm) || !osmIdToLat.containsKey(bOsm)) {
          continue;
        }
        final aIdx = indexFor(aOsm);
        final bIdx = indexFor(bOsm);
        ensureAdjacencySize(lats.length);

        final dist = RoadGraph.haversineM(
          osmIdToLat[aOsm]!,
          osmIdToLng[aOsm]!,
          osmIdToLat[bOsm]!,
          osmIdToLng[bOsm]!,
        );

        if (isReversedOneway) {
          adjacency[bIdx].add(RoadEdge(to: aIdx, distanceM: dist, nameIndex: nameIdx));
        } else {
          adjacency[aIdx].add(RoadEdge(to: bIdx, distanceM: dist, nameIndex: nameIdx));
          if (!isOneway) {
            adjacency[bIdx].add(RoadEdge(to: aIdx, distanceM: dist, nameIndex: nameIdx));
          }
        }
      }
    }

    ensureAdjacencySize(lats.length);

    return RoadGraph(
      lats: _toFloat64List(lats),
      lngs: _toFloat64List(lngs),
      adjacency: adjacency,
      roadNames: roadNames,
    );
  }
}

Float64List _toFloat64List(List<double> src) => Float64List.fromList(src);
