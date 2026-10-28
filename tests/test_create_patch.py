import json, os, random, tempfile, unittest, zipfile
from pathlib import Path
from release_packaging.create_patch import create_patch, apply_patch, member_report, sha256

C = 64 * 1024


def make_abm(path: Path, tiles: bytes, db: bytes, meta: bytes, db_type=zipfile.ZIP_STORED):
    # same layout as create_abm.py: sorted names, mbtiles STORED, others DEFLATE, fixed dates
    with zipfile.ZipFile(path, 'w') as z:
        for name, data, ct in sorted([('X.mbtiles', tiles, zipfile.ZIP_STORED),
                                      ('X.sqlite', db, db_type),
                                      ('metadata.json', meta, zipfile.ZIP_DEFLATED)]):
            zi = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0)); zi.compress_type = ct
            with z.open(zi, 'w', force_zip64=True) as d:
                d.write(data)


class PatchTest(unittest.TestCase):
    def roundtrip(self, base_args, target_args):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); rnd = random.Random(1)
            make_abm(d / 'a.abm', *base_args(rnd)); rnd = random.Random(1)
            make_abm(d / 'b.abm', *target_args(rnd))
            mpath, ppath = create_patch(d / 'a.abm', d / 'b.abm', 'X', d / 'out', C)
            m = json.loads(mpath.read_text())
            apply_patch(d / 'a.abm', m, ppath, d / 'r.abm')
            self.assertEqual(sha256(d / 'r.abm'), sha256(d / 'b.abm'))
            return m, ppath.stat().st_size, (d / 'b.abm').stat().st_size

    def test_same_size_change_stays_v1(self):
        def base(r): return os.urandom(0) + r.randbytes(C * 20), r.randbytes(C * 10), b'{"a":1}'
        def tgt(r):
            t, db, _ = base(r); t = bytearray(t); t[C * 5] ^= 1
            return bytes(t), db, b'{"a":2}'
        m, p, full = self.roundtrip(base, tgt)
        self.assertEqual(m['schema'], 'ABTINMAP-CHUNK-PATCH/1'); self.assertLess(p, full / 5)

    def test_growing_tiles_does_not_ruin_patch(self):
        def base(r): return r.randbytes(C * 20), r.randbytes(C * 10), b'{"a":1}'
        def tgt(r):
            t, db, _ = base(r)
            return t + b'extra-tiles-bytes', db, b'{"a":2}'   # shifts everything after mbtiles
        m, p, full = self.roundtrip(base, tgt)
        self.assertEqual(m['schema'], 'ABTINMAP-CHUNK-PATCH/2'); self.assertLess(p, full / 5)

    def test_member_report_shows_deflated_sqlite_is_not_reusable(self):
        # Production layout: mbtiles STORED, sqlite DEFLATE. One changed byte early in the sqlite
        # re-encodes the whole DEFLATE member, so nothing of it can be reused, while the STORED
        # mbtiles is fully reused.
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); r = random.Random(3)
            tiles = r.randbytes(C * 8)
            db = bytes(r.choice(b'abcdefgh') for _ in range(C * 6))
            make_abm(d / 'a.abm', tiles, db, b'{}', zipfile.ZIP_DEFLATED)
            db2 = bytearray(db); db2[10] ^= 1
            make_abm(d / 'b.abm', tiles, bytes(db2), b'{}', zipfile.ZIP_DEFLATED)
            rep = {m['name']: m for m in member_report(d / 'a.abm', d / 'b.abm', C)}
            self.assertEqual(rep['X.mbtiles']['reused_ratio'], 1.0)
            self.assertLess(rep['X.sqlite']['reused_ratio'], 0.1)
            mpath, ppath = create_patch(d / 'a.abm', d / 'b.abm', 'X', d / 'out', C)
            apply_patch(d / 'a.abm', json.loads(mpath.read_text()), ppath, d / 'r.abm')
            self.assertEqual(sha256(d / 'r.abm'), sha256(d / 'b.abm'))


if __name__ == '__main__':
    unittest.main()
