from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .osm import roads, buildings, landuse, water, boundaries, places, pois

class Dataset:
    def __init__(self): self.nodes=[]; self.ways=[]; self.relations=[]


def load_jsonl(path: Path) -> Dataset:
    d = Dataset()
    for line in path.open(encoding="utf-8"):
        if not line.strip(): continue
        obj = json.loads(line); (d.nodes if obj.get("kind") == "node" else d.ways if obj.get("kind") == "way" else d.relations).append(obj)
    return d


def load(path: Path) -> Dataset:
    if path.suffix.lower() in {".jsonl", ".json"}: return load_jsonl(path)
    try:
        import osmium
    except ImportError as e:
        raise RuntimeError("PBF input requires osmium; install requirements.txt") from e
    d = Dataset()

    # pyosmium hands each callback a *view* into a buffer it reuses/frees as
    # soon as the callback returns - the Way/Node/Relation object (and its
    # .tags/.nodes) becomes an invalid "removed OSM object" the moment
    # apply_file moves on. Storing those live objects in d.nodes/d.ways/
    # d.relations for later use (as this used to do) meant every attribute
    # access after the file finished loading raised or silently produced
    # nothing meaningful - e.g. tags_dict()'s `tags.items()` doesn't exist on
    # pyosmium's TagList and got swallowed by its `except AttributeError`,
    # so every extracted feature came back with empty tags/geometry.
    # We copy out exactly the plain-dict shape the rest of the pipeline
    # already expects from the JSONL test fixtures (id/lat/lon/tags for
    # nodes, id/geometry/tags for ways, id/tags/members for relations)
    # while the object is still live, inside the callback.
    class Handler(osmium.SimpleHandler):
        def node(self, o):
            loc = o.location
            d.nodes.append({
                "id": o.id,
                "lat": loc.lat if loc.valid() else None,
                "lon": loc.lon if loc.valid() else None,
                "tags": dict(o.tags),
            })

        def way(self, o):
            d.ways.append({
                "id": o.id,
                "geometry": [(n.location.lon, n.location.lat) for n in o.nodes if n.location.valid()],
                "tags": dict(o.tags),
            })

        def relation(self, o):
            d.relations.append({
                "id": o.id,
                "tags": dict(o.tags),
                "members": [{"type": m.type, "ref": m.ref, "role": m.role} for m in o.members],
            })

    Handler().apply_file(str(path), locations=True)
    return d


def _point_in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float]) -> bool:
    minlon, minlat, maxlon, maxlat = bbox
    return minlon <= lon <= maxlon and minlat <= lat <= maxlat


def _obj_point(obj: Any) -> tuple[float, float] | None:
    if isinstance(obj, dict):
        lat, lon = obj.get("lat"), obj.get("lon")
    else:
        lat, lon = getattr(obj, "lat", None), getattr(obj, "lon", None)
    if lat is None or lon is None:
        return None
    return float(lon), float(lat)


def _obj_geometry_points(obj: Any) -> list[tuple[float, float]]:
    from abm_builder.core import way_geometry
    pt = _obj_point(obj)
    if pt is not None:
        return [pt]
    return way_geometry(obj)


def clip_dataset(dataset: Dataset, bbox: tuple[float, float, float, float]) -> Dataset:
    """Return a new Dataset containing only nodes/ways whose geometry falls (at
    least partly) inside ``bbox``, plus every relation that references a kept
    way. This is a real geographic split (used for large countries such as the
    US that are broken into named regions), unlike the byte-level chunking in
    packaging/split_abm.py which only exists to satisfy hosting file-size caps
    and knows nothing about geography.

    A way/node is kept if ANY of its points fall inside the bbox, so features
    that straddle a region boundary appear (harmlessly duplicated) in both
    neighboring regions rather than being cut in half.
    """
    clipped = Dataset()
    kept_way_ids: set[int] = set()
    for node in dataset.nodes:
        pt = _obj_point(node)
        if pt is not None and _point_in_bbox(pt[0], pt[1], bbox):
            clipped.nodes.append(node)
    for way in dataset.ways:
        points = _obj_geometry_points(way)
        if any(_point_in_bbox(lon, lat, bbox) for lon, lat in points):
            clipped.ways.append(way)
            from abm_builder.core import entity_id
            kept_way_ids.add(entity_id(way))
    for rel in dataset.relations:
        members = rel.get("members", []) if isinstance(rel, dict) else list(getattr(rel, "members", []))
        member_ids = set()
        for m in members:
            ref = m.get("ref") if isinstance(m, dict) else getattr(m, "ref", None)
            if ref is not None:
                member_ids.add(int(ref))
        if member_ids & kept_way_ids:
            clipped.relations.append(rel)
    return clipped


def extract_all(dataset: Dataset) -> dict[str, list[dict[str, Any]]]:
    return {
        "roads.bin": list(roads(dataset.ways)),
        "buildings.bin": list(buildings(dataset.ways)),
        "landuse.bin": list(landuse(dataset.ways)),
        "water.bin": list(water(dataset.ways)),
        "boundaries.bin": list(boundaries(dataset.ways, dataset.relations)),
        "places.bin": list(places(dataset.nodes, dataset.ways)),
        "poi": list(pois(dataset.nodes, dataset.ways)),
    }
