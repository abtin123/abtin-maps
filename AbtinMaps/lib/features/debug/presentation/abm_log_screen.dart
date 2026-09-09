import 'package:flutter/material.dart';
import '../../../core/localization/app_localizations.dart';
import 'package:flutter/services.dart';

import '../../../core/abm_notifier.dart';
import '../../../core/abm_debug_log.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/page_header.dart';

/// صفحهٔ گزارش تشخیصی. دو لیست جدا نمایش داده می‌شود:
///  «GPS» → رخدادهای موقعیت، وضعیت سرویس، مجوزها، تغییر provider.
///  «عمومی» → کرش‌های build/framework/zone و خطاهای دانلود نقشه/مانیفست
///  (ثبت‌شده با AbmDebugLog.add؛ قبلاً این صفحه اصلاً این لیست را نشان
///  نمی‌داد، پس این خطاها بی‌اثر گم می‌شدند).
class AbmLogScreen extends StatefulWidget {
  const AbmLogScreen({super.key});

  @override
  State<AbmLogScreen> createState() => _AbmLogScreenState();
}

class _AbmLogScreenState extends State<AbmLogScreen> {
  bool _showGeneral = false;

  @override
  void initState() {
    super.initState();
    AbmNotifier.message.addListener(_onNewLine);
  }

  @override
  void dispose() {
    AbmNotifier.message.removeListener(_onNewLine);
    super.dispose();
  }

  void _onNewLine() {
    if (mounted) setState(() {});
  }

  Future<void> _copyAll(BuildContext context, List<String> logs) async {
    await Clipboard.setData(ClipboardData(text: logs.join('\n')));
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(_showGeneral ? 'گزارش عمومی کپی شد.' : 'گزارش GPS کپی شد.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final logs = _showGeneral ? AbmDebugLog.logs : AbmDebugLog.gpsLogs;
    return Scaffold(
      backgroundColor: AppColors.background(context),
      appBar: PageHeader(
        title: _showGeneral ? 'گزارش تشخیصی عمومی' : 'گزارش تشخیصی GPS',
        backRoute: '/settings',
        actions: [
          IconButton(
            icon: const Icon(Icons.copy_rounded),
            tooltip: 'کپی همه',
            onPressed: logs.isEmpty ? null : () => _copyAll(context, logs),
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline_rounded),
            tooltip: 'پاک‌کردن',
            onPressed: logs.isEmpty
                ? null
                : () => setState(
                      _showGeneral ? AbmDebugLog.clear : AbmDebugLog.clearGps,
                    ),
          ),
        ],
      ),
      body: Stack(
        children: [
          Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                child: Row(
                  children: [
                    Expanded(
                      child: _LogTabButton(
                        label: AppStrings.literal('GPS (${AbmDebugLog.gpsLogs.length})'),
                        selected: !_showGeneral,
                        onTap: () => setState(() => _showGeneral = false),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _LogTabButton(
                        label: AppStrings.literal('عمومی / کرش (${AbmDebugLog.logs.length})'),
                        selected: _showGeneral,
                        onTap: () => setState(() => _showGeneral = true),
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                  child: _LogList(
                      logs: logs,
                      emptyForGeneral: _showGeneral,
                      bottomPadding: 112)),
            ],
          ),
          const BottomNav(currentPage: NavKey.settings),
        ],
      ),
    );
  }
}

class _LogTabButton extends StatelessWidget {
  const _LogTabButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? Colors.white.withOpacity(0.12) : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Colors.white.withOpacity(selected ? 0.25 : 0.08)),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? Colors.white : Colors.white54,
            fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
            fontSize: 12.5,
          ),
        ),
      ),
    );
  }
}

class _LogList extends StatelessWidget {
  const _LogList({
    required this.logs,
    required this.emptyForGeneral,
    this.bottomPadding = 32,
  });

  final List<String> logs;
  final bool emptyForGeneral;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return logs.isEmpty
          ? Center(
              child: Text(
                emptyForGeneral
                    ? 'هنوز کرش یا خطای عمومی ثبت نشده است.\nمشکلات build، فریم‌ورک، async و دانلود نقشه/مانیفست اینجا نمایش داده می‌شوند.'
                    : 'هنوز رخداد GPS ثبت نشده است.\nپس از باز کردن نقشه، وضعیت سرویس، مجوز و اولین فیکس اینجا نمایش داده می‌شود.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white54),
              ),
            )
          : ListView.separated(
              padding: EdgeInsets.fromLTRB(16, 12, 16, bottomPadding),
              itemCount: logs.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, i) {
                final line = logs[i];
                final isError = line.contains('خطا') ||
                    line.contains('ناموفق') ||
                    line.contains('CRASH') ||
                    line.contains('failed') ||
                    line.contains('fallback');
                return Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: isError
                        ? const Color(0x33EB5757)
                        : Colors.white.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: isError
                          ? const Color(0x66EB5757)
                          : Colors.white.withOpacity(0.08),
                    ),
                  ),
                  child: SelectableText(
                    line,
                    style: TextStyle(
                      color: isError ? const Color(0xFFFF8A8A) : Colors.white70,
                      fontSize: 12.5,
                      fontFamily: 'monospace',
                      height: 1.4,
                    ),
                  ),
                );
              },
            );
  }
}
