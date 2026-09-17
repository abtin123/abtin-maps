from __future__ import annotations
from collections.abc import Iterable
from abm_builder.core import entity_id, tags_dict, way_geometry, prepare_geometry

ROAD_CLASSES = {"motorway", "trunk", "primary", "secondary", "tertiary", "residential", "service", "track"}
LANDUSE = {"forest", "farmland", "grass", "residential"}
POI_KEYS = {"hospital", "pharmacy", "fuel", "restaurant", "cafe", "bank", "school", "university", "police", "parking", "toilets", "supermarket", "mall", "convenience", "hotel", "attraction", "airport", "railway_station", "bus_station"}

# Simplification tolerance per layer, in meters. Chosen well below anything
# visible on a phone screen at the zoom each layer is actually shown at
# (see _featureAllowedAtZoom / the buildings zoom<13 gate in the app):
#   - roads/water/boundaries are shown zoomed out a lot, so a few meters of
#     wobble on a bend is invisible but the point-count savings are large.
#   - buildings only ever render at zoom>=13 (close-up), so their tolerance
#     is kept tight to avoid visibly squaring off small structures.
# Routing correctness is unaffected either way: the routing graph is built
# separately from the source PBF (build_graph_from_pbf), never from these
# rendering-only geometries.
_TOLERANCE_M = {
    "roads": 3.0,
    "buildings": 1.0,
    "landuse": 6.0,
    "water": 4.0,
    "boundaries": 8.0,
}


def _record(obj, kind, geom_points, *, layer: str, tags: dict[str, str]):
    geom = prepare_geometry(geom_points, tolerance_m=_TOLERANCE_M.get(layer, 0.0))
    # Drop empty/falsy values so a two-way road with no name doesn't carry
    # `"oneway":"no","bridge":"no","tunnel":"no"` (and friends) on every one
    # of a country's millions of road features - the app already treats a
    # missing tag as the same default those literal "no"s spelled out.
    clean_tags = {k: v for k, v in tags.items() if v not in ("", None)}
    # `kind`/`type` ("Road", "Building", ...) is never read by the app - it
    # infers layer from which vector/<layer>/*.bin file a chunk came from -
    # so it is not written to disk at all.
    del kind
    return {"id": entity_id(obj), "geometry": geom, "tags": clean_tags}


def roads(ways: Iterable):
    for w in ways:
        t = tags_dict(w); highway = t.get("highway", "")
        if highway in ROAD_CLASSES:
            oneway = t.get("oneway", "")
            bridge = t.get("bridge", "")
            tunnel = t.get("tunnel", "")
            yield _record(w, "Road", way_geometry(w), layer="roads", tags={
                "highway": highway,
                "name": t.get("name", ""), "name_fa": t.get("name:fa", ""), "name_en": t.get("name:en", ""),
                "oneway": oneway if oneway != "no" else "",
                "bridge": bridge if bridge != "no" else "",
                "tunnel": tunnel if tunnel != "no" else "",
                "maxspeed": t.get("maxspeed", ""), "access": t.get("access", ""),
            })


def buildings(ways: Iterable):
    for w in ways:
        t = tags_dict(w)
        if "building" in t:
            yield _record(w, "Building", way_geometry(w), layer="buildings", tags={
                "building": t.get("building", "yes"),
            })


def landuse(ways: Iterable):
    for w in ways:
        t = tags_dict(w)
        if t.get("landuse") in LANDUSE:
            yield _record(w, "Landuse", way_geometry(w), layer="landuse", tags={"landuse": t["landuse"]})


def water(ways: Iterable):
    for w in ways:
        t = tags_dict(w)
        natural, waterway = t.get("natural", ""), t.get("waterway", "")
        if natural in {"water", "coastline"} or waterway in {"river", "stream", "canal"}:
            # Keep the two source keys distinct (not collapsed into one
            # "water_type") - the app tells a water polygon (lake/sea) from a
            # waterway line (river/stream) by whether `waterway` is present.
            yield _record(w, "Water", way_geometry(w), layer="water", tags={
                "natural": natural, "waterway": waterway,
            })


def boundaries(ways: Iterable, relations: Iterable = ()):
    for obj in list(ways) + list(relations):
        t = tags_dict(obj)
        if t.get("boundary") == "administrative":
            yield _record(obj, "Boundary", way_geometry(obj), layer="boundaries", tags={
                "admin_level": t.get("admin_level", ""), "name": t.get("name", ""),
            })


def places(nodes: Iterable, ways: Iterable = ()):
    for obj in list(nodes) + list(ways):
        t = tags_dict(obj)
        if t.get("place") in {"city", "town", "village", "neighbourhood", "suburb", "hamlet"}:
            geom = way_geometry(obj) if hasattr(obj, "nodes") or isinstance(obj, dict) and obj.get("geometry") else []
            if not geom:
                lat, lon = getattr(obj, "lat", None), getattr(obj, "lon", None)
                if isinstance(obj, dict): lat, lon = obj.get("lat", lat), obj.get("lon", lon)
                geom = [(float(lon), float(lat))] if lat is not None and lon is not None else []
            yield _record(obj, "Place", geom, layer="places", tags={
                "place": t["place"], "name": t.get("name", ""),
                "name_fa": t.get("name:fa", ""), "name_en": t.get("name:en", ""),
            })


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
