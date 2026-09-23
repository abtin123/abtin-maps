import random, sqlite3, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build_abm import _build_one
from extractors.loader import load
from packaging.create_abm import verify_abm
from search.map_db import search

SAMPLE = Path(__file__).resolve().parent.parent / "sample" / "us_mini.jsonl"


def _abm(tmp: Path) -> Path:
    out = tmp / "t.abm"
    _build_one(load(SAMPLE), "US", out, SAMPLE)
    return out


def test_build_verify_and_no_duplicates():
    with tempfile.TemporaryDirectory() as d:
        out = _abm(Path(d))
        verify_abm(out)  # also enforces unique names / segments
        z = zipfile.ZipFile(out)
        assert {"map.sqlite", "map.mbtiles", "metadata.json"} <= set(z.namelist())
        z.extractall(d)
        c = sqlite3.connect(Path(d) / "map.sqlite")
        two_way = c.execute("SELECT COUNT(*) FROM segments s JOIN way_data w USING(way_id) WHERE w.oneway=0").fetchone()[0]
        segs = c.execute("SELECT COUNT(*) FROM segments").fetchone()[0]
        assert c.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == segs + two_way
        assert search(Path(d) / "map.sqlite", "Broadway")
