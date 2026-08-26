import argparse
import gzip
import json
import math


def _distance(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    if dx == 0 and dy == 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    return abs(dy * point[0] - dx * point[1] + end[0] * start[1] - end[1] * start[0]) / math.hypot(dx, dy)


def _simplify(points, tolerance):
    if len(points) < 4:
        return points
    keep = {0, len(points) - 1}
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        farthest, distance = -1, 0.0
        for index in range(first + 1, last):
            candidate = _distance(points[index], points[first], points[last])
            if candidate > distance:
                farthest, distance = index, candidate
        if distance > tolerance:
            keep.add(farthest)
            stack.extend(((first, farthest), (farthest, last)))
    return [point for index, point in enumerate(points) if index in keep]


def _encode_ring(raw_ring, scale, tolerance):
    points = _simplify([(float(lon), float(lat)) for lon, lat in raw_ring], tolerance)
    if len(points) < 4:
        return []
    encoded, previous_lon, previous_lat = [], 0, 0
    for lon, lat in points:
        longitude, latitude = round(lon * scale), round(lat * scale)
        encoded.append([longitude - previous_lon, latitude - previous_lat])
        previous_lon, previous_lat = longitude, latitude
    return encoded


def _rings(geometry):
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if kind == "Polygon":
        return coordinates
    if kind == "MultiPolygon":
        return [ring for polygon in coordinates for ring in polygon]
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--scale", type=int, default=10000)
    parser.add_argument("--tolerance", type=float, default=0.12)
    options = parser.parse_args()
    with open(options.input, encoding="utf-8") as source:
        data = json.load(source)
    boundaries = []
    for feature in data.get("features", []):
        rings = [
            encoded for raw_ring in _rings(feature.get("geometry") or {})
            if (encoded := _encode_ring(raw_ring, options.scale, options.tolerance))
        ]
        if rings:
            boundaries.append(rings)
    payload = json.dumps({"v": 1, "s": options.scale, "b": boundaries}, separators=(",", ":")).encode()
    with gzip.open(options.output, "wb", compresslevel=9) as target:
        target.write(payload)
    print(f"boundaries={len(boundaries)} bytes={len(payload)}")


if __name__ == "__main__":
    main()
