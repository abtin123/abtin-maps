import 'package:flutter/material.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/page_header.dart';

class SearchScreen extends StatelessWidget {
  const SearchScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const PageHeader(title: 'جستجو'),
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
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0x8C1E1A3A),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: AppColors.subGlassBorder),
                        ),
                        child: const Row(
                          children: [
                            Icon(Icons.close_rounded, color: AppColors.subAccentA, size: 18),
                            SizedBox(width: 8),
                            Expanded(
                              child: TextField(
                                textAlign: TextAlign.right,
                                style: TextStyle(color: Colors.white),
                                decoration: InputDecoration(
                                  hintText: 'جستجو در نقشه...',
                                  hintStyle: TextStyle(color: Color(0xFF8B929B)),
                                  border: InputBorder.none,
                                ),
                              ),
                            ),
                            SizedBox(width: 8),
                            Icon(Icons.search_rounded, color: AppColors.subAccentA, size: 20),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),
                      const Text('جستجوهای اخیر',
                          style: TextStyle(color: AppColors.subAccentB, fontWeight: FontWeight.bold, fontSize: 17)),
                      const SizedBox(height: 8),
                      ...const [
                        'میدان آزادی',
                        'رستوران ایتالیایی',
                        'رستوران ایتالیایی',
                      ].map((t) => _RecentItem(text: t)),
                      const SizedBox(height: 20),
                      GridView.count(
                        crossAxisCount: 2,
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        mainAxisSpacing: 10,
                        crossAxisSpacing: 10,
                        childAspectRatio: 2.4,
                        children: const [
                          _CategoryButton(icon: Icons.local_gas_station_rounded, label: 'پمپ بنزین'),
                          _CategoryButton(icon: Icons.home_work_rounded, label: 'رستوران'),
                          _CategoryButton(icon: Icons.local_cafe_rounded, label: 'کافه'),
                          _CategoryButton(icon: Icons.local_grocery_store_rounded, label: 'سوپرمارکت'),
                        ],
                      ),
                      const SizedBox(height: 10),
                      const _CategoryButton(icon: Icons.account_balance_rounded, label: 'بانک'),
                    ],
                  ),
                ),
              ),
            ),
            const BottomNav(currentPage: NavKey.search),
          ],
        ),
      ),
    );
  }
}

class _RecentItem extends StatelessWidget {
  final String text;
  const _RecentItem({required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: Colors.white.withOpacity(.06))),
      ),
      child: Row(
        children: [
          const Icon(Icons.history_rounded, color: AppColors.subAccentA, size: 16),
          const SizedBox(width: 10),
          Expanded(
            child: Text(text,
                textAlign: TextAlign.right,
                style: const TextStyle(color: Color(0xFFF0F2F4), fontSize: 16)),
          ),
        ],
      ),
    );
  }
}

class _CategoryButton extends StatelessWidget {
  final IconData icon;
  final String label;
  const _CategoryButton({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.subGlassBgSoft,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.subGlassBorder, width: 1.5),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: AppColors.subAccentA, size: 20),
          const SizedBox(width: 8),
          Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
        ],
      ),
    );
  }
}
