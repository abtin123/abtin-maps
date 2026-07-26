import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/glass_notice.dart';
import '../../../shared/widgets/page_header.dart';
import '../../routing/presentation/routing_providers.dart';
import '../data/iran_provinces.dart';
import '../data/offline_maps_service.dart';
import 'offline_maps_providers.dart';

class MapSettingsScreen extends ConsumerStatefulWidget {
  const MapSettingsScreen({super.key});

  @override
  ConsumerState<MapSettingsScreen> createState() => _MapSettingsScreenState();
}

class _MapSettingsScreenState extends ConsumerState<MapSettingsScreen> {
  final Map<String, double> _mapProgress = {};
  final Map<String, double> _graphProgress = {};
  final Set<String> _mapPaused = {};
  final Set<String> _graphPaused = {};

  DateTime? _speedWindowStart;
  double _speedWindowMb = 0;
  double _speedMbps = 0;

  void _trackSpeed(double deltaMb) {
    final now = DateTime.now();
    _speedWindowStart ??= now;
    _speedWindowMb += deltaMb;
    final elapsed = now.difference(_speedWindowStart!).inMilliseconds;
    if (elapsed >= 800) {
      setState(() => _speedMbps = _speedWindowMb / (elapsed / 1000));
      _speedWindowStart = now;
      _speedWindowMb = 0;
    }
  }

  Future<void> _downloadMap(Province p) async {
    final service = ref.read(offlineMapsServiceProvider);
    final quality = ref.read(selectedMapQualityProvider);
    setState(() {
      _mapProgress[p.id] = 0;
      _mapPaused.remove(p.id);
    });
    var lastP = 0.0;
    try {
      await service.downloadProvince(
        p,
        quality,
        onProgress: (v) {
          if (!mounted) return;
          final estMb = service.estimateSizeMb(p, quality);
          _trackSpeed((v - lastP).clamp(0, 1) * estMb);
          lastP = v;
          setState(() => _mapProgress[p.id] = v);
        },
      );
      if (!mounted) return;
      setState(() {
        _mapProgress.remove(p.id);
        _mapPaused.remove(p.id);
      });
      ref.invalidate(offlineRegionsProvider);
      _snack('نقشه «${p.name}» با موفقیت دانلود شد ✅', color: AppColors.subAccentA);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _mapProgress.remove(p.id);
        _mapPaused.remove(p.id);
      });
      _snack('خطا در دانلود نقشه «${p.name}»: $e', error: true);
    }
  }

  Future<void> _toggleMapPause(Province p) async {
    final service = ref.read(offlineMapsServiceProvider);
    if (_mapPaused.contains(p.id)) {
      await service.resumeProvinceDownload(p.id);
      if (mounted) setState(() => _mapPaused.remove(p.id));
    } else {
      await service.pauseProvinceDownload(p.id);
      if (mounted) setState(() => _mapPaused.add(p.id));
    }
  }

  Future<void> _downloadGraph(Province p) async {
    final graphStore = ref.read(offlineGraphStoreProvider);
    setState(() {
      _graphProgress[p.id] = 0;
      _graphPaused.remove(p.id);
    });
    var lastP = 0.0;
    try {
      await graphStore.downloadProvince(
        p,
        onProgress: (v) {
          if (!mounted) return;
          _trackSpeed((v - lastP).clamp(0, 1) * (p.areaFactor * 6));
          lastP = v;
          setState(() => _graphProgress[p.id] = v);
        },
      );
      if (!mounted) return;
      setState(() {
        _graphProgress.remove(p.id);
        _graphPaused.remove(p.id);
      });
      ref.invalidate(downloadedGraphsProvider);
      _snack('گراف «${p.name}» با موفقیت دانلود شد ✅', color: const Color(0xFF9B7BFF));
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _graphProgress.remove(p.id);
        _graphPaused.remove(p.id);
      });
      _snack('خطا در دانلود گراف «${p.name}»: $e', error: true);
    }
  }

  void _toggleGraphPause(Province p) {
    final graphStore = ref.read(offlineGraphStoreProvider);
    if (_graphPaused.contains(p.id)) {
      graphStore.resumeProvinceDownload(p.id);
      setState(() => _graphPaused.remove(p.id));
    } else {
      graphStore.pauseProvinceDownload(p.id);
      setState(() => _graphPaused.add(p.id));
    }
  }

  Future<void> _deleteMap(Province p) async {
    final service = ref.read(offlineMapsServiceProvider);
    await service.deleteProvince(p.id);
    if (!mounted) return;
    ref.invalidate(offlineRegionsProvider);
    _snack('نقشه «${p.name}» حذف شد', color: AppColors.subAccentA);
  }

  Future<void> _deleteGraph(Province p) async {
    final graphStore = ref.read(offlineGraphStoreProvider);
    await graphStore.deleteProvince(p.id);
    if (!mounted) return;
    ref.invalidate(downloadedGraphsProvider);
    _snack('گراف «${p.name}» حذف شد', color: const Color(0xFF9B7BFF));
  }

  Future<void> _downloadAllMaps(List<Province> provinces) async {
    for (final p in provinces) {
      if (_mapProgress.containsKey(p.id)) continue;
      await _downloadMap(p);
    }
  }

  Future<void> _downloadAllGraphs(List<Province> provinces) async {
    for (final p in provinces) {
      if (_graphProgress.containsKey(p.id)) continue;
      await _downloadGraph(p);
    }
  }

  void _snack(String msg, {bool error = false, Color color = AppColors.subAccentA}) {
    showGlassNotice(
      context,
      msg,
      icon: error ? Icons.error_outline_rounded : Icons.check_circle_outline_rounded,
      colors: error ? const [Color(0xFFFF7A7A), Color(0xFFE5544B)] : [color, color],
      showAboveBottomNav: false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final quality = ref.watch(selectedMapQualityProvider);
    final service = ref.read(offlineMapsServiceProvider);

    final regionsAsync = ref.watch(offlineRegionsProvider);
    final downloadedMapIds = <String>{};
    regionsAsync.whenData((regions) {
      for (final r in regions) {
        final pid = r.metadata['province'];
        if (pid is String) downloadedMapIds.add(pid);
      }
    });

    final graphsAsync = ref.watch(downloadedGraphsProvider);
    final downloadedGraphIds = <String>{};
    graphsAsync.whenData((g) => downloadedGraphIds.addAll(g));

    double totalMb = 0;
    double doneMb = 0;
    for (final p in kIranProvinces) {
      final mapSize = service.estimateSizeMb(p, quality);
      final graphSize = p.areaFactor * 6;
      totalMb += mapSize + graphSize;
      if (downloadedMapIds.contains(p.id)) {
        doneMb += mapSize;
      } else if (_mapProgress.containsKey(p.id)) {
        doneMb += mapSize * _mapProgress[p.id]!;
      }
      if (downloadedGraphIds.contains(p.id)) {
        doneMb += graphSize;
      } else if (_graphProgress.containsKey(p.id)) {
        doneMb += graphSize * _graphProgress[p.id]!;
      }
    }
    final overallPct = totalMb > 0 ? (doneMb / totalMb).clamp(0.0, 1.0) : 0.0;
    final anyActive = _mapProgress.isNotEmpty || _graphProgress.isNotEmpty;
    final remainMb = (totalMb - doneMb).clamp(0, totalMb);
    final remainMinutes =
        _speedMbps > 0.05 ? (remainMb / _speedMbps / 60).ceil() : null;

    return Scaffold(
      appBar: const PageHeader(title: 'تنظیمات نقشه'),
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment.topCenter,
            radius: 1.2,
            colors: [Color(0xFF10151A), Color(0xFF0A0C10)],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(16, 8, 16, 4),
                child: Text(
                  'نقشه و گراف مسیریابی دلخواه خود را دانلود و مدیریت کنید.',
                  textAlign: TextAlign.right,
                  style: TextStyle(color: AppColors.textSecondary, fontSize: 13, height: 1.5),
                ),
              ),
              _QualitySelector(
                selected: quality,
                onChanged: (q) => ref.read(selectedMapQualityProvider.notifier).state = q,
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                child: Opacity(
                  opacity: 0.5,
                  child: IgnorePointer(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: AppColors.subGlassBgSoft,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: AppColors.subGlassBorder),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.palette_outlined, color: AppColors.textMuted, size: 20),
                          const SizedBox(width: 10),
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Text('استایل و رنگ‌بندی نقشه',
                                    style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600)),
                                SizedBox(height: 2),
                                Text('به‌زودی (بعد از اتصال به MapTiler)',
                                    style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: _DownloadColumn(
                          title: 'دانلود گراف',
                          subtitle: 'گراف مسیریابی شهرها',
                          icon: Icons.bar_chart_rounded,
                          accent: const Color(0xFF9B7BFF),
                          provinces: kIranProvinces,
                          progress: _graphProgress,
                          paused: _graphPaused,
                          downloadedIds: downloadedGraphIds,
                          sizeOf: (p) => p.areaFactor * 6,
                          onDownload: _downloadGraph,
                          onTogglePause: _toggleGraphPause,
                          onDelete: _deleteGraph,
                          onDownloadAll: () => _downloadAllGraphs(kIranProvinces),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _DownloadColumn(
                          title: 'دانلود نقشه',
                          subtitle: 'نقشه‌های شهری و جاده‌ای',
                          icon: Icons.map_rounded,
                          accent: AppColors.subAccentA,
                          provinces: kIranProvinces,
                          progress: _mapProgress,
                          paused: _mapPaused,
                          downloadedIds: downloadedMapIds,
                          sizeOf: (p) => service.estimateSizeMb(p, quality),
                          onDownload: _downloadMap,
                          onTogglePause: _toggleMapPause,
                          onDelete: _deleteMap,
                          onDownloadAll: () => _downloadAllMaps(kIranProvinces),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              if (anyActive)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                  child: _SummaryBar(
                    percent: overallPct,
                    totalMb: totalMb,
                    doneMb: doneMb,
                    speedMbps: _speedMbps,
                    remainMinutes: remainMinutes,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DownloadColumn extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color accent;
  final List<Province> provinces;
  final Map<String, double> progress;
  final Set<String> paused;
  final Set<String> downloadedIds;
  final double Function(Province) sizeOf;
  final void Function(Province) onDownload;
  final void Function(Province) onTogglePause;
  final void Function(Province) onDelete;
  final VoidCallback onDownloadAll;

  const _DownloadColumn({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.accent,
    required this.provinces,
    required this.progress,
    required this.paused,
    required this.downloadedIds,
    required this.sizeOf,
    required this.onDownload,
    required this.onTogglePause,
    required this.onDelete,
    required this.onDownloadAll,
  });

  @override
  Widget build(BuildContext context) {
    final totalMb = provinces.fold<double>(0, (s, p) => s + sizeOf(p));

    return Container(
      decoration: BoxDecoration(
        color: AppColors.subGlassBg,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: accent.withOpacity(.28)),
      ),
      padding: const EdgeInsets.all(10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: accent.withOpacity(.16),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: accent, size: 20),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(title,
                        textAlign: TextAlign.right,
                        style: const TextStyle(
                            color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
                    Text(subtitle,
                        textAlign: TextAlign.right,
                        style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Expanded(
            child: ListView.separated(
              padding: EdgeInsets.zero,
              itemCount: provinces.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, i) {
                final p = provinces[i];
                return _ProvinceCard(
                  province: p,
                  accent: accent,
                  sizeMb: sizeOf(p),
                  progress: progress[p.id],
                  isPaused: paused.contains(p.id),
                  isDownloaded: downloadedIds.contains(p.id),
                  onDownload: () => onDownload(p),
                  onTogglePause: () => onTogglePause(p),
                  onDelete: () => onDelete(p),
                );
              },
            ),
          ),
          const SizedBox(height: 8),
          GestureDetector(
            onTap: onDownloadAll,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 12),
              decoration: BoxDecoration(
                color: accent.withOpacity(.14),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: accent.withOpacity(.5)),
              ),
              child: Column(
                children: [
                  Icon(Icons.download_rounded, color: accent, size: 18),
                  const SizedBox(height: 2),
                  Text('دانلود همه',
                      style: TextStyle(color: accent, fontSize: 12, fontWeight: FontWeight.bold)),
                  Text(_fmtSize(totalMb),
                      style: TextStyle(color: accent.withOpacity(.75), fontSize: 10)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ProvinceCard extends StatelessWidget {
  final Province province;
  final Color accent;
  final double sizeMb;
  final double? progress;
  final bool isPaused;
  final bool isDownloaded;
  final VoidCallback onDownload;
  final VoidCallback onTogglePause;
  final VoidCallback onDelete;

  const _ProvinceCard({
    required this.province,
    required this.accent,
    required this.sizeMb,
    required this.progress,
    required this.isPaused,
    required this.isDownloaded,
    required this.onDownload,
    required this.onTogglePause,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final isDownloading = progress != null;
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(.03),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withOpacity(.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              if (isDownloading)
                GestureDetector(
                  onTap: onTogglePause,
                  child: Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: accent.withOpacity(.14),
                      border: Border.all(color: accent, width: 1.4),
                    ),
                    child: Icon(
                      isPaused ? Icons.play_arrow_rounded : Icons.pause_rounded,
                      color: accent,
                      size: 16,
                    ),
                  ),
                )
              else if (isDownloaded)
                GestureDetector(
                  onTap: onDelete,
                  child: Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: const Color(0xFFFF6B81).withOpacity(.14),
                      border: Border.all(color: const Color(0xFFFF6B81), width: 1.2),
                    ),
                    child: const Icon(Icons.delete_outline_rounded, color: Color(0xFFFF6B81), size: 15),
                  ),
                )
              else
                GestureDetector(
                  onTap: onDownload,
                  child: Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: accent.withOpacity(.14),
                      border: Border.all(color: accent, width: 1.2),
                    ),
                    child: Icon(Icons.download_rounded, color: accent, size: 15),
                  ),
                ),
              const Spacer(),
              Expanded(
                flex: 3,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      province.name,
                      textAlign: TextAlign.right,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 1),
                    Text(
                      isDownloaded ? 'دانلود شده ✓' : _fmtSize(sizeMb),
                      style: TextStyle(
                        color: isDownloaded ? accent : AppColors.textMuted,
                        fontSize: 10.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (isDownloading) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                SizedBox(
                  width: 30,
                  child: Text(
                    '${((progress ?? 0) * 100).round()}٪',
                    textAlign: TextAlign.left,
                    style: TextStyle(color: accent, fontSize: 11, fontWeight: FontWeight.bold),
                  ),
                ),
                Expanded(child: _ThickProgressBar(value: progress ?? 0, color: accent, dim: isPaused)),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _ThickProgressBar extends StatelessWidget {
  final double value;
  final Color color;
  final bool dim;

  const _ThickProgressBar({required this.value, required this.color, this.dim = false});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        const height = 10.0;
        final w = constraints.maxWidth * value.clamp(0.0, 1.0);
        return Stack(
          children: [
            Container(
              height: height,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(.06),
                borderRadius: BorderRadius.circular(height / 2),
              ),
            ),
            AnimatedContainer(
              duration: const Duration(milliseconds: 250),
              height: height,
              width: w,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(height / 2),
                gradient: LinearGradient(
                  colors: [
                    color.withOpacity(dim ? .35 : 1),
                    color.withOpacity(dim ? .2 : .65),
                  ],
                ),
                boxShadow: dim
                    ? null
                    : [BoxShadow(color: color.withOpacity(.55), blurRadius: 6, spreadRadius: -1)],
              ),
            ),
          ],
        );
      },
    );
  }
}

class _SummaryBar extends StatelessWidget {
  final double percent;
  final double totalMb;
  final double doneMb;
  final double speedMbps;
  final int? remainMinutes;

  const _SummaryBar({
    required this.percent,
    required this.totalMb,
    required this.doneMb,
    required this.speedMbps,
    required this.remainMinutes,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.subGlassBg,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.subGlassBorder),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 46,
            height: 46,
            child: Stack(
              alignment: Alignment.center,
              children: [
                CircularProgressIndicator(
                  value: percent,
                  strokeWidth: 4,
                  backgroundColor: Colors.white.withOpacity(.08),
                  valueColor: const AlwaysStoppedAnimation(AppColors.subAccentA),
                ),
                Text('${(percent * 100).round()}٪',
                    style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                const Text('کل پیشرفت',
                    style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
                Text('${_fmtSize(doneMb)} / ${_fmtSize(totalMb)}',
                    style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600)),
              ],
            ),
          ),
          Container(width: 1, height: 30, color: Colors.white.withOpacity(.08)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                const Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text('سرعت دانلود', style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
                    SizedBox(width: 4),
                    Icon(Icons.arrow_downward_rounded, color: AppColors.textMuted, size: 12),
                  ],
                ),
                Text('${speedMbps.toStringAsFixed(1)} MB/s',
                    style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600)),
              ],
            ),
          ),
          Container(width: 1, height: 30, color: Colors.white.withOpacity(.08)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                const Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text('زمان باقی‌مانده', style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
                    SizedBox(width: 4),
                    Icon(Icons.access_time_rounded, color: AppColors.textMuted, size: 12),
                  ],
                ),
                Text(remainMinutes != null ? '$remainMinutes دقیقه' : '—',
                    style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _QualitySelector extends StatelessWidget {
  final MapQuality selected;
  final ValueChanged<MapQuality> onChanged;

  const _QualitySelector({required this.selected, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 4),
      child: Row(
        children: MapQuality.values.map((q) {
          final isSel = q == selected;
          return Expanded(
            child: GestureDetector(
              onTap: () => onChanged(q),
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 3),
                padding: const EdgeInsets.symmetric(vertical: 10),
                decoration: BoxDecoration(
                  color: isSel ? AppColors.subAccentA.withOpacity(.16) : AppColors.subGlassBgSoft,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isSel ? AppColors.subAccentA : AppColors.subGlassBorder,
                    width: isSel ? 1.4 : 1,
                  ),
                ),
                child: Column(
                  children: [
                    Text(q.label,
                        style: TextStyle(
                          color: isSel ? AppColors.subAccentA : Colors.white,
                          fontSize: 12.5,
                          fontWeight: FontWeight.bold,
                        )),
                    const SizedBox(height: 2),
                    Text(q.desc,
                        textAlign: TextAlign.center,
                        maxLines: 2,
                        style: const TextStyle(color: AppColors.textMuted, fontSize: 9.5)),
                  ],
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

String _fmtSize(double mb) {
  if (mb >= 1024) return '${(mb / 1024).toStringAsFixed(1)} GB';
  return '${mb.round()} MB';
}
