#!/usr/bin/env python3
"""Create a block-level ABM patch compatible with the Flutter app."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
SCHEMA='ABTINMAP-CHUNK-PATCH/1'; DEFAULT_CHUNK=4*1024*1024

def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--target',type=Path,required=True);p.add_argument('--code',required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--chunk-size',type=int,default=DEFAULT_CHUNK);a=p.parse_args()
 if a.chunk_size<=0:raise SystemExit('chunk-size must be positive')
 base_size=a.base.stat().st_size; target_size=a.target.stat().st_size
 blocks=[]; payload=bytearray(); changed=0
 with a.base.open('rb') as old,a.target.open('rb') as new:
  total=(target_size+a.chunk_size-1)//a.chunk_size
  for index in range(total):
   length=min(a.chunk_size,target_size-index*a.chunk_size)
   new_bytes=new.read(length)
   old_bytes=old.read(length) if index* a.chunk_size < base_size else b''
   if len(old_bytes)==length and old_bytes==new_bytes:continue
   offset=len(payload);payload.extend(new_bytes);blocks.append({'index':index,'offset':offset,'size':length});changed+=1
 # If target has shrunk, unchanged blocks after target end are irrelevant.
 a.output_dir.mkdir(parents=True,exist_ok=True)
 patch_bin=a.output_dir/f'{a.code}.patch.bin'; patch_json=a.output_dir/f'{a.code}.patch.json'
 patch_bin.write_bytes(payload)
 target_hash=sha(a.target); base_hash=sha(a.base); patch_hash=sha(patch_bin)
 manifest={'schema':SCHEMA,'code':a.code,'base_sha256':base_hash,'target_sha256':target_hash,'target_size':target_size,'chunk_size':a.chunk_size,'patch_sha256':patch_hash,'blocks':blocks}
 patch_json.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 full=target_size
 patch=patch_bin.stat().st_size
 if patch>=full:
  patch_bin.unlink();patch_json.unlink();print(json.dumps({'code':a.code,'usable':False,'reason':'patch_not_smaller','target_size':full,'patch_size':patch}));return 0
 print(json.dumps({'code':a.code,'usable':True,'target_size':full,'patch_size':patch,'blocks':changed,'manifest':patch_json.name,'binary':patch_bin.name}))
 return 0
if __name__=='__main__':raise SystemExit(main())
