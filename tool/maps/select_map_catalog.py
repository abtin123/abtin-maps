#!/usr/bin/env python3
"""Filter a complete country catalog using selectors such as IR, ALL, or ALL/IR."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def parse_selector(raw: str) -> tuple[set[str] | None, set[str]]:
    value = (raw or "all").strip().upper()
    if not value:
        value = "ALL"
    parts = [p.strip() for p in value.split("/") if p.strip()]
    if not parts:
        return None, set()
    if parts[0] == "ALL":
        return None, {p for p in parts[1:] if p != "ALL"}
    return {p for p in parts if p != "ALL"}, set()

def matches(entry: dict, include: set[str] | None, exclude: set[str]) -> bool:
    code = str(entry.get("code", "")).upper()
    country = str(entry.get("country_code", "")).upper()
    if include is not None:
        ok = code in include or country in include
    else:
        ok = True
    return ok and code not in exclude and country not in exclude

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--selector", default="all")
    a = p.parse_args()
    data = json.loads(a.input.read_text(encoding="utf-8"))
    entries = data.get("entries", data) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise SystemExit("catalog must be a JSON list or an object containing entries")
    include, exclude = parse_selector(a.selector)
    selected = [e for e in entries if isinstance(e, dict) and matches(e, include, exclude)]
    if include is not None and not selected:
        raise SystemExit(f"Selector matched no countries/regions: {a.selector}")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Selector {a.selector!r}: {len(selected)}/{len(entries)} entries selected")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
