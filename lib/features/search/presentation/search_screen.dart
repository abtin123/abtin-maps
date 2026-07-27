import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../map/presentation/destination_provider.dart';
import '../../offline_maps/presentation/offline_maps_providers.dart';
import '../../routing/presentation/routing_providers.dart';

class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _searchController = TextEditingController();
  List<SearchResult> _results = [];
  bool _isLoading = false;
  Timer? _debounce;

  @override
  void dispose() {
    _searchController.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    if (_debounce?.isActive ?? false) _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 500), () {
      if (query.length > 2) {
        _performSearch(query);
      } else {
        setState(() => _results = []);
      }
    });
  }

  Future<void> _performSearch(String query) async {
    setState(() => _isLoading = true);
    
    final results = <SearchResult>[];

    // 1. Offline Search (Currently being migrated to Valhalla)
    /*
    try {
      final graphStore = ref.read(offlineGraphStoreProvider);
      final downloadedGraphs = await ref.read(downloadedGraphsProvider.future);
      for (final provinceId in downloadedGraphs) {
        final graph = await graphStore.loadProvince(provinceId);
        if (graph != null) {
          for (var i = 0; i < graph.roadNames.length; i++) {
            final name = graph.roadNames[i];
            if (name.contains(query)) {
              // Find a node that has this road name
              int? nodeIdx;
              for (var n = 0; n < graph.adjacency.length; n++) {
                if (graph.adjacency[n].any((e) => e.nameIndex == i)) {
                  nodeIdx = n;
                  break;
                }
              }
              if (nodeIdx != null) {
                results.add(SearchResult(
                  title: name,
                  subtitle: 'مکان آفلاین (ذخیره شده)',
                  lat: graph.lats[nodeIdx],
                  lng: graph.lngs[nodeIdx],
                  isOffline: true,
                ));
              }
            }
            if (results.length > 5) break;
          }
        }
      }
    } catch (_) {}
    */

    // 2. Online Search (OSM Nominatim)
    try {
      final url = Uri.parse('https://nominatim.openstreetmap.org/search?q=$query&format=json&addressdetails=1&limit=10&countrycodes=ir');
      final response = await http.get(url, headers: {'User-Agent': 'AbtinNavigator/1.0'});
      if (response.statusCode == 200) {
        final data = json.decode(response.body) as List;
        for (var item in data) {
          results.add(SearchResult(
            title: item['display_name'].split(',')[0],
            subtitle: item['display_name'],
            lat: double.parse(item['lat']),
            lng: double.parse(item['lon']),
            isOffline: false,
          ));
        }
      }
    } catch (_) {}

    if (mounted) {
      setState(() {
        _results = results;
        _isLoading = false;
      });
    }
  }

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
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: _buildSearchField(),
                  ),
                  const SizedBox(height: 10),
                  if (_isLoading)
                    const LinearProgressIndicator(backgroundColor: Colors.transparent, color: Color(0xFF2FE6C4)),
                  Expanded(
                    child: _results.isEmpty && _searchController.text.isEmpty
                        ? _buildInitialView()
                        : _buildResultsList(),
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

  Widget _buildInitialView() {
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
          const _RecentSearchItem(title: 'اراک، خیابان عباس‌آباد', subtitle: 'مرکزی، ایران'),
          const _RecentSearchItem(title: 'میدان شهدا، اراک', subtitle: 'مرکزی، ایران'),
          const SizedBox(height: 120),
        ],
      ),
    );
  }

  Widget _buildResultsList() {
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
      itemCount: _results.length,
      itemBuilder: (context, index) {
        final res = _results[index];
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: GlassPanel(
            child: ListTile(
              onTap: () {
                ref.read(selectedDestinationProvider.notifier).state = SelectedDestination(
                  LatLng(res.lat, res.lng),
                  label: res.title,
                );
                Navigator.of(context).popUntil((route) => route.isFirst);
              },
              leading: Icon(res.isOffline ? Icons.cloud_off_rounded : Icons.location_on_rounded, 
                           color: res.isOffline ? Colors.orangeAccent : const Color(0xFF2FE6C4)),
              title: Text(res.title, textAlign: TextAlign.right, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              subtitle: Text(res.subtitle, textAlign: TextAlign.right, maxLines: 1, overflow: TextOverflow.ellipsis, 
                            style: const TextStyle(color: Colors.white38, fontSize: 12)),
            ),
          ),
        );
      },
    );
  }

  Widget _buildQuickActions() {
    return const Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        _QuickActionItem(icon: Icons.more_horiz_rounded, label: 'بیشتر'),
        _QuickActionItem(icon: Icons.local_gas_station_rounded, label: 'پمپ بنزین'),
        _QuickActionItem(icon: Icons.restaurant_rounded, label: 'رستوران'),
        _QuickActionItem(icon: Icons.work_rounded, label: 'محل کار'),
        _QuickActionItem(icon: Icons.home_rounded, label: 'خانه'),
      ],
    );
  }

  Widget _buildPopularCategories() {
    return const SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      reverse: true,
      child: Row(
        children: [
          _CategoryItem(icon: Icons.park_rounded, label: 'پارک', color: Colors.green),
          _CategoryItem(icon: Icons.hotel_rounded, label: 'هتل', color: Colors.blue),
          _CategoryItem(icon: Icons.shopping_bag_rounded, label: 'خرید', color: Colors.orange),
          _CategoryItem(icon: Icons.local_cafe_rounded, label: 'کافه', color: Colors.teal),
        ],
      ),
    );
  }
}

class SearchResult {
  final String title;
  final String subtitle;
  final double lat;
  final double lng;
  final bool isOffline;
  SearchResult({required this.title, required this.subtitle, required this.lat, required this.lng, required this.isOffline});
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
        Text(label, style: const TextStyle(color: Colors.white70, fontSize: 11)),
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
              Text(title, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w500)),
              Text(subtitle, style: const TextStyle(color: Colors.white38, fontSize: 12)),
            ],
          ),
          const SizedBox(width: 16),
          const Icon(Icons.history_rounded, color: Colors.white38, size: 22),
        ],
      ),
    );
  }
}
