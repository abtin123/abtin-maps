from __future__ import annotations
import sqlite3
from pathlib import Path
from abm_builder.core import norm_fa

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS places (id INTEGER PRIMARY KEY, name TEXT, name_fa TEXT, name_en TEXT, category TEXT, lat REAL, lon REAL, opening_hours TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(name, name_fa, name_en, category, content='places', content_rowid='id', tokenize='unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE IF NOT EXISTS spatial USING rtree(id, min_lon, max_lon, min_lat, max_lat);
"""

def create_search_db(path: Path, pois: list[dict], places: list[dict], roads: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path); con.executescript(SCHEMA)
    con.execute("DELETE FROM places"); con.execute("DELETE FROM spatial")
    rows=[]
    for p in pois:
        rows.append((int(p["id"]), p.get("name", ""), norm_fa(p.get("name_fa")), p.get("name_en", ""), p.get("category", "poi"), p["latitude"], p["longitude"], p.get("opening_hours", "")))
    for p in places:
        g=p.get("geometry", []); lat=sum(y for _,y in g)/len(g) if g else None; lon=sum(x for x,_ in g)/len(g) if g else None
        if lat is not None: rows.append((int(p["id"]), p.get("name", ""), norm_fa(p.get("name_fa")), p.get("name_en", ""), p.get("place_type", "place"), lat, lon, ""))
    for r in roads:
        g=r.get("geometry", []); 
        if g: rows.append((int(r["id"]), r.get("name", ""), norm_fa(r.get("name_fa")), r.get("name_en", ""), r.get("road_class", "road"), sum(y for _,y in g)/len(g), sum(x for x,_ in g)/len(g), ""))
    con.executemany("INSERT OR REPLACE INTO places VALUES (?,?,?,?,?,?,?,?)", rows)
    con.execute("INSERT INTO search_fts(search_fts) VALUES('rebuild')")
    con.executemany("INSERT OR REPLACE INTO spatial VALUES (?,?,?,?,?)", [(r[0],r[6],r[6],r[5],r[5]) for r in rows])
    con.commit(); con.close(); return len(rows)

def search(path: Path, query: str, limit=20):
    q=norm_fa(query).replace('"',' ')
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    rows=con.execute("SELECT p.*, bm25(search_fts) AS rank FROM search_fts JOIN places p ON p.id=search_fts.rowid WHERE search_fts MATCH ? ORDER BY rank LIMIT ?", (q+"*",limit)).fetchall(); con.close(); return [dict(r) for r in rows]
