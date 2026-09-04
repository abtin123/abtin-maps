#!/usr/bin/env python3
"""Attach generated ABM patch files to a chunk manifest."""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path

def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--patch-dir',type=Path,required=True);a=p.parse_args()
 m=json.loads(a.manifest.read_text(encoding='utf8'))
 for e in m.get('countries',[]):
  code=str(e.get('code','')).upper(); j=a.patch_dir/f'{code}.patch.json'; b=a.patch_dir/f'{code}.patch.bin'
  if not (j.is_file() and b.is_file()):continue
  d=json.loads(j.read_text(encoding='utf8'))
  if d.get('schema')!='ABTINMAP-CHUNK-PATCH/1':continue
  e['patch']={'base_sha256':d['base_sha256'],'manifest_file':j.name,'bin_file':b.name,'size':b.stat().st_size,'sha256':sha(b)}
 m['schema_version']=5
 a.manifest.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 return 0
if __name__=='__main__':raise SystemExit(main())
