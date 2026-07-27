import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:maplibre_gl/maplibre_gl.dart';
import '../../../core/database/app_database.dart';

class SearchResult {
  final String title;
  final String subtitle;
  final double lat;
  final double lng;
  final bool isOffline;

  SearchResult({
    required this.title,
    required this.subtitle,
    required this.lat,
    required this.lng,
    required this.isOffline,
  });
}

class SearchService {
  final AppDatabase database;

  SearchService(this.database);

  static const String _nominatimBaseUrl = 'https://nominatim.openstreetmap.org';

  /// Search for places using Nominatim (OSM)
  Future<List<SearchResult>> searchPlaces(String query) async {
    final results = <SearchResult>[];

    try {
      final url = Uri.parse(
        '$_nominatimBaseUrl/search?q=$query&format=json&addressdetails=1&limit=10&countrycodes=ir',
      );

      final response = await http.get(
        url,
        headers: {'User-Agent': 'AbtinNavigator/1.0'},
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as List;
        for (var item in data) {
          final title = (item['display_name'] as String).split(',')[0];
          results.add(SearchResult(
            title: title,
            subtitle: item['display_name'] as String,
            lat: double.parse(item['lat'] as String),
            lng: double.parse(item['lon'] as String),
            isOffline: false,
          ));
        }
      }
    } catch (e) {
      print('Error searching places: $e');
    }

    return results;
  }

  /// Get recent searches from database
  Future<List<SearchResult>> getRecentSearches({int limit = 10}) async {
    try {
      final searches = await database.getRecentSearches(limit: limit);
      return searches
          .map((s) => SearchResult(
                title: s.title,
                subtitle: s.subtitle ?? '',
                lat: s.latitude,
                lng: s.longitude,
                isOffline: s.isOffline,
              ))
          .toList();
    } catch (e) {
      print('Error getting recent searches: $e');
      return [];
    }
  }

  /// Add a search to history
  Future<void> addToHistory(SearchResult result, String query) async {
    try {
      await database.addSearchToHistory(
        query: query,
        title: result.title,
        subtitle: result.subtitle,
        latitude: result.lat,
        longitude: result.lng,
        isOffline: result.isOffline,
      );
    } catch (e) {
      print('Error adding to search history: $e');
    }
  }

  /// Clear all search history
  Future<void> clearHistory() async {
    try {
      await database.clearSearchHistory();
    } catch (e) {
      print('Error clearing search history: $e');
    }
  }

  /// Search by category (POI)
  Future<List<SearchResult>> searchByCategory(String category) async {
    final results = <SearchResult>[];

    try {
      final categoryQueries = {
        'gas': 'gas station Iran',
        'restaurant': 'restaurant Iran',
        'hotel': 'hotel Iran',
        'cafe': 'cafe Iran',
        'park': 'park Iran',
        'hospital': 'hospital Iran',
        'pharmacy': 'pharmacy Iran',
        'bank': 'bank Iran',
      };

      final query = categoryQueries[category] ?? category;
      return await searchPlaces(query);
    } catch (e) {
      print('Error searching by category: $e');
    }

    return results;
  }
}
