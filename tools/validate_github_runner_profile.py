import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    catalog = json.loads((ROOT / 'tools/countries.json').read_text(encoding='utf-8'))
    iran = next(country for country in catalog['countries'] if country['code'] == 'IR')
    assert iran['max_open_tiles'] <= 1024
    assert iran['render_workers'] == 1
    assert 1 <= iran['render_shard_parallelism'] <= 2
    assert iran['atlas_target_mb'] <= 400

    builder = (ROOT / 'tools/build_country_package.py').read_text(encoding='utf-8')
    assert 'render_shard_parallelism' in builder
    assert 'if len(running) >= parallelism:' in builder

    workflow = (ROOT / '.github/workflows/build-abtin-map.yml').read_text(encoding='utf-8')
    assert 'cancel-in-progress: false' in workflow
    assert 'timeout-minutes: 350' in workflow
    assert 'max-parallel: 1' in workflow
    assert 'free -h' in workflow
    assert 'df -h /' in workflow
    print('github_runner_profile_ok')


if __name__ == '__main__':
    main()
