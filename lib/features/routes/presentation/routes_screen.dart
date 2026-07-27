import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:drift/drift.dart' hide Column;
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../core/database/app_database.dart';

class RoutesScreen extends ConsumerWidget {
  const RoutesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final historyAsync = ref.watch(routeHistoryStreamProvider);
    return Scaffold(
      appBar: PageHeader(title: 'مسیرها'),
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
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 110),
              child: GlassPanel(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: const Color(0x8C1E1A3A),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: AppColors.subGlassBorder(context)),
                        ),
                        child: const Row(
                          children: [
                            Icon(Icons.search_rounded, color: AppColors.subAccentA, size: 18),
                            const SizedBox(width: 8),
                            Text('جستجوی مقصد...', style: TextStyle(color: Color(0xFF8B929B))),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),
                      const Text('تاریخچه سفرها',
                          style: TextStyle(color: AppColors.subAccentB, fontWeight: FontWeight.bold, fontSize: 17)),
                      const SizedBox(height: 8),
                      historyAsync.when(
                        data: (history) => history.isEmpty
                            ? const Padding(
                                padding: EdgeInsets.symmetric(vertical: 20),
                                child: Center(child: Text('هنوز سفری ثبت نشده است', style: TextStyle(color: Colors.white54))),
                              )
                            : Column(
                                children: history.map((item) => _DestItem(
                                  icon: Icons.history_rounded, 
                                  label: item.endLabel ?? 'مقصد نامشخص',
                                  date: item.createdAt,
                                )).toList(),
                              ),
                        loading: () => const Center(child: CircularProgressIndicator()),
                        error: (e, _) => Text('خطا: $e', style: const TextStyle(color: Colors.red)),
                      ),
                      const SizedBox(height: 20),
                      const Text('مسیرهای پیشنهادی',
                          style: TextStyle(color: AppColors.subAccentB, fontWeight: FontWeight.bold, fontSize: 17)),
                      const SizedBox(height: 10),
                      const _RouteCard(title: 'مسیر سریع‌تر', time: '۴۵ دقیقه', distance: '۱۴ کیلومتر', note: 'با ترافیک کم'),
                      const SizedBox(height: 10),
                      const _RouteCard(title: 'مسیر اقتصادی', time: '۵۵ دقیقه', distance: '۱۸ کیلومتر', note: 'بدون عوارض'),
                      const SizedBox(height: 20),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        decoration: BoxDecoration(
                          gradient: AppColors.subAccentGradient,
                          borderRadius: BorderRadius.circular(30),
                          boxShadow: [
                            BoxShadow(color: AppColors.subAccentB.withOpacity(.45), blurRadius: 22),
                          ],
                        ),
                        child: const Text('شروع مسیریابی',
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 17)),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const BottomNav(currentPage: NavKey.routes),
          ],
        ),
      ),
    );
  }
}

class _DestItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final DateTime? date;
  const _DestItem({required this.icon, required this.label, this.date});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppColors.subAccentA.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: AppColors.subAccentA, size: 20),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(label,
                    textAlign: TextAlign.right,
                    style: const TextStyle(color: Color(0xFFF0F2F4), fontSize: 15, fontWeight: FontWeight.w600)),
                if (date != null)
                  Text('${date!.hour}:${date!.minute} - ${date!.year}/${date!.month}/${date!.day}',
                      style: const TextStyle(color: Colors.white38, fontSize: 11)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

final routeHistoryStreamProvider = StreamProvider<List<RouteHistoryData>>((ref) {
  final db = ref.watch(appDatabaseProvider);
  return (db.select(db.routeHistory)..orderBy([(t) => OrderingTerm(expression: t.createdAt, mode: OrderingMode.desc)])).watch();
});

final appDatabaseProvider = Provider<AppDatabase>((ref) => AppDatabase());

class _RouteCard extends StatelessWidget {
  final String title;
  final String time;
  final String distance;
  final String note;

  const _RouteCard({
    required this.title,
    required this.time,
    required this.distance,
    required this.note,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.subGlassBgSoft(context),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.subGlassBorder(context)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 17)),
          const SizedBox(height: 6),
          Text(time, style: const TextStyle(color: Color(0xFFD5D9DD), fontSize: 15)),
          Text(distance, style: const TextStyle(color: Color(0xFFD5D9DD), fontSize: 15)),
          Text(note, style: const TextStyle(color: Color(0xFFD5D9DD), fontSize: 15)),
        ],
      ),
    );
  }
}
