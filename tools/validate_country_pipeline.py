#!/usr/bin/env python3
"""Static contract checks for the legal multi-country map build pipeline."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
WORKFLOW = ROOT / ".github/workflows/build-abtin-map.yml"

sync = (TOOLS / "sync_geofabrik_catalog.py").read_text(encoding="utf-8")
builder = (TOOLS / "build_country_package.py").read_text(encoding="utf-8")
manifest = (TOOLS / "make_manifest.py").read_text(encoding="utf-8")
workflow = WORKFLOW.read_text(encoding="utf-8")

assert "index-v1.json" in sync
assert "ALLOWED_HOSTS" in sync and "download.geofabrik.de" in sync
assert "sharded_parents" in sync
assert "source_attribution" in sync and "source_license_url" in sync

assert '"--continue-at", "-"' in builder
assert "build_country_package.py" in workflow
assert "sync_geofabrik_catalog.py" in workflow
assert "countries.resolved.json" in workflow
assert "--source-attribution" in workflow
assert "--rendered-meta" in workflow
assert "--include-subregions" not in workflow
assert 'rm -f "$FILE"' not in workflow

for argument in (
    "--source-url",
    "--source-provider",
    "--source-attribution",
    "--source-license-url",
    "--source-copyright-url",
):
    assert argument in manifest
assert '"source": {' in manifest

print("country_pipeline_contract_ok")
