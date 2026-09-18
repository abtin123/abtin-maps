from __future__ import annotations
import sqlite3
from pathlib import Path
from abm_builder.core import norm_fa

SCHEMA = """
PRAGMA journal_mode=OFF;
PRAGMA synchronous=OFF;
CREATE TABLE IF NOT EXISTS features (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    name_fa TEXT NOT NULL DEFAULT '',
    name_en TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    lat REAL,
    lon REAL,
    opening_hours TEXT NOT NULL DEFAULT '',
    road_class TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_features_kind ON features(kind);
CREATE INDEX IF NOT EXISTS idx_features_source ON features(source_id);
CREATE INDEX IF NOT EXISTS idx_features_name ON features(name);
CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
    name, name_fa, name_en, category,
    content='features', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE VIRTUAL TABLE IF NOT EXISTS spatial USING rtree(id, min_lon, max_lon, min_lat, max_lat);
CREATE VIEW IF NOT EXISTS places AS
SELECT id, name, name_fa, name_en, category, lat, lon, opening_hours FROM features;
CREATE VIEW IF NOT EXISTS poi AS
SELECT id, source_id, name, name_fa, name_en, category, lat, lon, opening_hours FROM features WHERE kind='poi';
"""

def _feature_id(kind: str, source_id: int, used: set[int]) -> int:
    # Keep normal OSM IDs when possible. If namespaces collide, allocate a
    # deterministic negative ID. source_id is retained separately.
    candidate = int(source_id)
    if candidate not in used:
        return candidate
    candidate = -abs(candidate) or -1
    while candidate in used:
        candidate -= 1
    return candidate


def create_map_db(path: Path, pois: list[dict], places: list[dict], roads: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.executescript(SCHEMA)
        con.execute("DELETE FROM features")
        con.execute("DELETE FROM spatial")
        used: set[int] = set()
        rows = []

        def add(source_id, kind, name, name_fa, name_en, category, lat, lon, hours='', road_class=''):
            fid = _feature_id(kind, int(source_id), used)
            used.add(fid)
            rows.append((fid, int(source_id), kind, name or '', norm_fa(name_fa), name_en or '',
                         category or '', lat, lon, hours or '', road_class or ''))

        for p in pois:
            add(p['id'], 'poi', p.get('name',''), p.get('name_fa',''), p.get('name_en',''),
                p.get('category','poi'), p.get('latitude'), p.get('longitude'), p.get('opening_hours',''))
        for p in places:
            # places.bin records are {"id","geometry","tags":{...}} (see
            # extractors/osm.py:_record) - reading p.get('name') on the
            # top-level dict always missed, silently indexing every place
            # with an empty name. Read from the nested tags dict instead.
            tags = p.get('tags', {})
            g = p.get('geometry', [])
            if g:
                lat = sum(y for _, y in g) / len(g); lon = sum(x for x, _ in g) / len(g)
            else:
                lat = lon = None
            add(p['id'], 'place', tags.get('name',''), tags.get('name_fa',''), tags.get('name_en',''),
                tags.get('place','place'), lat, lon)
        for r in roads:
            # Same nested-tags bug as places above: r.get('name') on the
            # top-level {"id","geometry","tags":{...}} record was always ''
            # and r.get('road_class') doesn't exist either (it's tags.highway),
            # so every single road was indexed as an identical, nameless
            # 'road' entry - purely wasted FTS5/rtree/features rows, since a
            # name-less entry can never surface in a name search anyway.
            #
            # Fixed to read the real name/highway out of tags, and to only
            # index roads that actually have a name - unnamed roads (the
            # vast majority: driveway fragments, unnamed residential stubs)
            # are unreachable by search regardless, so indexing them was the
            # dominant source of map.sqlite bloat for no functional benefit.
            tags = r.get('tags', {})
            name, name_fa, name_en = tags.get('name', ''), tags.get('name_fa', ''), tags.get('name_en', '')
            if not (name or name_fa or name_en):
                continue
            g = r.get('geometry', [])
            if not g:
                continue
            lat = sum(y for _, y in g) / len(g); lon = sum(x for x, _ in g) / len(g)
            road_class = tags.get('highway', 'road')
            add(r['id'], 'road', name, name_fa, name_en,
                road_class, lat, lon, road_class=road_class)

        con.executemany("INSERT INTO features VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
        con.execute("INSERT INTO search_fts(search_fts) VALUES('rebuild')")
        con.executemany(
            "INSERT INTO spatial VALUES (?,?,?,?,?)",
            [(r[0], r[8], r[8], r[7], r[7]) for r in rows if r[7] is not None and r[8] is not None]
        )
        con.commit()
        return len(rows)
    finally:
        con.close()


def search(path: Path, query: str, limit=20):
    q = norm_fa(query).replace('"', ' ')
    con = sqlite3.connect(path); con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT f.*, bm25(search_fts) AS rank FROM search_fts JOIN features f ON f.id=search_fts.rowid "
            "WHERE search_fts MATCH ? ORDER BY rank LIMIT ?", (q + '*', limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
