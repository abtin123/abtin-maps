#!/usr/bin/env python3
"""Builds an ABTINMAP v2 routing graph from an OSM PBF snapshot.

The output is a graph segment, not a standalone offline map. It must be packed
with a PMTiles v3 basemap by pack_abm_container.py before publication.
"""

from __future__ import annotations

import argparse
import math
import struct
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict, Iterable

try:
    import osmium
    import zstandard
except ImportError as exc:
    raise SystemExit(
        "Missing dependency. Install with: pip install osmium zstandard"
    ) from exc

MAGIC = b"ABTINMAP"
HEADER_SIZE = 128
COORD_SCALE = 10_000_000
MAX_LAT = 85.05112878

ROAD_CLASS = {
    "motorway": 1,
    "trunk": 2,
    "primary": 3,
    "secondary": 4,
    "tertiary": 5,
    "residential": 6,
    "service": 7,
    "unclassified": 8,
    "track": 9,
}
DEFAULT_SPEED_KMH = {
    "motorway": 110,
    "trunk": 90,
    "primary": 80,
    "secondary": 70,
    "tertiary": 60,
    "residential": 40,
    "service": 20,
    "unclassified": 45,
    "track": 15,
}
DEFAULT_WIDTH_M = {
    "motorway": 15.0,
    "trunk": 12.0,
    "primary": 9.0,
    "secondary": 7.5,
    "tertiary": 6.5,
    "residential": 6.0,
    "service": 3.5,
    "unclassified": 5.0,
    "track": 2.5,
}
UNPAVED_SURFACES = {
    "compacted",
    "dirt",
    "earth",
    "fine_gravel",
    "gravel",
    "ground",
    "mud",
    "pebblestone",
    "sand",
    "unpaved",
}

ATTR_ONEWAY_FORWARD = 1 << 0
ATTR_ONEWAY_BACKWARD = 1 << 1
ATTR_BRIDGE = 1 << 2
ATTR_TUNNEL = 1 << 3
ATTR_ROUNDABOUT = 1 << 4
ATTR_LINK = 1 << 5
ATTR_TOLL = 1 << 6
ATTR_UNPAVED = 1 << 7
ATTR_NO_ACCESS = 1 << 9
ATTR_EXPLICIT_SPEED = 1 << 11


@dataclass(frozen=True)
class Segment:
    start: tuple[int, int]
    end: tuple[int, int]
    klass: int
    attr: int
    min_zoom: int
    name: str
    speed_code: int
    width_dm: int
    forward10: int
    backward10: int


@dataclass(frozen=True)
class Poi:
    point: tuple[int, int]
    klass: int
    min_zoom: int
    name: str


def uvarint(value: int) -> bytes:
    if value < 0:
        raise ValueError("uvarint cannot encode a negative value")
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def svarint(value: int) -> bytes:
    return uvarint((value << 1) ^ (value >> 63))


def tile_x(lon: float, zoom: int) -> int:
    count = 1 << zoom
    return max(0, min(count - 1, int(math.floor((lon + 180.0) / 360.0 * count))))


def tile_y(lat: float, zoom: int) -> int:
    count = 1 << zoom
    clamped = max(-MAX_LAT, min(MAX_LAT, lat))
    radians = math.radians(clamped)
    value = (1.0 - math.log(math.tan(radians) + 1 / math.cos(radians)) / math.pi) / 2.0
    return max(0, min(count - 1, int(math.floor(value * count))))


def tile_origin_e7(x: int, y: int, zoom: int) -> tuple[int, int]:
    count = 1 << zoom
    lon = x / count * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / count))))
    return round(lon * COORD_SCALE), round(lat * COORD_SCALE)


def tile_id(zoom: int, x: int, y: int) -> int:
    return (zoom << 44) | (x << 22) | y


def graph_key(point: tuple[int, int]) -> int:
    lon_e7, lat_e7 = point
    return (lat_e7 + 900_000_000) * 3_600_000_001 + (lon_e7 + 1_800_000_000)


def haversine_meters(a: tuple[int, int], b: tuple[int, int]) -> float:
    lon1, lat1 = a[0] / COORD_SCALE, a[1] / COORD_SCALE
    lon2, lat2 = b[0] / COORD_SCALE, b[1] / COORD_SCALE
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    h = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return 6_371_000.0 * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def parse_positive_number(value: str | None) -> float | None:
    if not value:
        return None
    token = value.split(";")[0].strip().lower().replace("km/h", "").strip()
    try:
        parsed = float(token)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def road_speed_code(tags: object, highway: str) -> tuple[int, float, bool]:
    raw = tags.get("maxspeed")
    maxspeed = parse_positive_number(raw)
    if maxspeed is not None:
        return max(1, min(40, round(maxspeed / 5))), maxspeed, True
    fallback = DEFAULT_SPEED_KMH[highway]
    return (200 if highway in {"residential", "service"} else 201), fallback, False


def way_width_dm(tags: object, highway: str) -> int:
    explicit = parse_positive_number(tags.get("width"))
    if explicit is None:
        lanes = parse_positive_number(tags.get("lanes"))
        explicit = lanes * 3.25 if lanes is not None else DEFAULT_WIDTH_M[highway]
    return max(10, min(600, round(explicit * 10)))


def way_attributes(tags: object, highway: str, explicit_speed: bool) -> tuple[int, bool, bool]:
    attr = 0
    oneway = str(tags.get("oneway", "")).lower()
    roundabout = str(tags.get("junction", "")).lower() == "roundabout"
    if oneway in {"yes", "1", "true"} or roundabout:
        backward = False
        forward = True
        attr |= ATTR_ONEWAY_BACKWARD
    elif oneway == "-1":
        backward = True
        forward = False
        attr |= ATTR_ONEWAY_FORWARD
    else:
        backward = True
        forward = True
    if tags.get("bridge") not in {None, "", "no", "0", "false"}:
        attr |= ATTR_BRIDGE
    if tags.get("tunnel") not in {None, "", "no", "0", "false"}:
        attr |= ATTR_TUNNEL
    if roundabout:
        attr |= ATTR_ROUNDABOUT
    if highway.endswith("_link"):
        attr |= ATTR_LINK
    if str(tags.get("toll", "")).lower() in {"yes", "1", "true"}:
        attr |= ATTR_TOLL
    if str(tags.get("surface", "")).lower() in UNPAVED_SURFACES:
        attr |= ATTR_UNPAVED
    if str(tags.get("access", "")).lower() in {"private", "no"} or str(
        tags.get("motor_vehicle", "")
    ).lower() in {"private", "no"}:
        attr |= ATTR_NO_ACCESS
    if explicit_speed:
        attr |= ATTR_EXPLICIT_SPEED
    return attr, forward, backward


def min_zoom_for(highway: str) -> int:
    return {
        "motorway": 5,
        "trunk": 6,
        "primary": 8,
        "secondary": 9,
        "tertiary": 10,
        "unclassified": 12,
        "residential": 12,
        "service": 13,
        "track": 13,
    }[highway]


def poi_class(tags: object) -> int | None:
    """Map the small, app-supported OSM POI taxonomy to stable ABM classes."""
    amenity = str(tags.get("amenity", "")).lower()
    leisure = str(tags.get("leisure", "")).lower()
    tourism = str(tags.get("tourism", "")).lower()
    shop = str(tags.get("shop", "")).lower()
    highway = str(tags.get("highway", "")).lower()
    aeroway = str(tags.get("aeroway", "")).lower()
    place = str(tags.get("place", "")).lower()
    traffic_calming = str(tags.get("traffic_calming", "")).lower()

    if amenity == "fuel":
        return 50
    if amenity in {"parking", "bicycle_parking"}:
        return 51
    if amenity in {"hospital", "clinic", "doctors"}:
        return 52
    if amenity == "pharmacy":
        return 53
    if amenity == "police":
        return 54
    if amenity in {"school", "college", "university", "kindergarten"}:
        return 55
    if amenity in {"restaurant", "fast_food", "food_court"}:
        return 56
    if amenity in {"cafe", "ice_cream"}:
        return 57
    if amenity in {"bank", "atm"}:
        return 58
    if tourism in {"hotel", "motel", "hostel", "guest_house", "apartment"}:
        return 59
    if shop in {"supermarket", "convenience", "department_store", "mall", "greengrocer"}:
        return 60
    if amenity == "place_of_worship":
        return 61
    if amenity == "toilets":
        return 62
    if amenity == "bus_station" or highway == "bus_stop":
        return 63
    if aeroway in {"aerodrome", "airport"}:
        return 64
    if tourism in {"attraction", "museum", "viewpoint", "zoo", "theme_park"} or str(tags.get("historic", "")) in {"monument", "memorial", "castle", "archaeological_site"}:
        return 65
    if leisure in {"park", "garden", "nature_reserve"}:
        return 66
    if leisure in {"pitch", "sports_centre", "stadium"}:
        return 67
    if place in {"city", "town", "village", "suburb", "neighbourhood", "quarter", "hamlet", "locality"}:
        return 68
    if highway == "speed_camera":
        return 70
    if traffic_calming in {"bump", "hump", "table", "cushion", "chicane"}:
        return 71
    if highway == "traffic_signals":
        return 72
    return None


def poi_min_zoom(klass: int) -> int:
    if klass in {52, 63, 64, 68}:
        return 11
    if klass in {50, 53, 54, 58, 59, 61, 65, 66}:
        return 12
    return 13


class GraphCollector(osmium.SimpleHandler):
    def __init__(self, zoom: int) -> None:
        super().__init__()
        self.zoom = zoom
        self.tiles: DefaultDict[tuple[int, int], list[Segment]] = defaultdict(list)
        self.pois: DefaultDict[tuple[int, int], list[Poi]] = defaultdict(list)
        self.min_lon = 180.0
        self.min_lat = 90.0
        self.max_lon = -180.0
        self.max_lat = -90.0
        self.total_segments = 0
        self.total_pois = 0

    @staticmethod
    def _display_name(tags: object) -> str:
        # برای ایران نام فارسی در اولویت است؛ در کشورهای دیگر نام محلی OSM حفظ
        # می‌شود. سرچ همچنان با نام واقعی feature کار می‌کند، نه نام ساختگی.
        return str(tags.get("name:fa") or tags.get("name") or "").strip()

    def _append_poi(self, point: tuple[int, int], klass: int, name: str) -> None:
        lon, lat = point[0] / COORD_SCALE, point[1] / COORD_SCALE
        tile = (tile_x(lon, self.zoom), tile_y(lat, self.zoom))
        self.pois[tile].append(
            Poi(point=point, klass=klass, min_zoom=poi_min_zoom(klass), name=name)
        )
        self.total_pois += 1

    def node(self, node: object) -> None:
        klass = poi_class(node.tags)
        if klass is None or not node.location.valid():
            return
        self._append_poi(
            (
                round(node.location.lon * COORD_SCALE),
                round(node.location.lat * COORD_SCALE),
            ),
            klass,
            self._display_name(node.tags),
        )

    def way(self, way: object) -> None:
        tags = way.tags
        try:
            points = [
                (round(node.location.lon * COORD_SCALE), round(node.location.lat * COORD_SCALE))
                for node in way.nodes
                if node.location.valid()
            ]
        except (osmium.InvalidLocationError, RuntimeError):
            return

        # POIهایی که به‌شکل way/area در OSM ثبت شده‌اند (مانند بیمارستان و پارک)
        # هم در index آفلاین حضور دارند. مرکز میانگین فقط برای lookup است؛ خود
        # PMTiles برای نمایش، point-on-surface دقیق تولید می‌کند.
        klass = poi_class(tags)
        if klass is not None and points:
            self._append_poi(
                (
                    round(sum(point[0] for point in points) / len(points)),
                    round(sum(point[1] for point in points) / len(points)),
                ),
                klass,
                self._display_name(tags),
            )

        raw_highway = tags.get("highway")
        if raw_highway is None:
            return
        highway = str(raw_highway).replace("_link", "")
        if highway not in ROAD_CLASS:
            return
        if str(tags.get("access", "")).lower() in {"no", "private"}:
            return
        if str(tags.get("motor_vehicle", "")).lower() in {"no", "private"}:
            return
        if len(points) < 2:
            return
        original_highway = str(raw_highway)
        speed_code, speed_kmh, explicit_speed = road_speed_code(tags, highway)
        attr, forward, backward = way_attributes(tags, original_highway, explicit_speed)
        width_dm = way_width_dm(tags, highway)
        name = self._display_name(tags)
        seconds_per_meter = 3.6 / max(5.0, speed_kmh)
        for start, end in zip(points, points[1:]):
            distance = haversine_meters(start, end)
            if distance < 0.25:
                continue
            duration10 = max(1, round(distance * seconds_per_meter * 10))
            start_lon, start_lat = start[0] / COORD_SCALE, start[1] / COORD_SCALE
            tile = (tile_x(start_lon, self.zoom), tile_y(start_lat, self.zoom))
            self.tiles[tile].append(
                Segment(
                    start=start,
                    end=end,
                    klass=ROAD_CLASS[highway],
                    attr=attr,
                    min_zoom=min_zoom_for(highway),
                    name=name,
                    speed_code=speed_code,
                    width_dm=width_dm,
                    forward10=duration10 if forward else 0,
                    backward10=duration10 if backward else 0,
                )
            )
            self.min_lon = min(self.min_lon, start_lon, end[0] / COORD_SCALE)
            self.min_lat = min(self.min_lat, start_lat, end[1] / COORD_SCALE)
            self.max_lon = max(self.max_lon, start_lon, end[0] / COORD_SCALE)
            self.max_lat = max(self.max_lat, start_lat, end[1] / COORD_SCALE)
            self.total_segments += 1


def encode_tile(
    segments: list[Segment],
    pois: list[Poi],
    *,
    x: int,
    y: int,
    zoom: int,
    name_ids: dict[str, int],
) -> bytes:
    origin_lon, origin_lat = tile_origin_e7(x, y, zoom)
    node_ids: dict[tuple[int, int], int] = {}
    nodes: list[tuple[int, int]] = []
    for segment in segments:
        for point in (segment.start, segment.end):
            if point not in node_ids:
                node_ids[point] = len(nodes)
                nodes.append(point)

    node_payload = bytearray(uvarint(len(nodes)))
    previous_lon = previous_lat = 0
    for lon, lat in nodes:
        relative_lon = lon - origin_lon
        relative_lat = lat - origin_lat
        node_payload.extend(svarint(relative_lon - previous_lon))
        node_payload.extend(svarint(relative_lat - previous_lat))
        previous_lon, previous_lat = relative_lon, relative_lat

    way_payload = bytearray(uvarint(len(segments)))
    edge_payload = bytearray(uvarint(len(segments)))
    border_nodes: set[int] = set()
    for way_index, segment in enumerate(segments):
        way_payload.extend(uvarint(segment.klass))
        way_payload.extend(uvarint(segment.attr))
        way_payload.extend(uvarint(segment.min_zoom))
        way_payload.extend(uvarint(name_ids[segment.name]))
        way_payload.extend(uvarint(segment.speed_code))
        way_payload.extend(uvarint(segment.width_dm))
        way_payload.extend(uvarint(2))
        first, second = node_ids[segment.start], node_ids[segment.end]
        way_payload.extend(uvarint(first))
        way_payload.extend(svarint(second - first))

        # way_index در reader با delta جمع می‌شود؛ edge اول باید دقیقاً به
        # way صفر اشاره کند و edgeهای بعدی یک واحد جلو بروند.
        edge_payload.extend(uvarint(0 if way_index == 0 else 1))
        edge_payload.extend(uvarint(0))
        edge_payload.extend(uvarint(1))
        edge_payload.extend(uvarint(segment.forward10))
        edge_payload.extend(uvarint(segment.backward10))
        for point, node_index in ((segment.start, first), (segment.end, second)):
            node_lon, node_lat = point[0] / COORD_SCALE, point[1] / COORD_SCALE
            if (tile_x(node_lon, zoom), tile_y(node_lat, zoom)) != (x, y):
                border_nodes.add(node_index)

    border_payload = bytearray(uvarint(len(border_nodes)))
    for node_index in sorted(border_nodes):
        border_payload.extend(uvarint(node_index))
        border_payload.extend(uvarint(graph_key(nodes[node_index])))

    # Section 5 is the POI wire format consumed by AbmFile. Relative
    # coordinates are delta-coded exactly like graph nodes to keep country
    # archives compact while preserving one-file offline search data.
    poi_payload = bytearray(uvarint(len(pois)))
    previous_poi_lon = previous_poi_lat = 0
    for poi in sorted(pois, key=lambda item: (item.point[0], item.point[1], item.klass, item.name)):
        relative_lon = poi.point[0] - origin_lon
        relative_lat = poi.point[1] - origin_lat
        poi_payload.extend(svarint(relative_lon - previous_poi_lon))
        poi_payload.extend(svarint(relative_lat - previous_poi_lat))
        poi_payload.extend(uvarint(poi.klass))
        poi_payload.extend(uvarint(poi.min_zoom))
        poi_payload.extend(uvarint(name_ids[poi.name]))
        previous_poi_lon, previous_poi_lat = relative_lon, relative_lat

    sections = ((1, node_payload), (2, way_payload), (3, edge_payload))
    if pois:
        sections = (*sections, (5, poi_payload))
    if border_nodes:
        sections = (*sections, (6, border_payload))
    out = bytearray(uvarint(len(sections)))
    for section_type, payload in sections:
        out.extend(uvarint(section_type))
        out.extend(uvarint(len(payload)))
        out.extend(payload)
    return bytes(out)


def encode_strings(strings: list[str], compressor: object) -> tuple[bytes, int]:
    raw = bytearray(uvarint(len(strings)))
    for value in strings:
        encoded = value.encode("utf-8")
        raw.extend(uvarint(len(encoded)))
        raw.extend(encoded)
    return compressor.compress(bytes(raw)), len(raw)


def encode_index(
    records: list[tuple[int, bytes, int]],
    data_offset: int,
    compressor: object,
) -> tuple[bytes, int]:
    raw = bytearray()
    previous_id = 0
    previous_end = 0
    cursor = data_offset
    for current_id, compressed, raw_size in records:
        raw.extend(uvarint(current_id - previous_id))
        raw.extend(uvarint(cursor - previous_end))
        raw.extend(uvarint(len(compressed)))
        raw.extend(uvarint(raw_size))
        raw.extend(uvarint(0))
        previous_id = current_id
        previous_end = cursor + len(compressed)
        cursor = previous_end
    return compressor.compress(bytes(raw)), len(raw)


def build_graph(
    collector: GraphCollector,
    output: Path,
    region: str,
    zoom: int,
) -> None:
    if not collector.tiles:
        raise SystemExit("No drivable OSM road segments were found in the PBF input.")
    strings = sorted(
        {segment.name for values in collector.tiles.values() for segment in values}
        | {poi.name for values in collector.pois.values() for poi in values}
    )
    if "" not in strings:
        strings.insert(0, "")
    name_ids = {name: index for index, name in enumerate(strings)}
    compressor = zstandard.ZstdCompressor(level=10)
    records: list[tuple[int, bytes, int]] = []
    tile_keys = sorted(set(collector.tiles) | set(collector.pois))
    for x, y in tile_keys:
        segments = collector.tiles[(x, y)]
        pois = collector.pois[(x, y)]
        raw = encode_tile(
            segments,
            pois,
            x=x,
            y=y,
            zoom=zoom,
            name_ids=name_ids,
        )
        records.append((tile_id(zoom, x, y), compressor.compress(raw), len(raw)))
    strings_compressed, strings_raw_size = encode_strings(strings, compressor)

    data_offset = HEADER_SIZE + len(strings_compressed)
    for _ in range(8):
        index_compressed, index_raw_size = encode_index(records, data_offset, compressor)
        new_offset = HEADER_SIZE + len(index_compressed) + len(strings_compressed)
        if new_offset == data_offset:
            break
        data_offset = new_offset
    else:
        raise SystemExit("Could not stabilize the ABM index offsets.")
    index_compressed, index_raw_size = encode_index(records, data_offset, compressor)
    strings_offset = HEADER_SIZE + len(index_compressed)

    header = bytearray(HEADER_SIZE)
    header[0:8] = MAGIC
    struct.pack_into("<H", header, 8, 2)
    struct.pack_into("<H", header, 10, 0)
    header[12] = zoom
    header[13] = 0
    bbox = (collector.min_lon, collector.min_lat, collector.max_lon, collector.max_lat)
    for index, value in enumerate(bbox):
        struct.pack_into("<i", header, 20 + index * 4, round(value * COORD_SCALE))
    struct.pack_into("<I", header, 36, len(records))
    struct.pack_into("<Q", header, 40, HEADER_SIZE)
    struct.pack_into("<I", header, 48, len(index_compressed))
    struct.pack_into("<I", header, 52, index_raw_size)
    struct.pack_into("<Q", header, 56, strings_offset)
    struct.pack_into("<I", header, 64, len(strings_compressed))
    struct.pack_into("<I", header, 68, strings_raw_size)
    struct.pack_into("<I", header, 72, len(strings))
    struct.pack_into("<I", header, 76, COORD_SCALE)
    struct.pack_into("<Q", header, 80, int(time.time()))
    header[88:104] = region.encode("ascii", "ignore")[:16].ljust(16, b"\0")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        handle.write(header)
        handle.write(index_compressed)
        handle.write(strings_compressed)
        for _, compressed, _ in records:
            handle.write(compressed)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pbf", type=Path, required=True, help="Input .osm.pbf snapshot")
    parser.add_argument("--output", type=Path, required=True, help="Output graph ABM path")
    parser.add_argument("--region", required=True, help="Country code stored in graph header")
    parser.add_argument("--zoom", type=int, default=9, choices=range(5, 15))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.pbf.is_file():
        raise SystemExit(f"PBF input was not found: {args.pbf}")
    collector = GraphCollector(args.zoom)
    collector.apply_file(str(args.pbf), locations=True)
    build_graph(collector, args.output, args.region.upper(), args.zoom)
    print(
        f"Graph created: {args.output} | roads={collector.total_segments} | pois={collector.total_pois} | tiles={len(collector.tiles) + len(set(collector.pois) - set(collector.tiles))}"
    )


if __name__ == "__main__":
    main()
