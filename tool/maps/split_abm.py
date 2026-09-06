#!/usr/bin/env python3
"""Split a large ABM into concatenable GitHub Release parts without changing bytes."""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
MAX_PART=2*1024**3-16*1024**2

def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--code',required=True);a=p.parse_args()
 if a.archive.stat().st_size < MAX_PART:
  print(json.dumps({'split':False,'parts':[a.archive.name]}));return 0
 a.output_dir.mkdir(parents=True,exist_ok=True);parts=[]
 with a.archive.open('rb') as src:
  i=0
  while True:
   data=src.read(MAX_PART)
   if not data:break
   out=a.output_dir/f'{a.code}.abm.part{i}';tmp=out.with_suffix(out.suffix+'.part')
   with tmp.open('wb') as dst:dst.write(data);dst.flush();os.fsync(dst.fileno())
   tmp.replace(out);parts.append({'name':out.name,'size':out.stat().st_size,'sha256':sha(out)});i+=1
 a.archive.unlink()
 meta=a.output_dir/f'{a.code}.parts.json';meta.write_text(json.dumps({'code':a.code,'total_size':sum(x['size'] for x in parts),'parts':parts,'sha256':None},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'split':True,'parts':parts,'manifest':meta.name}));return 0
if __name__=='__main__':raise SystemExit(main())
