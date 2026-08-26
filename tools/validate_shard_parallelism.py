"""Exercise IR sharded-atlas command construction without downloading map data."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_country_package as builder  # noqa: E402


def main() -> None:
    profile = {
        "bbox": [44.0, 24.0, 64.0, 40.0],
        "render_workers": 1,
        "max_open_tiles": 512,
        "render_shard_parallelism": 2,
        "render_min_zoom": 2,
        "render_max_zoom": 14,
        "atlas_target_mb": 320,
    }
    launched: list[list[str]] = []

    class _SuccessfulProcess:
        def wait(self) -> int:
            return 0

    def fake_run(command, dry_run=False):
        launched.append([str(item) for item in command])

    def fake_popen(command):
        launched.append([str(item) for item in command])
        return _SuccessfulProcess()

    with tempfile.TemporaryDirectory() as directory, patch.object(
        builder.shutil, "which", return_value="/usr/bin/osmium"
    ), patch.object(builder, "run", side_effect=fake_run), patch.object(
        builder.subprocess, "Popen", side_effect=fake_popen
    ):
        builder.build_sharded_atlas(
            pbf=Path(directory) / "IR.osm.pbf",
            profile=profile,
            code="IR",
            out_dir=Path(directory) / "out",
            work_dir=Path(directory) / "work",
            dry_run=False,
        )
    renderer_commands = [command for command in launched if "rendered_tile_builder.py" in " ".join(command)]
    shard_commands = [command for command in renderer_commands if "--shard-out" in command]
    assert len(shard_commands) == 4
    assert all(command[command.index("--workers") + 1] == "1" for command in shard_commands)
    assert all(command[command.index("--max-open-tiles") + 1] == "512" for command in shard_commands)
    assert len(renderer_commands) == 5  # چهار شارد + ادغام
    print("shard_parallelism_dry_run_ok")


if __name__ == "__main__":
    main()
