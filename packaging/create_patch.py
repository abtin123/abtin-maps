from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

SCHEMA = 'ABTINMAP-CHUNK-PATCH/1'

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def create_patch(base: Path, target: Path, code: str, output_dir: Path, chunk_size: int = 4 * 1024 * 1024) -> tuple[Path, Path]:
    if chunk_size <= 0: raise ValueError('chunk_size must be positive')
    output_dir.mkdir(parents=True, exist_ok=True)
    patch_name = f'{code}.abmpatch.bin'
    manifest_name = f'{code}.abmpatch.json'
    patch_path = output_dir / patch_name
    blocks=[]
    patch_offset=0
    with base.open('rb') as old, target.open('rb') as new, patch_path.open('wb') as patch:
        index=0
        while True:
            old_chunk, new_chunk = old.read(chunk_size), new.read(chunk_size)
            if not new_chunk: break
            if old_chunk != new_chunk:
                patch.write(new_chunk)
                blocks.append({'index': index, 'offset': patch_offset, 'size': len(new_chunk)})
                patch_offset += len(new_chunk)
            index += 1
    manifest = {
        'schema': SCHEMA, 'code': code, 'base_sha256': sha256(base),
        'target_sha256': sha256(target), 'target_size': target.stat().st_size,
        'chunk_size': chunk_size, 'patch_sha256': sha256(patch_path), 'blocks': blocks,
    }
    manifest_path = output_dir / manifest_name
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    descriptor = {
        'base_sha256': manifest['base_sha256'], 'manifest_file': manifest_name,
        'bin_file': patch_name, 'size': patch_path.stat().st_size,
        'sha256': manifest['patch_sha256'],
    }
    (output_dir / 'patch-descriptor.json').write_text(json.dumps(descriptor, ensure_ascii=False, indent=2) + '\n')
    return manifest_path, patch_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create an ABTINMAP chunk patch')
    parser.add_argument('base', type=Path); parser.add_argument('target', type=Path)
    parser.add_argument('--code', required=True); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--chunk-size-mib', type=int, default=4)
    args = parser.parse_args()
    manifest, patch = create_patch(args.base, args.target, args.code, args.output, args.chunk_size_mib * 1024 * 1024)
    print(json.dumps({'manifest': str(manifest), 'patch': str(patch)}, indent=2))
