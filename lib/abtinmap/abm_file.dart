import 'dart:convert';
import 'dart:io';
import 'dart:isolate';
import 'dart:typed_data';

import '../core/abm_debug_log.dart';
import 'abm_container.dart';
import 'abm_models.dart';
import 'abm_varint.dart';
import 'abm_zstd.dart';

/// خواننده‌ی فرمت ABTINMAP (.abm) — پورت بایت‌به‌بایتِ abtinmap_inspect.py.
///
/// چیدمان هدر (۱۲۸ بایت، little-endian):
/// ```
/// 0   8s  magic  = "ABTINMAP"
/// 8   H   version
/// 10  H   flags
/// 12  B   base_zoom
/// 13  B   overview_zoom_count
/// 14  6B  overview_zooms
/// 20  4i  bbox (lon_min, lat_min, lon_max, lat_max) * 1e7
/// 36  I   tile_count
/// 40  Q   index_offset
/// 48  I   index_compressed_size
/// 52  I   index_raw_size
/// 56  Q   strings_offset
/// 64  I   strings_compressed_size
/// 68  I   strings_raw_size
/// 72  I   string_count
/// 76  I   coord_scale
/// 80  Q   build_epoch
/// 88  16s region (NUL-padded)
/// ```
class AbmFile {
  AbmFile._(
    this._raf,
    this._zstd,
    this.sourcePath,
    this._sourceLength,
    this._sourceOffset,
  );

  static const List<int> magic = [
    0x41,
    0x42,
    0x54,
    0x49,
    0x4E,
    0x4D,
    0x41,
    0x50
  ];
  static const int headerSize = 128;

  final RandomAccessFile _raf;
  final AbmZstd _zstd;

  /// مسیر فایل .abm روی دیسک — برای ساختن mapId کش رندر استفاده می‌شود.
  final String sourcePath;
  final int _sourceLength;
  final int _sourceOffset;

  /// صف سریال‌سازیِ دسترسی به [_raf]. `setPosition` و `read` دو عملیات جدا
  /// روی یک هندل‌اند؛ اگر رندرر (حین پن‌کردنِ نقشه) و مسیریاب (حین محاسبه‌ی
  /// مسیر بین‌شهری) هم‌زمان `tile()` صدا بزنند، دو جفت setPosition/read روی
  /// هم می‌افتند و دارت با
  /// `FileSystemException: An async operation is currently pending` خطا
  /// می‌دهد. همه‌ی خواندن‌های خام باید از [_readAt] رد شوند تا هر جفت
  /// setPosition+read به‌صورت اتمیک (بدون این‌که فراخوانیِ دیگری بینشان
  /// فاصله بیندازد) اجرا شود.
  Future<void> _ioQueue = Future<void>.value();

  Future<T> _readAt<T>(int position, Future<T> Function() body) {
    if (position < 0 || position >= _sourceLength) {
      return Future<T>.error(
        const AbmFormatException('offset خواندن graph ABM نامعتبر است.'),
      );
    }
    final result = _ioQueue.then((_) async {
      await _raf.setPosition(_sourceOffset + position);
      return body();
    });
    _ioQueue = result.then((_) {}, onError: (_) {});
    return result;
  }

  late final int version;
  late final int flags;
  late final int baseZoom;
  late final List<int> overviewZooms;

  /// [lonMin, latMin, lonMax, latMax]
  late final List<double> bbox;

  late final int tileCount;
  late final int indexOffset;
  late final int indexComp;
  late final int indexRaw;
  late final int stringsOffset;
  late final int stringsComp;
  late final int stringsRaw;
  late final int stringCount;
  late final int coordScale;
  late final DateTime buildTime;
  late final String region;

  late final List<String> strings;

  /// شناسه‌های کاشی (مرتب و صعودی) و رکورد ایندکس متناظر.
  late final List<int> tileIds;
  late final List<_TileRecord> tileRecords;

  final Map<int, AbmTile> _cache = {};
  int _cacheLimit = 192;

  /// اندازه‌ی حافظه‌ی نهان کاشی‌ها (تعداد کاشی).
  set cacheLimit(int value) => _cacheLimit = value < 8 ? 8 : value;

  static Future<AbmFile> open(File file, {AbmZstd? zstd}) async {
    final container = await AbtinMapContainer.tryOpen(file);
    final sourceOffset = container?.graph.offset ?? 0;
    final length = container?.graph.length ?? await file.length();
    await AbmDebugLog.add(
      'ABM open: ${file.path} graphSize=$length container=${container != null}',
    );
    final raf = await file.open();
    final map = AbmFile._(
      raf,
      zstd ?? PluginAbmZstd(),
      file.path,
      length,
      sourceOffset,
    );
    try {
      await map._readHeader();
      await map._readStrings();
      await map._readIndex();
      await AbmDebugLog.add(
          'ABM loaded tiles=${map.tileCount} zoom=${map.baseZoom}');
    } catch (e) {
      await AbmDebugLog.add('ABM OPEN ERROR: $e');
      await raf.close();
      rethrow;
    }
    return map;
  }

  Future<void> close() async {
    _cache.clear();
    await _raf.close();
  }

  Future<void> _readHeader() async {
    if (_sourceLength < headerSize) {
      throw const AbmFormatException(
          'segment graph کوتاه‌تر از هدر ۱۲۸ بایتی است.');
    }
    final h = await _readAt(0, () => _raf.read(headerSize));
    if (h.length < headerSize) {
      throw const AbmFormatException('فایل کوتاه‌تر از هدر ۱۲۸ بایتی است.');
    }
    for (var i = 0; i < 8; i++) {
      if (h[i] != magic[i]) {
        throw const AbmFormatException(
            'magic نامعتبر — این فایل ABTINMAP نیست.');
      }
    }
    final b = ByteData.sublistView(h);
    version = b.getUint16(8, Endian.little);
    // v2 فیلد جدید width_dm را به هر way اضافه کرد (بین speed_code و
    // تعداد refs)؛ خواندن فایل‌های v1 قدیمی با این خواننده باعث می‌شود
    // بایت‌ها اشتباه parse شوند (نه فقط عرض غلط، بلکه کل refs/edges بعدی
    // هم جابه‌جا می‌خورند) — پس صریحاً رد می‌کنیم تا خرابی خاموش رخ ندهد.
    if (version < 2) {
      throw AbmFormatException(
          'این فایل .abm با نسخه‌ی قدیمی‌تر (v$version) ساخته شده و با این نسخه‌ی اپ سازگار نیست؛ '
          'لطفاً نقشه را دوباره با abtinmap_build.py جدید بسازید.');
    }
    flags = b.getUint16(10, Endian.little);
    baseZoom = b.getUint8(12);
    final ovzCount = b.getUint8(13);
    final zooms = <int>[];
    for (var i = 0; i < 6; i++) {
      final z = b.getUint8(14 + i);
      if (z != 0) zooms.add(z);
    }
    overviewZooms = zooms.take(ovzCount).toList(growable: false);
    bbox = [
      b.getInt32(20, Endian.little) / 1e7,
      b.getInt32(24, Endian.little) / 1e7,
      b.getInt32(28, Endian.little) / 1e7,
      b.getInt32(32, Endian.little) / 1e7,
    ];
    tileCount = b.getUint32(36, Endian.little);
    indexOffset = b.getUint64(40, Endian.little);
    indexComp = b.getUint32(48, Endian.little);
    indexRaw = b.getUint32(52, Endian.little);
    stringsOffset = b.getUint64(56, Endian.little);
    stringsComp = b.getUint32(64, Endian.little);
    stringsRaw = b.getUint32(68, Endian.little);
    stringCount = b.getUint32(72, Endian.little);
    coordScale = b.getUint32(76, Endian.little);
    if (indexOffset > _sourceLength ||
        indexComp > _sourceLength - indexOffset ||
        stringsOffset > _sourceLength ||
        stringsComp > _sourceLength - stringsOffset) {
      throw const AbmFormatException('offsetهای داخلی graph ABM نامعتبر است.');
    }
    buildTime = DateTime.fromMillisecondsSinceEpoch(
        b.getUint64(80, Endian.little) * 1000,
        isUtc: true);
    final regionBytes = h.sublist(88, 104).where((c) => c != 0).toList();
    region = utf8.decode(regionBytes, allowMalformed: true);
  }

  Future<void> _readStrings() async {
    final comp = await _readAt(stringsOffset, () => _raf.read(stringsComp));
    final raw = await _zstd.decompress(Uint8List.fromList(comp),
        expectedSize: stringsRaw);
    final c = ByteCursor(raw);
    final n = c.uvarint();
    final out = List<String>.filled(n, '', growable: false);
    for (var i = 0; i < n; i++) {
      final len = c.uvarint();
      out[i] = utf8.decode(raw.sublist(c.p, c.p + len), allowMalformed: true);
      c.p += len;
    }
    strings = out;
  }

  /// آستانه‌ای که بالاتر از آن، حلقه‌ی uvarint-decode ایندکس (که برای
  /// نقشه‌های کشوری می‌تواند صدها هزار رکورد باشد) روی یک ایزوله‌ی جدا
  /// اجرا می‌شود تا isolate اصلی/UI حین باز کردن نقشه‌ی آفلاین فریز نکند.
  static const int _isolateParseThreshold = 20000;

  Future<void> _readIndex() async {
    final comp = await _readAt(indexOffset, () => _raf.read(indexComp));
    final raw = await _zstd.decompress(Uint8List.fromList(comp),
        expectedSize: indexRaw);
    final count = tileCount;
    // ریشه‌ی واقعیِ خطا: closureِ Isolate.run قبلاً همین‌جا، داخلِ خودِ
    // _readIndex (یک متد نمونه که به _raf/_zstd/tileIds/tileRecords هم
    // دسترسی دارد) تعریف می‌شد. حتی وقتی closure فقط raw/count را
    // می‌گرفت، چون در همان بلوکِ کد `this` هم استفاده می‌شود، کامپایلر
    // Dart یک Context مشترک برای کل اسکوپ می‌سازد و آن Context به‌طور
    // ضمنی `this` (شاملِ _raf/_zstd و هر Future معلقِ داخلشان) را هم به
    // ایزوله می‌فرستد — دقیقاً پیامِ خطای "Instance of AbmFile ... Class
    // _Future". فقط کپی‌کردنِ raw این را حل نمی‌کرد چون خودِ this هنوز
    // capture می‌شد. راه‌حلِ درست: کل فراخوانیِ Isolate.run را به یک متدِ
    // static مستقل منتقل می‌کنیم — در متدِ static اصلاً `this` وجود
    // ندارد، پس closure ساختاری امکانِ captureِ آن را ندارد.
    final parsed = await _parseIndexMaybeIsolated(raw, count);
    tileIds = parsed.ids;
    tileRecords = parsed.records;
  }

  /// این متد عمداً static است (نه یک تابعِ محلیِ داخلِ _readIndex) تا
  /// closureِ Isolate.run هیچ راهی برای captureِ `this` نداشته باشد.
  static Future<_ParsedIndex> _parseIndexMaybeIsolated(
      Uint8List raw, int tileCount) {
    if (tileCount <= _isolateParseThreshold) {
      return Future.value(_parseIndexBytes(raw, tileCount));
    }
    return Isolate.run(() => _parseIndexBytes(raw, tileCount));
  }

  static _ParsedIndex _parseIndexBytes(Uint8List raw, int tileCount) {
    final c = ByteCursor(raw);
    final ids = <int>[];
    final recs = <_TileRecord>[];
    var tid = 0;
    var end = 0;
    for (var i = 0; i < tileCount; i++) {
      final dt = c.uvarint();
      final deltaOffset = c.uvarint();
      final compLen = c.uvarint();
      final rawLen = c.uvarint();
      final mask = c.uvarint();
      tid += dt;
      final off = end + deltaOffset;
      end = off + compLen;
      ids.add(tid);
      recs.add(_TileRecord(off, compLen, rawLen, mask));
    }
    return _ParsedIndex(ids, recs);
  }

  /// شناسهٔ پایدار نقشه از نام فایل بدون پسوند (مثلاً "IR" از "IR.abm").
  String get mapId {
    final base = sourcePath.split(RegExp(r'[\\/]')).last;
    final dot = base.lastIndexOf('.');
    return dot > 0 ? base.substring(0, dot) : base;
  }

  /// امضای محتوای فایل .abm — از build_epoch (زمان ساختِ نقشه توسط
  /// abtinmap_build.py) + اندازه‌ی فایل ساخته می‌شود. اگر نقشه دوباره
  /// دانلود/بازسازی شود، build_epoch یا سایز عوض می‌شود و این فینگرپرینت
  /// هم عوض می‌شود؛ این مقدار برای تشخیص نصب و دادهٔ قدیمی استفاده می‌شود.
  String get sourceFingerprint =>
      '${buildTime.millisecondsSinceEpoch}_${_sourceLength}_v$version';

  String stringAt(int i) => (i >= 0 && i < strings.length) ? strings[i] : '';

  bool containsPoint(double lon, double lat) =>
      lon >= bbox[0] && lon <= bbox[2] && lat >= bbox[1] && lat <= bbox[3];

  /// زوم‌های موجود در فایل (base + overview) به‌صورت مرتب.
  List<int> get availableZooms {
    final s = <int>{baseZoom, ...overviewZooms}.toList()..sort();
    return s;
  }

  /// نزدیک‌ترین زوم موجود به [z] که بزرگ‌تر از آن نباشد.
  int resolveZoom(int z) {
    final zooms = availableZooms;
    var best = zooms.first;
    for (final candidate in zooms) {
      if (candidate <= z) best = candidate;
    }
    return best;
  }

  int _indexOfTile(int tileId) {
    var lo = 0;
    var hi = tileIds.length;
    while (lo < hi) {
      final mid = (lo + hi) >> 1;
      if (tileIds[mid] < tileId) {
        lo = mid + 1;
      } else {
        hi = mid;
      }
    }
    if (lo >= tileIds.length || tileIds[lo] != tileId) return -1;
    return lo;
  }

  bool hasTile(int z, int x, int y) =>
      _indexOfTile(AbmTileMath.tileId(z, x, y)) >= 0;

  /// خواندن یک کاشی؛ null اگر در فایل نباشد (دریا/خارج از پوشش).
  Future<AbmTile?> tile(int z, int x, int y) async {
    final id = AbmTileMath.tileId(z, x, y);
    final cached = _cache[id];
    if (cached != null) return cached;
    final i = _indexOfTile(id);
    if (i < 0) {
      // نبود کاشی بیرون از محدودهٔ نقشه یک حالت عادی است؛ لاگ‌کردن هر رخداد
      // در این مسیر داغ رندر، گزارش تشخیصی را با صدها سطر نامرتبط پر می‌کرد.
      return null;
    }
    final rec = tileRecords[i];
    final comp = await _readAt(rec.offset, () => _raf.read(rec.compLength));
    final body = await _zstd.decompress(Uint8List.fromList(comp),
        expectedSize: rec.rawLength);
    final parsed = _parseTile(body, z, x, y);
    if (_cache.length >= _cacheLimit) _cache.clear();
    _cache[id] = parsed;
    return parsed;
  }

  AbmTile _parseTile(Uint8List body, int z, int x, int y) {
    final tile =
        AbmTile(z: z, x: x, y: y, origin: AbmTileMath.tileOrigin(x, y, z));
    final c = ByteCursor(body);
    final sectionCount = c.uvarint();
    for (var i = 0; i < sectionCount; i++) {
      final stype = c.uvarint();
      final slen = c.uvarint();
      final start = c.p;
      _parseSection(tile, stype, body, start, start + slen);
      c.p = start + slen;
    }
    return tile;
  }

  void _parseSection(AbmTile t, int stype, Uint8List b, int start, int end) {
    final c = ByteCursor(b, start);
    final s = coordScale.toDouble();
    final olon = t.origin.lon;
    final olat = t.origin.lat;

    switch (stype) {
      case 1: // nodes — delta-coded
        final n = c.uvarint();
        var lo = 0;
        var la = 0;
        for (var i = 0; i < n; i++) {
          lo += c.svarint();
          la += c.svarint();
          t.nodes.add(AbmPoint(olon + lo / s, olat + la / s));
        }
        break;
      case 2: // ways
        final n = c.uvarint();
        for (var i = 0; i < n; i++) {
          final klass = c.uvarint();
          final attr = c.uvarint();
          final minZoom = c.uvarint();
          final nameId = c.uvarint();
          final speedCode = c.uvarint();
          // فیلد width_dm (عرض به دسی‌متر) از فرمت v2 اضافه شد — دقیقاً
          // بین speed_code و تعداد refs قرار دارد (abtinmap_build.py).
          final widthDm = c.uvarint();
          final cnt = c.uvarint();
          final refs = List<int>.filled(cnt, 0, growable: false);
          var prev = 0;
          for (var q = 0; q < cnt; q++) {
            if (q == 0) {
              prev = c.uvarint();
            } else {
              prev += c.svarint();
            }
            refs[q] = prev;
          }
          t.ways.add(AbmWay(
            klass: klass,
            attr: attr,
            minZoom: minZoom,
            name: stringAt(nameId),
            speedCode: speedCode,
            widthDm: widthDm,
            refs: refs,
          ));
        }
        break;
      case 3: // routing edges — delta-coded way index
        final n = c.uvarint();
        var wi = 0;
        for (var i = 0; i < n; i++) {
          wi += c.uvarint();
          final a = c.uvarint();
          final bb = c.uvarint();
          final fw = c.uvarint();
          final bw = c.uvarint();
          t.edges.add(AbmEdge(wi, a, bb, fw, bw));
        }
        break;
      case 4: // areas
        final n = c.uvarint();
        for (var i = 0; i < n; i++) {
          final klass = c.uvarint();
          final attr = c.uvarint();
          final minZoom = c.uvarint();
          final nameId = c.uvarint();
          final ringCount = c.uvarint();
          final rings = <List<AbmPoint>>[];
          for (var r = 0; r < ringCount; r++) {
            final cnt = c.uvarint();
            var lo = 0;
            var la = 0;
            final ring = <AbmPoint>[];
            for (var q = 0; q < cnt; q++) {
              lo += c.svarint();
              la += c.svarint();
              ring.add(AbmPoint(olon + lo / s, olat + la / s));
            }
            rings.add(ring);
          }
          t.areas.add(AbmArea(
            klass: klass,
            attr: attr,
            minZoom: minZoom,
            name: stringAt(nameId),
            rings: rings,
          ));
        }
        break;
      case 5: // POIs — delta-coded positions
        final n = c.uvarint();
        var lo = 0;
        var la = 0;
        for (var i = 0; i < n; i++) {
          lo += c.svarint();
          la += c.svarint();
          final klass = c.uvarint();
          final minZoom = c.uvarint();
          final nameId = c.uvarint();
          t.pois.add(AbmPoi(
            point: AbmPoint(olon + lo / s, olat + la / s),
            klass: klass,
            minZoom: minZoom,
            name: stringAt(nameId),
          ));
        }
        break;
      case 6: // border node → global graph key
        final n = c.uvarint();
        for (var i = 0; i < n; i++) {
          final ni = c.uvarint();
          final gk = c.uvarint();
          t.border[ni] = gk;
        }
        break;
      default:
        // بخش ناشناخته (نسخه‌ی جدیدتر فرمت) — نادیده گرفته می‌شود.
        break;
    }
  }

  /// کلید جهانی گره [nodeIndex] در کاشی [t] — هم‌ارز `_graph_key` مرجع.
  int graphKeyOf(AbmTile t, int nodeIndex) {
    final p = t.nodes[nodeIndex];
    return AbmTileMath.graphKey(
      (p.lon * coordScale).round(),
      (p.lat * coordScale).round(),
    );
  }

  /// آمار خلاصه (برای صفحه‌ی «نقشه‌های آفلاین»).
  AbmStats stats() {
    final perZoom = <int, int>{};
    var comp = 0;
    var raw = 0;
    for (var i = 0; i < tileIds.length; i++) {
      final z = tileIds[i] >> 44;
      perZoom[z] = (perZoom[z] ?? 0) + 1;
      comp += tileRecords[i].compLength;
      raw += tileRecords[i].rawLength;
    }
    return AbmStats(
      region: region,
      version: version,
      baseZoom: baseZoom,
      tileCount: tileCount,
      stringCount: stringCount,
      tilesPerZoom: perZoom,
      compressedBytes: comp,
      rawBytes: raw,
      buildTime: buildTime,
    );
  }
}

class _TileRecord {
  const _TileRecord(this.offset, this.compLength, this.rawLength, this.mask);
  final int offset;
  final int compLength;
  final int rawLength;
  final int mask;
}

class _ParsedIndex {
  const _ParsedIndex(this.ids, this.records);
  final List<int> ids;
  final List<_TileRecord> records;
}

class AbmStats {
  const AbmStats({
    required this.region,
    required this.version,
    required this.baseZoom,
    required this.tileCount,
    required this.stringCount,
    required this.tilesPerZoom,
    required this.compressedBytes,
    required this.rawBytes,
    required this.buildTime,
  });

  final String region;
  final int version;
  final int baseZoom;
  final int tileCount;
  final int stringCount;
  final Map<int, int> tilesPerZoom;
  final int compressedBytes;
  final int rawBytes;
  final DateTime buildTime;

  double get compressionRatio =>
      compressedBytes == 0 ? 0 : rawBytes / compressedBytes;
}

class AbmFormatException implements Exception {
  const AbmFormatException(this.message);
  final String message;
  @override
  String toString() => 'AbmFormatException: $message';
}
