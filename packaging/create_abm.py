from __future__ import annotations
import hashlib, json, zipfile
from pathlib import Path

FORBIDDEN=({'tile','tiles','pmtiles','mbtiles','style.json','render_cache'})

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
        "version": 2,
        "tiles": False,
        "style": "external",
        "renderer": "app",
        "search": True,
        "routing": True,
        "source": source.name,
        "bbox": list(bbox) if bbox is not None else None,
        "region": region,
        "stats": stats,
    }
    (staging/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    files=[p for p in staging.rglob('*') if p.is_file() and p.name not in {'manifest.json'}]
    manifest={"format":"ABM","files":{str(p.relative_to(staging)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (staging/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(staging.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(staging).as_posix())
    return output

def verify_abm(path: Path, *, require_bbox: bool = True) -> dict:
    required={'metadata.json','vector/roads.bin','vector/buildings.bin','vector/landuse.bin','vector/water.bin','vector/boundaries.bin','vector/places.bin','vector/terrain.bin','poi/poi.sqlite','search/search.sqlite','routing/graph.bin'}
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist()); missing=sorted(required-names)
        bad=[n for n in names if any(x in n.lower() for x in FORBIDDEN)]
        if missing or bad: raise ValueError(f"Invalid ABM: missing={missing}, forbidden={bad}")
        meta=json.loads(z.read('metadata.json'))
        assert meta['tiles'] is False and meta['style']=='external'
        if require_bbox and not meta.get('bbox'):
            raise ValueError(f"Invalid ABM: {path} has no bbox in metadata.json "
                              f"(required for the release manifest / World Overview coverage check)")
        return {"ok":True,"files":len(names),"metadata":meta}
