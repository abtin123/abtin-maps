from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import struct
import tempfile
from pathlib import Path
from typing import Iterable

from abm_builder.core import tags_dict, way_geometry, entity_id, haversine_m

ROAD_CLASSES = {
    "motorway", "motorway_link", "trunk", "trunk_link",
    "primary", "primary_link", "secondary", "secondary_link",
    "tertiary", "tertiary_link", "unclassified", "residential",
    "living_street", "service", "track", "road",
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
    con.execute("CREATE TABLE nodes (id INTEGER PRIMARY KEY, lat REAL NOT NULL, lon REAL NOT NULL)")
    con.execute("""CREATE TABLE edges (
        id INTEGER PRIMARY KEY, start INTEGER NOT NULL, end INTEGER NOT NULL,
        distance_m REAL NOT NULL, road_class TEXT NOT NULL, speed_kmh REAL NOT NULL,
        oneway INTEGER NOT NULL, access TEXT NOT NULL,
        name TEXT NOT NULL DEFAULT '', way_id INTEGER NOT NULL DEFAULT 0,
        junction TEXT NOT NULL DEFAULT '', surface TEXT NOT NULL DEFAULT ''
    )""")
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
    con.executemany(
        "INSERT OR IGNORE INTO nodes(id,lat,lon) VALUES (?,?,?)",
        [(int(nid), float(lat), float(lon)) for nid, (lon, lat) in zip(ids, geom)],
    )
    oneway = _is_oneway(tags)
    speed = _speed(tags)
    edge_count = 0
    for i, (a, b) in enumerate(zip(ids, ids[1:])):
        lon1, lat1 = geom[i]
        lon2, lat2 = geom[i + 1]
        dist = haversine_m((lat1, lon1), (lat2, lon2))
        con.execute(
            "INSERT INTO edges VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (next_edge, int(a), int(b), dist, highway, speed, int(oneway),
             tags.get("access", ""), tags.get("name:fa") or tags.get("name") or tags.get("name:en") or '',
             entity_id(way), tags.get("junction", ""), tags.get("surface", "")),
        )
        next_edge += 1
        edge_count += 1
        if not oneway:
            con.execute(
                "INSERT INTO edges VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (next_edge, int(b), int(a), dist, highway, speed, 0,
                 tags.get("access", ""), tags.get("name:fa") or tags.get("name") or tags.get("name:en") or '',
                 entity_id(way), tags.get("junction", ""), tags.get("surface", "")),
            )
            next_edge += 1
            edge_count += 1
    return next_edge, edge_count


def _write_graph(con: sqlite3.Connection, restrictions: list[tuple[int, str, list[int], list[int], list[int]]], out: Path) -> None:
    """Publish the routing graph as an indexed SQLite member.

    Keeping routing as SQLite inside ABM avoids materializing a country-sized
    JSON graph in the app. The old graph.bin format is intentionally not
    generated by new builds; the app still reads it for legacy ABMs.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    con.execute("CREATE INDEX IF NOT EXISTS idx_edges_start ON edges(start)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_edges_end ON edges(end)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_edges_class ON edges(road_class)")
    con.execute("""CREATE TABLE IF NOT EXISTS turn_restrictions (
        id INTEGER PRIMARY KEY, restriction TEXT NOT NULL,
        from_json TEXT NOT NULL, via_json TEXT NOT NULL, to_json TEXT NOT NULL
    )""")
    con.execute("DELETE FROM turn_restrictions")
    con.executemany(
        "INSERT INTO turn_restrictions VALUES (?,?,?,?,?)",
        [(rid, kind, json.dumps(fr), json.dumps(vi), json.dumps(to))
         for rid, kind, fr, vi, to in restrictions],
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_restriction_kind ON turn_restrictions(restriction)")
    try:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS node_rtree USING rtree(id,minLat,maxLat,minLon,maxLon)")
        con.execute("DELETE FROM node_rtree")
        con.executemany(
            "INSERT INTO node_rtree VALUES (?,?,?,?,?)",
            [(nid, lat, lat, lon, lon) for nid, lat, lon in con.execute("SELECT id,lat,lon FROM nodes")],
        )
    except sqlite3.OperationalError:
        # RTree is optional in unusual SQLite builds; the ordinary node index
        # below is still sufficient as a compatibility fallback.
        pass
    con.execute("CREATE INDEX IF NOT EXISTS idx_nodes_lat_lon ON nodes(lat,lon)")
    con.commit()
    if out.exists():
        out.unlink()
    # Backup gives us a consistent standalone SQLite file while keeping the
    # disk-backed construction database separate from the packaged member.
    dst = sqlite3.connect(out)
    try:
        con.backup(dst)
        dst.execute("PRAGMA journal_mode=DELETE")
        dst.commit()
    finally:
        dst.close()


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
        return {
            "nodes": int(con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]),
            "edges": int(con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]),
            "turn_restrictions": len(restrictions),
        }
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
    relations = []

    class Handler(osmium.SimpleHandler):
        def way(self, o):
            nonlocal next_edge, way_count
            tags = tags_dict(o)
            if tags.get("highway") not in ROAD_CLASSES:
                return
            points = []
            refs = []
            for n in o.nodes:
                if not n.location.valid():
                    return
                lon, lat = float(n.location.lon), float(n.location.lat)
                if not in_bbox(lon, lat):
                    # For regional builds, retain the inside portion of a way.
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
            w.tags = tags
            w.nodes = [Node(ref, lon, lat) for ref, (lon, lat) in zip(refs, points)]
            next_edge, _ = _add_way(con, w, next_edge)
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
        return {
            "nodes": int(con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]),
            "edges": int(con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]),
            "turn_restrictions": len(restrictions),
            "ways": way_count,
        }
    finally:
        con.close()
        db_path.unlink(missing_ok=True)
