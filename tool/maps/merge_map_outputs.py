#!/usr/bin/env python3
"""Merge map chunks and refuse to publish an incomplete release."""
from __future__ import annotations
import argparse,json,shutil
from pathlib import Path
MAX_RELEASE_ASSET_BYTES=2*1024**3

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--input-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--previous',type=Path);p.add_argument('--release-tag',required=True);p.add_argument('--expected-catalog',type=Path,required=True);p.add_argument('--allow-partial',action='store_true',help='publish successful maps and retain failures in build-report.json');a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=True)
 expected=json.loads(a.expected_catalog.read_text(encoding='utf-8'))
 expected_entries=expected.get('entries',[])
 expected_by={str(x.get('code','')).upper():x for x in expected_entries if isinstance(x,dict)}
 if not expected_by: raise SystemExit('Expected catalog is empty')
 entries={}
 if a.previous and a.previous.is_file():
  prev=json.loads(a.previous.read_text(encoding='utf-8'))
  entries={str(x['code']).upper():x for x in prev.get('countries',[]) if isinstance(x,dict) and x.get('code')}
 successes=[]; failures=[]
 # Artifacts are uploaded with both `dist/` and `patches/` directories, so
 # download-artifact recreates that nesting under chunk-output/map-dist-N/.
 # Use recursive lookup instead of assuming manifest.json is one level deep.
 for rp in sorted(a.input_root.rglob('build-report.json')):
  r=json.loads(rp.read_text(encoding='utf-8'));successes.extend(r.get('successes',[]));failures.extend(r.get('failures',[]))
 if failures and not a.allow_partial: raise SystemExit(f"Cannot publish: {len(failures)} map builds failed")
 for mp in sorted(a.input_root.rglob('manifest.json')):
  data=json.loads(mp.read_text(encoding='utf-8'))
  chunk_dir=mp.parent
  for item in data.get('countries',[]):
   if not isinstance(item,dict) or not item.get('code'): continue
   code=str(item['code']).upper()
   copied=False
   for part in item.get('files',[]):
    if not isinstance(part,dict) or not part.get('name'): continue
    src=chunk_dir/str(part['name'])
    if not src.is_file():
     # Large maps are placed under dist/parts/<code>/ by build_all_maps.
     src=chunk_dir/'parts'/code/str(part['name'])
    if not src.is_file(): raise SystemExit(f'Missing release file for {code}: {part.get("name")}')
    if src.stat().st_size>=MAX_RELEASE_ASSET_BYTES: raise SystemExit(f'{src.name} is >=2GiB')
    shutil.copy2(src,a.output/src.name);copied=True
   archive=chunk_dir/f'{code}.abm'
   if archive.is_file() and not copied:
    if archive.stat().st_size>=MAX_RELEASE_ASSET_BYTES: raise SystemExit(f'{code}.abm is >=2GiB')
    shutil.copy2(archive,a.output/archive.name);copied=True
   if copied: entries[code]=item
 missing=[];stale=[]
 for code,want in expected_by.items():
  got=entries.get(code)
  if got is None: missing.append(code);continue
  ws=str(want.get('source_signature','')); gs=str(got.get('source',{}).get('signature',''))
  if ws and gs and ws!=gs: stale.append(code)
 if (missing or stale) and not a.allow_partial:
  if missing: raise SystemExit('Missing expected maps: '+', '.join(missing[:50]))
  if stale: raise SystemExit('Stale maps detected: '+', '.join(stale[:50]))
 if a.allow_partial:
  for code in set(missing + stale): entries.pop(code, None)
  countries=[entries[k] for k in sorted(entries) if k in expected_by and k not in stale]
 else:
  countries=[entries[k] for k in sorted(expected_by)]
 manifest={'schema_version':5,'release_tag':a.release_tag,'expected_count':len(expected_by),'published_count':len(countries),'partial':bool(failures or missing or stale),'countries':countries}
 (a.output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 report={'release_tag':a.release_tag,'expected_count':len(expected_by),'published_count':len(countries),'success_count':len(successes),'failure_count':len(failures),'successes':successes,'failures':failures,'missing_codes':missing,'stale_codes':stale}
 (a.output/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'Merged release: published={len(countries)}/{len(expected_by)} rebuilt_or_checked={len(successes)} failures={len(failures)}')
 return 0
if __name__=='__main__':raise SystemExit(main())
