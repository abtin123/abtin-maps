import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'abm_notifier.dart';

/// ذخیره‌ساز رخدادهای تشخیصی برنامه.
///
/// گزارش عمومی برای رخدادهای نادر باقی می‌ماند، اما GPS مسیر مستقل خود را
/// دارد. این جداسازی مانع می‌شود رندرِ ده‌ها/صدها کاشیِ نقشه، اولین فیکس،
/// وضعیت مجوز یا خطای provider مکان را از گزارش قابل ارسالِ کاربر خارج کند.
class AbmDebugLog {
  static const int _maxGeneralLogs = 200;
  static const int _maxGpsLogs = 300;

  static final List<String> _logs = [];
  static final List<String> _gpsLogs = [];

  static List<String> get logs => List.unmodifiable(_logs.reversed);
  static List<String> get gpsLogs => List.unmodifiable(_gpsLogs.reversed);

  /// رخداد عمومیِ کم‌تعداد. رخدادهای داخل حلقهٔ رندر نباید از این متد استفاده
  /// کنند؛ آن‌ها نه برای کاربر مفیدند و نه نباید I/O اضافی ایجاد کنند.
  static Future<void> add(String text) async {
    final line = _line(text);
    _appendToMemory(_logs, line, _maxGeneralLogs);
    AbmNotifier.show(text);
    await _appendToFile('abm_debug.log', line);
  }

  /// لاگ مستقل GPS شامل زمان شروع، وضعیت سرویس/مجوز، اولین فیکس، تغییر provider
  /// و خطاها. صفحهٔ گزارش برنامه دقیقاً همین لیست را نشان می‌دهد.
  static Future<void> addGps(String text) async {
    final line = _line('[GPS] $text');
    _appendToMemory(_gpsLogs, line, _maxGpsLogs);
    AbmNotifier.show(text);
    await _appendToFile('gps_debug.log', line);
  }

  static String _line(String text) =>
      '[${DateTime.now().toIso8601String()}] $text';

  static void _appendToMemory(List<String> target, String line, int limit) {
    target.add(line);
    if (target.length > limit) target.removeRange(0, target.length - limit);
  }

  static Future<void> _appendToFile(String name, String line) async {
    try {
      final dir = await getApplicationSupportDirectory();
      final file = File('${dir.path}/$name');
      await file.writeAsString('$line\n', mode: FileMode.append, flush: false);
    } catch (_) {
      // لاگ نباید هرگز مسیر اصلی GPS یا رابط کاربری را مختل کند.
    }
  }

  static void clear() {
    _logs.clear();
    _gpsLogs.clear();
  }

  static void clearGps() => _gpsLogs.clear();
}
