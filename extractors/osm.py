from __future__ import annotations
from collections.abc import Iterable
from abm_builder.core import entity_id, tags_dict, way_geometry

ROAD_CLASSES = {"motorway", "trunk", "primary", "secondary", "tertiary", "residential", "service", "track"}
LANDUSE = {"forest", "farmland", "grass", "residential"}
POI_KEYS = {"hospital", "pharmacy", "fuel", "restaurant", "cafe", "bank", "school", "university", "police", "parking", "toilets", "supermarket", "mall", "convenience", "hotel", "attraction", "airport", "railway_station", "bus_station"}


def _record(obj, kind, geom=None, **extra):
    return {"id": entity_id(obj), "type": kind, "geometry": geom or [], "tags": tags_dict(obj), **extra}


def roads(ways: Iterable):
    for w in ways:
        t = tags_dict(w); highway = t.get("highway", "")
        if highway in ROAD_CLASSES:
            yield _record(w, "Road", way_geometry(w), road_class=highway,
                          name=t.get("name", ""), name_fa=t.get("name:fa", ""), name_en=t.get("name:en", ""),
                          oneway=t.get("oneway", "no"), bridge=t.get("bridge", "no"), tunnel=t.get("tunnel", "no"),
                          maxspeed=t.get("maxspeed", ""), access=t.get("access", ""))


def buildings(ways: Iterable):
    for w in ways:
        t = tags_dict(w)
        if "building" in t:
            yield _record(w, "Building", way_geometry(w), building_type=t.get("building", "yes"), levels=t.get("building:levels", ""))


def landuse(ways: Iterable):
    for w in ways:
        t = tags_dict(w)
        if t.get("landuse") in LANDUSE:
            yield _record(w, "Landuse", way_geometry(w), landuse=t["landuse"])


def water(ways: Iterable):
    for w in ways:
        t = tags_dict(w)
        if t.get("natural") in {"water", "coastline"} or t.get("waterway") in {"river", "stream", "canal"}:
            yield _record(w, "Water", way_geometry(w), water_type=t.get("natural", t.get("waterway", "water")))


def boundaries(ways: Iterable, relations: Iterable = ()):
    for obj in list(ways) + list(relations):
        t = tags_dict(obj)
        if t.get("boundary") == "administrative":
            yield _record(obj, "Boundary", way_geometry(obj), admin_level=t.get("admin_level", ""), name=t.get("name", ""))


def places(nodes: Iterable, ways: Iterable = ()):
    for obj in list(nodes) + list(ways):
        t = tags_dict(obj)
        if t.get("place") in {"city", "town", "village", "neighbourhood", "suburb", "hamlet"}:
            geom = way_geometry(obj) if hasattr(obj, "nodes") or isinstance(obj, dict) and obj.get("geometry") else []
            if not geom:
                lat, lon = getattr(obj, "lat", None), getattr(obj, "lon", None)
                if isinstance(obj, dict): lat, lon = obj.get("lat", lat), obj.get("lon", lon)
                geom = [(float(lon), float(lat))] if lat is not None and lon is not None else []
            yield _record(obj, "Place", geom, place_type=t["place"], name=t.get("name", ""), name_fa=t.get("name:fa", ""), name_en=t.get("name:en", ""))


def pois(nodes: Iterable, ways: Iterable = ()):
    for obj in list(nodes) + list(ways):
        t = tags_dict(obj); value = ""
        for key in ("amenity", "shop", "tourism", "aeroway", "railway", "public_transport"):
            if t.get(key) in POI_KEYS: value = t[key]; break
        if not value: continue
        lat, lon = getattr(obj, "lat", None), getattr(obj, "lon", None)
        if isinstance(obj, dict): lat, lon = obj.get("lat", lat), obj.get("lon", lon)
        if lat is None or lon is None:
            geom = way_geometry(obj)
            if not geom: continue
            lon, lat = sum(x for x, _ in geom) / len(geom), sum(y for _, y in geom) / len(geom)
        yield {"id": entity_id(obj), "name": t.get("name", ""), "name_fa": t.get("name:fa", ""), "name_en": t.get("name:en", ""), "category": value, "latitude": float(lat), "longitude": float(lon), "opening_hours": t.get("opening_hours", "")}
