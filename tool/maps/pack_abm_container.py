#!/usr/bin/env python3
"""Pack a country map as a PMTiles v3 ABM container."""
from __future__ import annotations
import argparse, gzip, hashlib, json, os, struct, tempfile
from dataclasses import dataclass
from pathlib import Path

PMTILES_MAGIC=b"PMTiles"; ABM_MAGIC=b"ABTINMAP"; HEADER_SIZE=127
REQUIRED=(
 "styles/day.json","styles/night.json","search/places.sqlite",
 "sprites/abtin.json","sprites/abtin.png","sprites/abtin@2x.json","sprites/abtin@2x.png",
 "glyphs/Vazirmatn/0-255.pbf","glyphs/Vazirmatn/256-511.pbf","glyphs/Vazirmatn/1536-1791.pbf",
 "glyphs/Vazirmatn/1792-2047.pbf","glyphs/Vazirmatn/8192-8447.pbf","glyphs/Vazirmatn/64256-64511.pbf",
 "glyphs/Vazirmatn/64512-64767.pbf","glyphs/Vazirmatn/65024-65279.pbf","glyphs/Vazirmatn/65280-65535.pbf")

@dataclass(frozen=True)
class Parts:
 header: bytearray; root: bytes; leaf: bytes; tiles: bytes; metadata: dict; compression: int

def digest_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def digest_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def read_range(h,off,n,label):
 h.seek(off); b=h.read(n)
 if len(b)!=n: raise SystemExit(f"PMTiles {label} is truncated")
 return b
def decode(b,c):
 if c==1:return b
 if c==2:return gzip.decompress(b)
 if c==3:
  import brotli; return brotli.decompress(b)
 if c==4:
  import zstandard; return zstandard.ZstdDecompressor().decompress(b)
 raise SystemExit(f"Unsupported metadata compression {c}")
def encode(b,c):
 if c==1:return b
 if c==2:return gzip.compress(b,mtime=0)
 if c==3:
  import brotli; return brotli.compress(b)
 if c==4:
  import zstandard; return zstandard.ZstdCompressor(level=19).compress(b)
 raise SystemExit(f"Unsupported metadata compression {c}")
def read_pmtiles(p:Path)->Parts:
 if not p.is_file():raise SystemExit(f"PMTiles archive does not exist: {p}")
 total=p.stat().st_size
 with p.open('rb') as h:
  head=bytearray(read_range(h,0,HEADER_SIZE,'header'))
  if head[:7]!=PMTILES_MAGIC or head[7]!=3:raise SystemExit(f"Input must be PMTiles v3: {p}")
  ro,rn=struct.unpack_from('<QQ',head,8); mo,mn=struct.unpack_from('<QQ',head,24); lo,ln=struct.unpack_from('<QQ',head,40); to,tn=struct.unpack_from('<QQ',head,56)
  for o,n,l in ((ro,rn,'root'),(mo,mn,'metadata'),(lo,ln,'leaf'),(to,tn,'tiles')):
   if o>total or n>total-o:raise SystemExit(f"PMTiles {l} range invalid")
  comp=head[97]; meta=json.loads(decode(read_range(h,mo,mn,'metadata'),comp).decode())
  if not isinstance(meta,dict):raise SystemExit('PMTiles metadata must be an object')
  return Parts(head,read_range(h,ro,rn,'root'),read_range(h,lo,ln,'leaf'),read_range(h,to,tn,'tiles'),meta,comp)

def resource_arg(raw:str):
 if '=' not in raw:raise argparse.ArgumentTypeError('--resource must be INTERNAL_PATH=LOCAL_PATH')
 internal,local=raw.split('=',1); parts=internal.replace('\\','/').split('/')
 if not internal or internal.startswith('/') or any(x in ('','.','..') for x in parts):raise argparse.ArgumentTypeError(f'unsafe resource path: {internal}')
 return internal,Path(local)

def normalize_style(raw:bytes)->bytes:
 """Normalize the embedded client contract to zoom 2-16 and compact JSON.

    The repository style files may contain legacy client metadata, but the ABM
    itself is authoritative. No z17-20 tiles are generated or requested.
    """
 s=json.loads(raw.decode())
 if not isinstance(s,dict): raise SystemExit('Style must be a JSON object')
 meta=s.setdefault('metadata',{}).setdefault('abtin',{})
 if isinstance(meta,dict): meta['max_zoom']=16
 src=s.setdefault('sources',{}).setdefault('abtin',{})
 if isinstance(src,dict):
  src['minzoom']=2
  src['maxzoom']=16
 return json.dumps(s,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()

def build(a):
 p=read_pmtiles(a.pmtiles)
 if not a.graph.is_file() or not a.graph.read_bytes().startswith(ABM_MAGIC):raise SystemExit(f"Graph must be a valid ABTINMAP segment: {a.graph}")
 if not a.search_index.is_file():raise SystemExit(f"Search index is missing: {a.search_index}")
 resources={'styles/day.json':a.day_style,'styles/night.json':a.night_style}
 for raw in a.resource:
  k,v=resource_arg(raw);resources[k]=v
 missing=[k for k in REQUIRED if k not in resources or not resources[k].is_file()]
 if missing:raise SystemExit('Missing required ABM resources: '+', '.join(missing))
 payloads=[('graph',a.graph.read_bytes()),('search/places.sqlite',a.search_index.read_bytes())]
 payloads += [(k,resources[k].read_bytes()) for k in REQUIRED if k not in ('styles/day.json','styles/night.json')]
 payloads.insert(2,('styles/day.json',normalize_style(resources['styles/day.json'].read_bytes())))
 payloads.insert(3,('styles/night.json',normalize_style(resources['styles/night.json'].read_bytes())))
 root_off=HEADER_SIZE; leaf_off=root_off+len(p.root); tile_off=leaf_off+len(p.leaf); cursor=tile_off+len(p.tiles)
 graph_info=None; entries=[]
 for name,data in payloads:
  item={'offset':cursor,'length':len(data),'sha256':digest_bytes(data)}
  if name=='graph':graph_info=item
  else:entries.append({'path':name,**item})
  cursor+=len(data)
 metadata=dict(p.metadata);metadata['abtin_container']={'version':1,'region':a.region.upper(),'contracts':{'pmtiles_minzoom':2,'pmtiles_maxzoom':16,'app_overzoom_maxzoom':16,'offline_search':'search/places.sqlite','rendered_pois':False,'styles':'embedded'},'graph':graph_info,'entries':entries}
 meta=encode(json.dumps(metadata,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode(),p.compression); meta_off=cursor
 head=bytearray(p.header);struct.pack_into('<QQ',head,8,root_off,len(p.root));struct.pack_into('<QQ',head,24,meta_off,len(meta));struct.pack_into('<QQ',head,40,leaf_off,len(p.leaf));struct.pack_into('<QQ',head,56,tile_off,cursor-tile_off)
 a.output.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix='.'+a.output.name+'.',suffix='.part',dir=a.output.parent)
 try:
  with os.fdopen(fd,'wb') as out:
   out.write(head);out.write(p.root);out.write(p.leaf);out.write(p.tiles)
   for _,data in payloads:out.write(data)
   out.write(meta);out.flush();os.fsync(out.fileno())
  os.replace(tmp,a.output)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 print(json.dumps({'container':str(a.output),'bytes':a.output.stat().st_size,'sha256':digest_file(a.output),'pmtiles_payload_bytes':len(p.tiles),'graph_payload_bytes':a.graph.stat().st_size,'embedded_entries':len(entries)},ensure_ascii=False))

def main():
 q=argparse.ArgumentParser();q.add_argument('--region',required=True);q.add_argument('--pmtiles',type=Path,required=True);q.add_argument('--graph',type=Path,required=True);q.add_argument('--search-index',type=Path,required=True);q.add_argument('--day-style',type=Path,required=True);q.add_argument('--night-style',type=Path,required=True);q.add_argument('--resource',action='append',default=[]);q.add_argument('--output',type=Path,required=True);build(q.parse_args())
if __name__=='__main__':main()
