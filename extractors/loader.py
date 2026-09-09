from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .osm import roads, buildings, landuse, water, boundaries, places, pois


class Dataset:
    def __init__(self):
        self.nodes = []
        self.ways = []
        self.relations = []


def load_jsonl(path: Path) -> Dataset:
    d = Dataset()
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("kind") == "node":
                d.nodes.append(obj)
            elif obj.get("kind") == "way":
                d.ways.append(obj)
            else:
                d.relations.append(obj)
    return d


def _point_in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float]) -> bool:
    minlon, minlat, maxlon, maxlat = bbox
    return minlon <= lon <= maxlon and minlat <= lat <= maxlat


def _geometry_in_bbox(geometry, bbox) -> bool:
    return any(_point_in_bbox(float(lon), float(lat), bbox) for lon, lat in geometry)


def load(path: Path, bbox: tuple[float, float, float, float] | None = None) -> Dataset:
    """Load JSONL or PBF into plain Python objects.

    For PBF regional builds, ``bbox`` is applied while the file is streamed.
    This is important for large extracts such as the US: the old pipeline first
    materialized the entire tagged PBF in RAM and only then clipped it.
    """
    if path.suffix.lower() in {".jsonl", ".json"}:
        d = load_jsonl(path)
        return clip_dataset(d, bbox) if bbox is not None else d

    try:
        import osmium
    except ImportError as e:
        raise RuntimeError("PBF input requires osmium; install requirements.txt") from e

    d = Dataset()

    class Handler(osmium.SimpleHandler):
        def node(self, o):
            if not o.tags:
                return
            loc = o.location
            if not loc.valid():
                return
            lat, lon = float(loc.lat), float(loc.lon)
            if bbox is not None and not _point_in_bbox(lon, lat, bbox):
                return
            d.nodes.append({
                "id": int(o.id),
                "lat": lat,
                "lon": lon,
                "tags": dict(o.tags),
            })

        def way(self, o):
            if not o.tags:
                return
            geometry = [
                (float(n.location.lon), float(n.location.lat))
                for n in o.nodes
                if n.location.valid()
            ]
            if bbox is not None and not _geometry_in_bbox(geometry, bbox):
                return
            d.ways.append({
                "id": int(o.id),
                "geometry": geometry,
                "tags": dict(o.tags),
            })

        def relation(self, o):
            if not o.tags:
                return
            # Relations are cheap compared with ways, but for regional builds
            # retain only relations that reference a kept way.  This avoids
            # carrying thousands of unrelated relations into every region.
            members = [{"type": m.type, "ref": int(m.ref), "role": m.role} for m in o.members]
            if bbox is None:
                d.relations.append({"id": int(o.id), "tags": dict(o.tags), "members": members})
            else:
                # We cannot know yet whether a member way will be kept, so
                # store the relation temporarily and filter it below.
                d.relations.append({"id": int(o.id), "tags": dict(o.tags), "members": members})

    Handler().apply_file(str(path), locations=True)

    if bbox is not None:
        kept_way_ids = {int(w["id"]) for w in d.ways}
        d.relations = [
            r for r in d.relations
            if any(int(m.get("ref", -1)) in kept_way_ids for m in r.get("members", []))
        ]
    return d


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
    """Geographically clip a Dataset without altering feature geometry.

    Features crossing a boundary are retained in both neighboring regions;
    this is intentional so roads/water/boundaries do not disappear at edges.
    """
    clipped = Dataset()
    kept_way_ids: set[int] = set()

    for node in dataset.nodes:
        pt = _obj_point(node)
        if pt is not None and _point_in_bbox(pt[0], pt[1], bbox):
            clipped.nodes.append(node)

    for way in dataset.ways:
        points = _obj_geometry_points(way)
        if _geometry_in_bbox(points, bbox):
            clipped.ways.append(way)
            from abm_builder.core import entity_id
            kept_way_ids.add(entity_id(way))

    for rel in dataset.relations:
        members = rel.get("members", []) if isinstance(rel, dict) else list(getattr(rel, "members", []))
        if any(
            (int(m.get("ref")) if isinstance(m, dict) and m.get("ref") is not None
             else getattr(m, "ref", None)) in kept_way_ids
            for m in members
        ):
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
