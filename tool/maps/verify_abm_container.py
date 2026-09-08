#!/usr/bin/env python3
"""Validate a v3 ABM without treating its custom tail as PMTiles tile data."""
from __future__ import annotations
import argparse,gzip,hashlib,json,sqlite3,struct,tempfile
from pathlib import Path
PM=b'PMTiles'; ABM=b'ABTINMAP'; HEAD=127
REQ={"search/places.sqlite"}
def fail(s): raise SystemExit('Invalid ABM container: '+s)
def read(h,o,n,label):
 h.seek(o); b=h.read(n)
 if len(b)!=n: fail(label+' truncated')
 return b
def dec(b,c):
 if c==1:return b
 if c==2:return gzip.decompress(b)
 if c==3:
  import brotli; return brotli.decompress(b)
 if c==4:
  import zstandard; return zstandard.ZstdDecompressor().decompress(b)
 fail('unsupported compression')
def sha(b): return hashlib.sha256(b).hexdigest()
def payload(h,size,obj,label,magic=None):
 if not isinstance(obj,dict): fail(label+' metadata missing')
 o,n,s=obj.get('offset'),obj.get('length'),obj.get('sha256')
 if not isinstance(o,int) or not isinstance(n,int) or n<=0 or o<0 or o+n>size: fail(label+' range invalid')
 b=read(h,o,n,label)
 if not isinstance(s,str) or sha(b)!=s.lower(): fail(label+' checksum mismatch')
 if magic and not b.startswith(magic): fail(label+' magic mismatch')
 return o,n,b
def style_check(b,label):
 try:s=json.loads(b.decode())
 except Exception as e: fail(label+' JSON invalid: '+str(e))
 src=s.get('sources',{}).get('abtin',{}); meta=s.get('metadata',{}).get('abtin',{})
 if src.get('minzoom')!=2 or src.get('maxzoom')!=16 or meta.get('max_zoom')!=16: fail(label+' zoom must be 2-16')
def search_check(b):
 with tempfile.NamedTemporaryFile(suffix='.sqlite') as f:
  f.write(b); f.flush(); db=sqlite3.connect(f.name)
  try:
   if not db.execute("select count(*) from sqlite_master where name='places_fts'").fetchone()[0]: fail('search index missing places_fts')
   if db.execute('select count(*) from places_fts').fetchone()[0]<=0: fail('offline search index empty')
  finally: db.close()
def verify(path,region):
 size=path.stat().st_size
 with path.open('rb') as h:
  head=read(h,0,HEAD,'header')
  if head[:7]!=PM or head[7]!=3: fail('not PMTiles v3')
  ro,rn=struct.unpack_from('<QQ',head,8); mo,mn=struct.unpack_from('<QQ',head,24); lo,ln=struct.unpack_from('<QQ',head,40); to,tn=struct.unpack_from('<QQ',head,56)
  for o,n,name in ((ro,rn,'root'),(mo,mn,'metadata'),(lo,ln,'leaf'),(to,tn,'tiles')):
   if o>size or n>size-o: fail(name+' range invalid')
  if to+tn>size: fail('tile data range invalid')
  meta=json.loads(dec(read(h,mo,mn,'metadata'),head[97]).decode())
  c=meta.get('abtin_container',{})
  if c.get('version')!=4: fail('abtin_container v3 missing')
  if c.get('region')!=str(c.get('region','')).upper(): fail('region invalid')
  if region and c.get('region')!=region.upper(): fail('wrong region')
  contract=c.get('contracts',{})
  if contract.get('pmtiles_minzoom')!=2 or contract.get('pmtiles_maxzoom')!=16 or contract.get('app_overzoom_maxzoom')!=20: fail('zoom contract must be tile-pyramid 2-16 with app overzoom to 20')
  ranges=[]
  go,gn,_=payload(h,size,c.get('graph'),'graph',ABM); ranges.append((go,gn,'graph'))
  seen=set()
  for e in c.get('entries',[]):
   p=e.get('path')
   if not isinstance(p,str) or p in seen or p not in REQ: fail('invalid entry '+str(p))
   seen.add(p); o,n,b=payload(h,size,e,'entry '+p); ranges.append((o,n,p))
   codec=e.get('codec','none')
   if codec in ('zstd','gzip'):
    raw=dec(b,4 if codec=='zstd' else 2)
    if e.get('raw_length')!=len(raw): fail(p+' raw length mismatch')
    if p=='search/places.sqlite': search_check(raw)
   elif p=='search/places.sqlite': search_check(b)
   if p.startswith('styles/') or p.startswith('sprites/') or p.startswith('glyphs/'): fail('renderer asset must not be embedded: '+p)
  if seen!=REQ: fail('required entries missing')
  # Custom graph/search/resource tail begins after PMTiles tile data.
  end=to+tn
  if any(o<end for o,n,name in ranges): fail('ABM tail overlaps PMTiles tile data')
  for i,(o,n,name) in enumerate(ranges):
   for oo,nn,oname in ranges[i+1:]:
    if o<oo+nn and oo<o+n: fail(name+' overlaps '+oname)
 return {'archive':str(path),'bytes':size,'region':c.get('region'),'entries':sorted(seen),'sha256':sha(path.read_bytes())}
def main():
 p=argparse.ArgumentParser(); p.add_argument('archive',type=Path); p.add_argument('--region'); a=p.parse_args(); print(json.dumps(verify(a.archive,a.region),ensure_ascii=False))
if __name__=='__main__': main()
