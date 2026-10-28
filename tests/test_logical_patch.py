"""Logical patch: built from REAL builder output (two consecutive builds of a synthetic region),
because the whole point is the production layout (sequential ids, DEFLATE sqlite, dedup'd tiles)."""
import gzip, hashlib, json, random, sqlite3, sys, tempfile, zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build_abm import _build_one
from extractors.loader import load
from release_packaging.create_abm import verify_abm
from release_packaging.create_patch import create_patch
from release_packaging.logical_patch import (
    SCHEMA, apply_logical_patch, content_digest, create_logical_patch, extract_stores,
)
from search.map_db import search

NAMES = ['خیابان', 'کوچه', 'بلوار', 'میدان']
CATS = ['restaurant', 'cafe', 'pharmacy', 'hospital', 'school', 'fuel', 'bank', 'shop']


def _h(*k) -> random.Random:
    return random.Random(int(hashlib.md5(repr(k).encode()).hexdigest()[:12], 16))


def make_jsonl(path: Path, G: int = 24, variant: int = 0) -> None:
    """variant 0 = base. Higher variants add/remove/rename/reclassify ~1% of the objects.
    Every random choice is keyed by object, so unrelated objects never change."""
    ch = lambda *k: _h('churn', variant, *k).random() if variant else 1.0
    lat0, lon0, d = 35.60, 51.20, 0.004
    nid = lambda i, j: 1000000 + i * (G + 1) + j
    out = []
    for i in range(G + 1):
        for j in range(G + 1):
            out.append({"kind": "node", "id": nid(i, j), "lat": lat0 + i * d, "lon": lon0 + j * d, "tags": {}})
    wid = 5000
    for horizontal in (True, False):
        for i in range(G + 1):
            for j in range(G):
                wid += 1
                r = ch('way', wid)
                if r < 0.01:
                    continue                                        # removed way
                a, b = (nid(i, j), nid(i, j + 1)) if horizontal else (nid(j, i), nid(j + 1, i))
                pts = [[lon0 + (j if horizontal else i) * d, lat0 + (i if horizontal else j) * d],
                       [lon0 + ((j + 1) if horizontal else i) * d, lat0 + (i if horizontal else (j + 1)) * d]]
                hw = _h('hw', wid).choice(['residential', 'tertiary', 'secondary'])
                if 0.01 <= r < 0.02:
                    hw = 'primary'                                   # reclassified way
                nm = f"{NAMES[(i + j) % 4]} {i % 17}-{j % 7}"
                if 0.02 <= r < 0.03:
                    nm += ' جدید'                                    # renamed way
                tags = {"highway": hw, "name": nm, "name:fa": nm, "name:en": f"Street {i % 17}-{j % 7}"}
                if 0.03 <= r < 0.04:
                    tags["maxspeed"] = "30"
                out.append({"kind": "way", "id": wid, "node_ids": [a, b], "geometry": pts, "tags": tags})
    # long ways (> PIECE segments => several road_index pieces) and roundabouts
    for L in range(6):
        wid += 1
        r = ch('long', L)
        if r < 0.15:
            continue
        pts_n = [[lon0 + c * d / 2, lat0 + (G + 2 + L) * d + (d / 9 if (variant and c == 11 and r < 0.5) else 0)]
                 for c in range(21)]
        out.append({"kind": "way", "id": wid, "node_ids": [2000000 + L * 100 + c for c in range(21)],
                    "geometry": pts_n, "tags": {"highway": "secondary", "name": f"بزرگراه {L}",
                                                "name:fa": f"بزرگراه {L}", "name:en": f"Highway {L}"}})
    for R in range(4):
        wid += 1
        if ch('rb', R) < 0.2:
            continue
        cx, cy = lon0 + (3 + R * 5) * d, lat0 + (G + 12) * d
        ring = [[cx + 0.0005 * m1, cy + 0.0005 * m2] for m1, m2 in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 0))]
        out.append({"kind": "way", "id": wid, "node_ids": [3000000 + R * 10 + c for c in (0, 1, 2, 3, 0)],
                    "geometry": ring, "tags": {"highway": "residential", "junction": "roundabout"}})
    pid = 9000000
    for k in range(G * G):
        pid += 1
        r = ch('poi', k)
        if r < 0.01:
            continue
        nm = f"مکان {k}" + (' نو' if 0.01 <= r < 0.02 else '')
        out.append({"kind": "node", "id": pid,
                    "lat": lat0 + _h('la', k).random() * G * d, "lon": lon0 + _h('lo', k).random() * G * d,
                    "tags": {"amenity": CATS[k % 8], "name": nm, "name:fa": nm, "name:en": f"Place {k}"}})
    if variant:
        for k in range(max(3, G * G // 80)):
            pid += 1
            out.append({"kind": "node", "id": pid, "lat": lat0 + _h('nla', variant, k).random() * G * d,
                        "lon": lon0 + _h('nlo', variant, k).random() * G * d,
                        "tags": {"amenity": "cafe", "name": f"تازه {variant}-{k}",
                                 "name:fa": f"تازه {variant}-{k}", "name:en": f"Fresh {variant}-{k}"}})
    with path.open('w', encoding='utf-8') as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')


@pytest.fixture(scope='module')
def abms():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        built = {}
        for v in (0, 1, 2):
            src = d / f'v{v}.jsonl'
            make_jsonl(src, variant=v)
            out = d / f'v{v}' / 'XX.abm'
            out.parent.mkdir()
            _build_one(load(src), 'XX', out, src)
            built[v] = out
        yield built


def test_logical_patch_roundtrip_and_size(abms):
    base, target = abms[0], abms[1]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        mpath, ppath = create_logical_patch(base, target, 'XX', d / 'p')
        manifest = json.loads(mpath.read_text())
        assert manifest['schema'] == SCHEMA
        (d / 'r').mkdir()
        apply_logical_patch(base, manifest, ppath, d / 'r' / 'XX.abm')
        verify_abm(d / 'r' / 'XX.abm')                                     # same validator as the builder
        with tempfile.TemporaryDirectory() as t:
            got = extract_stores(d / 'r' / 'XX.abm', Path(t) / 'g')
            want = extract_stores(target, Path(t) / 'w')
            assert content_digest(got['sqlite'], got['mbtiles'])[0] == manifest['target_digest']
            assert content_digest(want['sqlite'], want['mbtiles'])[0] == manifest['target_digest']
            con = sqlite3.connect(got['sqlite'])
            assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            # runtime contract: road_index piece -> contiguous segment id range, resolved by key
            q = ('SELECT s.way_id, s.a, s.b, s.dist_dm, r.min_lon, r.max_lon, r.min_lat, r.max_lat '
                 'FROM road_index r JOIN segments s ON s.id BETWEEN r.seg_from AND r.seg_to')
            assert sorted(con.execute(q)) == sorted(sqlite3.connect(want['sqlite']).execute(q))
            assert con.execute('SELECT COUNT(*) FROM road_index r WHERE r.id <> r.seg_from').fetchone()[0] == 0
            multi = con.execute('SELECT COUNT(*) FROM (SELECT way_id FROM road_index r JOIN segments s '
                                'ON s.id = r.seg_from GROUP BY way_id HAVING COUNT(*) > 1)').fetchone()[0]
            assert multi >= 1, 'fixture must contain multi-piece ways'
            assert con.execute("SELECT COUNT(*) FROM roundabout_info").fetchone()[0] >= 1
            # search must behave exactly like on a fresh build (FTS / names maintained)
            for q in ('مکان 5', 'مکان 1', 'تازه', 'نو', 'خیابان 3', 'جدید'):
                a = [(r['id'], r['name'], r['category']) for r in search(got['sqlite'], q, limit=50)]
                b = [(r['id'], r['name'], r['category']) for r in search(want['sqlite'], q, limit=50)]
                assert sorted(a) == sorted(b), q
        # the whole point: far smaller than the full file, and than the old byte patch
        full = target.stat().st_size
        _, old_patch = create_patch(base, target, 'XX', d / 'old')
        assert ppath.stat().st_size < full * 0.5, (ppath.stat().st_size, full)
        assert ppath.stat().st_size < old_patch.stat().st_size * 0.5


def test_patch_chain_and_unchanged(abms):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        m1, p1 = create_logical_patch(abms[0], abms[1], 'XX', d / 'p1')
        (d / 'a1').mkdir(); (d / 'a2').mkdir()
        apply_logical_patch(abms[0], json.loads(m1.read_text()), p1, d / 'a1' / 'XX.abm')
        # second hop starts from the *patched* archive, not from a pristine build
        m2, p2 = create_logical_patch(d / 'a1' / 'XX.abm', abms[2], 'XX', d / 'p2')
        apply_logical_patch(d / 'a1' / 'XX.abm', json.loads(m2.read_text()), p2, d / 'a2' / 'XX.abm')
        verify_abm(d / 'a2' / 'XX.abm')
        m3, p3 = create_logical_patch(abms[2], abms[2], 'XX', d / 'p3')
        lines = [json.loads(l) for l in gzip.open(p3, 'rt', encoding='utf-8')]
        assert [l['k'] for l in lines] == ['hdr', 'members', 'end']      # nothing changed


def test_corrupt_patch_is_rejected(abms):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        m, p = create_logical_patch(abms[0], abms[1], 'XX', d / 'p')
        manifest = json.loads(m.read_text())
        lines = [json.loads(l) for l in gzip.open(p, 'rt', encoding='utf-8')]
        for l in lines:                                              # tamper with one put row
            if l['k'] == 'put' and l['t'] == 'way_data':
                l['rows'][0][8] += 1
                break
        else:
            pytest.fail('expected a way_data put')
        bad = d / 'bad.bin'
        with gzip.open(bad, 'wt', encoding='utf-8') as f:
            for l in lines:
                f.write(json.dumps(l, ensure_ascii=False) + '\n')
        with pytest.raises(ValueError, match='digest'):
            apply_logical_patch(abms[0], manifest, bad, d / 'r.abm')


def test_prepare_release_picks_logical_patch(abms):
    from release_packaging.prepare_release import build_candidates
    with tempfile.TemporaryDirectory() as d:
        found = build_candidates(abms[0], abms[1], 'XX', Path(d))
        kinds = [k for _, k, _ in found]
        assert kinds[0] == 'logical' and 'chunk' in kinds
        desc = json.loads((found[0][2] / 'patch-descriptor.json').read_text())
        assert desc['manifest_file'] == 'XX.abmpatch.json' and desc['bin_file'] == 'XX.abmpatch.bin'
        assert json.loads((found[0][2] / desc['manifest_file']).read_text())['schema'] == SCHEMA
