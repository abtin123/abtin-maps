import 'dart:io';
import 'dart:math' as math;
import 'package:sqlite3/sqlite3.dart';
import '../../../core/geo/geo_types.dart';
import '../../../abtinmap/abm_map_service.dart';
import '../../../map_engine/abm_reader.dart';
import '../../../map_engine/cache_manager.dart';
import 'place_search_service.dart';
class OfflinePlaceSearchService { OfflinePlaceSearchService(this._maps); final AbmMapService _maps; String? _openedMap,_dbPath;
 Future<List<PlaceSearchResult>> search(String query,{required String mapFileName,double? biasLat,double? biasLng,String? city,int limit=12}) async {if(query.trim().length<2)return const[];final path=await _ensureIndex(mapFileName);if(path==null)return const[];final db=sqlite3.open(path,mode:OpenMode.readOnly);try{final q=query.trim().replaceAll('"',' ').split(RegExp(r'\s+')).where((x)=>x.isNotEmpty).map((x)=>'"${x.replaceAll('"','""')}"*').join(' AND ');final rows=db.select('SELECT p.name,p.category,p.lat,p.lon FROM search_fts f JOIN places p ON p.id=f.rowid WHERE search_fts MATCH ? LIMIT ?',[q,math.max(limit*4,40)]);final o=biasLat!=null&&biasLng!=null?LatLng(biasLat,biasLng):null;final out=<PlaceSearchResult>[];for(final r in rows){final point=LatLng((r['lat'] as num).toDouble(),(r['lon'] as num).toDouble());out.add(PlaceSearchResult(name:'${r['name']??''}',region:'${r['category']??''}',point:point,isOffline:true,distanceMeters:o==null?null:_d(o,point)));}out.sort((a,b)=>(a.distanceMeters??double.infinity).compareTo(b.distanceMeters??double.infinity));return out.take(limit).toList(growable:false);}finally{db.dispose();}}
 Future<String?> _ensureIndex(String name) async {if(_openedMap==name&&_dbPath!=null&&await File(_dbPath!).exists())return _dbPath;final f=await _maps.localFile(name);try{final r=await AbmReader.open(f,await MapCacheManager().country(name.replaceAll('.abm','')));if(!await r.searchDatabase.exists())return null;_openedMap=name;_dbPath=r.searchDatabase.path;return _dbPath;}catch(_){return null;}}
 double _d(LatLng a,LatLng b){const R=6371000.0;final p1=a.latitude*math.pi/180,p2=b.latitude*math.pi/180,dp=(b.latitude-a.latitude)*math.pi/180,dl=(b.longitude-a.longitude)*math.pi/180;final h=math.sin(dp/2)*math.sin(dp/2)+math.cos(p1)*math.cos(p2)*math.sin(dl/2)*math.sin(dl/2);return 2*R*math.atan2(math.sqrt(h),math.sqrt(1-h));}}
