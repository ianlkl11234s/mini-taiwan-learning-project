#!/usr/bin/env python3
"""
Build WL-C Coastal Line O-D Tracks (Zhunan <-> Changhua)

This script:
1. Merges WL-H and WL-H2 track segments in correct order
2. Extends track to cover Changhua and Zhunan stations
3. Projects all stations onto the track
4. Calculates station progress values
5. Creates Golden Track and O-D Track files

Coastal Line Stations (18 stations):
竹南 → 談文 → 大山 → 後龍 → 龍港 → 白沙屯 → 新埔 → 通霄 → 苑裡 →
日南 → 大甲 → 臺中港 → 清水 → 沙鹿 → 龍井 → 大肚 → 追分 → 彰化
"""

import json
import math
import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRA_DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OFFICIAL_DIR = os.path.join(TRA_DATA_DIR, 'tracks_official')
TRACKS_GOLDEN_DIR = os.path.join(TRA_DATA_DIR, 'tracks_golden')
TRACKS_OD_DIR = os.path.join(TRA_DATA_DIR, 'tracks_od')
SCHEDULES_OD_DIR = os.path.join(TRA_DATA_DIR, 'schedules_od')

# Coastal line stations (south to north order for direction 0: Changhua -> Zhunan)
COASTAL_STATIONS = [
    ('3360', '彰化', 120.538540, 24.081770),
    ('2260', '追分', 120.570180, 24.120510),
    ('2250', '大肚', 120.542490, 24.154170),
    ('2240', '龍井', 120.543350, 24.197480),
    ('2230', '沙鹿', 120.557520, 24.237020),
    ('2220', '清水', 120.569180, 24.263640),
    ('2210', '臺中港', 120.602310, 24.304410),
    ('2200', '大甲', 120.627020, 24.344480),
    ('2190', '日南', 120.654120, 24.378150),
    ('2180', '苑裡', 120.651460, 24.443440),
    ('2170', '通霄', 120.678430, 24.491410),
    ('2160', '新埔', 120.695180, 24.540180),
    ('2150', '白沙屯', 120.708240, 24.564810),
    ('2140', '龍港', 120.758120, 24.611690),
    ('2130', '後龍', 120.787310, 24.616210),
    ('2120', '大山', 120.803760, 24.645650),
    ('2110', '談文', 120.858250, 24.656410),
    ('1250', '竹南', 120.880910, 24.686470),
]


def calculate_distance(coord1, coord2):
    """Calculate Euclidean distance in degrees"""
    dx = coord2[0] - coord1[0]
    dy = coord2[1] - coord1[1]
    return math.sqrt(dx * dx + dy * dy)


def get_total_length(coords):
    """Calculate total track length in degrees"""
    total = 0
    for i in range(len(coords) - 1):
        total += calculate_distance(coords[i], coords[i+1])
    return total


def project_to_segment(p, a, b):
    """
    Project point p onto line segment ab.
    Returns: (projected_point, distance, t_value)
    """
    ax, ay = a
    bx, by = b
    px, py = p

    dx = bx - ax
    dy = by - ay
    len_sq = dx * dx + dy * dy

    if len_sq == 0:
        return list(a), calculate_distance(p, a), 0

    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / len_sq))
    proj = [ax + t * dx, ay + t * dy]
    dist = calculate_distance(p, proj)

    return proj, dist, t


def find_station_projection(station_coord, coords):
    """
    Find the best projection point for a station on the track.
    Returns: (segment_index, t_value, projected_coord, distance)
    """
    best_segment = -1
    best_t = 0
    best_proj = None
    best_dist = float('inf')

    for i in range(len(coords) - 1):
        proj, dist, t = project_to_segment(station_coord, coords[i], coords[i+1])
        if dist < best_dist:
            best_dist = dist
            best_segment = i
            best_t = t
            best_proj = proj

    return best_segment, best_t, best_proj, best_dist


def calculate_station_progress(stations, coords):
    """
    Calculate progress values for all stations.
    Returns: dict of {station_id: progress}
    """
    total_length = get_total_length(coords)

    # Calculate cumulative distances
    cumulative = [0]
    for i in range(len(coords) - 1):
        cumulative.append(cumulative[-1] + calculate_distance(coords[i], coords[i+1]))

    progress_map = {}

    for sid, name, lng, lat in stations:
        segment_idx, t, proj, dist = find_station_projection([lng, lat], coords)

        # Calculate progress
        segment_start_dist = cumulative[segment_idx]
        segment_length = calculate_distance(coords[segment_idx], coords[segment_idx + 1])
        station_dist = segment_start_dist + t * segment_length
        progress = station_dist / total_length

        progress_map[sid] = round(progress, 6)
        print(f"  {sid} {name}: progress={progress:.6f}, dist_to_track={dist*111000:.1f}m")

    return progress_map


def insert_station_projections(coords, stations):
    """
    Insert station projection points into track coordinates.
    This ensures trains stop exactly on track at station positions.
    """
    # Find all projections
    projections = []
    for sid, name, lng, lat in stations:
        segment_idx, t, proj, dist = find_station_projection([lng, lat], coords)
        projections.append({
            'station_id': sid,
            'name': name,
            'segment': segment_idx,
            't': t,
            'coord': proj,
            'dist': dist
        })

    # Sort by segment and t value (reverse order for insertion)
    projections.sort(key=lambda x: (x['segment'], x['t']), reverse=True)

    # Insert projection points
    new_coords = list(coords)
    for proj in projections:
        seg = proj['segment']
        t = proj['t']
        coord = proj['coord']

        # Only insert if t is not 0 or 1 (not at segment endpoints)
        if 0 < t < 1:
            insert_pos = seg + 1
            new_coords.insert(insert_pos, coord)

    return new_coords


def load_and_merge_tracks():
    """
    Load WL-H and WL-H2 tracks and merge them in correct order.
    """
    # Load tracks
    with open(os.path.join(TRACKS_OFFICIAL_DIR, 'WL-H-0.geojson')) as f:
        wl_h = json.load(f)

    with open(os.path.join(TRACKS_OFFICIAL_DIR, 'WL-H2-0.geojson')) as f:
        wl_h2 = json.load(f)

    # Get segments
    # WL-H seg 0: 追分→清水 (120.5701,24.1202) -> (120.5694,24.2648)
    # WL-H seg 2: 清水→臺中港 (120.5688,24.2635) -> (120.6027,24.3042)
    # WL-H seg 1: 臺中港→白沙屯 (120.6028,24.3050) -> (120.7150,24.5855)
    # WL-H2 seg 0: 龍港→談文 (120.7150,24.5855) -> (120.8803,24.6819)

    seg0 = wl_h['features'][0]['geometry']['coordinates'][0]  # 追分→清水
    seg1 = wl_h['features'][0]['geometry']['coordinates'][2]  # 清水→臺中港
    seg2 = wl_h['features'][0]['geometry']['coordinates'][1]  # 臺中港→白沙屯
    seg3 = wl_h2['features'][0]['geometry']['coordinates'][0]  # 龍港→談文

    # Merge coordinates
    merged_coords = []

    # Start with Changhua station
    changhua_station = [COASTAL_STATIONS[0][2], COASTAL_STATIONS[0][3]]
    merged_coords.append(changhua_station)

    # Add all segments (skip duplicate connection points)
    merged_coords.extend(seg0)
    merged_coords.extend(seg1[1:])
    merged_coords.extend(seg2[1:])
    merged_coords.extend(seg3[1:])

    # End with Zhunan station
    zhunan_station = [COASTAL_STATIONS[-1][2], COASTAL_STATIONS[-1][3]]
    merged_coords.append(zhunan_station)

    print(f"Merged track: {len(merged_coords)} points")
    print(f"Start: ({merged_coords[0][0]:.6f}, {merged_coords[0][1]:.6f})")
    print(f"End: ({merged_coords[-1][0]:.6f}, {merged_coords[-1][1]:.6f})")

    return merged_coords


def check_track_quality(coords, stations):
    """Check for jumps and coverage issues in the track."""
    print("\n=== Track Quality Check ===")

    # Check for large jumps (>500m)
    jump_count = 0
    for i in range(len(coords) - 1):
        dist = calculate_distance(coords[i], coords[i+1]) * 111000
        if dist > 500:
            jump_count += 1
            print(f"Jump at {i}->{i+1}: {dist:.1f}m")

    if jump_count == 0:
        print("No large jumps detected")
    else:
        print(f"Total jumps: {jump_count}")

    # Check station coverage
    print("\n=== Station Coverage ===")
    all_ok = True
    for sid, name, lng, lat in stations:
        min_dist = float('inf')
        for coord in coords:
            dist = calculate_distance([lng, lat], coord)
            min_dist = min(min_dist, dist)
        status = "OK" if min_dist * 111000 < 500 else "FAR"
        if status == "FAR":
            all_ok = False
            print(f"  {sid} {name}: {min_dist * 111000:.1f}m [FAR]")

    if all_ok:
        print("All stations covered (within 500m)")

    return jump_count == 0 and all_ok


def create_golden_track(coords, direction=0):
    """Create Golden Track GeoJSON for display."""
    if direction == 0:
        track_id = "WL-C-CH-ZN-0"
        name = "海線 (彰化→竹南)"
        origin = "彰化"
        destination = "竹南"
        track_coords = coords
    else:
        track_id = "WL-C-ZN-CH-1"
        name = "海線 (竹南→彰化)"
        origin = "竹南"
        destination = "彰化"
        track_coords = list(reversed(coords))

    feature = {
        "type": "Feature",
        "properties": {
            "track_id": track_id,
            "line_id": "WL-C",
            "direction": direction,
            "name": name,
            "origin": origin,
            "destination": destination
        },
        "geometry": {
            "type": "LineString",
            "coordinates": track_coords
        }
    }

    return {
        "type": "FeatureCollection",
        "features": [feature]
    }


def create_od_track(coords, direction=0):
    """Create O-D Track GeoJSON for train calculation."""
    if direction == 0:
        track_id = "WL-CH-ZN-0"
        name = "海線 (彰化→竹南)"
        origin = "彰化"
        destination = "竹南"
        origin_station = "3360"
        destination_station = "1250"
        track_coords = coords
    else:
        track_id = "WL-ZN-CH-1"
        name = "海線 (竹南→彰化)"
        origin = "竹南"
        destination = "彰化"
        origin_station = "1250"
        destination_station = "3360"
        track_coords = list(reversed(coords))

    feature = {
        "type": "Feature",
        "properties": {
            "track_id": track_id,
            "name": name,
            "origin": origin,
            "destination": destination,
            "origin_station": origin_station,
            "destination_station": destination_station,
            "direction": direction
        },
        "geometry": {
            "type": "LineString",
            "coordinates": track_coords
        }
    }

    return {
        "type": "FeatureCollection",
        "features": [feature]
    }


def main():
    print("=== Building WL-C Coastal Line O-D Tracks ===\n")

    # Step 1: Load and merge tracks
    print("Step 1: Loading and merging WL-H and WL-H2 tracks...")
    merged_coords = load_and_merge_tracks()

    # Step 2: Check track quality
    check_track_quality(merged_coords, COASTAL_STATIONS)

    # Step 3: Insert station projections
    print("\nStep 3: Inserting station projection points...")
    enhanced_coords = insert_station_projections(merged_coords, COASTAL_STATIONS)
    print(f"Enhanced track: {len(enhanced_coords)} points (added {len(enhanced_coords) - len(merged_coords)} station points)")

    # Step 4: Calculate station progress for direction 0 (Changhua -> Zhunan)
    print("\nStep 4: Calculating station progress (direction 0)...")
    progress_0 = calculate_station_progress(COASTAL_STATIONS, enhanced_coords)

    # Step 5: Calculate station progress for direction 1 (Zhunan -> Changhua)
    print("\nStep 5: Calculating station progress (direction 1)...")
    reversed_coords = list(reversed(enhanced_coords))
    reversed_stations = list(reversed(COASTAL_STATIONS))
    progress_1 = calculate_station_progress(reversed_stations, reversed_coords)

    # Step 6: Create output files
    print("\nStep 6: Creating output files...")

    # Golden Tracks
    golden_0 = create_golden_track(enhanced_coords, direction=0)
    golden_1 = create_golden_track(enhanced_coords, direction=1)

    golden_0_path = os.path.join(TRACKS_GOLDEN_DIR, 'WL-C-CH-ZN-0.geojson')
    golden_1_path = os.path.join(TRACKS_GOLDEN_DIR, 'WL-C-ZN-CH-1.geojson')

    with open(golden_0_path, 'w') as f:
        json.dump(golden_0, f, indent=2)
    print(f"  Created: {golden_0_path}")

    with open(golden_1_path, 'w') as f:
        json.dump(golden_1, f, indent=2)
    print(f"  Created: {golden_1_path}")

    # O-D Tracks
    od_0 = create_od_track(enhanced_coords, direction=0)
    od_1 = create_od_track(enhanced_coords, direction=1)

    od_0_path = os.path.join(TRACKS_OD_DIR, 'WL-CH-ZN-0.geojson')
    od_1_path = os.path.join(TRACKS_OD_DIR, 'WL-ZN-CH-1.geojson')

    with open(od_0_path, 'w') as f:
        json.dump(od_0, f, indent=2)
    print(f"  Created: {od_0_path}")

    with open(od_1_path, 'w') as f:
        json.dump(od_1, f, indent=2)
    print(f"  Created: {od_1_path}")

    # Step 7: Update station progress
    print("\nStep 7: Updating station progress...")

    progress_path = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')
    with open(progress_path) as f:
        all_progress = json.load(f)

    all_progress['WL-CH-ZN-0'] = progress_0
    all_progress['WL-ZN-CH-1'] = progress_1

    with open(progress_path, 'w') as f:
        json.dump(all_progress, f, indent=2)
    print(f"  Updated: {progress_path}")

    # Step 8: Summary
    print("\n=== Summary ===")
    print(f"Track length: {get_total_length(enhanced_coords) * 111:.2f} km")
    print(f"Coordinate points: {len(enhanced_coords)}")
    print(f"Stations: {len(COASTAL_STATIONS)}")
    print(f"Direction 0: 彰化 (progress=0.0) → 竹南 (progress=1.0)")
    print(f"Direction 1: 竹南 (progress=0.0) → 彰化 (progress=1.0)")

    print("\n=== Files Created ===")
    print("Golden Tracks:")
    print(f"  - {golden_0_path}")
    print(f"  - {golden_1_path}")
    print("O-D Tracks:")
    print(f"  - {od_0_path}")
    print(f"  - {od_1_path}")


if __name__ == '__main__':
    main()
