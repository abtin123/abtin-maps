#!/usr/bin/env python3
"""Build the offline SQLite FTS5 index consumed by AbtinMaps."""
from __future__ import annotations
import argparse, sqlite3
from pathlib import Path
import osmium

class Handler(osmium.SimpleHandler):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__(); self.conn=conn; self.rows=[]; self.batch=2000
    def _add(self, obj):
        tags=obj.tags
        name=tags.get("name") or tags.get("name:fa") or tags.get("name:en")
        if not name: return
        region=tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:district") or tags.get("place") or tags.get("name:fa") or ""
        lat=lon=None
        if isinstance(obj, osmium.osm.Node):
            try: lat=float(obj.location.lat); lon=float(obj.location.lon)
            except Exception: return
        else:
            # Way centroids are intentionally omitted unless pyosmium provides a
            # location; named roads/places without coordinates are not useful to
            # the mobile search result. Nodes carry the useful POI/place points.
            try:
                loc=obj.nodes[0].location if obj.nodes else None
                if loc: lat=float(loc.lat); lon=float(loc.lon)
            except Exception: return
        self.rows.append((str(name),str(region),lat,lon))
        if len(self.rows)>=self.batch: self.conn.executemany('INSERT INTO places VALUES (?,?,?,?)',self.rows); self.conn.commit(); self.rows.clear()
    def node(self,n): self._add(n)
    def way(self,w): self._add(w)
    def flush(self):
        if self.rows: self.conn.executemany('INSERT INTO places VALUES (?,?,?,?)',self.rows); self.conn.commit(); self.rows.clear()

def main():
    p=argparse.ArgumentParser(); p.add_argument('--pbf',required=True,type=Path); p.add_argument('--output',required=True,type=Path); a=p.parse_args()
    if not a.pbf.is_file(): raise SystemExit(f'PBF not found: {a.pbf}')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.output.exists(): a.output.unlink()
    c=sqlite3.connect(a.output); c.execute('PRAGMA journal_mode=DELETE'); c.execute('PRAGMA synchronous=OFF')
    c.execute('CREATE TABLE places(name TEXT NOT NULL, region TEXT, latitude REAL NOT NULL, longitude REAL NOT NULL)')
    c.execute("CREATE VIRTUAL TABLE places_fts USING fts5(name,region,latitude UNINDEXED,longitude UNINDEXED, content='places', content_rowid='rowid', tokenize='unicode61 remove_diacritics 2')")
    h=Handler(c); h.apply_file(str(a.pbf), locations=True); h.flush()
    c.execute('INSERT INTO places_fts(rowid,name,region,latitude,longitude) SELECT rowid,name,region,latitude,longitude FROM places')
    c.execute('CREATE INDEX places_region_idx ON places(region)'); c.execute('PRAGMA optimize'); c.execute('VACUUM'); c.close()
    print(f'Built offline search index: {a.output} ({a.output.stat().st_size} bytes)')
if __name__=='__main__': main()
