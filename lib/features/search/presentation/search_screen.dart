import 'package:flutter/material.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/glass_panel.dart';

class SearchScreen extends StatelessWidget {
  const SearchScreen({super.key});

  @override
  Widget build(BuildContext context) {
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
                    'جستجو',
                    style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 20),
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          _buildSearchField(),
                          const SizedBox(height: 24),
                          _buildQuickActions(),
                          const SizedBox(height: 30),
                          const Text(
                            'دسته‌بندی‌های محبوب',
                            textAlign: TextAlign.right,
                            style: TextStyle(color: Color(0xFF2FE6C4), fontSize: 15, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 16),
                          _buildPopularCategories(),
                          const SizedBox(height: 30),
                          const Text(
                            'اخیراً جستجو شده',
                            textAlign: TextAlign.right,
                            style: TextStyle(color: Color(0xFF2FE6C4), fontSize: 15, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 12),
                          _RecentSearchItem(title: 'تجریش، تهران', subtitle: 'تهران، ایران'),
                          _RecentSearchItem(title: 'فرودگاه بین‌المللی امام خمینی', subtitle: 'تهران، ایران'),
                          _RecentSearchItem(title: 'بام لند', subtitle: 'تهران، بزرگراه شهید همت'),
                          const SizedBox(height: 30),
                          const Text(
                            'مکان‌های پیشنهادی نزدیک شما',
                            textAlign: TextAlign.right,
                            style: TextStyle(color: Color(0xFF2FE6C4), fontSize: 15, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 16),
                          _SuggestedPlaceCard(
                            title: 'کافه رستوران ایوان',
                            subtitle: 'ولنجک، خیابان افشار',
                            distance: '1.2 کیلومتر',
                            icon: Icons.local_cafe_rounded,
                            iconColor: Colors.tealAccent,
                          ),
                          _SuggestedPlaceCard(
                            title: 'مرکز خرید ارگ تجریش',
                            subtitle: 'تجریش، خیابان ولیعصر',
                            distance: '1.8 کیلومتر',
                            icon: Icons.shopping_bag_rounded,
                            iconColor: Colors.orangeAccent,
                          ),
                          const SizedBox(height: 120),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const BottomNav(currentPage: NavKey.search),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchField() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFF141A26),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: const Row(
        children: [
          Icon(Icons.mic_none_rounded, color: Color(0xFF2FE6C4), size: 22),
          SizedBox(width: 8),
          Expanded(
            child: TextField(
              textAlign: TextAlign.right,
              style: TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'مقصد، آدرس یا مکان مورد نظر را ...',
                hintStyle: TextStyle(color: Colors.white38, fontSize: 14),
                border: InputBorder.none,
              ),
            ),
          ),
          SizedBox(width: 8),
          Icon(Icons.search_rounded, color: Colors.white54, size: 22),
        ],
      ),
    );
  }

  Widget _buildQuickActions() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        _QuickActionItem(icon: Icons.more_horiz_rounded, label: 'بیشتر'),
        _QuickActionItem(icon: Icons.local_gas_station_rounded, label: 'پمپ بنزین'),
        _QuickActionItem(icon: Icons.star_rounded, label: 'علاقه‌مندی‌ها'),
        _QuickActionItem(icon: Icons.work_rounded, label: 'محل کار'),
        _QuickActionItem(icon: Icons.home_rounded, label: 'خانه'),
      ],
    );
  }

  Widget _buildPopularCategories() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      reverse: true,
      child: Row(
        children: [
          _CategoryItem(icon: Icons.park_rounded, label: 'پارک و تفریح', color: Colors.green),
          _CategoryItem(icon: Icons.hotel_rounded, label: 'هتل', color: Colors.blue),
          _CategoryItem(icon: Icons.shopping_bag_rounded, label: 'مراکز خرید', color: Colors.orange),
          _CategoryItem(icon: Icons.local_cafe_rounded, label: 'کافی‌شاپ', color: Colors.teal),
          _CategoryItem(icon: Icons.restaurant_rounded, label: 'رستوران', color: Colors.amber),
        ],
      ),
    );
  }
}

class _QuickActionItem extends StatelessWidget {
  final IconData icon;
  final String label;
  const _QuickActionItem({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 60,
          height: 60,
          decoration: BoxDecoration(
            color: const Color(0xFF1A1F2B),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withOpacity(0.05)),
          ),
          child: Icon(icon, color: const Color(0xFF2FE6C4), size: 26),
        ),
        const SizedBox(height: 8),
        Text(label, style: const TextStyle(color: Colors.white70, fontSize: 12)),
      ],
    );
  }
}

class _CategoryItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  const _CategoryItem({required this.icon, required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 16),
      child: Column(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: color.withOpacity(0.1),
              border: Border.all(color: color.withOpacity(0.3), width: 1.5),
            ),
            child: Icon(icon, color: color, size: 28),
          ),
          const SizedBox(height: 8),
          Text(label, style: const TextStyle(color: Colors.white70, fontSize: 12)),
        ],
      ),
    );
  }
}

class _RecentSearchItem extends StatelessWidget {
  final String title;
  final String subtitle;

  const _RecentSearchItem({required this.title, required this.subtitle});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          const Icon(Icons.north_east_rounded, color: Color(0xFF2FE6C4), size: 20),
          const Spacer(),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(title, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w500)),
              Text(subtitle, style: const TextStyle(color: Colors.white38, fontSize: 13)),
            ],
          ),
          const SizedBox(width: 16),
          const Icon(Icons.history_rounded, color: Colors.white38, size: 22),
        ],
      ),
    );
  }
}

class _SuggestedPlaceCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final String distance;
  final IconData icon;
  final Color iconColor;

  const _SuggestedPlaceCard({
    required this.title,
    required this.subtitle,
    required this.distance,
    required this.icon,
    required this.iconColor,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GlassPanel(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Text(distance, style: const TextStyle(color: Color(0xFF2FE6C4), fontSize: 13)),
              const Spacer(),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(title, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text(subtitle, style: const TextStyle(color: Colors.white38, fontSize: 12)),
                ],
              ),
              const SizedBox(width: 12),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: iconColor.withOpacity(0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, color: iconColor, size: 24),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
