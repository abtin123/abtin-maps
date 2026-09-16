#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, tempfile, gc
from pathlib import Path
from abm_builder.core import setup_logging, write_records, write_spatial_chunks, records_bbox, LOG
from extractors.loader import load, clip_dataset
from extractors.osm import roads, buildings, landuse, water, boundaries, places, pois
from search.create_search_db import create_search_db
from routing.graph_builder import build_graph, build_graph_from_pbf
from packaging.create_abm import create_abm, verify_abm

VECTOR_NAMES = ('roads.bin', 'buildings.bin', 'landuse.bin', 'water.bin', 'boundaries.bin', 'places.bin')


def _build_one(dataset, country: str, output: Path, source: Path, region: dict | None = None) -> Path:
    """Run the full extract -> search -> routing -> package pipeline once,
    against whichever dataset is handed in (the whole country, or one
    already clipped to a region's bbox). This is the single code path used
    both for ordinary countries and for each part of a geographically split
    large country, so region builds get exactly the same validation
    (bbox, no-tile-files check, required-file check) as a normal build.
    """
    work = Path(tempfile.mkdtemp(prefix='abm-build-'))
    try:
        LOG.info('[1/5] Extracting vector features for %s', region['code'] if region else country)
        # Do not materialize all seven extracted layers simultaneously.  On a
        # country-sized PBF that duplicates a large amount of geometry while
        # the source Dataset is already resident in RAM.  Process one layer at
        # a time and immediately release its records.
        extractors = {
            'roads.bin': roads(dataset.ways),
            'buildings.bin': buildings(dataset.ways),
            'landuse.bin': landuse(dataset.ways),
            'water.bin': water(dataset.ways),
            'boundaries.bin': boundaries(dataset.ways, dataset.relations),
            'places.bin': places(dataset.nodes, dataset.ways),
        }
        vector_index = {"version": 1, "layers": {}, "chunk_size": 768}
        stats = {}
        for name, records in extractors.items():
            layer = name[:-4]
            layer_index = write_spatial_chunks(work / 'vector', layer, records, chunk_size=768)
            vector_index['layers'][layer] = layer_index
            stats[name] = int(layer_index.get('count', 0))
            gc.collect()
        # terrain remains an empty ABM stream when no DEM is supplied.
        write_records(work / 'vector' / 'terrain.bin', [])
        (work / 'vector' / 'index.json').write_text(
            json.dumps(vector_index, ensure_ascii=False, separators=(",", ":")) + '\n',
            encoding='utf-8',
        )

        # Derive the published bbox from chunk indexes instead of retaining
        # every extracted record just to calculate it.
        boxes = [
            tuple(c['bbox'])
            for li in vector_index['layers'].values()
            for c in li.get('chunks', [])
            if c.get('count', 0) > 0
        ]
        bbox = None
        if boxes:
            bbox = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                    max(b[2] for b in boxes), max(b[3] for b in boxes))
        if region is not None:
            # A region archive's published bbox is the region's own
            # configured bbox (used for coverage/World-Overview checks),
            # not just the bounding box of whatever geometry happened to be
            # clipped into it - those can differ slightly at the edges.
            bbox = tuple(region['bbox'])

        LOG.info('[2/5] Building POI and FTS5/RTree databases')
        # Search/POI inputs are also generated one at a time.  This keeps the
        # peak heap bounded by the source Dataset plus one extracted layer.
        poi_data = list(pois(dataset.nodes, dataset.ways))
        place_data = list(places(dataset.nodes, dataset.ways))
        road_data = list(roads(dataset.ways))
        stats['poi'] = len(poi_data)
        create_search_db(work / 'search' / 'search.sqlite', poi_data, place_data, road_data)
        create_search_db(work / 'poi' / 'poi.sqlite', poi_data, [], [])
        del poi_data, place_data, road_data, extractors
        gc.collect()

        LOG.info('[3/5] Building routing graph')
        # Prefer the streamed PBF graph so normal country builds keep the low
        # memory profile.  Some PBF extracts can expose highway ways without
        # usable per-node locations to a second osmium pass; in that case the
        # streamed builder can legitimately produce an empty graph even though
        # the first extraction pass already proved that routable roads exist.
        # Keep the materialized Dataset until routing finishes and fall back to
        # it only when the streamed graph is empty.  This prevents publishing a
        # visually valid ABM whose offline routing database has 0 nodes/edges.
        if source.suffix.lower() not in {'.jsonl', '.json'}:
            graph_stats = build_graph_from_pbf(
                source, work / 'routing' / 'graph.sqlite', bbox=bbox
            )
            if graph_stats.get('nodes', 0) <= 0 or graph_stats.get('edges', 0) <= 0:
                LOG.warning(
                    'Streamed PBF routing graph is empty; falling back to the already-loaded '
                    'road dataset (ways=%d) for a reliable graph build', len(dataset.ways)
                )
                graph_stats = build_graph(
                    dataset.ways, dataset.relations, work / 'routing' / 'graph.sqlite'
                )
            del dataset
            gc.collect()
        else:
            graph_stats = build_graph(dataset.ways, dataset.relations, work / 'routing' / 'graph.sqlite')

        LOG.info('[4/5] Packaging and validating ABM: %s', output)
        stats['routing'] = graph_stats
        create_abm(work, output, country, source, stats, bbox, region)
        result = verify_abm(output)
        LOG.info('[5/5] ABM ready: %s (%d files)', output, result['files'])
        return output
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _load_regions_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding='utf-8'))
    if 'regions' not in cfg or not cfg['regions']:
        raise SystemExit(f'--regions config {path} has no "regions" list')
    for r in cfg['regions']:
        for key in ('code', 'name_fa', 'name_en', 'bbox'):
            if key not in r:
                raise SystemExit(f'--regions config {path}: region entry missing "{key}": {r}')
        if len(r['bbox']) != 4:
            raise SystemExit(f'--regions config {path}: region {r["code"]} bbox must be [minlon,minlat,maxlon,maxlat]')
        try:
            minlon, minlat, maxlon, maxlat = map(float, r['bbox'])
        except (TypeError, ValueError):
            raise SystemExit(f'--regions config {path}: region {r["code"]} bbox must contain numbers')
        if not (-180 <= minlon <= maxlon <= 180 and -90 <= minlat <= maxlat <= 90):
            raise SystemExit(f'--regions config {path}: invalid bbox for {r["code"]}: {r["bbox"]}')
    return cfg


def main():
    ap = argparse.ArgumentParser(description='Build a tile-free Abtin Maps ABM country archive')
    ap.add_argument('input', type=Path, help='OSM .pbf or test .jsonl input')
    ap.add_argument('-o', '--output', type=Path, required=True,
                     help='Output .abm file (whole-country build), or output '
                          'directory when --regions is given')
    ap.add_argument('--country', required=True, help='ISO-3166 alpha-2 country code')
    ap.add_argument('--regions', type=Path, default=None,
                     help='Optional JSON config splitting a large country into real '
                          'geographic regions (bbox-clipped), instead of one whole-country '
                          '.abm. See sample/regions/US.json for the format. This is '
                          'independent from packaging/split_abm.py, which only exists to '
                          'chop an already-built .abm into byte-sized parts for hosting '
                          'limits and knows nothing about geography.')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()
    setup_logging(args.verbose)

    if args.regions is None:
        LOG.info('Loading OSM input: %s', args.input)
        data = load(args.input)

        if args.output.suffix.lower() != '.abm':
            raise SystemExit('Output must end with .abm (use --regions for a multi-file, per-region build)')
        try:
            _build_one(data, args.country, args.output, args.input)
        except Exception:
            LOG.exception('ABM build failed')
            raise
        return

    cfg = _load_regions_config(args.regions)
    args.output.mkdir(parents=True, exist_ok=True)
    built = []
    # For PBF input, load each region directly from the stream.  Never
    # materialize a whole-country PBF before clipping: large extracts can
    # otherwise exhaust the GitHub runner's RAM.
    is_pbf = args.input.suffix.lower() not in {'.jsonl', '.json'}
    data = None if is_pbf else load(args.input)
    try:
        for region_def in cfg['regions']:
            code = region_def['code']
            LOG.info('--- Region %s (%s) ---', code, region_def['name_en'])
            bbox = tuple(float(x) for x in region_def['bbox'])
            clipped = load(args.input, bbox=bbox) if is_pbf else clip_dataset(data, bbox)
            if not clipped.ways and not clipped.nodes:
                LOG.warning('Region %s has no data in %s - skipping (check bbox / input coverage)', code, args.input)
                continue
            out_path = args.output / f'{code}.abm'
            region_meta = {
                'code': code,
                'name_fa': region_def['name_fa'],
                'name_en': region_def['name_en'],
                'bbox': region_def['bbox'],
                'country_code': args.country.upper(),
                'country_name_fa': cfg.get('country_name_fa', ''),
                'country_name_en': cfg.get('country_name_en', ''),
            }
            _build_one(clipped, args.country, out_path, args.input, region=region_meta)
            built.append(code)
        LOG.info('Built %d region archives in %s: %s', len(built), args.output, ', '.join(built))
        if not built:
            raise SystemExit(f'No region in {args.regions} matched any data in {args.input}')
    except Exception:
        LOG.exception('Regional ABM build failed')
        raise


if __name__ == '__main__':
    main()
