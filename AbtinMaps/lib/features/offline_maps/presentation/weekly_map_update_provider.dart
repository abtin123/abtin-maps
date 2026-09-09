import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/abtinmap_providers.dart';
import '../../../core/database/database_provider.dart';
import '../data/map_catalog.dart';
import '../data/weekly_map_update_service.dart';
final weeklyMapUpdateProvider = FutureProvider<void>((ref) async => WeeklyMapUpdateService(ref.watch(abmMapServiceProvider), MapCatalogService(), ref.watch(appDatabaseProvider)).checkAndUpdate());
