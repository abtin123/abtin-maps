#!/usr/bin/env python3
"""Strict ABTINMAP container validator used before a map can be released."""
from __future__ import annotations
import argparse, gzip, hashlib, json, sqlite3, struct, tempfile
from pathlib import Path
from typing import Any

PMTILES_MAGIC=b"PMTiles"; PMTILES_VERSION=3; PMTILES_HEADER_SIZE=127; ABM_MAGIC=b"ABTINMAP"
REQUIRED_ENTRIES={
"styles/day.json","styles/night.json","search/places.sqlite",
"sprites/abtin.json","sprites/abtin.png","sprites/abtin@2x.json","sprites/abtin@2x.png",
"glyphs/Vazirmatn/0-255.pbf","glyphs/Vazirmatn/256-511.pbf","glyphs/Vazirmatn/1536-1791.pbf","glyphs/Vazirmatn/1792-2047.pbf","glyphs/Vazirmatn/8192-8447.pbf","glyphs/Vazirmatn/64256-64511.pbf","glyphs/Vazirmatn/64512-64767.pbf","glyphs/Vazirmatn/65024-65279.pbf","glyphs/Vazirmatn/65280-65535.pbf"}
STYLE_ENTRIES={"styles/day.json","styles/night.json"}

def fail(m:str)->None: raise SystemExit(f"Invalid ABM container: {m}")
def exact(h:Any,o:int,n:int,label:str)->bytes:
 h.seek(o); d=h.read(n)
 if len(d)!=n: fail(f"{label} truncated")
 return d

def decode(d:bytes,c:int)->bytes:
 if c==1:return d
 if c==2:return gzip.decompress(d)
 if c==3:
  import brotli; return brotli.decompress(d)
 if c==4:
  import zstandard; return zstandard.ZstdDecompressor().decompress(d)
 fail(f"unsupported metadata compression {c}")

def digest(d:bytes)->str:return hashlib.sha256(d).hexdigest()
def fdigest(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def payload(h:Any,size:int,v:object,label:str,magic:bytes|None=None)->tuple[int,int,bytes]:
 if not isinstance(v,dict):fail(f"{label} is not object")
 o=v.get('offset'); n=v.get('length'); sh=v.get('sha256')
 if not isinstance(o,int) or o<0 or not isinstance(n,int) or n<=0:fail(f"{label} offset/length invalid")
 if not isinstance(sh,str) or len(sh)!=64:fail(f"{label} sha256 invalid")
 if o>size or n>size-o:fail(f"{label} outside archive")
 d=exact(h,o,n,label)
 if digest(d)!=sh.lower():fail(f"{label} checksum mismatch")
 if magic and not d.startswith(magic):fail(f"{label} magic mismatch")
 return o,n,d

def validate_style(raw:bytes,label:str)->None:
 try:s=json.loads(raw.decode())
 except Exception as e:fail(f"{label} JSON invalid: {e}")
 if not isinstance(s,dict):fail(f"{label} not object")
 src=s.get('sources',{}).get('abtin') if isinstance(s.get('sources'),dict) else None
 if not isinstance(src,dict) or src.get('minzoom')!=2 or src.get('maxzoom')!=20:fail(f"{label} must set source zoom range 2-20")
 layers=s.get('layers',[])
 by={x.get('id'):x for x in layers if isinstance(x,dict)}
 required={'road-labels-major':8,'road-labels-local':14,'buildings':14,'poi-symbols':12}
 for lid,z in required.items():
  if lid not in by:fail(f"{label} missing {lid}")
  if by[lid].get('minzoom')!=z:fail(f"{label} {lid} minzoom must be {z}")
 if '__ABTIN_PMTILES_URI__' not in raw.decode():fail(f"{label} missing PMTiles placeholder")

def validate_search(data:bytes)->int:
 with tempfile.NamedTemporaryFile(suffix='.sqlite') as f:
  f.write(data); f.flush(); db=sqlite3.connect(f.name)
  try:
   tables={r[0] for r in db.execute("select name from sqlite_master where type in ('table','view')")}
   if 'places_fts' not in tables:fail('search index missing places_fts')
   cols=[r[1] for r in db.execute("pragma table_info(places_fts)")]
   for c in ('name','region','latitude','longitude'):
    if c not in cols:fail(f'search index missing {c}')
   count=db.execute('select count(*) from places_fts').fetchone()[0]
   if count<=0:fail('offline search index is empty')
   db.execute("select name,region,latitude,longitude from places_fts limit 1").fetchone()
   return int(count)
  finally: db.close()

def verify(path:Path,region:str|None)->dict:
 if not path.is_file():fail(f"archive missing: {path}")
 size=path.stat().st_size
 with path.open('rb') as h:
  head=exact(h,0,127,'header')
  if head[:7]!=PMTILES_MAGIC or head[7]!=3:fail('not PMTiles v3')
  root_o,root_n=struct.unpack_from('<QQ',head,8); meta_o,meta_n=struct.unpack_from('<QQ',head,24); leaf_o,leaf_n=struct.unpack_from('<QQ',head,40); tile_o,tile_n=struct.unpack_from('<QQ',head,56)
  for o,n,l in ((root_o,root_n,'root'),(meta_o,meta_n,'metadata'),(leaf_o,leaf_n,'leaf'),(tile_o,tile_n,'tile')):
   if o>size or n>size-o:fail(f'{l} range invalid')
  if meta_o+meta_n!=size:fail('metadata must be final')
  try: meta=json.loads(decode(exact(h,meta_o,meta_n,'metadata'),head[97]).decode())
  except Exception as e:fail(f'metadata invalid: {e}')
  c=meta.get('abtin_container') if isinstance(meta,dict) else None
  if not isinstance(c,dict) or c.get('version')!=1:fail('abtin_container v1 missing')
  reg=c.get('region')
  if not isinstance(reg,str) or reg!=reg.upper() or not reg.replace('-','').isalnum():fail('region invalid')
  if region and reg!=region.upper():fail(f'region {reg} != {region.upper()}')
  go,gn,_=payload(h,size,c.get('graph'),'graph',ABM_MAGIC)
  entries=c.get('entries');
  if not isinstance(entries,list):fail('entries is not list')
  seen=set(); ranges=[(go,gn,'graph')]; search_count=0
  for e in entries:
   if not isinstance(e,dict):fail('entry not object')
   p=e.get('path')
   if not isinstance(p,str) or not p or p.startswith('/') or '..' in p.split('/') or p in seen:fail(f'invalid/duplicate entry {p}')
   seen.add(p); o,n,d=payload(h,size,e,f'entry {p}')
   if p in STYLE_ENTRIES:validate_style(d,p)
   if p=='search/places.sqlite':search_count=validate_search(d)
   ranges.append((o,n,p))
  missing=REQUIRED_ENTRIES-seen
  if missing:fail('missing required entries: '+', '.join(sorted(missing)))
  tile_end=tile_o+tile_n
  for o,n,l in ranges:
   if o<tile_o or o+n>tile_end:fail(f'{l} outside declared tile-data')
  for i,(o,n,l) in enumerate(ranges):
   for oo,nn,ll in ranges[i+1:]:
    if o<oo+nn and oo<o+n:fail(f'{l} overlaps {ll}')
 return {'archive':str(path),'bytes':size,'region':reg,'entries':sorted(seen),'search_rows':search_count,'graph_bytes':gn,'sha256':fdigest(path)}

def main():
 p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('--region');a=p.parse_args();print(json.dumps(verify(a.archive,a.region),ensure_ascii=False))
if __name__=='__main__':main()
