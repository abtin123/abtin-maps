#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from packaging.create_abm import verify_abm  # noqa: E402
if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('abm',type=Path); a=p.parse_args(); print(json.dumps(verify_abm(a.abm),ensure_ascii=False,indent=2))
