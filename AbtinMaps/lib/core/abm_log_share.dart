import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

class AbmLogShare {
  static Future<void> send(String log) async {
    final dir = await getTemporaryDirectory();
    final file = File('${dir.path}/abm_debug_log.txt');
    await file.writeAsString(log);
    await Share.shareXFiles(
      [XFile(file.path)],
      text: 'ABTINMAP ABM Debug Log',
    );
  }
}
