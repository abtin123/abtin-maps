#!/usr/bin/env python3
"""Discover the complete stable country/region catalog once per workflow run."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from build_all_maps import discover_entries, fetch_json, INDEX_URL

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--index-url',default=INDEX_URL);a=p.parse_args()
 entries=discover_entries(fetch_json(a.index_url))
 if not entries: raise SystemExit('catalog is empty')
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(f'Discovered {len(entries)} country/region map entries')
 return 0
if __name__=='__main__':raise SystemExit(main())
