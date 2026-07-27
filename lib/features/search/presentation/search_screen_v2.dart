import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'dart:async';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../map/presentation/destination_provider.dart';
import '../data/search_service.dart';
import 'search_providers.dart';

class SearchScreenV2 extends ConsumerStatefulWidget {
  const SearchScreenV2({super.key});

  @override
  ConsumerState<SearchScreenV2> createState() => _SearchScreenV2State();
}

class _SearchScreenV2State extends ConsumerState<SearchScreenV2> {
  final _searchController = TextEditingController();
  Timer? _debounce;
  bool _showRecent = true;

  @override
  void dispose() {
    _searchController.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    if (_debounce?.isActive ?? false) _debounce?.cancel();
    
    setState(() {
      _showRecent = query.isEmpty;
    });
    
    _debounce = Timer(const Duration(milliseconds: 300), () {
      ref.read(searchQueryProvider.notifier).state = query;
    });
  }

  void _selectResult(SearchResult result) async {
    // Add to history
    final searchService = ref.read(searchServiceProvider);
    await searchService.addToHistory(result, _searchController.text);
    
    // Set destination
    ref.read(selectedDestinationProvider.notifier).state = SelectedDestination(
      LatLng(result.lat, result.lng),
      label: result.title,
    );
    
    // Refresh recent searches
    ref.refresh(recentSearchesProvider);
    
    // Navigate back
    Navigator.of(context).popUntil((route) => route.isFirst);
  }

  @override
  Widget build(BuildContext context) {
    final recentSearches = ref.watch(recentSearchesProvider);
    final searchResults = ref.watch(searchResultsProvider);

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
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 20),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: _buildSearchField(),
                  ),
                  const SizedBox(height: 10),
                  Expanded(
                    child: _showRecent
                        ? _buildInitialView(recentSearches)
                        : _buildResultsList(searchResults),
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
      child: Row(
        children: [
          const Icon(Icons.mic_none_rounded, color: Color(0xFF2FE6C4), size: 22),
          const SizedBox(width: 8),
          Expanded(
            child: TextField(
              controller: _searchController,
              onChanged: _onSearchChanged,
              textAlign: TextAlign.right,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                hintText: 'جستجوی مقصد یا آدرس...',
                hintStyle: TextStyle(color: Colors.white38, fontSize: 14),
                border: InputBorder.none,
              ),
            ),
          ),
          const SizedBox(width: 8),
          const Icon(Icons.search_rounded, color: Colors.white54, size: 22),
        ],
      ),
    );
  }

  Widget _buildInitialView(AsyncValue<List<SearchResult>> recentSearches) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 20),
          _buildQuickActions(),
          const SizedBox(height: 30),
          const Text(
            'دسته‌بندی‌های محبوب',
            textAlign: TextAlign.right,
            style: TextStyle(
              color: Color(0xFF2FE6C4),
              fontSize: 15,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          _buildPopularCategories(),
          const SizedBox(height: 30),
          const Text(
            'اخیراً جستجو شده',
            textAlign: TextAlign.right,
            style: TextStyle(
              color: Color(0xFF2FE6C4),
              fontSize: 15,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          recentSearches.when(
            data: (searches) => searches.isEmpty
                ? const Padding(
                    padding: EdgeInsets.symmetric(vertical: 20),
                    child: Text(
                      'هنوز جستجویی انجام نداده‌اید',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.white38),
                    ),
                  )
                : Column(
                    children: searches
                        .take(5)
                        .map((search) => _buildRecentSearchItem(search))
                        .toList(),
                  ),
            loading: () => const CircularProgressIndicator(
              color: Color(0xFF2FE6C4),
            ),
            error: (err, stack) => Text(
              'خطا در بارگذاری: $err',
              style: const TextStyle(color: Colors.red),
            ),
          ),
          const SizedBox(height: 120),
        ],
      ),
    );
  }

  Widget _buildResultsList(AsyncValue<List<SearchResult>> searchResults) {
    return searchResults.when(
      data: (results) => results.isEmpty
          ? Center(
              child: Text(
                'نتیجه‌ای یافت نشد',
                style: TextStyle(color: Colors.white38),
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
              itemCount: results.length,
              itemBuilder: (context, index) {
                final res = results[index];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: GlassPanel(
                    child: ListTile(
                      onTap: () => _selectResult(res),
                      leading: Icon(
                        res.isOffline
                            ? Icons.cloud_off_rounded
                            : Icons.location_on_rounded,
                        color: res.isOffline
                            ? Colors.orangeAccent
                            : const Color(0xFF2FE6C4),
                      ),
                      title: Text(
                        res.title,
                        textAlign: TextAlign.right,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      subtitle: Text(
                        res.subtitle,
                        textAlign: TextAlign.right,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white38,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
      loading: () => const Center(
        child: CircularProgressIndicator(color: Color(0xFF2FE6C4)),
      ),
      error: (err, stack) => Center(
        child: Text(
          'خطا: $err',
          style: const TextStyle(color: Colors.red),
        ),
      ),
    );
  }

  Widget _buildRecentSearchItem(SearchResult search) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: GestureDetector(
        onTap: () => _selectResult(search),
        child: Row(
          children: [
            const Icon(Icons.north_east_rounded, color: Color(0xFF2FE6C4), size: 20),
            const Spacer(),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  search.title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  search.subtitle,
                  style: const TextStyle(color: Colors.white38, fontSize: 12),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
            const SizedBox(width: 16),
            const Icon(Icons.history_rounded, color: Colors.white38, size: 22),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickActions() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        _QuickActionItem(
          icon: Icons.more_horiz_rounded,
          label: 'بیشتر',
          onTap: () {},
        ),
        _QuickActionItem(
          icon: Icons.local_gas_station_rounded,
          label: 'پمپ بنزین',
          onTap: () => _searchCategory('gas'),
        ),
        _QuickActionItem(
          icon: Icons.restaurant_rounded,
          label: 'رستوران',
          onTap: () => _searchCategory('restaurant'),
        ),
        _QuickActionItem(
          icon: Icons.work_rounded,
          label: 'محل کار',
          onTap: () {},
        ),
        _QuickActionItem(
          icon: Icons.home_rounded,
          label: 'خانه',
          onTap: () {},
        ),
      ],
    );
  }

  void _searchCategory(String category) {
    _searchController.text = category;
    _onSearchChanged(category);
  }

  Widget _buildPopularCategories() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      reverse: true,
      child: Row(
        children: [
          _CategoryItem(
            icon: Icons.park_rounded,
            label: 'پارک',
            color: Colors.green,
            onTap: () => _searchCategory('park'),
          ),
          _CategoryItem(
            icon: Icons.hotel_rounded,
            label: 'هتل',
            color: Colors.blue,
            onTap: () => _searchCategory('hotel'),
          ),
          _CategoryItem(
            icon: Icons.shopping_bag_rounded,
            label: 'خرید',
            color: Colors.orange,
            onTap: () => _searchCategory('shopping'),
          ),
          _CategoryItem(
            icon: Icons.local_cafe_rounded,
            label: 'کافه',
            color: Colors.teal,
            onTap: () => _searchCategory('cafe'),
          ),
        ],
      ),
    );
  }
}

class _QuickActionItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _QuickActionItem({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
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
          Text(label, style: const TextStyle(color: Colors.white70, fontSize: 11)),
        ],
      ),
    );
  }
}

class _CategoryItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _CategoryItem({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Padding(
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
      ),
    );
  }
}
