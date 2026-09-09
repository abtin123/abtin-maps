import 'dart:io';
import 'dart:math' as math
import '../../../core/geo/geo_types.dart';
import '../../../abtinmap/abm_map_service.dart';
import '../../../map_engine/abm_reader.dart';
import '../../../map_engine/cache_manager.dart';
import '../../../routing/routing_engine.dart' as engine;
import 'routing_provider.dart';
import 'routing_service.dart';

class AbtinmapRoutingProvider implements RoutingProvider {
  AbtinmapRoutingProvider({required AbmMapService mapService,this.mapName='IR.abm',this.languageCode=_defaultLanguageCode}):_mapService=mapService;
  final AbmMapService _mapService; final String mapName; final String Function() languageCode; static String _defaultLanguageCode()=> 'fa';
  engine.AbmRoutingEngine? _router; String? _lastError;
  @override RoutingEngine get engine => RoutingEngine.abtinmap;
  @override String get displayName=>'آبتین‌مپ (آفلاین)';
  @override bool get isOffline=>true;
  @override String? get lastError=>_lastError;
  Future<File?> _graph() async { final f=await _mapService.localFile(mapName); if(!await f.exists())return null; try{return (await AbmReader.open(f,await MapCacheManager().country(mapName.replaceAll('.abm','')))).routingGraph;}catch(_){return null;} }
  @override Future<bool> isReady() async => (await _graph())!=null;
  @override Future<RouteInfo?> calculateRoute({required LatLng origin,required LatLng destination,bool offlineOnly=false,bool avoidUnpavedRoads=false,bool avoidTolls=false}) async { _lastError=null; final g=await _graph(); if(g==null){_lastError='نقشهٔ آفلاین ABM آماده نیست.';return null;} _router??=engine.AbmRoutingEngine(); try{final points=await _router!.route(g,engine.RoutePoint(origin.latitude,origin.longitude),engine.RoutePoint(destination.latitude,destination.longitude)); if(points.isEmpty){_lastError='مسیری روی نقشهٔ آفلاین پیدا نشد.';return null;} return RouteInfo(geometry:[for(final p in points)LatLng(p.lat,p.lon)],distanceKm:_distanceKm(points),durationMin:0,instructions:const [],alerts:const []);}catch(e){_lastError='خطای مسیریابی آفلاین: $e';return null;} }
  Future<List<RouteInfo>> calculateRoutes({required LatLng origin,required LatLng destination,bool offlineOnly=false,bool avoidUnpavedRoads=false,bool avoidTolls=false}) async {final r=await calculateRoute(origin:origin,destination:destination,offlineOnly:offlineOnly,avoidUnpavedRoads:avoidUnpavedRoads,avoidTolls:avoidTolls);return r==null?const[]:[r];}
  double _distanceKm(List<engine.RoutePoint> p){double m=0;for(var i=1;i<p.length;i++){final dx=(p[i].lat-p[i-1].lat)*111000,dy=(p[i].lon-p[i-1].lon)*111000;m += math.sqrt(dx*dx + dy*dy);}return m/1000;}
}
