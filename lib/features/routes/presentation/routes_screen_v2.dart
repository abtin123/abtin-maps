import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'package:intl/intl.dart';
import '../../../core/database/app_database.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../map/presentation/destination_provider.dart';

final routeHistoryProvider = FutureProvider.autoDispose<List<RouteHistory>>((ref) async {
  final db = ref.watch(databaseProvider);
  return (await db.select(db.routeHistory).get())
      .toList()
      .reversed
      .toList();
});

final databaseProvider = Provider<AppDatabase>((ref) {
  return AppDatabase();
});

class RoutesScreenV2 extends ConsumerStatefulWidget {
  const RoutesScreenV2({super.key});

  @override
  ConsumerState<RoutesScreenV2> createState() => _RoutesScreenV2State();
}

class _RoutesScreenV2State extends ConsumerState<RoutesScreenV2> {
  @override
  Widget build(BuildContext context) {
    final routeHistory = ref.watch(routeHistoryProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF0A0C10),
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment.topCenter,
            radius: 1.2,
            colors: [Color(0xFF10151A), Color(0xFF0A0C10)],
          ),
        ),
        child: Stack(
          children: [
            SafeArea(
              child: Column(
                children: [
                  const SizedBox(height: 10),
                  const Text(
                    'سابقه مسیرها',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 20),
                  Expanded(
                    child: routeHistory.when(
                      data: (routes) => routes.isEmpty
                          ? _buildEmptyState()
                          : _buildRoutesList(routes),
                      loading: () => const Center(
                        child: CircularProgressIndicator(
                          color: Color(0xFF2FE6C4),
                        ),
                      ),
                      error: (err, stack) => Center(
                        child: Text(
                          'خطا: $err',
                          style: const TextStyle(color: Colors.red),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const BottomNav(currentPage: NavKey.routes),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.history_rounded,
            size: 64,
            color: Colors.white.withOpacity(0.3),
          ),
          const SizedBox(height: 16),
          Text(
            'هنوز مسیری طی نشده است',
            style: TextStyle(
              color: Colors.white.withOpacity(0.5),
              fontSize: 16,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'مسیرهای شما اینجا نمایش داده خواهند شد',
            style: TextStyle(
              color: Colors.white.withOpacity(0.3),
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRoutesList(List<RouteHistory> routes) {
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
      itemCount: routes.length,
      itemBuilder: (context, index) {
        final route = routes[index];
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: _buildRouteCard(route),
        );
      },
    );
  }

  Widget _buildRouteCard(RouteHistory route) {
    final formatter = DateFormat('HH:mm — d MMM', 'fa_IR');
    final timeStr = formatter.format(route.createdAt);

    // Calculate approximate distance
    const earthRadius = 6371000.0; // meters
    final dLat = (route.endLat - route.startLat) * 3.14159 / 180;
    final dLng = (route.endLng - route.startLng) * 3.14159 / 180;
    final a = (dLat / 2) * (dLat / 2) +
        (dLng / 2) * (dLng / 2);
    final distance = earthRadius * 2 * (a.sqrt() / (1 + a).sqrt());
    final distanceKm = (distance / 1000).toStringAsFixed(1);

    return GlassPanel(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(
                            Icons.location_on_rounded,
                            color: Color(0xFF2FE6C4),
                            size: 18,
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              '${route.startLat.toStringAsFixed(4)}, ${route.startLng.toStringAsFixed(4)}',
                              style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 12,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          const Icon(
                            Icons.flag_rounded,
                            color: Colors.orangeAccent,
                            size: 18,
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              route.endLabel ??
                                  '${route.endLat.toStringAsFixed(4)}, ${route.endLng.toStringAsFixed(4)}',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFF2FE6C4).withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '$distanceKm km',
                        style: const TextStyle(
                          color: Color(0xFF2FE6C4),
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      timeStr,
                      style: const TextStyle(
                        color: Colors.white38,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _navigateToRoute(route),
                    icon: const Icon(Icons.navigation_rounded, size: 16),
                    label: const Text('ناوبری'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF2FE6C4),
                      foregroundColor: const Color(0xFF0A0C10),
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _deleteRoute(route),
                    icon: const Icon(Icons.delete_rounded, size: 16),
                    label: const Text('حذف'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red,
                      side: const BorderSide(color: Colors.red),
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _navigateToRoute(RouteHistory route) {
    ref.read(selectedDestinationProvider.notifier).state = SelectedDestination(
      LatLng(route.endLat, route.endLng),
      label: route.endLabel ?? 'مقصد ذخیره شده',
    );
    Navigator.of(context).popUntil((route) => route.isFirst);
  }

  void _deleteRoute(RouteHistory route) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF141A26),
        title: const Text(
          'حذف مسیر',
          style: TextStyle(color: Colors.white),
        ),
        content: const Text(
          'آیا مطمئن هستید که می‌خواهید این مسیر را حذف کنید؟',
          style: TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('انصراف'),
          ),
          TextButton(
            onPressed: () async {
              final db = ref.read(databaseProvider);
              await db.delete(db.routeHistory)
                  .where((tbl) => tbl.id.equals(route.id))
                  .go();
              ref.refresh(routeHistoryProvider);
              Navigator.pop(context);
            },
            child: const Text(
              'حذف',
              style: TextStyle(color: Colors.red),
            ),
          ),
        ],
      ),
    );
  }
}
