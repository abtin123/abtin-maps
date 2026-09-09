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


def test_search_keeps_colliding_osm_ids(tmp_path):
    from search.create_search_db import create_search_db
    p = tmp_path / 'search.sqlite'
    create_search_db(
        p,
        [{'id': 1, 'name': 'Hospital', 'name_fa': '', 'name_en': '', 'category': 'hospital',
          'latitude': 35.7, 'longitude': 51.4}],
        [],
        [{'id': 1, 'name': 'Main Road', 'name_fa': '', 'name_en': '', 'road_class': 'primary',
          'geometry': [(51.4, 35.7), (51.5, 35.8)]}],
    )
    rows = search(p, 'Hospital', limit=10)
    assert rows and rows[0]['name'] == 'Hospital'
    import sqlite3
    con = sqlite3.connect(p)
    assert con.execute('select count(*) from places').fetchone()[0] == 2
    con.close()


def test_routing_restrictions_use_relation_members(tmp_path):
    from routing.graph_builder import build_graph
    class Obj: pass
    rel = {'id': 99, 'tags': {'type': 'restriction', 'restriction': 'no_left_turn'},
           'members': [{'type': 'w', 'ref': 10, 'role': 'from'},
                       {'type': 'n', 'ref': 20, 'role': 'via'},
                       {'type': 'w', 'ref': 30, 'role': 'to'}]}
    out = tmp_path / 'graph.bin'
    stats = build_graph([], [rel], out)
    assert stats['turn_restrictions'] == 1
    raw = out.read_bytes()
    assert b'10' in raw and b'30' in raw


def test_routing_graph_is_disk_backed_and_preserves_format(tmp_path):
    from routing.graph_builder import build_graph
    ways = [
        {'id': 10, 'geometry': [(51.0, 35.0), (51.01, 35.01), (51.02, 35.02)],
         'node_ids': [100, 101, 102],
         'tags': {'highway': 'primary', 'maxspeed': '80', 'oneway': 'no'}},
    ]
    out = tmp_path / 'graph.bin'
    stats = build_graph(ways, [], out)
    assert stats['nodes'] == 3
    assert stats['edges'] == 4
    raw = out.read_bytes()
    assert raw.startswith(b'ABMGRAPH1\n')
    size = int.from_bytes(raw[10:14], 'big')
    payload = raw[14:14 + size]
    data = __import__('json').loads(payload)
    assert len(data['nodes']) == 3
    assert len(data['edges']) == 4
