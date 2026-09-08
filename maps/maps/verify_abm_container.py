#!/usr/bin/env python3
"""Validate a v4 ABTINMAP data-only container."""
from __future__ import annotations
import argparse,gzip,hashlib,json,sqlite3,struct,tempfile
from pathlib import Path
PM=b'PMTiles'; ABM=b'ABTINMAP'; HEAD=127

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
  meta=json.loads(dec(read(h,mo,mn,'metadata'),head[97]).decode())
  if meta.get('format') not in (None,'pbf'): fail('PMTiles payload is not vector/PBF data')
  c=meta.get('abtin_container',{})
  if c.get('version')!=4: fail('abtin_container v4 missing')
  if c.get('region')!=str(c.get('region','')).upper(): fail('region invalid')
  if region and c.get('region')!=region.upper(): fail('wrong region')
  contract=c.get('contracts',{})
  if contract.get('container_data_only') is not True: fail('data-only contract missing')
  if contract.get('pmtiles_minzoom')!=2 or contract.get('pmtiles_maxzoom')!=16 or contract.get('app_overzoom_maxzoom')!=18: fail('zoom contract invalid')
  if contract.get('rendered_pois') is not False: fail('rendered POI flag must be false')
  ranges=[]
  go,gn,_=payload(h,size,c.get('graph'),'graph',ABM); ranges.append((go,gn,'graph'))
  entries=c.get('entries',[])
  if not isinstance(entries,list) or len(entries)!=1 or entries[0].get('path')!='search/places.sqlite': fail('data-only entries are invalid')
  e=entries[0]; o,n,b=payload(h,size,e,'entry search/places.sqlite'); ranges.append((o,n,'search/places.sqlite'))
  codec=e.get('codec','none'); raw=dec(b,4 if codec=='zstd' else 2) if codec in ('zstd','gzip') else b
  if e.get('raw_length')!=len(raw): fail('search raw length mismatch')
  search_check(raw)
  end=to+tn
  if any(o<end for o,n,name in ranges): fail('ABM tail overlaps PMTiles tile data')
  for i,(o,n,name) in enumerate(ranges):
   for oo,nn,oname in ranges[i+1:]:
    if o<oo+nn and oo<o+n: fail(name+' overlaps '+oname)
 return {'archive':str(path),'bytes':size,'region':c.get('region'),'entries':['search/places.sqlite'],'sha256':sha(path.read_bytes())}
def main():
 p=argparse.ArgumentParser(); p.add_argument('archive',type=Path); p.add_argument('--region'); a=p.parse_args(); print(json.dumps(verify(a.archive,a.region),ensure_ascii=False))
if __name__=='__main__': main()
