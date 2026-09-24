from __future__ import annotations
import hashlib, json, shutil, sqlite3, tempfile, zipfile
from pathlib import Path

FORBIDDEN=({'pmtiles','style.json','render_cache','vector/'})
_CHUNK = 4 * 1024 * 1024  # 4 MiB - stream large files instead of loading them whole into RAM

def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(_CHUNK), b''):
            h.update(chunk)
    return h.hexdigest()

def create_abm(staging: Path, output: Path, country: str, source: Path, stats: dict,
                bbox: tuple[float, float, float, float] | None,
                region: dict | None = None) -> Path:
    """Package a staged vector/poi/search/routing tree into a single tile-free
    `.abm` archive.

    ``bbox`` is required by the app's release manifest (it draws the region's
    footprint on the World Overview and decides whether "این منطقه دانلود
    نشده است" should show). A build with genuinely no geometry (an empty test
    fixture) may pass ``bbox=None``, but real builds should always have one -
    verify_abm raises if it's missing so a broken/empty build can't ship
    silently.

    ``region`` is set only when this archive is one part of a country that
    was split geographically (see build_abm.py --regions): it carries the
    parent country code plus the region's own code/names so the release
    manifest can group them correctly.
    """
    metadata={
        "country": country.upper(),
        "format": "ABM",
        "version": 6,
        "tiles": True,
        "tile_file": "map.mbtiles",
        "tile_format": "pbf",
        "tile_compression": "gzip",
        "tile_extent": 4096,
        "tile_minzoom": 0,
        "tile_maxzoom": (stats.get("tiles") or {}).get("maxzoom", 14),
        "style": "external",
        "renderer": "app",
        "search": True,
        "routing": True,
        "schema_version": 7,
        "graph_version": 2,
        "routing_partition": {"type": "geo_grid", "cell_degrees": 0.25, "lazy": True},
        "routing_geometry": {"encoding": "delta-zigzag-varint-e5", "separate": True},
        "database": "map.sqlite",
        "source": source.name,
        "bbox": list(bbox) if bbox is not None else None,
        "region": region,
        "stats": stats,
    }
    (staging/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    files=[p for p in staging.rglob('*') if p.is_file() and p.name not in {'manifest.json'}]
    manifest={"format":"ABM","files":{str(p.relative_to(staging)):_sha256_file(p) for p in files}}
    (staging/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    output.parent.mkdir(parents=True,exist_ok=True)
    # Deterministic ZIP metadata (fixed timestamps) so rebuilding an unchanged ABM
    # does not rewrite every local-file header; create_patch.py compares fixed-size
    # chunks. DEFLATE is used for everything except map.mbtiles: it is decoded fast
    # (zlib, NEON on ARM) and every zip reader supports it. Costs ~5-10% more size
    # than LZMA.
    # map.mbtiles holds already-gzipped MVT blobs: recompressing gains ~0, so STORED.
    STORED = {'map.mbtiles'}
    with zipfile.ZipFile(output, 'w', compresslevel=6) as z:
        for p in sorted(staging.rglob('*')):
            if not p.is_file():
                continue
            name = p.relative_to(staging).as_posix()
            compress_type = (
                zipfile.ZIP_STORED if name in STORED
                else zipfile.ZIP_DEFLATED
            )
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = compress_type
            info.create_system = 3
            info.external_attr = 0o644 << 16
            # Stream through the compressor in chunks rather than loading the
            # whole file into memory with read_bytes()/writestr().
            with p.open('rb') as src, z.open(info, 'w', force_zip64=True) as dest:
                shutil.copyfileobj(src, dest, length=_CHUNK)
    return output

def _extract(z: zipfile.ZipFile, name: str, suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        with z.open(name) as member:
            shutil.copyfileobj(member, tmp, length=_CHUNK)
    return Path(tmp.name)


def verify_abm(path: Path, *, require_bbox: bool = True) -> dict:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from abm_builder.mvt import decode_tile
    required={'metadata.json','map.sqlite','map.mbtiles'}
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist()); missing=sorted(required-names)
        bad=[n for n in names if any(x in n.lower() for x in FORBIDDEN)]
        if missing or bad: raise ValueError(f"Invalid ABM: missing={missing}, forbidden={bad}")
        meta=json.loads(z.read('metadata.json'))
        assert meta['tiles'] is True and meta['style']=='external' and meta['tile_format']=='pbf'
        if require_bbox and not meta.get('bbox'):
            raise ValueError(f"Invalid ABM: {path} has no bbox in metadata.json "
                              f"(required for the release manifest / World Overview coverage check)")

        # --- map.sqlite: search + POI + routing, one copy of every record ---
        db_path = _extract(z, 'map.sqlite', '.sqlite')
        try:
            db = sqlite3.connect(db_path)
            try:
                have = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
                need = {'features','names','categories','search_fts','spatial','node_data','way_data',
                        'segments','road_index','turn_restrictions','turn_restriction_lookup','routing_cells','node_index','way_geometry','hierarchy_edges','roundabout_info',
                        'nodes','ways','edges','places','poi'}
                if need - have:
                    raise ValueError(f"Invalid ABM: map.sqlite missing tables/views: {sorted(need - have)}")
                q = lambda sql: int(db.execute(sql).fetchone()[0])
                if db.execute("PRAGMA user_version").fetchone()[0] < 7:
                    raise ValueError("Invalid ABM: map.sqlite schema version is older than 7")
                if q('SELECT COUNT(*) FROM node_data') <= 0 or q('SELECT COUNT(*) FROM segments') <= 0:
                    raise ValueError("Invalid ABM: routing graph is empty")
                if q('SELECT COUNT(*) FROM features') <= 0:
                    raise ValueError("Invalid ABM: map.sqlite contains no searchable features")
                # No-duplicate guards.
                if q('SELECT COUNT(*) FROM (SELECT 1 FROM names GROUP BY name,name_fa,name_en HAVING COUNT(*)>1)'):
                    raise ValueError("Invalid ABM: duplicate rows in names")
                if q('SELECT COUNT(*) FROM (SELECT 1 FROM segments GROUP BY a,b,way_id HAVING COUNT(*)>1)'):
                    raise ValueError("Invalid ABM: duplicate segments")
                if q('SELECT COUNT(*) FROM segments WHERE way_id NOT IN (SELECT way_id FROM way_data)'):
                    raise ValueError("Invalid ABM: segments reference missing ways")
                if q('SELECT COUNT(*) FROM turn_restriction_lookup r LEFT JOIN turn_restrictions t ON t.id=r.restriction_id WHERE t.id IS NULL'):
                    raise ValueError("Invalid ABM: turn restriction lookup references missing restrictions")
                db.execute("SELECT rowid FROM search_fts LIMIT 1").fetchone()
            finally:
                db.close()
        finally:
            db_path.unlink(missing_ok=True)

        # --- map.mbtiles ---
        tp = _extract(z, 'map.mbtiles', '.mbtiles')
        try:
            tdb = sqlite3.connect(tp)
            try:
                md = dict(tdb.execute("SELECT name, value FROM metadata").fetchall())
                if md.get('format') != 'pbf':
                    raise ValueError("Invalid ABM: map.mbtiles format must be pbf")
                n = int(tdb.execute("SELECT COUNT(*) FROM map").fetchone()[0])
                if n <= 0:
                    raise ValueError("Invalid ABM: map.mbtiles has no tiles")
                if int(tdb.execute("SELECT COUNT(*) FROM map WHERE tile_id NOT IN (SELECT tile_id FROM images)").fetchone()[0]):
                    raise ValueError("Invalid ABM: map.mbtiles references missing images")
                row = tdb.execute("SELECT tile_data FROM tiles ORDER BY zoom_level DESC LIMIT 1").fetchone()
                if not decode_tile(row[0]):
                    raise ValueError("Invalid ABM: sample tile is empty/undecodable")
            finally:
                tdb.close()
        finally:
            tp.unlink(missing_ok=True)

        return {"ok":True,"files":len(names),"metadata":meta}
