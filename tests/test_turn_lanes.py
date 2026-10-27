import sqlite3
from pathlib import Path

from routing.graph_builder import build_graph


def test_turn_lanes_are_stored_per_direction(tmp_path: Path):
    ways = [
        {"id": 1, "node_ids": [1, 2], "geometry": [(0.0, 35.0), (0.001, 35.0)],
         "tags": {"highway": "primary", "oneway": "yes", "lanes": "3",
                  "turn:lanes": "left|through|through;right"}},
        {"id": 2, "node_ids": [2, 3], "geometry": [(0.001, 35.0), (0.002, 35.0)],
         "tags": {"highway": "primary", "turn:lanes:forward": "left|through",
                  "turn:lanes:backward": "through|right"}},
    ]
    out = tmp_path / "g.sqlite"
    build_graph(ways, [], out)
    con = sqlite3.connect(out)
    rows = dict((r[0], r[1:]) for r in con.execute(
        "SELECT way_id, turn_lanes, turn_lanes_bwd FROM way_data"))
    assert rows[1] == ("left|through|through;right", "")
    assert rows[2] == ("left|through", "through|right")
