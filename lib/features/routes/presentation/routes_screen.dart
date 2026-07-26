import 'package:flutter/material.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/page_header.dart';

class RoutesScreen extends StatelessWidget {
  const RoutesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const PageHeader(title: 'مسیرها'),
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
                          border: Border.all(color: AppColors.subGlassBorder),
                        ),
                        child: const Row(
                          children: [
                            Icon(Icons.search_rounded, color: AppColors.subAccentA, size: 18),
                            SizedBox(width: 8),
                            Text('جستجوی مقصد...', style: TextStyle(color: Color(0xFF8B929B))),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),
                      const Text('آخرین مقاصد',
                          style: TextStyle(color: AppColors.subAccentB, fontWeight: FontWeight.bold, fontSize: 17)),
                      const SizedBox(height: 8),
                      const _DestItem(icon: Icons.work_rounded, label: 'دفتر کار'),
                      const _DestItem(icon: Icons.restaurant_rounded, label: 'رستوران شب‌های تهران'),
                      const _DestItem(icon: Icons.flight_rounded, label: 'فرودگاه مهرآباد'),
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
  const _DestItem({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, color: AppColors.subAccentA, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(label,
                textAlign: TextAlign.right,
                style: const TextStyle(color: Color(0xFFF0F2F4), fontSize: 16)),
          ),
        ],
      ),
    );
  }
}

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
        color: AppColors.subGlassBgSoft,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.subGlassBorder),
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
