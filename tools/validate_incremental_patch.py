"""Deterministic verification for the ABTINMAP chunk patch format."""

import hashlib
import json
import tempfile
from pathlib import Path

from abtinmap_diff import build_patch


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_fixture_patch(old: Path, patch: Path, manifest: dict, output: Path) -> None:
    block_by_index = {block["index"]: block for block in manifest["blocks"]}
    target_size = manifest["target_size"]
    chunk_size = manifest["chunk_size"]
    with old.open("rb") as source, patch.open("rb") as changed, output.open("wb") as result:
        count = (target_size + chunk_size - 1) // chunk_size
        for index in range(count):
            size = min(chunk_size, target_size - index * chunk_size)
            block = block_by_index.get(index)
            if block is None:
                source.seek(index * chunk_size)
                data = source.read(size)
            else:
                changed.seek(block["offset"])
                data = changed.read(block["size"])
            assert len(data) == size
            result.write(data)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        old = root / "IR-old.abm"
        new = root / "IR-new.abm"
        old.write_bytes((b"A" * 1024) + (b"B" * 1024) + (b"C" * 303))
        new.write_bytes((b"A" * 1024) + (b"D" * 1024) + (b"C" * 303) + b"ABTATLS2")
        manifest_path, patch_path = build_patch(
            old, new, root, "IR", chunk_size=1024,
        )
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        assert manifest["schema"] == "ABTINMAP-CHUNK-PATCH/1"
        assert manifest["base_sha256"] == sha256(old)
        assert manifest["target_sha256"] == sha256(new)
        assert manifest["changed_block_count"] == 2
        rebuilt = root / "IR-rebuilt.abm"
        apply_fixture_patch(old, Path(patch_path), manifest, rebuilt)
        assert rebuilt.read_bytes() == new.read_bytes()
        assert sha256(rebuilt) == manifest["target_sha256"]
    print("incremental_patch_fixture_ok")


if __name__ == "__main__":
    main()
