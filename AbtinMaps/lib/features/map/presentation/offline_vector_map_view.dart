import 'dart:async';
import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:abtin_maps/core/geo/geo_types.dart';
import 'package:abtin_maps/map_engine/abm_reader.dart';
import 'package:abtin_maps/map_engine/cache_manager.dart';
import 'package:abtin_maps/map_engine/vector_renderer.dart';
import 'package:abtin_maps/styles/style_manager.dart';
import '../../../abtinmap/abm_map_service.dart';
import '../../gps/data/location_service.dart';
import '../../vehicle/presentation/car_marker.dart';
import '../../vehicle/presentation/nav_arrow_painter.dart';
import '../../../shared/providers/map_style_providers.dart';
import '../../../world/world_renderer.dart';

class OfflineVectorMapView extends StatefulWidget {
  const OfflineVectorMapView({super.key, required this.mapFile, required this.country, required this.vehiclePosition, required this.showCarModel, required this.modelIndex, required this.isDark, required this.followVehicle, required this.cameraTiltDegrees, required this.markerColor, required this.pinSizePercent, required this.carSizePercent, required this.pinShadowEnabled, required this.carCameraAngleDegrees, required this.routeGeometry, required this.routeColor, required this.routeWidth, this.onLongPress, this.onUserGestureStart, this.onCameraPositionChanged, this.onCameraIdle});
  final File mapFile; final String country; final VehiclePosition? vehiclePosition; final bool showCarModel; final int modelIndex; final bool isDark, followVehicle; final double cameraTiltDegrees; final Color markerColor; final double pinSizePercent, carSizePercent; final bool pinShadowEnabled; final double carCameraAngleDegrees; final List<LatLng>? routeGeometry; final Color routeColor; final double routeWidth;
  final ValueChanged<LatLng>? onLongPress; final VoidCallback? onUserGestureStart; final VoidCallback? onCameraIdle; final ValueChanged<dynamic>? onCameraPositionChanged;
  @override State<OfflineVectorMapView> createState() => _OfflineVectorMapViewState();
}

class _OfflineVectorMapViewState extends State<OfflineVectorMapView> {
  AbmReader? reader; MapStyle? style; List<AbmFeature> features = const []; double zoom = 5.0; Offset center = const Offset(54, 32.5); Offset? _gestureStart; double _gestureZoom = 5;
  @override void initState(){super.initState(); _load();}
  Future<void> _load() async { final r=await AbmReader.open(widget.mapFile, await MapCacheManager().country(widget.country)); final s=await StyleManager.load(name: widget.isDark?'night':'default',dark:widget.isDark); final f=await r.readAllFeatures(); if(mounted)setState((){reader=r;style=s;features=f;}); }
  @override void didUpdateWidget(covariant OfflineVectorMapView old){super.didUpdateWidget(old); if(old.isDark!=widget.isDark) _load(); if(widget.followVehicle && widget.vehiclePosition!=null){ center=Offset(widget.vehiclePosition!.lng,widget.vehiclePosition!.lat); }}
  Offset _project(LatLng p, Size size){final scale=math.pow(2,zoom).toDouble()*0.45; return Offset(size.width/2+(p.longitude-center.dx)*scale,size.height/2-(p.latitude-center.dy)*scale);}
  @override Widget build(BuildContext context){ final r=reader,s=style; if(r==null||s==null)return const ColoredBox(color:Color(0xFFEEF0F2),child:Center(child:CircularProgressIndicator())); final vp=widget.vehiclePosition; final marker=vp==null?null:_project(LatLng(vp.lat,vp.lng),MediaQuery.sizeOf(context)); return GestureDetector(onScaleStart:(d){_gestureStart=d.focalPoint;_gestureZoom=zoom;widget.onUserGestureStart?.call();},onScaleUpdate:(d){setState((){zoom=(_gestureZoom+math.log(d.scale)/math.ln2).clamp(2,18);});},onScaleEnd:(_){widget.onCameraIdle?.call();},onLongPress:(){},child:Stack(children:[Positioned.fill(child: zoom <= 4.25
                  ? WorldRenderer(center:center, zoom:zoom, isDark:widget.isDark)
                  : Transform(alignment:Alignment.center,transform:Matrix4.identity()..setEntry(3,2,0.001)..rotateX(-widget.cameraTiltDegrees*math.pi/180*0.55),child:VectorMapRenderer(features:features,style:s,center:center,zoom:zoom,route:[for(final p in widget.routeGeometry??const[]) [p.longitude,p.latitude]]))),if(marker!=null)Positioned(left:marker.dx-32,top:marker.dy-32,width:64,height:64,child:widget.showCarModel?CarMarker3D(size:64,modelIndex:widget.modelIndex,headingDeg:vp.headingDeg,cameraAngleDegrees:widget.carCameraAngleDegrees,sizePercent:widget.carSizePercent):CustomPaint(painter:NavArrowPainter(baseColor:widget.markerColor,glow:widget.pinShadowEnabled))),])); }
}
