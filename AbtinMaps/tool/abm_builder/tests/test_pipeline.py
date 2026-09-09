from pathlib import Path
import json, zipfile
from build_abm import main
from search.create_search_db import search

SAMPLE = Path(__file__).resolve().parent.parent / 'sample'


def test_build_and_validate(tmp_path, monkeypatch):
    out = tmp_path / 'iran.abm'
    monkeypatch.setattr('sys.argv', ['build_abm.py', str(SAMPLE / 'mini_country.jsonl'), '--country', 'IR', '--output', str(out)])
    main()
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        assert 'metadata.json' in names
        assert not any(x.lower().endswith(('.pmtiles', '.mbtiles')) or 'tile' in x.lower() for x in names)
        assert 'vector/roads.bin' in names
        meta = json.loads(z.read('metadata.json'))
        assert meta['tiles'] is False
        # bbox is required by the app's release manifest / World Overview
        # coverage check - a build without it must not be considered valid.
        assert meta['bbox'] and len(meta['bbox']) == 4
        assert meta['region'] is None


def test_search_normalization(tmp_path):
    from search.create_search_db import create_search_db
    p = tmp_path / 'search.sqlite'
    create_search_db(p, [{'id': 1, 'name': '', 'name_fa': 'بیمارستان', 'name_en': 'Hospital', 'category': 'hospital', 'latitude': 35.7, 'longitude': 51.4}], [], [])
    assert search(p, 'بيمارستان')[0]['id'] == 1


def test_regional_split_is_geographic(tmp_path, monkeypatch):
    """A large-country build with --regions must clip by real geography, not
    just chop bytes: New York (Northeast) and Los Angeles (Southwest/West)
    must not both land in the same region archive."""
    out_dir = tmp_path / 'us_dist'
    monkeypatch.setattr('sys.argv', [
        'build_abm.py', str(SAMPLE / 'us_mini.jsonl'), '--country', 'US',
        '--regions', str(SAMPLE / 'regions' / 'US.json'), '--output', str(out_dir),
    ])
    main()
    assert (out_dir / 'US-NE.abm').exists()
    with zipfile.ZipFile(out_dir / 'US-NE.abm') as z:
        meta = json.loads(z.read('metadata.json'))
        assert meta['region']['code'] == 'US-NE'
        assert meta['region']['country_code'] == 'US'
        roads = z.read('vector/roads.bin')
    assert b'Interstate 10' not in roads  # LA's road must not leak into the NE archive
