from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
WORKFLOW = ROOT / '.github/workflows/build-abtin-map.yml'


def main() -> None:
    for name in (
        'countries.json',
        'sync_geofabrik_catalog.py',
        'checkpoint_render.py',
        'build_country_package.py',
        'abtinmap_diff.py',
        'make_manifest.py',
        'merge_manifests.py',
        'extract_manifest_countries.py',
        'update_osm_source_state.py',
    ):
        assert (TOOLS / name).is_file(), name

    sync = (TOOLS / 'sync_geofabrik_catalog.py').read_text(encoding='utf-8')
    builder = (TOOLS / 'build_country_package.py').read_text(encoding='utf-8')
    manifest = (TOOLS / 'make_manifest.py').read_text(encoding='utf-8')
    workflow = WORKFLOW.read_text(encoding='utf-8')

    assert 'index-v1.json' in sync
    assert 'download.geofabrik.de' in sync
    assert 'sharded_parents' in sync
    assert 'render_shard_parallelism' in builder
    assert 'sync_geofabrik_catalog.py' in workflow
    assert 'checkpoint_render.py' in workflow
    assert 'build_country_package.py' in workflow
    assert 'countries.resolved.json' in workflow
    assert '--source-attribution' in workflow
    assert '--rendered-meta' in workflow
    assert '"source": {' in manifest
    print('country_pipeline_contract_ok')


if __name__ == '__main__':
    main()
