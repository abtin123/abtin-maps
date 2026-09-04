#!/usr/bin/env python3
"""Verify that the release manifest contains exactly the expected map catalog."""
from __future__ import annotations
import argparse,json
from pathlib import Path

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);a=p.parse_args()
 c=json.loads(a.catalog.read_text(encoding='utf8'));m=json.loads(a.manifest.read_text(encoding='utf8'))
 want={str(x['code']).upper():x for x in c.get('entries',[]) if isinstance(x,dict) and x.get('code')}
 got={str(x['code']).upper():x for x in m.get('countries',[]) if isinstance(x,dict) and x.get('code')}
 if set(want)!=set(got):
  print('Missing:',sorted(set(want)-set(got)));print('Unexpected:',sorted(set(got)-set(want)));return 1
 stale=[]
 for code in want:
  ws=str(want[code].get('source_signature',''));gs=str(got[code].get('source',{}).get('signature',''))
  if ws and gs and ws!=gs: stale.append(code)
 if stale: print('Stale:',stale);return 1
 print(f'Catalog verification OK: {len(want)} maps')
 return 0
if __name__=='__main__':raise SystemExit(main())
