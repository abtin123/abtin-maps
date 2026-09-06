#!/usr/bin/env python3
"""Pack one country/region as a single ABM container.

The PMTiles payload stays directly range-readable at the beginning of the
file. Routing graph remains seekable, while the large SQLite search index is
compressed inside the ABM and decompressed lazily by the app.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,os,struct,tempfile
from pathlib import Path
PM=b"PMTiles"; ABM=b"ABTINMAP"; HEAD=127
REQ={"styles/day.json","styles/night.json","search/places.sqlite","sprites/abtin.json","sprites/abtin.png","sprites/abtin@2x.json","sprites/abtin@2x.png","glyphs/Vazirmatn/0-255.pbf","glyphs/Vazirmatn/256-511.pbf","glyphs/Vazirmatn/1536-1791.pbf","glyphs/Vazirmatn/1792-2047.pbf","glyphs/Vazirmatn/8192-8447.pbf","glyphs/Vazirmatn/64256-64511.pbf","glyphs/Vazirmatn/64512-64767.pbf","glyphs/Vazirmatn/65024-65279.pbf","glyphs/Vazirmatn/65280-65535.pbf"}

def sha256(data): return hashlib.sha256(data).hexdigest()
def file_sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def read_range(h,o,n,label):
 h.seek(o); b=h.read(n)
 if len(b)!=n: raise SystemExit(f'PMTiles {label} is truncated')
 return b
def decode(data,c):
 if c==1:return data
 if c==2:return gzip.decompress(data)
 if c==3:
  import brotli; return brotli.decompress(data)
 if c==4:
  import zstandard; return zstandard.ZstdDecompressor().decompress(data)
 raise SystemExit(f'Unsupported PMTiles compression: {c}')
def encode(data,c):
 if c==1:return data
 if c==2:return gzip.compress(data,mtime=0)
 if c==3:
  import brotli; return brotli.compress(data)
 if c==4:
  import zstandard; return zstandard.ZstdCompressor(level=19).compress(data)
 raise SystemExit(f'Unsupported PMTiles compression: {c}')
def read_pmtiles(path):
 total=path.stat().st_size
 with path.open('rb') as h:
  head=bytearray(read_range(h,0,HEAD,'header'))
  if head[:7]!=PM or head[7]!=3: raise SystemExit(f'Input must be PMTiles v3: {path}')
  ro,rn=struct.unpack_from('<QQ',head,8); mo,mn=struct.unpack_from('<QQ',head,24); lo,ln=struct.unpack_from('<QQ',head,40); to,tn=struct.unpack_from('<QQ',head,56)
  for o,n,name in ((ro,rn,'root'),(mo,mn,'metadata'),(lo,ln,'leaf'),(to,tn,'tiles')):
   if o>total or n>total-o: raise SystemExit(f'PMTiles {name} range invalid')
  comp=head[97]
  metadata=json.loads(decode(read_range(h,mo,mn,'metadata'),comp).decode())
  return head,read_range(h,ro,rn,'root'),read_range(h,lo,ln,'leaf'),read_range(h,to,tn,'tiles'),metadata,comp

def normalize_style(path):
 s=json.loads(path.read_text(encoding='utf-8'))
 s.setdefault('metadata',{}).setdefault('abtin',{})['max_zoom']=16
 src=s.setdefault('sources',{}).setdefault('abtin',{})
 if isinstance(src,dict): src['minzoom']=2; src['maxzoom']=16
 return json.dumps(s,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()
def resource_arg(raw):
 if '=' not in raw: raise argparse.ArgumentTypeError('--resource must be INTERNAL_PATH=LOCAL_PATH')
 internal,local=raw.split('=',1); parts=internal.replace('\\','/').split('/')
 if not internal or internal.startswith('/') or any(x in ('','.','..') for x in parts): raise argparse.ArgumentTypeError(f'unsafe resource path: {internal}')
 return internal,Path(local)
def build(a):
 head,root,leaf,tiles,base_meta,comp=read_pmtiles(a.pmtiles)
 if not a.graph.is_file() or not a.graph.read_bytes().startswith(ABM): raise SystemExit(f'Graph must be a valid ABTINMAP segment: {a.graph}')
 if not a.search_index.is_file(): raise SystemExit(f'Search index is missing: {a.search_index}')
 resources={'styles/day.json':a.day_style,'styles/night.json':a.night_style}
 for raw in a.resource:
  k,v=resource_arg(raw); resources[k]=v
 missing=[k for k in REQ if k not in resources or not resources[k].is_file()]
 if missing: raise SystemExit('Missing required ABM resources: '+', '.join(sorted(missing)))
 graph=a.graph.read_bytes(); search_raw=a.search_index.read_bytes()
 try:
  import zstandard
  search=zstandard.ZstdCompressor(level=19,threads=1,write_checksum=True).compress(search_raw); search_codec='zstd'
 except Exception:
  search=gzip.compress(search_raw,compresslevel=9,mtime=0); search_codec='gzip'
 payloads=[('graph',graph,'none',len(graph)),('search/places.sqlite',search,search_codec,len(search_raw))]
 for name in sorted(REQ):
  if name=='search/places.sqlite': continue
  if name=='styles/day.json': payloads.append((name,normalize_style(resources[name]),'none',0))
  elif name=='styles/night.json': payloads.append((name,normalize_style(resources[name]),'none',0))
  else: payloads.append((name,resources[name].read_bytes(),'none',0))
 root_off=HEAD; leaf_off=root_off+len(root); tile_off=leaf_off+len(leaf); cursor=tile_off+len(tiles)
 graph_info=None; entries=[]
 for name,data,codec,raw_length in payloads:
  item={'offset':cursor,'length':len(data),'sha256':sha256(data),'codec':codec,'raw_length':raw_length or len(data)}
  if name=='graph': graph_info=item
  else: entries.append({'path':name,**item})
  cursor+=len(data)
 meta=dict(base_meta)
 meta['abtin_container']={'version':3,'region':a.region.upper(),'contracts':{'pmtiles_minzoom':2,'pmtiles_maxzoom':16,'app_overzoom_maxzoom':16,'offline_search':'search/places.sqlite','rendered_pois':True,'styles':'app_bundled'},'graph':graph_info,'entries':entries}
 encoded=encode(json.dumps(meta,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode(),comp); meta_off=cursor
 struct.pack_into('<QQ',head,8,root_off,len(root)); struct.pack_into('<QQ',head,24,meta_off,len(encoded)); struct.pack_into('<QQ',head,40,leaf_off,len(leaf))
 # IMPORTANT: tile_data_length covers only actual PMTiles tiles, not the ABM tail.
 struct.pack_into('<QQ',head,56,tile_off,len(tiles))
 a.output.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix='.'+a.output.name+'.',suffix='.part',dir=a.output.parent)
 try:
  with os.fdopen(fd,'wb') as out:
   out.write(head); out.write(root); out.write(leaf); out.write(tiles)
   for _,data,_,_ in payloads: out.write(data)
   out.write(encoded); out.flush(); os.fsync(out.fileno())
  os.replace(tmp,a.output)
 finally:
  if os.path.exists(tmp): os.unlink(tmp)
 print(json.dumps({'container':str(a.output),'bytes':a.output.stat().st_size,'sha256':file_sha256(a.output),'pmtiles_payload_bytes':len(tiles),'graph_payload_bytes':len(graph),'search_raw_bytes':len(search_raw),'search_stored_bytes':len(search)},ensure_ascii=False))
def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument('--region',required=True); p.add_argument('--pmtiles',type=Path,required=True); p.add_argument('--graph',type=Path,required=True); p.add_argument('--search-index',type=Path,required=True); p.add_argument('--day-style',type=Path,required=True); p.add_argument('--night-style',type=Path,required=True); p.add_argument('--resource',action='append',default=[],help='Deprecated compatibility option: INTERNAL_PATH=LOCAL_PATH'); p.add_argument('--output',type=Path,required=True); build(p.parse_args())
if __name__=='__main__': main()
