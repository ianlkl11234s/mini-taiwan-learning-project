#!/usr/bin/env python3
"""
Recalculate od_station_progress.json for ALL TRA OD tracks using the actual
track GeoJSON geometries and station coordinates.

Adapted for mini-taipei-v3 path structure.
"""

import json
import math
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(BASE, "public", "data")


def haversine_m(lng1, lat1, lng2, lat2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def euclidean_deg(a, b):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return math.sqrt(dx * dx + dy * dy)


def calc_total_length(coords):
    total = 0
    for i in range(len(coords) - 1):
        total += euclidean_deg(coords[i], coords[i + 1])
    return total


def find_nearest_progress(coords, station_lng, station_lat):
    total_length = calc_total_length(coords)
    if total_length == 0:
        return 0.0, float("inf")

    best_progress = 0.0
    best_dist_m = float("inf")
    accumulated = 0.0

    for i in range(len(coords) - 1):
        a = coords[i]
        b = coords[i + 1]
        seg_len = euclidean_deg(a, b)

        if seg_len == 0:
            continue

        dx = b[0] - a[0]
        dy = b[1] - a[1]
        t = ((station_lng - a[0]) * dx + (station_lat - a[1]) * dy) / (
            dx * dx + dy * dy
        )
        t = max(0, min(1, t))

        proj_lng = a[0] + t * dx
        proj_lat = a[1] + t * dy
        dist_m = haversine_m(proj_lng, proj_lat, station_lng, station_lat)

        if dist_m < best_dist_m:
            best_dist_m = dist_m
            best_progress = (accumulated + t * seg_len) / total_length

        accumulated += seg_len

    return best_progress, best_dist_m


def extract_coords(data):
    if data.get("type") == "FeatureCollection":
        feat = data["features"][0]
    elif data.get("type") == "Feature":
        feat = data
    else:
        return None
    geom = feat.get("geometry", {})
    if geom.get("type") == "LineString":
        return geom["coordinates"]
    return None


def main():
    # Load station coordinates
    stations_path = os.path.join(PUBLIC, "tra/stations.geojson")
    with open(stations_path) as f:
        stations_data = json.load(f)

    station_coords = {}
    for feat in stations_data["features"]:
        props = feat["properties"]
        sid = props.get("station_id", "")
        if sid:
            lng, lat = feat["geometry"]["coordinates"][:2]
            station_coords[sid] = (lng, lat)

    print(f"Loaded {len(station_coords)} TRA station coordinates")

    # Load existing od_station_progress.json
    sp_path = os.path.join(PUBLIC, "tra/tracks_od/od_station_progress.json")
    with open(sp_path) as f:
        old_sp = json.load(f)

    print(f"Existing od_station_progress has {len(old_sp)} tracks")

    # Recalculate progress for each track
    new_sp = {}
    tracks_dir = os.path.join(PUBLIC, "tra/tracks_od")
    updated = 0
    skipped = 0
    errors = []

    for track_id, old_progress_map in old_sp.items():
        track_path = os.path.join(tracks_dir, f"{track_id}.geojson")
        if not os.path.exists(track_path):
            new_sp[track_id] = old_progress_map
            skipped += 1
            continue

        with open(track_path) as f:
            track_data = json.load(f)

        coords = extract_coords(track_data)
        if not coords or len(coords) < 2:
            new_sp[track_id] = old_progress_map
            skipped += 1
            continue

        new_progress_map = {}

        for station_id in old_progress_map:
            if station_id not in station_coords:
                new_progress_map[station_id] = old_progress_map[station_id]
                continue

            lng, lat = station_coords[station_id]
            progress, dist_m = find_nearest_progress(coords, lng, lat)
            new_progress_map[station_id] = round(progress, 6)

            if dist_m > 500:
                errors.append(
                    f"  WARNING: {track_id}/{station_id} nearest={dist_m:.0f}m"
                )

        new_sp[track_id] = new_progress_map
        updated += 1

    print(f"\nRecalculated {updated} tracks, skipped {skipped}")

    # Save
    with open(sp_path, "w", encoding="utf-8") as f:
        json.dump(new_sp, f, ensure_ascii=False, indent=2)
    print(f"\nSaved updated od_station_progress.json")

    if errors:
        print(f"\nWarnings ({len(errors)}):")
        for e in errors[:20]:
            print(e)
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")


if __name__ == "__main__":
    main()
