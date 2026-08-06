import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'country_models.dart';
import 'country_providers.dart';

/// صفحه‌ی «دانلود نقشه‌ی کشورها» — لیست همه‌ی کشورهای موجود در manifest.json
/// و امکان دانلود/حذف نقشه‌ی هر کدام به‌صورت مستقل.
class CountriesScreen extends ConsumerWidget {
  const CountriesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final manifestAsync = ref.watch(countryManifestProvider);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: const Color(0xFF0E0B1F),
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          title: const Text('دانلود نقشه‌ی کشورها'),
        ),
        body: manifestAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => _ErrorState(
            message: 'دریافت لیست کشورها ناموفق بود',
            onRetry: () => ref.invalidate(countryManifestProvider),
          ),
          data: (manifest) {
            final countries = manifest.countries.where((c) => c.enabled).toList()
              ..sort((a, b) => a.nameFa.compareTo(b.nameFa));
            if (countries.isEmpty) {
              return const Center(child: Text('در حال حاضر کشوری موجود نیست'));
            }
            return ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: countries.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, i) => _CountryCard(entry: countries[i]),
            );
          },
        ),
      ),
    );
  }
}

class _CountryCard extends ConsumerWidget {
  final CountryMapEntry entry;
  const _CountryCard({required this.entry});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dl = ref.watch(countryDownloadProvider(entry));
    final notifier = ref.read(countryDownloadProvider(entry).notifier);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: Colors.white.withOpacity(0.06),
        border: Border.all(color: Colors.white.withOpacity(0.10)),
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.deepPurpleAccent.withOpacity(0.25),
            ),
            child: const Icon(Icons.public, color: Colors.white70),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(entry.nameFa,
                    style: const TextStyle(
                        color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
                const SizedBox(height: 2),
                Text('${entry.nameEn} · ${entry.totalSizeMb.toStringAsFixed(0)} مگابایت',
                    style: TextStyle(color: Colors.white.withOpacity(0.55), fontSize: 12)),
                if (dl.status == CountryDownloadStatus.downloading) ...[
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(
                      value: dl.progress,
                      minHeight: 6,
                      backgroundColor: Colors.white.withOpacity(0.1),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text('${(dl.progress * 100).toStringAsFixed(0)}٪',
                      style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 11)),
                ],
                if (dl.status == CountryDownloadStatus.failed) ...[
                  const SizedBox(height: 4),
                  Text('خطا در دانلود — دوباره تلاش کنید',
                      style: TextStyle(color: Colors.redAccent.shade100, fontSize: 12)),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          _ActionButton(status: dl.status, notifier: notifier),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final CountryDownloadStatus status;
  final CountryDownloadNotifier notifier;
  const _ActionButton({required this.status, required this.notifier});

  @override
  Widget build(BuildContext context) {
    switch (status) {
      case CountryDownloadStatus.installed:
        return IconButton(
          icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
          onPressed: notifier.delete,
          tooltip: 'حذف نقشه',
        );
      case CountryDownloadStatus.downloading:
        return IconButton(
          icon: const Icon(Icons.close, color: Colors.white70),
          onPressed: notifier.cancelDownload,
          tooltip: 'لغو دانلود',
        );
      case CountryDownloadStatus.notDownloaded:
      case CountryDownloadStatus.paused:
      case CountryDownloadStatus.failed:
        return IconButton(
          icon: const Icon(Icons.download_rounded, color: Colors.white),
          onPressed: notifier.download,
          tooltip: 'دانلود',
        );
    }
  }
}

class _ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorState({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.wifi_off, color: Colors.white38, size: 40),
          const SizedBox(height: 12),
          Text(message, style: const TextStyle(color: Colors.white70)),
          const SizedBox(height: 12),
          ElevatedButton(onPressed: onRetry, child: const Text('تلاش دوباره')),
        ],
      ),
    );
  }
}
