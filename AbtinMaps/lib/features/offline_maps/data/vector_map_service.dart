import 'dart:io';
import 'dart:convert';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import '../../../map_engine/abm_reader.dart';

class VectorMapInstallException implements Exception { const VectorMapInstallException(this.message); final String message; @override String toString()=>message; }
class VectorMapService {
  Future<Directory> cacheDirectory(String id) async { final base=await getApplicationSupportDirectory(); final d=Directory(p.join(base.path,'AbtinMaps','cache',id.toUpperCase())); if(!await d.exists()) await d.create(recursive:true); return d; }
  Future<bool> isInstalled({required File containerFile}) async { try { final r=await AbmReader.open(containerFile,await cacheDirectory(p.basenameWithoutExtension(containerFile.path))); return await r.routingGraph.exists() && await r.searchDatabase.exists(); } catch(_){return false;} }
  Future<void> delete(String id) async { final d=await cacheDirectory(id); if(await d.exists()) await d.delete(recursive:true); }
  Future<void> prepare({required File containerFile,required String id,void Function(double)? onProgress}) async {
    final dir=await cacheDirectory(id); onProgress?.call(.05);
    final r=await AbmReader.open(containerFile,dir); onProgress?.call(.35);
    for(final f in [r.searchDatabase,r.poiDatabase,r.routingGraph]) if(!await f.exists()) throw const VectorMapInstallException('ABM کامل نیست: search/poi/routing داده نشده است.');
    // search.sqlite already contains FTS5 + RTree; no secondary tile index is created.
    await File(p.join(dir.path,'search.ready')).writeAsString('FTS5+RTree'); onProgress?.call(.55);
    await File(p.join(dir.path,'spatial.ready')).writeAsString('RTree'); onProgress?.call(.7);
    await File(p.join(dir.path,'routing.ready')).writeAsString('ABMGRAPH1'); onProgress?.call(.8);
    final features=await r.readAllFeatures();
    await File(p.join(dir.path,'render_cache.json')).writeAsString(jsonEncode({'version':1,'feature_count':features.length,'layers':['roads','buildings','landuse','water','boundaries','places']}),flush:true);
    await File(p.join(dir.path,'render.ready')).writeAsString('offline-vector'); onProgress?.call(1);
  }
}
