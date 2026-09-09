#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from create_abm import verify_abm
if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('abm',type=Path); a=p.parse_args(); print(json.dumps(verify_abm(a.abm),ensure_ascii=False,indent=2))
