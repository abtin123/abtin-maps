import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/database/app_database.dart';
import '../data/search_service.dart';

final databaseProvider = Provider<AppDatabase>((ref) {
  return AppDatabase();
});

final searchServiceProvider = Provider<SearchService>((ref) {
  final database = ref.watch(databaseProvider);
  return SearchService(database);
});

final recentSearchesProvider = FutureProvider.autoDispose<List<SearchResult>>((ref) async {
  final searchService = ref.watch(searchServiceProvider);
  return await searchService.getRecentSearches(limit: 15);
});

final searchQueryProvider = StateProvider<String>((ref) => '');

final searchResultsProvider = FutureProvider.autoDispose<List<SearchResult>>((ref) async {
  final query = ref.watch(searchQueryProvider);
  
  if (query.isEmpty) {
    return [];
  }
  
  final searchService = ref.watch(searchServiceProvider);
  return await searchService.searchPlaces(query);
});
