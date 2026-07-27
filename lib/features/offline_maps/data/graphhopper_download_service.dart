import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:resumable_downloader/resumable_downloader.dart';
import 'package:archive/archive_io.dart';
import 'iran_provinces.dart';

class GraphHopperDownloadService {
  static const String _graphHopperBaseUrl = 'https://download.abtin-nav.ir/routing/graphhopper'; // Placeholder URL

  Future<String> _getGraphHopperDir(String provinceId) async {
    final appDocDir = await getApplicationDocumentsDirectory();
    final graphDir = Directory('${appDocDir.path}/graphhopper_graphs/$provinceId');
    if (!await graphDir.exists()) {
      await graphDir.create(recursive: true);
    }
    return graphDir.path;
  }

  Future<void> downloadGraph(Province province, {Function(double)? onProgress}) async {
    final graphDir = await _getGraphHopperDir(province.id);
    final downloadUrl = '$_graphHopperBaseUrl/${province.id}.zip'; // Assuming GraphHopper graphs are zipped
    final filePath = '$graphDir/${province.id}.zip';

    final downloader = ResumableDownloader(
      url: downloadUrl,
      filePath: filePath,
      onProgress: (received, total) {
        if (total != -1) {
          onProgress?.call(received / total);
        }
      },
    );

    await downloader.download();

        // Extract the zip file
    final bytes = File(filePath).readAsBytesSync();
    final archive = ZipDecoder().decodeBytes(bytes);

    for (final file in archive) {
      final filename = file.name;
      if (file.isFile) {
        final data = file.content as List<int>;
        File("$graphDir/$filename")
          ..createSync(recursive: true)
          ..writeAsBytesSync(data);
      } else {
        Directory("$graphDir/$filename").create(recursive: true);
      }
    }
    // Delete the zip file after extraction
    File(filePath).deleteSync();
  }

  Future<void> pauseDownload(String provinceId) async {
    // ResumableDownloader handles pause/resume internally based on file existence
    // No explicit pause needed here, just stop current download if any.
  }

  Future<void> resumeDownload(String provinceId) async {
    // ResumableDownloader handles pause/resume internally based on file existence
    // Just call downloadGraph again.
  }

  Future<void> deleteGraph(String provinceId) async {
    final graphDir = await _getGraphHopperDir(provinceId);
    final dir = Directory(graphDir);
    if (await dir.exists()) {
      await dir.delete(recursive: true);
    }
  }

  Future<bool> isGraphDownloaded(String provinceId) async {
    final graphDir = await _getGraphHopperDir(provinceId);
    // This check needs to be more robust, e.g., check for specific GraphHopper files
    return await Directory(graphDir).exists();
  }

  // Placeholder for estimating size, will need actual data
  double estimateSizeMb(Province p) {
    // This is a placeholder. Actual size should come from a metadata service or hardcoded values.
    return 100.0; // Example: 100 MB per province
  }

  Future<Set<String>> listDownloadedGraphs() async {
    final appDocDir = await getApplicationDocumentsDirectory();
    final graphHopperRoot = Directory("${appDocDir.path}/graphhopper_graphs");
    if (!await graphHopperRoot.exists()) {
      return {};
    }
    final downloaded = <String>{};
    await for (final entity in graphHopperRoot.list()) {
      if (entity is Directory) {
        // Check if the directory contains actual graphhopper files (e.g., graph.gh)
        // For now, just checking directory existence as a proxy
        if (await File("${entity.path}/graph.gh").exists()) {
          downloaded.add(entity.path.split("/").last);
        }
      }
    }
    return downloaded;
  }
}
