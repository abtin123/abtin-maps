"""Contract check for the bundled real Arak offline-map test package."""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT / "assets" / "maps" / "ARAK-TEST.abm"
EXPECTED_ABM = "385f1bbe12cd5223c2b907e59887d956e05067634901fc624b0b82701e473080"
EXPECTED_ATLAS = "711ae1913fa6af15c284ac418da631e88348776155085578478c3355e3982922"
FOOTER = struct.Struct("<8sQQQQ32s")


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def main() -> None:
    assert ASSET.exists(), f"missing bundled map asset: {ASSET}"
    data = ASSET.read_bytes()
    assert hashlib.sha256(data).hexdigest() == EXPECTED_ABM
    assert len(data) >= FOOTER.size
    magic, atlas_offset, atlas_size, preview_offset, preview_size, atlas_digest = FOOTER.unpack(
        data[-FOOTER.size :]
    )
    assert magic == b"ABTATLS2"
    assert atlas_offset >= 128 and atlas_size > 0
    assert atlas_offset + atlas_size <= len(data) - FOOTER.size
    assert preview_size > 0 and preview_offset >= atlas_offset + atlas_size
    assert preview_offset + preview_size <= len(data) - FOOTER.size
    assert sha256(data[atlas_offset : atlas_offset + atlas_size]).hex() == EXPECTED_ATLAS
    assert atlas_digest.hex() == EXPECTED_ATLAS

    assert "- assets/maps/" in (ROOT / "pubspec.yaml").read_text(encoding="utf-8")
    service = (ROOT / "lib/abtinmap/abm_map_service.dart").read_text(encoding="utf-8")
    catalog = (ROOT / "lib/features/offline_maps/data/map_catalog.dart").read_text(encoding="utf-8")
    controller = (ROOT / "lib/features/offline_maps/presentation/map_download_providers.dart").read_text(encoding="utf-8")
    screen = (ROOT / "lib/features/settings/presentation/map_settings_screen.dart").read_text(encoding="utf-8")
    assert "installBundledAsset" in service
    assert "ARAK-TEST" in catalog and "assets/maps/ARAK-TEST.abm" in catalog
    assert "_region.isBundledAsset" in controller
    assert "entry.id == 'ARAK-TEST'" in screen
    print("demo-map contract OK")


if __name__ == "__main__":
    main()
