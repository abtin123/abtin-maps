from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import struct
import tempfile
from pathlib import Path
from typing import Iterable

from abm_builder.core import tags_dict, way_geometry, entity_id, haversine_m, name_triple

PIECE = 8  # segments per road_index (snap) entry
MINOR_ROAD_CLASSES = {"service", "track"}  # driveways/parking aisles/farm tracks -
# highest edge-count, lowest routing value; excluded by default to fit the
# app's ~600 MB per-country size budget. Add back into ROAD_CLASSES below to
# restore door-to-door routing into parking lots and off-road tracks.
ROAD_CLASSES = {
    "motorway", "motorway_link", "trunk", "trunk_link",
    "primary", "primary_link", "secondary", "secondary_link",
    "tertiary", "tertiary_link", "unclassified", "residential",
    "living_street", "road",
}
DEFAULT_SPEED = {
    "motorway": 110, "motorway_link": 70, "trunk": 90, "trunk_link": 65,
    "primary": 70, "primary_link": 55, "secondary": 60, "secondary_link": 50,
    "tertiary": 50, "tertiary_link": 40, "unclassified": 40,
    "residential": 30, "living_street": 20, "service": 20, "track": 15, "road": 40,
}


def _speed(tags: dict[str, str]) -> float:
    raw = str(tags.get("maxspeed", ""))
    num = ""
    for ch in raw:
        if ch.isdigit() or ch == ".":
            num += ch
        elif num:
            break
    try:
        value = float(num) if num else float(DEFAULT_SPEED[tags["highway"]])
    except (ValueError, KeyError):
        value = float(DEFAULT_SPEED.get(tags.get("highway", ""), 30))
    if "mph" in raw.lower():
        value *= 1.609344
    return value


def _is_oneway(tags: dict[str, str]) -> bool:
    return str(tags.get("oneway", "")).lower() in {"yes", "1", "true"}


def _restriction_rows(relations: Iterable) -> list[tuple[int, str, list[int], list[int], list[int]]]:
    rows = []
    for rel in relations:
        t = tags_dict(rel)
        kind = t.get("restriction", "")
        if t.get("type") != "restriction" and not kind.startswith(("only_", "no_")):
            continue
        members = rel.get("members", []) if isinstance(rel, dict) else list(getattr(rel, "members", []))
        role_refs = {"from": [], "via": [], "to": []}
        for m in members:
            role = m.get("role", "") if isinstance(m, dict) else getattr(m, "role", "")
            ref = m.get("ref") if isinstance(m, dict) else getattr(m, "ref", None)
            if role in role_refs and ref is not None:
                try:
                    role_refs[role].append(int(ref))
                except (TypeError, ValueError):
                    pass
        rows.append((entity_id(rel), kind, role_refs["from"], role_refs["via"], role_refs["to"]))
    return rows


def _open_store() -> tuple[sqlite3.Connection, Path]:
    fd, name = tempfile.mkstemp(prefix="abm-routing-", suffix=".sqlite3")
    os.close(fd)
    path = Path(name)
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    con.execute("PRAGMA temp_store=FILE")
    # Staging only; map.sqlite gets the normalized form (see merge_graph).
    con.executescript("""
        CREATE TABLE node_data(id INTEGER PRIMARY KEY, lat_e7 INTEGER NOT NULL, lon_e7 INTEGER NOT NULL);
        CREATE TABLE way_data(way_id INTEGER PRIMARY KEY, class TEXT NOT NULL,
            name TEXT NOT NULL, name_fa TEXT NOT NULL, name_en TEXT NOT NULL,
            access TEXT NOT NULL, junction TEXT NOT NULL, surface TEXT NOT NULL,
            speed_kmh INTEGER NOT NULL, oneway INTEGER NOT NULL);
        CREATE TABLE segments(id INTEGER PRIMARY KEY, a INTEGER NOT NULL, b INTEGER NOT NULL,
            dist_dm INTEGER NOT NULL, way_id INTEGER NOT NULL);
        CREATE VIRTUAL TABLE road_index USING rtree(id, min_lon, max_lon, min_lat, max_lat,
            +seg_from INTEGER, +seg_to INTEGER);
        CREATE TABLE turn_restrictions(id INTEGER PRIMARY KEY, restriction TEXT NOT NULL,
            from_json TEXT NOT NULL, via_json TEXT NOT NULL, to_json TEXT NOT NULL);
    """)
    con.commit()
    return con, path


def _node_ids(way, geom: list[tuple[float, float]]) -> list[int]:
    raw = list(getattr(way, "nodes", []) or [])
    if isinstance(way, dict):
        raw = list(way.get("node_ids", raw) or [])
    ids = []
    for n in raw:
        if isinstance(n, int):
            ids.append(n)
        elif isinstance(n, dict) and n.get("ref") is not None:
            ids.append(int(n["ref"]))
        elif getattr(n, "ref", None) is not None:
            ids.append(int(n.ref))
    if len(ids) == len(geom):
        return ids
    # Stable fallback for JSON fixtures that have geometry but no node refs.
    result = []
    for lon, lat in geom:
        digest = hashlib.blake2b(f"{lon:.7f},{lat:.7f}".encode(), digest_size=8).digest()
        result.append(int.from_bytes(digest, "big") & ((1 << 63) - 1))
    return result


def _add_way(con: sqlite3.Connection, way, next_edge: int) -> tuple[int, int]:
    tags = tags_dict(way)
    highway = tags.get("highway")
    if highway not in ROAD_CLASSES:
        return next_edge, 0
    geom = way_geometry(way)
    if len(geom) < 2:
        return next_edge, 0
    ids = _node_ids(way, geom)
    ow = str(tags.get("oneway", "")).lower()
    reverse = ow == "-1"
    oneway = int(ow in {"yes", "1", "true", "-1"})
    # ONE row per segment: a two-way road is not mirrored into a second row
    # (the `edges` view derives the reverse direction), and speed/oneway/name
    # live once per way in way_data instead of on every segment.
    segs = []
    for i, (a, b) in enumerate(zip(ids, ids[1:])):
        if a == b:
            continue
        (lon1, lat1), (lon2, lat2) = geom[i], geom[i + 1]
        dist_dm = int(round(haversine_m((lat1, lon1), (lat2, lon2)) * 10))
        segs.append((b, a, dist_dm, i) if reverse else (a, b, dist_dm, i))
    if not segs:
        return next_edge, 0
    way_id = entity_id(way)
    n, fa, en = name_triple(tags.get("name"), tags.get("name:fa"), tags.get("name:en"))
    cur = con.execute(
        "INSERT OR IGNORE INTO way_data VALUES (?,?,?,?,?,?,?,?,?,?)",
        (way_id, highway, n, fa, en, tags.get("access", ""), tags.get("junction", ""),
         tags.get("surface", ""), int(round(_speed(tags))), oneway))
    if cur.rowcount == 0:  # this way was already added: never insert it twice
        return next_edge, 0
    con.executemany(
        "INSERT OR IGNORE INTO node_data VALUES (?,?,?)",
        [(int(nid), int(round(lat * 1e7)), int(round(lon * 1e7))) for nid, (lon, lat) in zip(ids, geom)])
    con.executemany("INSERT INTO segments VALUES (?,?,?,?,?)",
                    [(next_edge + j, a, b, d, way_id) for j, (a, b, d, _) in enumerate(segs)])
    pieces = []
    for st in range(0, len(segs), PIECE):
        chunk = segs[st:st + PIECE]
        pts = [geom[i] for *_, i in chunk] + [geom[chunk[-1][3] + 1]]
        pts += [geom[i + 1] for *_, i in chunk]
        pieces.append((next_edge + st, min(p[0] for p in pts), max(p[0] for p in pts),
                       min(p[1] for p in pts), max(p[1] for p in pts),
                       next_edge + st, next_edge + st + len(chunk) - 1))
    con.executemany("INSERT INTO road_index VALUES (?,?,?,?,?,?,?)", pieces)
    return next_edge + len(segs), len(segs)


def _write_graph(con: sqlite3.Connection, restrictions: list[tuple[int, str, list[int], list[int], list[int]]], out: Path) -> None:
    """Persist the staging graph as a standalone SQLite file for merge_graph()."""
    out.parent.mkdir(parents=True, exist_ok=True)
    con.executemany(
        "INSERT OR IGNORE INTO turn_restrictions VALUES (?,?,?,?,?)",
        [(rid, kind, json.dumps(fr), json.dumps(vi), json.dumps(to)) for rid, kind, fr, vi, to in restrictions],
    )
    con.commit()
    if out.exists():
        out.unlink()
    dst = sqlite3.connect(out)
    try:
        con.backup(dst)
        dst.commit()
    finally:
        dst.close()


def merge_graph(map_db: Path, graph_db: Path) -> None:
    """Fold the staged routing graph into map.sqlite in normalized form:
    names/categories are shared with search (no repeated strings), per-way data
    is stored once, coordinates are int e7, and road_index replaces the huge
    per-node rtree for snapping."""
    con = sqlite3.connect(map_db)
    try:
        con.execute("ATTACH DATABASE ? AS g", (str(graph_db),))
        con.executescript("""
            INSERT OR IGNORE INTO categories(name) SELECT DISTINCT class FROM g.way_data;
            INSERT OR IGNORE INTO nm(name, name_fa, name_en)
                SELECT DISTINCT name, name_fa, name_en FROM g.way_data
                WHERE name <> '' OR name_fa <> '' OR name_en <> '';
            CREATE TABLE node_data(id INTEGER PRIMARY KEY, lat_e7 INTEGER NOT NULL, lon_e7 INTEGER NOT NULL);
            CREATE TABLE way_data(way_id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL, name_id INTEGER,
                access TEXT, junction TEXT, surface TEXT, speed_kmh INTEGER NOT NULL, oneway INTEGER NOT NULL);
            CREATE TABLE segments(id INTEGER PRIMARY KEY, a INTEGER NOT NULL, b INTEGER NOT NULL,
                dist_dm INTEGER NOT NULL, way_id INTEGER NOT NULL);
            CREATE VIRTUAL TABLE road_index USING rtree(id, min_lon, max_lon, min_lat, max_lat,
                +seg_from INTEGER, +seg_to INTEGER);
            CREATE TABLE turn_restrictions(id INTEGER PRIMARY KEY, restriction TEXT NOT NULL,
                from_json TEXT NOT NULL, via_json TEXT NOT NULL, to_json TEXT NOT NULL);
            INSERT INTO node_data SELECT id, lat_e7, lon_e7 FROM g.node_data ORDER BY id;
            INSERT INTO way_data
                SELECT w.way_id, c.id, n.id, NULLIF(w.access,''), NULLIF(w.junction,''),
                       NULLIF(w.surface,''), w.speed_kmh, w.oneway
                FROM g.way_data w JOIN categories c ON c.name = w.class
                LEFT JOIN nm n ON n.name = w.name AND n.name_fa = w.name_fa AND n.name_en = w.name_en
                ORDER BY w.way_id;
            INSERT INTO segments SELECT id, a, b, dist_dm, way_id FROM g.segments ORDER BY id;
            INSERT INTO road_index(id, min_lon, max_lon, min_lat, max_lat, seg_from, seg_to)
                SELECT id, min_lon, max_lon, min_lat, max_lat, seg_from, seg_to FROM g.road_index ORDER BY id;
            INSERT INTO turn_restrictions SELECT id, restriction, from_json, via_json, to_json
                FROM g.turn_restrictions ORDER BY id;
        """)
        con.commit()
        con.execute("DETACH DATABASE g")
    finally:
        con.close()


def build_graph(ways, relations, out: Path) -> dict:
    """Build the existing graph format with disk-backed intermediate storage."""
    con, db_path = _open_store()
    next_edge = 1
    try:
        for way in ways:
            next_edge, edge_count = _add_way(con, way, next_edge)
            if edge_count and next_edge % 100_000 < edge_count:
                con.commit()
        con.commit()
        restrictions = _restriction_rows(relations)
        _write_graph(con, restrictions, out)
        stats = {
            "nodes": int(con.execute("SELECT COUNT(*) FROM node_data").fetchone()[0]),
            "edges": int(con.execute("SELECT COUNT(*) FROM segments").fetchone()[0]),
            "turn_restrictions": len(restrictions),
        }
        if stats["nodes"] <= 0 or stats["edges"] <= 0:
            raise RuntimeError(
                f"Routing graph is empty: nodes={stats['nodes']} "
                f"edges={stats['edges']}"
            )
        return stats
    finally:
        con.close()
        db_path.unlink(missing_ok=True)


def build_graph_from_pbf(path: Path, out: Path, bbox: tuple[float, float, float, float] | None = None) -> dict:
    """Build routing directly from a PBF stream; ways are never materialized."""
    try:
        import osmium
    except ImportError as e:
        raise RuntimeError("PBF input requires osmium; install requirements.txt") from e

    def in_bbox(lon: float, lat: float) -> bool:
        return bbox is None or (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3])

    con, db_path = _open_store()
    next_edge = 1
    way_count = 0
    highway_count = 0
    invalid_location_count = 0
    outside_bbox_count = 0
    relations = []

    class Handler(osmium.SimpleHandler):
        def way(self, o):
            nonlocal next_edge, way_count
            tags = tags_dict(o)
            if tags.get("highway") not in ROAD_CLASSES:
                return
            nonlocal highway_count, invalid_location_count, outside_bbox_count
            highway_count += 1
            points = []
            refs = []
            for n in o.nodes:
                if not n.location.valid():
                    invalid_location_count += 1
                    continue
                lon, lat = float(n.location.lon), float(n.location.lat)
                if not in_bbox(lon, lat):
                    # For regional builds, retain the inside portion of a way.
                    outside_bbox_count += 1
                    continue
                refs.append(int(n.ref))
                points.append((lon, lat))
            if len(points) < 2:
                return

            class Node:
                def __init__(self, ref, lon, lat):
                    self.ref, self.lon, self.lat = ref, lon, lat
            class Way:
                pass
            w = Way()
            # The staging writer keys way_data by the real OSM way id.
            # Omitting this id made every streamed PBF way look like way 0;
            # INSERT OR IGNORE then kept only the first road in map.sqlite.
            # That was the direct cause of IR graphs such as nodes=2/segments=1/ways=1.
            w.id = int(o.id)
            w.tags = tags
            w.nodes = [Node(ref, lon, lat) for ref, (lon, lat) in zip(refs, points)]
            next_edge, edge_count = _add_way(con, w, next_edge)
            if edge_count > 0:
                way_count += 1
            if next_edge % 100_000 < 3:
                con.commit()

        def relation(self, o):
            tags = tags_dict(o)
            kind = tags.get("restriction", "")
            if tags.get("type") != "restriction" and not kind.startswith(("only_", "no_")):
                return
            relations.append({
                "id": int(o.id), "tags": tags,
                "members": [{"type": m.type, "ref": int(m.ref), "role": m.role} for m in o.members],
            })

    try:
        Handler().apply_file(str(path), locations=True)
        con.commit()
        restrictions = _restriction_rows(relations)
        _write_graph(con, restrictions, out)
        stats = {
            "nodes": int(con.execute("SELECT COUNT(*) FROM node_data").fetchone()[0]),
            "segments": int(con.execute("SELECT COUNT(*) FROM segments").fetchone()[0]),
            "edges": int(con.execute("SELECT COUNT(*) FROM segments").fetchone()[0]),
            "ways": int(con.execute("SELECT COUNT(*) FROM way_data").fetchone()[0]),
            "turn_restrictions": len(restrictions),
            "highway_ways_seen": highway_count,
            "invalid_locations": invalid_location_count,
            "outside_bbox_nodes": outside_bbox_count,
        }
        # A streamed PBF must retain distinct OSM way ids. If the source contains
        # many routable ways but the staging DB contains only one, fail the build
        # before packaging a truncated country graph. Small fixtures are allowed.
        if stats["highway_ways_seen"] >= 10 and stats["ways"] < max(2, int(stats["highway_ways_seen"] * 0.01)):
            raise RuntimeError(
                "Routing graph lost most routable ways: "
                + ", ".join(f"{key}={value}" for key, value in stats.items())
            )
        if stats["nodes"] <= 0 or stats["edges"] <= 0:
            raise RuntimeError(
                "Routing graph is empty: "
                + ", ".join(f"{key}={value}" for key, value in stats.items())
            )
        return stats
    finally:
        con.close()
        db_path.unlink(missing_ok=True)

