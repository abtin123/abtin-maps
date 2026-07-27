import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'package:share_plus/share_plus.dart';
import '../../../core/database/app_database.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/page_header.dart';
import '../../gps/presentation/gps_providers.dart';
import '../../map/presentation/destination_provider.dart';
import 'saved_places_providers.dart';

class _CategoryMeta {
  final String label;
  final IconData icon;
  const _CategoryMeta(this.label, this.icon);
}

const Map<String, _CategoryMeta> _categoryMeta = {
  'home': _CategoryMeta('خانه', Icons.home_rounded),
  'work': _CategoryMeta('محل کار', Icons.work_rounded),
  'favorite': _CategoryMeta('سایر', Icons.star_rounded),
  'recent': _CategoryMeta('اخیر', Icons.history_rounded),
};

_CategoryMeta _metaFor(String category) => _categoryMeta[category] ?? const _CategoryMeta('سایر', Icons.star_rounded);

class SavedPlacesScreen extends ConsumerWidget {
  const SavedPlacesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final placesAsync = ref.watch(savedPlacesListProvider);

    return Scaffold(
      appBar: const PageHeader(title: 'مکان‌های مورد علاقه', backRoute: '/settings'),
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
              child: placesAsync.when(
                loading: () => const Center(child: CircularProgressIndicator(color: AppColors.subAccentA)),
                error: (e, st) => Center(
                  child: Text('خطا در خواندن دیتابیس: $e', style: const TextStyle(color: Colors.white70)),
                ),
                data: (places) {
                  if (places.isEmpty) {
                    return Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text('هنوز مکانی ذخیره نکرده‌اید', style: TextStyle(color: AppColors.textSecondary())),
                        const SizedBox(height: 20),
                        _AddPlaceButton(onTap: () => _showAddDialog(context, ref)),
                      ],
                    );
                  }

                  final grouped = <String, List<SavedPlace>>{};
                  for (final p in places) {
                    grouped.putIfAbsent(p.category, () => []).add(p);
                  }
                  final orderedKeys = ['home', 'work', 'favorite', 'recent']
                      .where((k) => grouped.containsKey(k))
                      .toList()
                    ..addAll(grouped.keys.where((k) => !['home', 'work', 'favorite', 'recent'].contains(k)));

                  return ListView(
                    children: [
                      for (final key in orderedKeys) ...[
                        _CategoryHeader(
                          meta: _metaFor(key),
                          count: grouped[key]!.length,
                          onDeleteAll: () => _confirmDeleteCategory(context, ref, grouped[key]!),
                        ),
                        const SizedBox(height: 12),
                        for (final place in grouped[key]!) ...[
                          _PlaceCard(
                            place: place,
                            onNavigate: () {
                              ref.read(selectedDestinationProvider.notifier).state = SelectedDestination(
                                LatLng(place.latitude, place.longitude),
                                label: place.name,
                              );
                              context.go('/');
                            },
                            onEdit: () => _showEditDialog(context, ref, place),
                            onShare: () => _sharePlace(place),
                            onDelete: () => ref.read(savedPlacesRepositoryProvider).remove(place.id),
                          ),
                          const SizedBox(height: 14),
                        ],
                        const SizedBox(height: 8),
                      ],
                      _AddPlaceButton(onTap: () => _showAddDialog(context, ref)),
                    ],
                  );
                },
              ),
            ),
            const BottomNav(currentPage: NavKey.settings),
          ],
        ),
      ),
    );
  }

  void _sharePlace(SavedPlace place) {
    final link = 'https://www.openstreetmap.org/?mlat=${place.latitude}&mlon=${place.longitude}#map=17/${place.latitude}/${place.longitude}';
    final text = '${place.name}${place.address != null ? '\n${place.address}' : ''}\n$link';
    SharePlus.instance.share(ShareParams(text: text, subject: place.name));
  }

  void _confirmDeleteCategory(BuildContext context, WidgetRef ref, List<SavedPlace> places) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF14181D),
        title: const Text('حذف این دسته', style: TextStyle(color: Colors.white)),
        content: Text('همه‌ی ${places.length} مکان این دسته حذف شود؟', style: TextStyle(color: AppColors.textSecondary())),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('انصراف')),
          TextButton(
            onPressed: () async {
              for (final p in places) {
                await ref.read(savedPlacesRepositoryProvider).remove(p.id);
              }
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('حذف همه', style: TextStyle(color: Color(0xFFFF6B81))),
          ),
        ],
      ),
    );
  }

  void _showAddDialog(BuildContext context, WidgetRef ref) {
    final nameController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF14181D),
        title: const Text('افزودن موقعیت فعلی', style: TextStyle(color: Colors.white)),
        content: TextField(
          controller: nameController,
          textAlign: TextAlign.right,
          style: const TextStyle(color: Colors.white),
          decoration: const InputDecoration(
            hintText: 'مثلاً خانه، محل کار...',
            hintStyle: TextStyle(color: Color(0xFF8B929B)),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('انصراف')),
          TextButton(
            onPressed: () async {
              final name = nameController.text.trim();
              if (name.isEmpty) return;
              final pos = ref.read(vehiclePositionProvider).valueOrNull;
              if (pos == null) {
                Navigator.pop(ctx);
                return;
              }
              await ref.read(savedPlacesRepositoryProvider).add(
                    name: name,
                    latitude: pos.lat,
                    longitude: pos.lng,
                  );
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('ذخیره موقعیت فعلی من'),
          ),
        ],
      ),
    );
  }

  void _showEditDialog(BuildContext context, WidgetRef ref, SavedPlace place) {
    final nameController = TextEditingController(text: place.name);
    final addressController = TextEditingController(text: place.address ?? '');
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF14181D),
        title: const Text('ویرایش مکان', style: TextStyle(color: Colors.white)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              textAlign: TextAlign.right,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(hintText: 'نام مکان', hintStyle: TextStyle(color: Color(0xFF8B929B))),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: addressController,
              textAlign: TextAlign.right,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(hintText: 'آدرس (اختیاری)', hintStyle: TextStyle(color: Color(0xFF8B929B))),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('انصراف')),
          TextButton(
            onPressed: () async {
              final name = nameController.text.trim();
              if (name.isEmpty) return;
              await ref.read(savedPlacesRepositoryProvider).rename(
                    id: place.id,
                    name: name,
                    address: addressController.text.trim().isEmpty ? null : addressController.text.trim(),
                  );
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('ذخیره'),
          ),
        ],
      ),
    );
  }
}

class _CategoryHeader extends StatelessWidget {
  final _CategoryMeta meta;
  final int count;
  final VoidCallback onDeleteAll;

  const _CategoryHeader({required this.meta, required this.count, required this.onDeleteAll});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        PopupMenuButton<String>(
          icon: Icon(Icons.more_vert_rounded, color: AppColors.textSecondary()),
          color: const Color(0xFF14181D),
          onSelected: (v) {
            if (v == 'delete') onDeleteAll();
          },
          itemBuilder: (ctx) => [
            const PopupMenuItem(value: 'delete', child: Text('حذف همه‌ی این دسته', style: TextStyle(color: Color(0xFFFF6B81)))),
          ],
        ),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(meta.label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 17)),
              Text('$count مکان', style: TextStyle(color: AppColors.textSecondary(), fontSize: 13)),
            ],
          ),
        ),
        const SizedBox(width: 10),
        Container(
          width: 44,
          height: 44,
          decoration: const BoxDecoration(shape: BoxShape.circle, gradient: AppColors.subAccentGradient),
          child: Icon(meta.icon, color: const Color(0xFF0A0C10), size: 22),
        ),
      ],
    );
  }
}

class _PlaceCard extends StatelessWidget {
  final SavedPlace place;
  final VoidCallback onNavigate;
  final VoidCallback onEdit;
  final VoidCallback onShare;
  final VoidCallback onDelete;

  const _PlaceCard({
    required this.place,
    required this.onNavigate,
    required this.onEdit,
    required this.onShare,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      borderRadius: 18,
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              PopupMenuButton<String>(
                padding: EdgeInsets.zero,
                icon: const Icon(Icons.star_rounded, color: Color(0xFFF4C230), size: 22),
                color: const Color(0xFF14181D),
                onSelected: (v) {
                  if (v == 'delete') onDelete();
                },
                itemBuilder: (ctx) => [
                  const PopupMenuItem(value: 'delete', child: Text('حذف این مکان', style: TextStyle(color: Color(0xFFFF6B81)))),
                ],
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(place.name,
                          textAlign: TextAlign.right,
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 17)),
                      if (place.address != null && place.address!.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(place.address!,
                            textAlign: TextAlign.right,
                            style: TextStyle(color: AppColors.textSecondary(), fontSize: 13)),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: AppColors.subGlassBgSoft(),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Icon(Icons.location_on_rounded, color: AppColors.subAccentA, size: 26),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Divider(color: Colors.white.withOpacity(.08), height: 1),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _ActionButton(icon: Icons.navigation_rounded, label: 'مسیریابی', onTap: onNavigate),
              _ActionButton(icon: Icons.edit_rounded, label: 'ویرایش', onTap: onEdit),
              _ActionButton(icon: Icons.ios_share_rounded, label: 'اشتراک‌گذاری', onTap: onShare),
            ],
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _ActionButton({required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(label, style: const TextStyle(color: AppColors.subAccentA, fontSize: 13, fontWeight: FontWeight.w600)),
              const SizedBox(width: 6),
              Icon(icon, color: AppColors.subAccentA, size: 17),
            ],
          ),
        ),
      ),
    );
  }
}

class _AddPlaceButton extends StatelessWidget {
  final VoidCallback onTap;
  const _AddPlaceButton({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(top: 4),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(30),
          border: Border.all(color: AppColors.subAccentB, width: 1.5),
        ),
        child: const Center(
          child: Text(
            '+ افزودن مکان جدید',
            style: TextStyle(color: AppColors.subAccentA, fontWeight: FontWeight.bold, fontSize: 15),
          ),
        ),
      ),
    );
  }
}
