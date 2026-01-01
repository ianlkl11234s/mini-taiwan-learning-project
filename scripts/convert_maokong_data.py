#!/usr/bin/env python3
"""
Convert TDX Maokong Gondola data to project format.

This script converts the downloaded TDX API data into the format used by mini-taipei-v3:
1. Station GeoJSON
2. Track GeoJSON (bidirectional)
3. Schedule JSON
4. Station progress JSON
"""

import json
import os
import re
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TDX_DATA_DIR = PROJECT_ROOT / "data" / "tdx_maokong"
OUTPUT_DIR = PROJECT_ROOT / "public" / "data"
TRACKS_DIR = OUTPUT_DIR / "tracks"
SCHEDULES_DIR = OUTPUT_DIR / "schedules"

# Maokong Gondola configuration
MK_CONFIG = {
    "line_id": "MK",
    "color": "#06b8e6",  # Maokong Gondola blue
    "route_id": "MK-1",
    "travel_time_minutes": 30,
    "dwell_time_seconds": 30,  # Gondola station time is shorter

    # Station travel times in seconds (from first_last.json analysis)
    "segment_times": {
        "MK01-MK02": 600,   # 10 minutes
        "MK02-MK03": 720,   # 12 minutes
        "MK03-MK04": 480,   # 8 minutes
    },

    # Operating hours
    "weekday_first": "09:00",
    "weekday_last": "21:00",
    "weekend_first": "09:00",
    "weekend_last": "22:00",

    # Gondola intervals (seconds)
    "peak_interval": 15,
    "off_peak_interval": 25,
}


def parse_wkt_linestring(wkt_geometry: str) -> list:
    """Parse WKT LINESTRING to coordinate array."""
    # Extract coordinates from LINESTRING(...)
    match = re.match(r'LINESTRING\s*\((.*)\)', wkt_geometry.strip())
    if not match:
        raise ValueError(f"Invalid WKT LINESTRING: {wkt_geometry[:50]}...")

    coords_str = match.group(1)
    coordinates = []

    for point in coords_str.split(','):
        parts = point.strip().split()
        if len(parts) >= 2:
            lng, lat = float(parts[0]), float(parts[1])
            coordinates.append([lng, lat])

    return coordinates


def create_stations_geojson():
    """Create maokong_stations.geojson from TDX station data."""
    print("Creating maokong_stations.geojson...")

    with open(TDX_DATA_DIR / "station.json", "r", encoding="utf-8") as f:
        stations = json.load(f)

    features = []
    for station in stations:
        feature = {
            "type": "Feature",
            "properties": {
                "station_id": station["StationID"],
                "name_zh": station["StationName"]["Zh_tw"],
                "name_en": station["StationName"]["En"],
                "line_id": "MK"
            },
            "geometry": {
                "type": "Point",
                "coordinates": [
                    station["StationPosition"]["PositionLon"],
                    station["StationPosition"]["PositionLat"]
                ]
            }
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    output_path = OUTPUT_DIR / "maokong_stations.geojson"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"  Created: {output_path}")
    return features


def create_track_geojson(coordinates: list, direction: int) -> dict:
    """Create track GeoJSON for one direction.

    Note: The TDX shape data goes from MK04 (Maokong) to MK01 (Zoo).
    - Direction 0: MK01 -> MK04 (to Maokong) - needs reversal
    - Direction 1: MK04 -> MK01 (to Zoo) - original order
    """
    if direction == 0:
        # Reverse for direction 0 (Zoo -> Maokong)
        coordinates = list(reversed(coordinates))
        name = "動物園 → 貓空"
        start_station = "MK01"
        end_station = "MK04"
    else:
        name = "貓空 → 動物園"
        start_station = "MK04"
        end_station = "MK01"

    track_id = f"MK-1-{direction}"

    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "color": MK_CONFIG["color"],
                "route_id": MK_CONFIG["route_id"],
                "direction": direction,
                "name": name,
                "start_station": start_station,
                "end_station": end_station,
                "travel_time": MK_CONFIG["travel_time_minutes"],
                "line_id": MK_CONFIG["line_id"]
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            }
        }]
    }


def create_tracks_geojson():
    """Create track GeoJSON files from TDX shape data."""
    print("Creating track GeoJSON files...")

    with open(TDX_DATA_DIR / "shape.json", "r", encoding="utf-8") as f:
        shapes = json.load(f)

    if not shapes:
        raise ValueError("No shape data found")

    shape = shapes[0]
    coordinates = parse_wkt_linestring(shape["Geometry"])
    print(f"  Parsed {len(coordinates)} coordinate points from shape data")

    # Ensure tracks directory exists
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)

    # Create both directions
    for direction in [0, 1]:
        track_geojson = create_track_geojson(coordinates, direction)
        track_id = f"MK-1-{direction}"
        output_path = TRACKS_DIR / f"{track_id}.geojson"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(track_geojson, f, ensure_ascii=False, indent=2)

        print(f"  Created: {output_path}")

    return coordinates


def calculate_station_progress(coordinates: list) -> dict:
    """Calculate station progress values based on track geometry.

    Note: The original TDX shape data goes from MK04 (Maokong) to MK01 (Zoo).
    For direction 0 (MK01 -> MK04), we reverse the coordinates.
    For direction 1 (MK04 -> MK01), we use original coordinates.
    """
    from math import radians, sin, cos, sqrt, atan2

    def haversine_distance(coord1, coord2):
        """Calculate distance between two coordinates in meters."""
        R = 6371000  # Earth radius in meters
        lat1, lon1 = radians(coord1[1]), radians(coord1[0])
        lat2, lon2 = radians(coord2[1]), radians(coord2[0])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c

    # Load station positions
    with open(TDX_DATA_DIR / "station.json", "r", encoding="utf-8") as f:
        stations = json.load(f)

    station_coords = {}
    for station in stations:
        sid = station["StationID"]
        station_coords[sid] = [
            station["StationPosition"]["PositionLon"],
            station["StationPosition"]["PositionLat"]
        ]

    # For direction 0 (MK01 -> MK04), reverse the coordinates
    coords_dir0 = list(reversed(coordinates))

    # Calculate cumulative distances along track for direction 0
    cumulative_distances = [0]
    for i in range(1, len(coords_dir0)):
        dist = haversine_distance(coords_dir0[i-1], coords_dir0[i])
        cumulative_distances.append(cumulative_distances[-1] + dist)

    total_length = cumulative_distances[-1]
    print(f"  Total track length: {total_length:.2f} meters")

    # Find nearest track point for each station (using direction 0 coordinates)
    station_order = ["MK01", "MK02", "MK03", "MK04"]
    progress_0 = {}  # Direction 0: MK01 -> MK04
    progress_1 = {}  # Direction 1: MK04 -> MK01

    for sid in station_order:
        scoord = station_coords[sid]
        min_dist = float('inf')
        min_idx = 0

        for i, coord in enumerate(coords_dir0):
            dist = haversine_distance(scoord, coord)
            if dist < min_dist:
                min_dist = dist
                min_idx = i

        # Progress for direction 0 (MK01 -> MK04)
        progress_0[sid] = cumulative_distances[min_idx] / total_length

        # Progress for direction 1 (MK04 -> MK01) is inverted
        progress_1[sid] = 1.0 - progress_0[sid]

        print(f"  {sid}: track_idx={min_idx}, distance={min_dist:.2f}m, progress_0={progress_0[sid]:.4f}, progress_1={progress_1[sid]:.4f}")

    return {
        "MK-1-0": progress_0,
        "MK-1-1": progress_1
    }


def create_schedule_json(direction: int, is_weekday: bool = True) -> dict:
    """Create schedule JSON for one direction."""
    if direction == 0:
        stations = ["MK01", "MK02", "MK03", "MK04"]
        name = "動物園 → 貓空"
        origin = "MK01"
        destination = "MK04"
        segment_order = ["MK01-MK02", "MK02-MK03", "MK03-MK04"]
    else:
        stations = ["MK04", "MK03", "MK02", "MK01"]
        name = "貓空 → 動物園"
        origin = "MK04"
        destination = "MK01"
        segment_order = ["MK03-MK04", "MK02-MK03", "MK01-MK02"]

    track_id = f"MK-1-{direction}"

    # Calculate station arrival times
    segment_times = MK_CONFIG["segment_times"]
    dwell_time = MK_CONFIG["dwell_time_seconds"]

    station_times = []
    cumulative_time = 0

    for i, sid in enumerate(stations):
        if i == 0:
            station_times.append({
                "station_id": sid,
                "arrival": 0,
                "departure": dwell_time
            })
            cumulative_time = dwell_time
        else:
            # Get segment time (reverse segment key for direction 1)
            if direction == 0:
                seg_key = f"{stations[i-1]}-{sid}"
            else:
                seg_key = f"{sid}-{stations[i-1]}"

            travel_time = segment_times.get(seg_key, 600)  # Default 10 min
            cumulative_time += travel_time

            station_times.append({
                "station_id": sid,
                "arrival": cumulative_time,
                "departure": cumulative_time + dwell_time
            })
            cumulative_time += dwell_time

    total_travel_time = station_times[-1]["arrival"]

    # Generate departures
    first_time = MK_CONFIG["weekday_first"] if is_weekday else MK_CONFIG["weekend_first"]
    last_time = MK_CONFIG["weekday_last"] if is_weekday else MK_CONFIG["weekend_last"]

    first_hour, first_min = map(int, first_time.split(":"))
    last_hour, last_min = map(int, last_time.split(":"))

    first_seconds = first_hour * 3600 + first_min * 60
    last_seconds = last_hour * 3600 + last_min * 60

    # Use off-peak interval for simpler simulation
    interval = MK_CONFIG["off_peak_interval"]

    departures = []
    current_time = first_seconds
    train_num = 1

    while current_time <= last_seconds:
        hours = current_time // 3600
        minutes = (current_time % 3600) // 60
        seconds = current_time % 60

        departure_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        departures.append({
            "departure_time": departure_time,
            "train_id": f"{track_id}-{train_num:03d}",
            "origin_station": origin,
            "total_travel_time": total_travel_time,
            "stations": station_times
        })

        current_time += interval
        train_num += 1

    return {
        "track_id": track_id,
        "route_id": MK_CONFIG["route_id"],
        "name": name,
        "origin": origin,
        "destination": destination,
        "stations": stations,
        "travel_time_minutes": MK_CONFIG["travel_time_minutes"],
        "dwell_time_seconds": dwell_time,
        "is_weekday": is_weekday,
        "departure_count": len(departures),
        "departures": departures
    }


def create_schedules():
    """Create schedule JSON files."""
    print("Creating schedule JSON files...")

    SCHEDULES_DIR.mkdir(parents=True, exist_ok=True)

    for direction in [0, 1]:
        schedule = create_schedule_json(direction)
        track_id = f"MK-1-{direction}"
        output_path = SCHEDULES_DIR / f"{track_id}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(schedule, f, ensure_ascii=False, indent=2)

        print(f"  Created: {output_path} ({schedule['departure_count']} departures)")


def update_station_progress(station_progress: dict):
    """Update station_progress.json with MK line data."""
    print("Updating station_progress.json...")

    progress_file = OUTPUT_DIR / "station_progress.json"

    if progress_file.exists():
        with open(progress_file, "r", encoding="utf-8") as f:
            all_progress = json.load(f)
    else:
        all_progress = {}

    # Add MK progress
    all_progress.update(station_progress)

    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)

    print(f"  Updated: {progress_file}")


def main():
    print("=" * 60)
    print("Converting TDX Maokong Gondola data to project format")
    print("=" * 60)
    print()

    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)
    SCHEDULES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Create stations GeoJSON
    create_stations_geojson()
    print()

    # 2. Create tracks GeoJSON
    coordinates = create_tracks_geojson()
    print()

    # 3. Calculate and update station progress
    station_progress = calculate_station_progress(coordinates)
    update_station_progress(station_progress)
    print()

    # 4. Create schedules
    create_schedules()
    print()

    print("=" * 60)
    print("Conversion complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Update src/constants/lineInfo.ts to add MK line")
    print("2. Update src/hooks/useData.ts to load MK tracks and stations")
    print("3. Test the gondola visualization")


if __name__ == "__main__":
    main()
