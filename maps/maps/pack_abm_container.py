#!/usr/bin/env python3
"""Pack vector map data into one random-access ABTINMAP container.

The container deliberately stores DATA only: PMTiles vector tiles, the offline
routing graph and the offline search database. Visual styles, glyphs and POI
sprites are application assets so every country does not duplicate the same
renderer resources.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,os,struct,tempfile
from pathlib import Path
PM=b"PMTiles"; ABM=b"ABTINMAP"; HEAD=127

def sha256(data:bytes)->str: return hashlib.sha256(data).hexdigest()
def read_range(h,o,n,label):
    h.seek(o); b=h.read(n)
    if len(b)!=n: raise SystemExit(f"PMTiles {label} is truncated")
    return b

def decode(b,c):
    if c==1:return b
    if c==2:return gzip.decompress(b)
    if c==3:
        import brotli; return brotli.decompress(b)
    if c==4:
        import zstandard; return zstandard.ZstdDecompressor().decompress(b)
    raise SystemExit(f"Unsupported PMTiles compression: {c}")

def encode(b,c):
    if c==1:return b
    if c==2:return gzip.compress(b,compresslevel=9,mtime=0)
    if c==3:
        import brotli; return brotli.compress(b,quality=11)
    if c==4:
        import zstandard; return zstandard.ZstdCompressor(level=19,threads=1,write_checksum=True).compress(b)
    raise SystemExit(f"Unsupported PMTiles compression: {c}")

def read_pmtiles(path):
    with path.open('rb') as h:
        head=bytearray(read_range(h,0,HEAD,'header'))
        if head[:7]!=PM or head[7]!=3: raise SystemExit(f'Input must be PMTiles v3: {path}')
        total=path.stat().st_size
        ro,rn=struct.unpack_from('<QQ',head,8); mo,mn=struct.unpack_from('<QQ',head,24); lo,ln=struct.unpack_from('<QQ',head,40); to,tn=struct.unpack_from('<QQ',head,56)
        for o,n,name in ((ro,rn,'root'),(mo,mn,'metadata'),(lo,ln,'leaf'),(to,tn,'tiles')):
            if o>total or n>total-o: raise SystemExit(f'PMTiles {name} range invalid')
        metadata=decode(read_range(h,mo,mn,'metadata'),head[97])
        meta=json.loads(metadata.decode('utf-8'))
        if meta.get('format') not in (None,'pbf'):
            raise SystemExit(f'PMTiles is not vector/PBF data: format={meta.get("format")!r}')
        return head,read_range(h,ro,rn,'root'),read_range(h,lo,ln,'leaf'),read_range(h,to,tn,'tiles'),meta,head[97]

def build(a):
    head,root,leaf,tiles,base_meta,comp=read_pmtiles(a.pmtiles)
    if not a.graph.is_file() or not a.graph.read_bytes().startswith(ABM): raise SystemExit(f'Graph must be a valid ABTINMAP segment: {a.graph}')
    if not a.search_index.is_file(): raise SystemExit(f'Search index is missing: {a.search_index}')
    graph=a.graph.read_bytes(); search_raw=a.search_index.read_bytes()
    try:
        import zstandard
        search=zstandard.ZstdCompressor(level=19,threads=1,write_checksum=True).compress(search_raw); search_codec='zstd'
    except Exception:
        search=gzip.compress(search_raw,compresslevel=9,mtime=0); search_codec='gzip'
    root_off=HEAD; leaf_off=root_off+len(root); tile_off=leaf_off+len(leaf); cursor=tile_off+len(tiles)
    graph_info={'offset':cursor,'length':len(graph),'sha256':sha256(graph),'codec':'none','raw_length':len(graph)}; cursor+=len(graph)
    search_info={'offset':cursor,'length':len(search),'sha256':sha256(search),'codec':search_codec,'raw_length':len(search_raw)}; cursor+=len(search)
    meta=dict(base_meta)
    meta['abtin_container']={
      'version':4,
      'region':a.region.upper(),
      'contracts':{
        'container_data_only':True,
        'pmtiles_minzoom':2,
        'pmtiles_maxzoom':16,
        'app_overzoom_maxzoom':18,
        'offline_search':'search/places.sqlite',
        'rendered_pois':False,
        'styles':'app_bundled',
        'glyphs':'app_bundled',
        'sprites':'app_bundled'
      },
      'graph':graph_info,
      'entries':[{'path':'search/places.sqlite',**search_info}],
    }
    encoded=encode(json.dumps(meta,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode(),comp); meta_off=cursor
    struct.pack_into('<QQ',head,8,root_off,len(root)); struct.pack_into('<QQ',head,24,meta_off,len(encoded)); struct.pack_into('<QQ',head,40,leaf_off,len(leaf)); struct.pack_into('<QQ',head,56,tile_off,len(tiles))
    a.output.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix='.'+a.output.name+'.',suffix='.part',dir=a.output.parent)
    try:
        with os.fdopen(fd,'wb') as out:
            out.write(head); out.write(root); out.write(leaf); out.write(tiles); out.write(graph); out.write(search); out.write(encoded); out.flush(); os.fsync(out.fileno())
        os.replace(tmp,a.output)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    print(json.dumps({'container':str(a.output),'bytes':a.output.stat().st_size,'sha256':sha256(a.output.read_bytes()),'pmtiles_payload_bytes':len(tiles),'graph_payload_bytes':len(graph),'search_raw_bytes':len(search_raw),'search_stored_bytes':len(search)},ensure_ascii=False))

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--region',required=True); p.add_argument('--pmtiles',type=Path,required=True); p.add_argument('--graph',type=Path,required=True); p.add_argument('--search-index',type=Path,required=True); p.add_argument('--output',type=Path,required=True); main_args=p.parse_args(); build(main_args)
if __name__=='__main__': main()
