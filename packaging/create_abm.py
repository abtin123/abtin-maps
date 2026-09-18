from __future__ import annotations
import hashlib, json, shutil, sqlite3, tempfile, zipfile
from pathlib import Path

FORBIDDEN=({'tile','tiles','pmtiles','mbtiles','style.json','render_cache'})
_CHUNK = 4 * 1024 * 1024  # 4 MiB - stream large files instead of loading them whole into RAM

# ISO 3166-1 alpha-2 codes for countries/territories that drive on the left.
# Used to derive driving_side for metadata.json so the app can render
# roundabout rotation (and any other direction-dependent UI) correctly per
# country instead of assuming right-hand traffic everywhere. Source: common
# reference list of left-driving countries (UK, Ireland, Japan, Australia,
# NZ, most of southern/eastern Africa, South Asia, Southeast Asia, and a
# handful of Caribbean/Pacific states).
LEFT_HAND_TRAFFIC_COUNTRIES = {
    'AG','AU','BS','BD','BB','BT','BW','BN','CY','DM','FJ','GD','GY','HK',
    'IN','ID','IE','JM','JP','KE','KI','LS','MO','MW','MY','MV','MT','MU',
    'MZ','NA','NP','NZ','PK','PG','SC','SG','SB','ZA','LK','SR','SZ','TZ',
    'TH','TT','TV','UG','GB','VU','ZM','ZW',
}

def driving_side(country_code: str) -> str:
    return 'left' if country_code.upper() in LEFT_HAND_TRAFFIC_COUNTRIES else 'right'

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
        "driving_side": driving_side(country),
        "format": "ABM",
        "version": 4,
        "tiles": False,
        "style": "external",
        "renderer": "app",
        "search": True,
        "routing": True,
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
    # Use deterministic ZIP metadata so rebuilding an unchanged ABM does not
    # rewrite every local-file header with a new filesystem timestamp. Stable
    # headers are important because create_patch.py compares fixed-size chunks.
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(staging.rglob('*')):
            if not p.is_file():
                continue
            name = p.relative_to(staging).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            # Stream through the DEFLATE compressor in chunks rather than
            # loading the whole file into memory with read_bytes()/writestr().
            with p.open('rb') as src, z.open(info, 'w', force_zip64=True) as dest:
                shutil.copyfileobj(src, dest, length=_CHUNK)
    return output

def verify_abm(path: Path, *, require_bbox: bool = True) -> dict:
    required={'metadata.json','vector/index.json','vector/terrain.bin','map.sqlite'}
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist()); missing=sorted(required-names)
        for layer in ('roads','buildings','landuse','water','boundaries','places'):
            if not any(n.startswith(f'vector/{layer}/') and n.endswith('.bin') for n in names):
                missing.append(f'vector/{layer}/*.bin')
        bad=[n for n in names if any(x in n.lower() for x in FORBIDDEN)]
        if missing or bad: raise ValueError(f"Invalid ABM: missing={missing}, forbidden={bad}")
        meta=json.loads(z.read('metadata.json'))
        assert meta['tiles'] is False and meta['style']=='external'
        if require_bbox and not meta.get('bbox'):
            raise ValueError(f"Invalid ABM: {path} has no bbox in metadata.json "
                              f"(required for the release manifest / World Overview coverage check)")

        # The canonical map database contains search, POI and routing tables.
        # Validate all three in the same SQLite file so a build cannot publish
        # an archive with only one working subsystem.
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            with z.open('map.sqlite') as member:
                shutil.copyfileobj(member, tmp, length=_CHUNK)
            db_path = Path(tmp.name)
        try:
            db = sqlite3.connect(db_path)
            try:
                tables = {r[0] for r in db.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
                )}
                required_tables = {'features', 'search_fts', 'spatial', 'nodes', 'edges', 'turn_restrictions', 'places', 'poi'}
                missing_tables = required_tables - tables
                if missing_tables:
                    raise ValueError(f"Invalid ABM: map.sqlite missing tables/views: {sorted(missing_tables)}")
                nodes = int(db.execute('SELECT COUNT(*) FROM nodes').fetchone()[0])
                edges = int(db.execute('SELECT COUNT(*) FROM edges').fetchone()[0])
                features = int(db.execute('SELECT COUNT(*) FROM features').fetchone()[0])
                if nodes <= 0 or edges <= 0:
                    raise ValueError(
                        f"Invalid ABM: routing graph is empty (nodes={nodes}, edges={edges})"
                    )
                if features <= 0:
                    raise ValueError("Invalid ABM: map.sqlite contains no searchable features")
                # Ensure the FTS external-content index is queryable.
                db.execute("SELECT rowid FROM search_fts LIMIT 1").fetchone()
            finally:
                db.close()
        finally:
            db_path.unlink(missing_ok=True)

        return {"ok":True,"files":len(names),"metadata":meta}
