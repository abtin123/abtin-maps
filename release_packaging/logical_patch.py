"""Logical (row-level) patches for ABM archives - ``ABTINMAP-LOGICAL-PATCH/1``.

Why this exists
---------------
A byte patch between two weekly ``.abm`` files is useless: ``X.sqlite`` is DEFLATE-compressed
and rebuilt from scratch, so one changed row shifts every following page; ``images.tile_id``,
``names.id``, ``categories.id`` and ``segments.id`` are sequential numbers that shift after any
insert, so even a row diff keyed by primary key sees ~100% of the rows changed.

This module diffs the two archives by *stable keys* instead:

  features        -> OSM-namespaced id, names/categories resolved to text
  node_data       -> OSM node id
  way_data        -> OSM way id, names/categories resolved to text
  way_geometry    -> OSM way id
  segments        -> (a, b, way_id)  (+ its road_index rtree row)
  mbtiles tiles   -> (z, x, y)       (blob content, not tile_id)

and ships only the changed rows. The client applies them to the extracted ``X.sqlite`` /
``X.mbtiles`` with plain INSERT/UPDATE/DELETE (SQLite maintains the secondary indexes, the
rtrees are updated explicitly), rebuilds ``hierarchy_edges`` with the builder's own SQL, and then
verifies the result against ``target_digest``: a SHA-256 over the *resolved* content of every
table, so it is independent of sequential ids, page layout and DEFLATE output.

The app implements the same algorithm in Dart (``abm_logical_patch.dart``). Keep the two in sync:
SECTIONS / apply order / digest text format below are the contract.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import shutil
import sqlite3
import struct
import tempfile
import zipfile
from pathlib import Path
from typing import Iterator

SCHEMA = 'ABTINMAP-LOGICAL-PATCH/1'
SPEC = 1
_CHUNK = 4 * 1024 * 1024
_LINE_BYTES = 1024 * 1024        # target size of one JSON line in the patch stream


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(_CHUNK), b''):
            h.update(block)
    return h.hexdigest()


# --------------------------------------------------------------------------- contract
class Section:
    """One logical table. ``cols`` are SQL expressions; the first ``key`` of them are the stable
    key. ``blobs`` are the indexes of BLOB columns (base64 in the patch). ``stream`` replaces the
    plain SELECT for sections whose logical row is a group of SQL rows (way_segments)."""

    def __init__(self, name, db, cols, frm, order, key, blobs=(), prefix='', stream=None):
        self.name, self.db, self.cols, self.frm, self.order = name, db, cols, frm, order
        self.key, self.blobs, self.prefix, self.stream = key, tuple(blobs), prefix, stream

    def select(self) -> str:
        return f"{self.prefix} SELECT {', '.join(self.cols)} {self.frm} ORDER BY {self.order}"

    def rows(self, con):
        return self.stream(con) if self.stream else con.execute(self.select())


def _way_segment_groups(con) -> Iterator[tuple]:
    """One logical row per way: (way_id, segments, pieces).

    segments = [[a, b, dist_dm, cell_id], ...] in id order; pieces = road_index rows as
    [from_ord, to_ord, min_lon, max_lon, min_lat, max_lat] where the ords index ``segments``.
    The runtime joins ``segments.id BETWEEN road_index.seg_from AND seg_to``, so the ids of one
    piece must stay contiguous - which is why a way is always rewritten as a whole."""
    import itertools
    segs = itertools.groupby(
        con.execute('SELECT way_id, id, a, b, dist_dm, cell_id FROM segments ORDER BY way_id, id'),
        key=lambda r: r[0])
    pieces = itertools.groupby(
        con.execute('SELECT s.way_id, r.seg_from, r.seg_to, r.min_lon, r.max_lon, r.min_lat, r.max_lat '
                    'FROM road_index r JOIN segments s ON s.id = r.seg_from '
                    'ORDER BY s.way_id, r.seg_from'),
        key=lambda r: r[0])
    pw, pg = next(pieces, (None, None))
    for way_id, grp in segs:
        grp = list(grp)
        ords = {row[1]: i for i, row in enumerate(grp)}
        plist = []
        while pw is not None and pw < way_id:        # pieces of a way without segments: ignore
            pw, pg = next(pieces, (None, None))
        if pw == way_id:
            plist = [[ords[r[1]], ords[r[2]], r[3], r[4], r[5], r[6]] for r in pg]
            pw, pg = next(pieces, (None, None))
        yield (way_id, json.dumps([[r[2], r[3], r[4], r[5]] for r in grp], separators=(',', ':')),
               json.dumps(plist, separators=(',', ':')))


_NAME_JOIN = 'LEFT JOIN names n ON n.id = {x}.name_id'

# Order == patch order == apply order. 'db' is 'sqlite' or 'mbtiles'.
SECTIONS: list[Section] = [
    Section('features', 'sqlite',
            ['f.id', 'f.kind', 'n.name', 'n.name_fa', 'n.name_en', 'c.name', 'f.opening_hours',
             's.min_lon', 's.max_lon', 's.min_lat', 's.max_lat'],
            'FROM features f JOIN categories c ON c.id = f.category_id '
            + _NAME_JOIN.format(x='f') + ' LEFT JOIN spatial s ON s.id = f.id',
            'f.id', 1),
    Section('node_data', 'sqlite', ['id', 'lat_e7', 'lon_e7', 'cell_id'],
            'FROM node_data', 'id', 1),
    Section('way_data', 'sqlite',
            ['w.way_id', 'c.name', 'n.name', 'n.name_fa', 'n.name_en', 'w.access', 'w.junction',
             'w.surface', 'w.speed_kmh', 'w.oneway', 'w.lanes', 'w.flags', 'w.turn_lanes',
             'w.turn_lanes_bwd'],
            'FROM way_data w JOIN categories c ON c.id = w.class_id ' + _NAME_JOIN.format(x='w'),
            'w.way_id', 1),
    Section('way_geometry', 'sqlite', ['way_id', 'encoding', 'geometry'],
            'FROM way_geometry', 'way_id', 1, blobs=[2]),
    Section('way_segments', 'sqlite', ['way_id', 'segments', 'pieces'], '', 'way_id', 1,
            stream=_way_segment_groups),
    Section('roundabout_info', 'sqlite',
            ['r.way_id', 'r.junction', 'e.a', 'e.b', 'e.way_id', 'x.a', 'x.b', 'x.way_id',
             'r.exit_number', 'r.exit_count'],
            'FROM roundabout_info r LEFT JOIN segments e ON e.id = r.entry_edge '
            'LEFT JOIN segments x ON x.id = r.exit_edge', 'r.way_id', 1),
    Section('routing_cells', 'sqlite',
            ['cell_id', 'min_lon', 'min_lat', 'max_lon', 'max_lat', 'node_count', 'edge_count'],
            'FROM routing_cells', 'cell_id', 1),
    Section('turn_restrictions', 'sqlite',
            ['id', 'restriction', 'from_json', 'via_json', 'to_json'],
            'FROM turn_restrictions', 'id', 1),
    Section('turn_restriction_lookup', 'sqlite',
            ['restriction_id', 'from_way', 'via_node', 'to_way', 'restriction'],
            'FROM turn_restriction_lookup', 'restriction_id, from_way, via_node, to_way', 4),
    Section('mbtiles_metadata', 'mbtiles', ['name', 'value'], 'FROM metadata', 'name', 1),
    Section('tiles', 'mbtiles', ['zoom_level', 'tile_column', 'tile_row', 'tile_data'],
            'FROM tiles', 'zoom_level, tile_column, tile_row', 3, blobs=[3]),
]
SECTION_BY_NAME = {s.name: s for s in SECTIONS}

# Digest-only sections (derived tables that the client regenerates or maintains itself).
DIGEST_ONLY = [
    Section('node_index', 'sqlite', ['id', 'min_lon', 'max_lon', 'min_lat', 'max_lat'],
            'FROM node_index', 'id', 1),
    Section('segments_flat', 'sqlite',
            ['way_id', 'ROW_NUMBER() OVER (PARTITION BY way_id ORDER BY id) - 1', 'a', 'b',
             'dist_dm', 'cell_id'], 'FROM segments', 'way_id, id', 2),
    Section('pieces_flat', 'sqlite',
            ['f.way_id', 'f.ord', 'g.ord', 'r.min_lon', 'r.max_lon', 'r.min_lat', 'r.max_lat'],
            'FROM road_index r JOIN f ON f.id = r.seg_from JOIN f g ON g.id = r.seg_to',
            'f.way_id, f.ord', 2,
            prefix='WITH f AS (SELECT id, way_id, ROW_NUMBER() OVER (PARTITION BY way_id ORDER BY id) - 1 '
                   'AS ord FROM segments)'),
    Section('hierarchy_edges', 'sqlite', ['s.a', 's.b', 's.way_id', 'h.level'],
            'FROM hierarchy_edges h JOIN segments s ON s.id = h.edge_id',
            's.a, s.b, s.way_id, h.level', 3),
]

HIERARCHY_SQL = """
INSERT INTO hierarchy_edges(level, edge_id)
SELECT CASE
    WHEN c.name = 'motorway' THEN 3
    WHEN c.name IN ('trunk','motorway_link','trunk_link') THEN 2
    WHEN c.name IN ('primary','primary_link','secondary','secondary_link') THEN 1
    ELSE 0 END,
    s.id
FROM segments s
JOIN way_data w ON w.way_id = s.way_id
JOIN categories c ON c.id = w.class_id
"""
NODE_INDEX_SQL = """
INSERT INTO node_index(id, min_lon, max_lon, min_lat, max_lat)
SELECT id, lon_e7*1e-7, lon_e7*1e-7, lat_e7*1e-7, lat_e7*1e-7 FROM node_data WHERE id = ?
"""


# --------------------------------------------------------------------------- digest
def _fmt(v) -> str:
    """Canonical, language-independent text of one SQLite value (the Dart side does the same).
    REALs are hashed by their IEEE-754 bits: SQL's own float printing differs between SQLite
    versions, which would make builder and phone disagree about identical data."""
    if v is None:
        return 'N'
    if isinstance(v, int):
        return f'i{v}'
    if isinstance(v, float):
        return 'f' + struct.pack('>d', v).hex()
    if isinstance(v, str):
        return f's{len(v.encode("utf-8"))}:{v}'
    return 'b' + bytes(v).hex()


def content_digest(sqlite_path: Path, mbtiles_path: Path) -> tuple[str, dict[str, str]]:
    """SHA-256 over the resolved content of both stores (see module docstring)."""
    sections: dict[str, str] = {}
    for db_kind, path in (('sqlite', sqlite_path), ('mbtiles', mbtiles_path)):
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        try:
            for sec in [s for s in SECTIONS + DIGEST_ONLY if s.db == db_kind and not s.stream]:
                h = hashlib.sha256()
                if sec.name == 'tiles':
                    for z, x, y, blob in con.execute(sec.select()):
                        h.update(f'{z},{x},{y},{len(blob)}\n'.encode())
                        h.update(blob)
                else:
                    for row in con.execute(sec.select()):
                        h.update(','.join(_fmt(v) for v in row).encode('utf-8'))
                        h.update(b'\n')
                sections[sec.name] = h.hexdigest()
        finally:
            con.close()
    ordered = '\n'.join(f'{k}={sections[k]}' for k in sorted(sections))
    return hashlib.sha256(ordered.encode()).hexdigest(), sections


# --------------------------------------------------------------------------- archive io
def extract_stores(abm: Path, out_dir: Path) -> dict:
    """Extract metadata/manifest + the two stores of an .abm into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(abm) as z:
        meta_raw = z.read('metadata.json')
        meta = json.loads(meta_raw)
        db_name, tile_name = meta['database'], meta['tile_file']
        manifest_raw = z.read('manifest.json') if 'manifest.json' in z.namelist() else b''
        for name in (db_name, tile_name):
            with z.open(name) as src, (out_dir / name).open('wb') as dst:
                shutil.copyfileobj(src, dst, _CHUNK)
    return {'sqlite': out_dir / db_name, 'mbtiles': out_dir / tile_name,
            'sqlite_name': db_name, 'mbtiles_name': tile_name,
            'metadata_json': meta_raw.decode('utf-8'), 'manifest_json': manifest_raw.decode('utf-8')}


def write_abm(out: Path, stores: dict) -> None:
    """Pack extracted stores back into an .abm (DEFLATE for everything except the mbtiles)."""
    with zipfile.ZipFile(out, 'w') as z:
        members = [(stores['mbtiles_name'], stores['mbtiles'], zipfile.ZIP_STORED),
                   (stores['sqlite_name'], stores['sqlite'], zipfile.ZIP_DEFLATED)]
        for name, path, ct in sorted(members):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0)); info.compress_type = ct
            with path.open('rb') as src, z.open(info, 'w', force_zip64=True) as dst:
                shutil.copyfileobj(src, dst, _CHUNK)
        for name, text in (('manifest.json', stores['manifest_json']),
                           ('metadata.json', stores['metadata_json'])):
            if text:
                info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, text.encode('utf-8'))


# --------------------------------------------------------------------------- diff
def _same(a: tuple, b: tuple) -> bool:
    return a == b and all(type(x) is type(y) for x, y in zip(a, b))


def _merge_diff(old: Iterator[tuple], new: Iterator[tuple], k: int) -> Iterator[tuple[str, tuple]]:
    a, b = next(old, None), next(new, None)
    while a is not None or b is not None:
        if b is None or (a is not None and a[:k] < b[:k]):
            yield 'del', a[:k]
            a = next(old, None)
        elif a is None or b[:k] < a[:k]:
            yield 'put', b
            b = next(new, None)
        else:
            if not _same(a, b):
                yield 'put', b
            a, b = next(old, None), next(new, None)


def _json_row(row: tuple, blobs: tuple[int, ...]) -> list:
    out = list(row)
    for i in blobs:
        if out[i] is not None:
            out[i] = base64.b64encode(out[i]).decode('ascii')
    return out


class _LineWriter:
    """Collects rows into JSON lines of roughly ``_LINE_BYTES``."""

    def __init__(self, sink):
        self.sink, self.kind, self.table, self.rows, self.size = sink, None, None, [], 0

    def add(self, kind: str, table: str, row: list) -> None:
        if (kind, table) != (self.kind, self.table):
            self.flush()
            self.kind, self.table = kind, table
        self.rows.append(row)
        self.size += len(json.dumps(row, ensure_ascii=False, separators=(',', ':')))
        if self.size >= _LINE_BYTES:
            self.flush()

    def flush(self) -> None:
        if self.rows:
            self.sink.write(json.dumps({'k': self.kind, 't': self.table, 'rows': self.rows},
                                       ensure_ascii=False, separators=(',', ':')) + '\n')
        self.rows, self.size = [], 0


def create_logical_patch(base_abm: Path, target_abm: Path, code: str, output_dir: Path
                         ) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    patch_name, manifest_name = f'{code}.abmpatch.bin', f'{code}.abmpatch.json'
    patch_path = output_dir / patch_name
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        base = extract_stores(base_abm, tmp / 'base')
        target = extract_stores(target_abm, tmp / 'target')
        if (base['sqlite_name'], base['mbtiles_name']) != (target['sqlite_name'], target['mbtiles_name']):
            raise ValueError('base and target use different store names; no logical patch')
        touched = set()
        with gzip.open(patch_path, 'wt', encoding='utf-8', compresslevel=9, newline='\n') as sink:
            sink.write(json.dumps({'k': 'hdr', 'spec': SPEC, 'code': code}) + '\n')
            sink.write(json.dumps({'k': 'members', 'metadata_json': target['metadata_json'],
                                   'manifest_json': target['manifest_json']},
                                  ensure_ascii=False) + '\n')
            writer = _LineWriter(sink)
            conns = {}
            for kind in ('sqlite', 'mbtiles'):
                conns[kind] = (sqlite3.connect(f"file:{base[kind]}?mode=ro", uri=True),
                               sqlite3.connect(f"file:{target[kind]}?mode=ro", uri=True))
            try:
                for sec in SECTIONS:
                    ca, cb = conns[sec.db]
                    dels, puts = [], 0
                    # deletions first (apply order), then puts: two passes over the diff
                    for op, row in _merge_diff(sec.rows(ca), sec.rows(cb), sec.key):
                        if op == 'del':
                            writer.add('del', sec.name, list(row)); touched.add(sec.name)
                    for op, row in _merge_diff(sec.rows(ca), sec.rows(cb), sec.key):
                        if op == 'put':
                            if sec.stream:
                                row = (row[0], json.loads(row[1]), json.loads(row[2]))
                            writer.add('put', sec.name, _json_row(row, sec.blobs)); touched.add(sec.name)
                    writer.flush()
            finally:
                for a, b in conns.values():
                    a.close(); b.close()
            sink.write(json.dumps({'k': 'end'}) + '\n')
        digest, sections = content_digest(target['sqlite'], target['mbtiles'])
        manifest = {
            'schema': SCHEMA, 'spec': SPEC, 'code': code,
            'base_sha256': _sha256_file(base_abm), 'target_sha256': _sha256_file(target_abm),
            'target_size': target_abm.stat().st_size, 'patch_sha256': _sha256_file(patch_path),
            'target_digest': digest, 'section_digests': sections,
            'sqlite_member': target['sqlite_name'], 'mbtiles_member': target['mbtiles_name'],
            'touched': sorted(touched),
        }
    manifest_path = output_dir / manifest_name
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    descriptor = {
        'base_sha256': manifest['base_sha256'], 'manifest_file': manifest_name,
        'bin_file': patch_name, 'size': patch_path.stat().st_size,
        'sha256': manifest['patch_sha256'],
    }
    (output_dir / 'patch-descriptor.json').write_text(json.dumps(descriptor, indent=2) + '\n')
    return manifest_path, patch_path


# --------------------------------------------------------------------------- apply (reference)
class _Ids:
    """get-or-create ids for categories and names (names has no unique index in the shipped DB,
    so a temporary one is created for the duration of the apply)."""

    def __init__(self, con: sqlite3.Connection):
        self.con = con
        self.cats = {n: i for i, n in con.execute('SELECT id, name FROM categories')}
        con.execute('CREATE INDEX IF NOT EXISTS ix_apply_names ON names(name, name_fa, name_en)')
        self.names: dict[tuple, int] = {}

    def category(self, name: str) -> int:
        i = self.cats.get(name)
        if i is None:
            i = self.cats[name] = self.con.execute(
                'INSERT INTO categories(name) VALUES (?)', (name,)).lastrowid
        return i

    def name(self, n, fa, en):
        if n is None:
            return None
        key = (n, fa, en)
        i = self.names.get(key)
        if i is None:
            row = self.con.execute(
                'SELECT id FROM names WHERE name = ? AND name_fa = ? AND name_en = ? LIMIT 1', key
            ).fetchone()
            if row:
                i = row[0]
            else:
                i = self.con.execute('INSERT INTO names(name, name_fa, name_en) VALUES (?,?,?)',
                                     key).lastrowid
                self.con.execute(
                    'INSERT INTO search_fts(rowid, name, name_fa, name_en) VALUES (?,?,?,?)',
                    (i, n, fa, en))
            self.names[key] = i
        return i

    def close(self):
        self.con.execute('DROP INDEX IF EXISTS ix_apply_names')


def _seg_id(con, a, b, way):
    if a is None:
        return None
    row = con.execute('SELECT id FROM segments WHERE a = ? AND b = ? AND way_id = ?',
                      (a, b, way)).fetchone()
    return row[0] if row else None


def _apply_sqlite_rows(con, ids: _Ids, table: str, kind: str, rows: list, state: dict) -> None:
    ex = con.execute
    if table == 'features':
        for r in rows:
            if kind == 'del':
                ex('DELETE FROM features WHERE id = ?', (r[0],)); ex('DELETE FROM spatial WHERE id = ?', (r[0],))
                continue
            fid, k, n, fa, en, cat, hours, x0, x1, y0, y1 = r
            ex('INSERT OR REPLACE INTO features(id, kind, name_id, category_id, opening_hours) '
               'VALUES (?,?,?,?,?)', (fid, k, ids.name(n, fa, en), ids.category(cat), hours))
            ex('DELETE FROM spatial WHERE id = ?', (fid,))
            if x0 is not None:
                ex('INSERT INTO spatial(id, min_lon, max_lon, min_lat, max_lat) VALUES (?,?,?,?,?)',
                   (fid, x0, x1, y0, y1))
    elif table == 'node_data':
        for r in rows:
            ex('DELETE FROM node_index WHERE id = ?', (r[0],))
            if kind == 'del':
                ex('DELETE FROM node_data WHERE id = ?', (r[0],)); continue
            ex('INSERT OR REPLACE INTO node_data(id, lat_e7, lon_e7, cell_id) VALUES (?,?,?,?)', r)
            ex(NODE_INDEX_SQL, (r[0],))
    elif table == 'way_data':
        state['hierarchy'] = True
        for r in rows:
            if kind == 'del':
                ex('DELETE FROM way_data WHERE way_id = ?', (r[0],)); continue
            (wid, cls, n, fa, en, access, junction, surface, speed, oneway, lanes, flags, tl, tlb) = r
            ex('INSERT OR REPLACE INTO way_data(way_id, class_id, name_id, access, junction, surface, '
               'speed_kmh, oneway, lanes, flags, turn_lanes, turn_lanes_bwd) '
               'VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
               (wid, ids.category(cls), ids.name(n, fa, en), access, junction, surface, speed,
                oneway, lanes, flags, tl, tlb))
    elif table == 'way_geometry':
        for r in rows:
            if kind == 'del':
                ex('DELETE FROM way_geometry WHERE way_id = ?', (r[0],)); continue
            ex('INSERT OR REPLACE INTO way_geometry(way_id, encoding, geometry) VALUES (?,?,?)',
               (r[0], r[1], base64.b64decode(r[2])))
    elif table == 'way_segments':
        state['hierarchy'] = True
        if not state.get('seg_index'):
            ex('CREATE INDEX IF NOT EXISTS ix_apply_seg_way ON segments(way_id)')
            state['seg_index'] = True
        for r in rows:
            for (sid,) in ex('SELECT id FROM segments WHERE way_id = ?', (r[0],)).fetchall():
                ex('DELETE FROM road_index WHERE id = ?', (sid,))
            ex('DELETE FROM segments WHERE way_id = ?', (r[0],))
            if kind == 'del':
                continue
            way_id, segs, pieces = r
            seg_ids = [ex('INSERT INTO segments(a, b, dist_dm, way_id, cell_id) VALUES (?,?,?,?,?)',
                          (a, b, dist, way_id, cell)).lastrowid for a, b, dist, cell in segs]
            for i in range(1, len(seg_ids)):
                if seg_ids[i] != seg_ids[i - 1] + 1:       # road_index ranges need contiguous ids
                    raise ValueError('segment ids of a way are not contiguous')
            for f, t, x0, x1, y0, y1 in pieces:
                ex('INSERT INTO road_index(id, min_lon, max_lon, min_lat, max_lat, seg_from, seg_to) '
                   'VALUES (?,?,?,?,?,?,?)', (seg_ids[f], x0, x1, y0, y1, seg_ids[f], seg_ids[t]))
    elif table == 'roundabout_info':
        for r in rows:
            if kind == 'del':
                ex('DELETE FROM roundabout_info WHERE way_id = ?', (r[0],)); continue
            wid, junction, ea, eb, ew, xa, xb, xw, num, cnt = r
            ex('INSERT OR REPLACE INTO roundabout_info(way_id, junction, entry_edge, exit_edge, '
               'exit_number, exit_count) VALUES (?,?,?,?,?,?)',
               (wid, junction, _seg_id(con, ea, eb, ew), _seg_id(con, xa, xb, xw), num, cnt))
    elif table == 'routing_cells':
        for r in rows:
            if kind == 'del':
                ex('DELETE FROM routing_cells WHERE cell_id = ?', (r[0],)); continue
            ex('INSERT OR REPLACE INTO routing_cells(cell_id, min_lon, min_lat, max_lon, max_lat, '
               'node_count, edge_count) VALUES (?,?,?,?,?,?,?)', r)
    elif table == 'turn_restrictions':
        for r in rows:
            if kind == 'del':
                ex('DELETE FROM turn_restrictions WHERE id = ?', (r[0],)); continue
            ex('INSERT OR REPLACE INTO turn_restrictions(id, restriction, from_json, via_json, to_json) '
               'VALUES (?,?,?,?,?)', r)
    elif table == 'turn_restriction_lookup':
        for r in rows:
            if kind == 'del':
                ex('DELETE FROM turn_restriction_lookup WHERE restriction_id = ? AND from_way = ? '
                   'AND via_node = ? AND to_way = ?', r[:4]); continue
            ex('INSERT OR REPLACE INTO turn_restriction_lookup(restriction_id, from_way, via_node, '
               'to_way, restriction) VALUES (?,?,?,?,?)', r)
    else:
        raise ValueError(f'unknown sqlite section {table}')


def _apply_mbtiles_rows(con, table: str, kind: str, rows: list) -> None:
    ex = con.execute
    if table == 'mbtiles_metadata':
        for r in rows:
            if kind == 'del':
                ex('DELETE FROM metadata WHERE name = ?', (r[0],))
            else:
                ex('INSERT OR REPLACE INTO metadata(name, value) VALUES (?,?)', r)
    elif table == 'tiles':
        for r in rows:
            if kind == 'del':
                ex('DELETE FROM map WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?', r)
                continue
            tid = ex('INSERT INTO images(tile_data) VALUES (?)', (base64.b64decode(r[3]),)).lastrowid
            ex('INSERT OR REPLACE INTO map(zoom_level, tile_column, tile_row, tile_id) VALUES (?,?,?,?)',
               (r[0], r[1], r[2], tid))
    else:
        raise ValueError(f'unknown mbtiles section {table}')


def apply_logical_patch_to_stores(stores: dict, manifest: dict, patch_bin: Path) -> dict:
    """Apply in place on the extracted stores; verify; return updated ``stores`` (members text)."""
    if manifest.get('schema') != SCHEMA:
        raise ValueError('not a logical patch manifest')
    sq = sqlite3.connect(stores['sqlite'], isolation_level=None)
    mb = sqlite3.connect(stores['mbtiles'], isolation_level=None)
    try:
        for con in (sq, mb):
            con.execute('PRAGMA journal_mode = OFF'); con.execute('PRAGMA synchronous = OFF')
            con.execute('BEGIN')
        ids = _Ids(sq)
        state = {'hierarchy': False, 'seg_index': False}
        members = None
        with gzip.open(patch_bin, 'rt', encoding='utf-8') as fh:
            for line in fh:
                msg = json.loads(line)
                k = msg['k']
                if k == 'hdr':
                    if msg.get('spec') != SPEC:
                        raise ValueError(f"unsupported logical patch spec {msg.get('spec')}")
                elif k == 'members':
                    members = msg
                elif k in ('put', 'del'):
                    sec = SECTION_BY_NAME[msg['t']]
                    if sec.db == 'sqlite':
                        _apply_sqlite_rows(sq, ids, sec.name, k, msg['rows'], state)
                    else:
                        _apply_mbtiles_rows(mb, sec.name, k, msg['rows'])
                elif k == 'end':
                    break
        if members is None:
            raise ValueError('patch has no members record')
        if state['hierarchy']:
            sq.execute('DELETE FROM hierarchy_edges')
            sq.execute(HIERARCHY_SQL)
        ids.close()
        if state.get('seg_index'):
            sq.execute('DROP INDEX IF EXISTS ix_apply_seg_way')
        mb.execute('DELETE FROM images WHERE tile_id NOT IN (SELECT tile_id FROM map)')
        sq.execute('COMMIT'); mb.execute('COMMIT')
    except BaseException:
        for con in (sq, mb):
            try:
                con.execute('ROLLBACK')
            except sqlite3.Error:
                pass
        raise
    finally:
        sq.close(); mb.close()
    digest, _ = content_digest(stores['sqlite'], stores['mbtiles'])
    if digest != manifest['target_digest']:
        raise ValueError('logical patch result does not match target digest')
    stores = dict(stores)
    stores['metadata_json'], stores['manifest_json'] = members['metadata_json'], members['manifest_json']
    return stores


def apply_logical_patch(base_abm: Path, manifest: dict, patch_bin: Path, out: Path) -> None:
    """Reference implementation (the app does the same)."""
    with tempfile.TemporaryDirectory() as tmp:
        stores = extract_stores(base_abm, Path(tmp) / 'work')
        stores = apply_logical_patch_to_stores(stores, manifest, patch_bin)
        write_abm(out, stores)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Create an ABTINMAP logical patch')
    ap.add_argument('base', type=Path); ap.add_argument('target', type=Path)
    ap.add_argument('--code', required=True); ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    m, p = create_logical_patch(a.base, a.target, a.code, a.output)
    print(json.dumps({'manifest': str(m), 'patch': str(p), 'size': p.stat().st_size}, indent=2))
