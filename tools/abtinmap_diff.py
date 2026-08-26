"""Build a safe binary incremental patch between two complete ABM files.

The ABM payload now includes the server-rendered SQLite/WebP atlas and its
``ABTATLS2`` footer.  Therefore an update patch compares the *entire binary*
in fixed-size blocks rather than inspecting only legacy vector tiles.  A phone
copies unchanged blocks from its validated installed ABM and downloads only
the blocks listed here.  The final SHA-256 is still verified before an atomic
replacement, so an interrupted or invalid patch can never damage the map
already installed on the device.

Usage:
    python3 abtinmap_diff.py old/IR.abm new/IR.abm --code IR --out-dir out
"""

import argparse
import hashlib
import json
import os


DEFAULT_CHUNK_SIZE = 1024 * 1024
SCHEMA = "ABTINMAP-CHUNK-PATCH/1"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_patch(old_path, new_path, out_dir, code, chunk_size=DEFAULT_CHUNK_SIZE):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    os.makedirs(out_dir, exist_ok=True)
    patch_path = os.path.join(out_dir, f"{code}.abmpatch")
    changed = []
    kept = 0

    with open(old_path, "rb") as old, open(new_path, "rb") as new, open(patch_path, "wb") as patch:
        index = 0
        while True:
            new_chunk = new.read(chunk_size)
            if not new_chunk:
                break
            old_chunk = old.read(len(new_chunk))
            if old_chunk == new_chunk:
                kept += 1
            else:
                offset = patch.tell()
                patch.write(new_chunk)
                changed.append({
                    "index": index,
                    "offset": offset,
                    "size": len(new_chunk),
                })
            index += 1

    manifest = {
        "schema": SCHEMA,
        "code": code,
        "base_sha256": sha256_file(old_path),
        "target_sha256": sha256_file(new_path),
        "target_size": os.path.getsize(new_path),
        "chunk_size": chunk_size,
        "blocks": changed,
        "changed_block_count": len(changed),
        "kept_block_count": kept,
        "patch_size": os.path.getsize(patch_path),
        "patch_sha256": sha256_file(patch_path),
    }
    manifest_path = os.path.join(out_dir, f"patch-{code}.json")
    with open(manifest_path, "w", encoding="utf-8") as target:
        json.dump(manifest, target, ensure_ascii=False, indent=2)

    full_size = manifest["target_size"]
    patch_size = manifest["patch_size"]
    ratio = 0 if full_size == 0 else patch_size * 100 / full_size
    print(
        f"{code}: {len(changed):,} بلوک تغییرکرده، {kept:,} بلوک بدون تغییر\n"
        f"  فایل کامل: {full_size / 1e6:.1f} MB   پچ: {patch_size / 1e6:.1f} MB ({ratio:.1f}٪)\n"
        f"  -> {patch_path}\n  -> {manifest_path}"
    )
    return manifest_path, patch_path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("old_abm")
    parser.add_argument("new_abm")
    parser.add_argument("--code", required=True)
    parser.add_argument("--out-dir", default="out")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    args = parser.parse_args(argv)
    build_patch(args.old_abm, args.new_abm, args.out_dir, args.code, args.chunk_size)


if __name__ == "__main__":
    main()
