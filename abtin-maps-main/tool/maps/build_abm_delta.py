#!/usr/bin/env python3
"""Create the ABTINMAP-CHUNK-PATCH/1 delta consumed by the Flutter app."""
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(); p.add_argument('--old',required=True,type=Path); p.add_argument('--new',required=True,type=Path); p.add_argument('--output',required=True,type=Path); p.add_argument('--code',required=True); p.add_argument('--chunk-size',type=int,default=1<<20); a=p.parse_args()
    if a.chunk_size<=0: raise SystemExit('chunk-size must be positive')
    old_size=a.old.stat().st_size; target_size=a.new.stat().st_size; blocks=[]
    with a.old.open('rb') as fo, a.new.open('rb') as fn, a.output.open('wb') as patch:
        index=0
        while index*a.chunk_size < target_size:
            nb=fn.read(a.chunk_size); ob=fo.read(a.chunk_size)
            if nb != ob:
                offset=patch.tell(); patch.write(nb); blocks.append({'index':index,'offset':offset,'size':len(nb)})
            index += 1
    patch_sha=sha(a.output)
    meta={'schema':'ABTINMAP-CHUNK-PATCH/1','code':a.code.upper(),'base_sha256':sha(a.old),'target_sha256':sha(a.new),'target_size':target_size,'chunk_size':a.chunk_size,'patch_sha256':patch_sha,'blocks':blocks,'created_at':int(time.time())}
    meta_path=a.output.with_suffix('.delta.json'); meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'code':a.code.upper(),'changed_blocks':len(blocks),'patch_bytes':a.output.stat().st_size,'target_bytes':target_size,'patch':str(a.output),'manifest':str(meta_path)},ensure_ascii=False))
if __name__=='__main__': main()
