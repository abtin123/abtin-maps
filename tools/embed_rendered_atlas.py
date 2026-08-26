"""Append a rendered SQLite atlas to an ABM and write a discoverable footer."""
import argparse
import hashlib
import os
import struct


MAGIC = b"ABTATLS2"
FOOTER_STRUCT = struct.Struct("<8sQQQQ32s")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.digest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("abm")
    parser.add_argument("atlas")
    parser.add_argument("--preview")
    args = parser.parse_args()
    atlas_size = os.path.getsize(args.atlas)
    with open(args.abm, "ab") as target:
        atlas_offset = target.tell()
        with open(args.atlas, "rb") as source:
            while chunk := source.read(1 << 20):
                target.write(chunk)
        preview_offset, preview_size = 0, 0
        if args.preview:
            preview_offset = target.tell()
            preview_size = os.path.getsize(args.preview)
            with open(args.preview, "rb") as source:
                while chunk := source.read(1 << 20):
                    target.write(chunk)
        target.write(FOOTER_STRUCT.pack(
            MAGIC, atlas_offset, atlas_size, preview_offset, preview_size, sha256(args.atlas)))
    print(f"atlas embedded offset={atlas_offset} size={atlas_size} preview={preview_size}")


if __name__ == "__main__":
    main()
