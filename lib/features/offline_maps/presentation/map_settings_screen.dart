import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/glass_notice.dart';
import '../../../shared/widgets/page_header.dart';
import '../../routing/presentation/routing_providers.dart';
import '../data/iran_provinces.dart';
import '../data/offline_maps_service.dart';
import '../data/graphhopper_download_service.dart'; // Import the new service
import 'offline_maps_providers.dart';

class MapSettingsScreen extends ConsumerStatefulWidget {
  const MapSettingsScreen({super.key});

  @override
  ConsumerState<MapSettingsScreen> createState() => _MapSettingsScreenState();
}

class _MapSettingsScreenState extends ConsumerState<MapSettingsScreen> {
  final Map<String, double> _mapProgress = {};
  final Map<String, double> _graphProgress = {}; // Track GraphHopper download progress

  final Set<String> _mapPaused = {};
  final Set<String> _graphPaused = {}; // Track GraphHopper paused status

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

  Future<void> _deleteMap(Province p) async {
    final service = ref.read(offlineMapsServiceProvider);
    await service.deleteProvince(p.id);
    if (!mounted) return;
    ref.invalidate(offlineRegionsProvider);
    _snack('نقشه «${p.name}» حذف شد', color: AppColors.subAccentA);
  }

  Future<void> _downloadGraph(Province p) async {
    final service = ref.read(graphHopperDownloadServiceProvider);
    setState(() {
      _graphProgress[p.id] = 0;
      _graphPaused.remove(p.id);
    });
    var lastP = 0.0;
    try {
      await service.downloadGraph(
        p,
        onProgress: (v) {
          if (!mounted) return;
          final estMb = service.estimateSizeMb(p);
          _trackSpeed((v - lastP).clamp(0, 1) * estMb);
          lastP = v;
          setState(() => _graphProgress[p.id] = v);
        },
      );
      if (!mounted) return;
      setState(() {
        _graphProgress.remove(p.id);
        _graphPaused.remove(p.id);
      });
      ref.read(graphDownloadRefreshProvider.notifier).state++;
      _snack('گراف مسیریابی «${p.name}» با موفقیت دانلود شد ✅', color: AppColors.subAccentA);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _graphProgress.remove(p.id);
        _graphPaused.remove(p.id);
      });
      _snack('خطا در دانلود گراف مسیریابی «${p.name}»: $e', error: true);
    }
  }

  Future<void> _toggleGraphPause(Province p) async {
    final service = ref.read(graphHopperDownloadServiceProvider);
    if (_graphPaused.contains(p.id)) {
      await service.resumeDownload(p.id);
      if (mounted) setState(() => _graphPaused.remove(p.id));
    } else {
      await service.pauseDownload(p.id);
      if (mounted) setState(() => _graphPaused.add(p.id));
    }
  }

  Future<void> _deleteGraph(Province p) async {
    final service = ref.read(graphHopperDownloadServiceProvider);
    await service.deleteGraph(p.id);
    if (!mounted) return;
      ref.read(graphDownloadRefreshProvider.notifier).state++;
      _snack('گراف مسیریابی «${p.name}» حذف شد', color: AppColors.subAccentA);
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
    final offlineMapService = ref.read(offlineMapsServiceProvider);
    final graphHopperService = ref.read(graphHopperDownloadServiceProvider);

    final regionsAsync = ref.watch(offlineRegionsProvider);
    final downloadedMapIds = <String>{};
    regionsAsync.whenData((regions) {
      for (final r in regions) {
        final pid = r.metadata['province'];
        if (pid is String) downloadedMapIds.add(pid);
      }
    });

    final downloadedGraphIdsAsync = ref.watch(downloadedGraphIdsProvider);
    final downloadedGraphIds = downloadedGraphIdsAsync.value ?? {};

    double totalMapMb = 0;
    double doneMapMb = 0;
    for (final p in kIranProvinces) {
      final mapSize = offlineMapService.estimateSizeMb(p, quality);
      totalMapMb += mapSize;
      if (downloadedMapIds.contains(p.id)) {
        doneMapMb += mapSize;
      } else if (_mapProgress.containsKey(p.id)) {
        doneMapMb += mapSize * _mapProgress[p.id]!;
      }
    }

    double totalGraphMb = 0;
    double doneGraphMb = 0;
    for (final p in kIranProvinces) {
      final graphSize = graphHopperService.estimateSizeMb(p);
      totalGraphMb += graphSize;
      if (downloadedGraphIds.contains(p.id)) {
        doneGraphMb += graphSize;
      } else if (_graphProgress.containsKey(p.id)) {
        doneGraphMb += graphSize * _graphProgress[p.id]!;
      }
    }

    final overallTotalMb = totalMapMb + totalGraphMb;
    final overallDoneMb = doneMapMb + doneGraphMb;
    final overallPct = overallTotalMb > 0 ? (overallDoneMb / overallTotalMb).clamp(0.0, 1.0) : 0.0;
    final anyActive = _mapProgress.isNotEmpty || _graphProgress.isNotEmpty;
    final remainMb = (overallTotalMb - overallDoneMb).clamp(0, overallTotalMb);
    final remainMinutes =
        _speedMbps > 0.05 ? (remainMb / _speedMbps / 60).ceil() : null;

    return Scaffold(
      appBar: PageHeader(title: 'دانلود نقشه'),
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
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
                child: Text(
                  'برای مسیریابی بدون اینترنت، نقشه‌های مورد نظر خود را دانلود کنید.',
                  textAlign: TextAlign.right,
                  style: TextStyle(color: AppColors.textSecondary(context), fontSize: 13, height: 1.5),
                ),
              ),
              // Suggested Maps Section
              _SuggestedMapsSection(
                offlineMapService: offlineMapService,
                graphHopperService: graphHopperService,
                quality: quality,
                downloadedMapIds: downloadedMapIds,
                downloadedGraphIds: downloadedGraphIds,
                mapProgress: _mapProgress,
                graphProgress: _graphProgress,
                mapPaused: _mapPaused,
                graphPaused: _graphPaused,
                onDownloadMap: _downloadMap,
                onDownloadGraph: _downloadGraph,
              ),
              const SizedBox(height: 16),
              // Downloaded Maps Section
              Expanded(
                child: _DownloadedMapsSection(
                  offlineMapService: offlineMapService,
                  graphHopperService: graphHopperService,
                  quality: quality,
                  downloadedMapIds: downloadedMapIds,
                  downloadedGraphIds: downloadedGraphIds,
                  mapProgress: _mapProgress,
                  graphProgress: _graphProgress,
                  mapPaused: _mapPaused,
                  graphPaused: _graphPaused,
                  onDownloadMap: _downloadMap,
                  onToggleMapPause: _toggleMapPause,
                  onDeleteMap: _deleteMap,
                  onDownloadGraph: _downloadGraph,
                  onToggleGraphPause: _toggleGraphPause,
                  onDeleteGraph: _deleteGraph,
                ),
              ),
              // Storage Space Section
              _StorageSpaceSection(
                overallTotalMb: overallTotalMb,
                overallDoneMb: overallDoneMb,
              ),
              if (anyActive)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                  child: _SummaryBar(
                    percent: overallPct,
                    totalMb: overallTotalMb,
                    doneMb: overallDoneMb,
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

class _SuggestedMapsSection extends StatelessWidget {
  final OfflineMapsService offlineMapService;
  final GraphHopperDownloadService graphHopperService;
  final MapQuality quality;
  final Set<String> downloadedMapIds;
  final Set<String> downloadedGraphIds;
  final Map<String, double> mapProgress;
  final Map<String, double> graphProgress;
  final Set<String> mapPaused;
  final Set<String> graphPaused;
  final Function(Province) onDownloadMap;
  final Function(Province) onDownloadGraph;

  const _SuggestedMapsSection({
    required this.offlineMapService,
    required this.graphHopperService,
    required this.quality,
    required this.downloadedMapIds,
    required this.downloadedGraphIds,
    required this.mapProgress,
    required this.graphProgress,
    required this.mapPaused,
    required this.graphPaused,
    required this.onDownloadMap,
    required this.onDownloadGraph,
  });

  @override
  Widget build(BuildContext context) {
    // Filter out already downloaded maps from suggested maps
    final suggestedProvinces = kIranProvinces.where((p) => !downloadedMapIds.contains(p.id)).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            'نقشه‌های پیشنهادی',
            textAlign: TextAlign.right,
            style: TextStyle(color: AppColors.textSecondary(context), fontSize: 14, fontWeight: FontWeight.bold),
          ),
        ),
        SizedBox(
          height: 150, // Adjust height as needed
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            reverse: true, // For RTL layout
            padding: const EdgeInsets.symmetric(horizontal: 16),
            itemCount: suggestedProvinces.length,
            itemBuilder: (context, index) {
              final p = suggestedProvinces[index];
              final isMapDownloading = mapProgress.containsKey(p.id);
              final isGraphDownloading = graphProgress.containsKey(p.id);
              final isMapPaused = mapPaused.contains(p.id);
              final isGraphPaused = graphPaused.contains(p.id);

              return _SuggestedMapCard(
                province: p,
                offlineMapService: offlineMapService,
                graphHopperService: graphHopperService,
                quality: quality,
                isMapDownloading: isMapDownloading,
                isGraphDownloading: isGraphDownloading,
                isMapPaused: isMapPaused,
                isGraphPaused: isGraphPaused,
                mapProgress: mapProgress[p.id],
                graphProgress: graphProgress[p.id],
                onDownloadMap: () => onDownloadMap(p),
                onDownloadGraph: () => onDownloadGraph(p),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _SuggestedMapCard extends StatelessWidget {
  final Province province;
  final OfflineMapsService offlineMapService;
  final GraphHopperDownloadService graphHopperService;
  final MapQuality quality;
  final bool isMapDownloading;
  final bool isGraphDownloading;
  final bool isMapPaused;
  final bool isGraphPaused;
  final double? mapProgress;
  final double? graphProgress;
  final VoidCallback onDownloadMap;
  final VoidCallback onDownloadGraph;

  const _SuggestedMapCard({
    required this.province,
    required this.offlineMapService,
    required this.graphHopperService,
    required this.quality,
    required this.isMapDownloading,
    required this.isGraphDownloading,
    required this.isMapPaused,
    required this.isGraphPaused,
    required this.mapProgress,
    required this.graphProgress,
    required this.onDownloadMap,
    required this.onDownloadGraph,
  });

  @override
  Widget build(BuildContext context) {
    final mapSize = offlineMapService.estimateSizeMb(province, quality);
    final graphSize = graphHopperService.estimateSizeMb(province);

    return Container(
      width: 160, // Fixed width for suggested map cards
      margin: const EdgeInsets.symmetric(horizontal: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.subGlassBg(context),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.subAccentA.withOpacity(.28)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          // Placeholder for map image
          Container(
            height: 60,
            width: double.infinity,
            color: Colors.grey.withOpacity(0.2),
            child: Center(child: Text(province.name, style: TextStyle(color: Colors.white))),
          ),
          const SizedBox(height: 8),
          Text(
            province.name,
            textAlign: TextAlign.right,
            style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
          ),
          Text(
            'همراه با شهرهای اطراف',
            textAlign: TextAlign.right,
            style: TextStyle(color: AppColors.textMuted(context), fontSize: 10),
          ),
          const Spacer(),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '${_fmtSize(mapSize)} / ${_fmtSize(graphSize)}',
                style: TextStyle(color: AppColors.textMuted(context), fontSize: 10),
              ),
              if (isMapDownloading || isGraphDownloading)
                SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(
                    value: isMapDownloading ? mapProgress : graphProgress,
                    strokeWidth: 2,
                    backgroundColor: Colors.white.withOpacity(.08),
                    valueColor: const AlwaysStoppedAnimation(AppColors.subAccentA),
                  ),
                )
              else
                GestureDetector(
                  onTap: () {
                    onDownloadMap();
                    onDownloadGraph();
                  },
                  child: Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppColors.subAccentA.withOpacity(.14),
                      border: Border.all(color: AppColors.subAccentA, width: 1.2),
                    ),
                    child: const Icon(Icons.download_rounded, color: AppColors.subAccentA, size: 14),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DownloadedMapsSection extends StatelessWidget {
  final OfflineMapsService offlineMapService;
  final GraphHopperDownloadService graphHopperService;
  final MapQuality quality;
  final Set<String> downloadedMapIds;
  final Set<String> downloadedGraphIds;
  final Map<String, double> mapProgress;
  final Map<String, double> graphProgress;
  final Set<String> mapPaused;
  final Set<String> graphPaused;
  final Function(Province) onDownloadMap;
  final Function(Province) onToggleMapPause;
  final Function(Province) onDeleteMap;
  final Function(Province) onDownloadGraph;
  final Function(Province) onToggleGraphPause;
  final Function(Province) onDeleteGraph;

  const _DownloadedMapsSection({
    required this.offlineMapService,
    required this.graphHopperService,
    required this.quality,
    required this.downloadedMapIds,
    required this.downloadedGraphIds,
    required this.mapProgress,
    required this.graphProgress,
    required this.mapPaused,
    required this.graphPaused,
    required this.onDownloadMap,
    required this.onToggleMapPause,
    required this.onDeleteMap,
    required this.onDownloadGraph,
    required this.onToggleGraphPause,
    required this.onDeleteGraph,
  });

  @override
  Widget build(BuildContext context) {
    final downloadedProvinces = kIranProvinces.where((p) => downloadedMapIds.contains(p.id) || downloadedGraphIds.contains(p.id) || mapProgress.containsKey(p.id) || graphProgress.containsKey(p.id)).toList();

    if (downloadedProvinces.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            'نقشه‌های دانلود شده',
            textAlign: TextAlign.right,
            style: TextStyle(color: AppColors.textSecondary(context), fontSize: 14, fontWeight: FontWeight.bold),
          ),
        ),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            itemCount: downloadedProvinces.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (context, i) {
              final p = downloadedProvinces[i];
              final isMapDownloaded = downloadedMapIds.contains(p.id);
              final isGraphDownloaded = downloadedGraphIds.contains(p.id);
              final isMapDownloading = mapProgress.containsKey(p.id);
              final isGraphDownloading = graphProgress.containsKey(p.id);
              final isMapPaused = mapPaused.contains(p.id);
              final isGraphPaused = graphPaused.contains(p.id);

              final mapSize = offlineMapService.estimateSizeMb(p, quality);
              final graphSize = graphHopperService.estimateSizeMb(p);

              return _DownloadedMapCard(
                province: p,
                mapSize: mapSize,
                graphSize: graphSize,
                isMapDownloaded: isMapDownloaded,
                isGraphDownloaded: isGraphDownloaded,
                isMapDownloading: isMapDownloading,
                isGraphDownloading: isGraphDownloading,
                isMapPaused: isMapPaused,
                isGraphPaused: isGraphPaused,
                mapProgress: mapProgress[p.id],
                graphProgress: graphProgress[p.id],
                onDownloadMap: () => onDownloadMap(p),
                onToggleMapPause: () => onToggleMapPause(p),
                onDeleteMap: () => onDeleteMap(p),
                onDownloadGraph: () => onDownloadGraph(p),
                onToggleGraphPause: () => onToggleGraphPause(p),
                onDeleteGraph: () => onDeleteGraph(p),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _DownloadedMapCard extends StatelessWidget {
  final Province province;
  final double mapSize;
  final double graphSize;
  final bool isMapDownloaded;
  final bool isGraphDownloaded;
  final bool isMapDownloading;
  final bool isGraphDownloading;
  final bool isMapPaused;
  final bool isGraphPaused;
  final double? mapProgress;
  final double? graphProgress;
  final VoidCallback onDownloadMap;
  final VoidCallback onToggleMapPause;
  final VoidCallback onDeleteMap;
  final VoidCallback onDownloadGraph;
  final VoidCallback onToggleGraphPause;
  final VoidCallback onDeleteGraph;

  const _DownloadedMapCard({
    required this.province,
    required this.mapSize,
    required this.graphSize,
    required this.isMapDownloaded,
    required this.isGraphDownloaded,
    required this.isMapDownloading,
    required this.isGraphDownloading,
    required this.isMapPaused,
    required this.isGraphPaused,
    required this.mapProgress,
    required this.graphProgress,
    required this.onDownloadMap,
    required this.onToggleMapPause,
    required this.onDeleteMap,
    required this.onDownloadGraph,
    required this.onToggleGraphPause,
    required this.onDeleteGraph,
  });

  @override
  Widget build(BuildContext context) {
    final totalSize = mapSize + graphSize;
    final currentProgress = (mapProgress ?? 0) * mapSize + (graphProgress ?? 0) * graphSize;
    final overallProgress = totalSize > 0 ? currentProgress / totalSize : 0.0;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(.03),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              // Placeholder for map image
              Container(
                width: 60,
                height: 60,
                color: Colors.grey.withOpacity(0.2),
                child: Center(child: Text(province.name, style: TextStyle(color: Colors.white))),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      province.name,
                      textAlign: TextAlign.right,
                      style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
                    ),
                    Text(
                      'همراه با شهرهای اطراف',
                      textAlign: TextAlign.right,
                      style: TextStyle(color: AppColors.textMuted(context), fontSize: 11),
                    ),
                    const SizedBox(height: 4),
                    LinearProgressIndicator(
                      value: overallProgress,
                      backgroundColor: Colors.white.withOpacity(.08),
                      valueColor: const AlwaysStoppedAnimation(AppColors.subAccentA),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          '${(overallProgress * 100).round()}%',
                          style: const TextStyle(color: Colors.white, fontSize: 10),
                        ),
                        Text(
                          '${_fmtSize(currentProgress)} / ${_fmtSize(totalSize)}',
                          style: TextStyle(color: AppColors.textMuted(context), fontSize: 10),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _DownloadActionButton(
                label: 'نقشه',
                isDownloaded: isMapDownloaded,
                isDownloading: isMapDownloading,
                isPaused: isMapPaused,
                onDownload: onDownloadMap,
                onTogglePause: onToggleMapPause,
                onDelete: onDeleteMap,
                accentColor: AppColors.subAccentA,
              ),
              _DownloadActionButton(
                label: 'گراف',
                isDownloaded: isGraphDownloaded,
                isDownloading: isGraphDownloading,
                isPaused: isGraphPaused,
                onDownload: onDownloadGraph,
                onTogglePause: onToggleGraphPause,
                onDelete: onDeleteGraph,
                accentColor: AppColors.subAccentA,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DownloadActionButton extends StatelessWidget {
  final String label;
  final bool isDownloaded;
  final bool isDownloading;
  final bool isPaused;
  final VoidCallback onDownload;
  final VoidCallback onTogglePause;
  final VoidCallback onDelete;
  final Color accentColor;

  const _DownloadActionButton({
    required this.label,
    required this.isDownloaded,
    required this.isDownloading,
    required this.isPaused,
    required this.onDownload,
    required this.onTogglePause,
    required this.onDelete,
    required this.accentColor,
  });

  @override
  Widget build(BuildContext context) {
    Widget iconWidget;
    VoidCallback? onPressed;
    Color buttonColor = Colors.transparent;
    Color textColor = accentColor;

    if (isDownloading) {
      iconWidget = Icon(isPaused ? Icons.play_arrow_rounded : Icons.pause_rounded, color: accentColor, size: 18);
      onPressed = onTogglePause;
      buttonColor = accentColor.withOpacity(0.14);
    } else if (isDownloaded) {
      iconWidget = Icon(Icons.check_circle_outline_rounded, color: Colors.green, size: 18);
      onPressed = onDelete; // Option to delete downloaded item
      textColor = Colors.green;
    } else {
      iconWidget = Icon(Icons.download_rounded, color: accentColor, size: 18);
      onPressed = onDownload;
      buttonColor = accentColor.withOpacity(0.14);
    }

    return GestureDetector(
      onTap: onPressed,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
        decoration: BoxDecoration(
          color: buttonColor,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: textColor.withOpacity(0.5)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            iconWidget,
            const SizedBox(width: 6),
            Text(label, style: TextStyle(color: textColor, fontSize: 12, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }
}

class _StorageSpaceSection extends StatelessWidget {
  final double overallTotalMb;
  final double overallDoneMb;

  const _StorageSpaceSection({
    required this.overallTotalMb,
    required this.overallDoneMb,
  });

  @override
  Widget build(BuildContext context) {
    final usedSpaceGb = overallDoneMb / 1024;
    final totalSpaceGb = overallTotalMb / 1024; // Placeholder for total device storage
    final availableSpaceGb = totalSpaceGb - usedSpaceGb;

    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.subGlassBg(context),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(.06)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'فضای ذخیره‌سازی',
              textAlign: TextAlign.right,
              style: TextStyle(color: AppColors.textSecondary(context), fontSize: 14, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: totalSpaceGb > 0 ? usedSpaceGb / totalSpaceGb : 0.0,
              backgroundColor: Colors.white.withOpacity(.08),
              valueColor: const AlwaysStoppedAnimation(AppColors.subAccentA),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'استفاده شده: ${_fmtSize(overallDoneMb)}',
                  style: TextStyle(color: AppColors.textMuted(context), fontSize: 12),
                ),
                Text(
                  'موجود: ${_fmtSize(overallTotalMb - overallDoneMb)}',
                  style: TextStyle(color: AppColors.textMuted(context), fontSize: 12),
                ),
              ],
            ),
            const SizedBox(height: 16),
            GestureDetector(
              onTap: () {
                // Storage management feature for future implementation
              },
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(
                  color: AppColors.subAccentA.withOpacity(.14),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.subAccentA.withOpacity(.5)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.storage_rounded, color: AppColors.subAccentA, size: 18),
                    const SizedBox(width: 8),
                    Text(
                      'مدیریت فضای ذخیره‌سازی نقشه',
                      style: TextStyle(color: AppColors.subAccentA, fontSize: 14, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
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
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.subGlassBg(context),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(.06)),
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
                Text('کل پیشرفت',
                    style: TextStyle(color: AppColors.textMuted(context), fontSize: 11)),
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
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text('سرعت دانلود', style: TextStyle(color: AppColors.textMuted(context), fontSize: 11)),
                    const SizedBox(width: 4),
                    Icon(Icons.arrow_downward_rounded, color: AppColors.textMuted(context), size: 12),
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
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text('زمان باقی‌مانده', style: TextStyle(color: AppColors.textMuted(context), fontSize: 11)),
                    const SizedBox(width: 4),
                    Icon(Icons.access_time_rounded, color: AppColors.textMuted(context), size: 12),
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

String _fmtSize(double mb) {
  if (mb >= 1024) return '${(mb / 1024).toStringAsFixed(1)} GB';
  return '${mb.round()} MB';
}
