#!/usr/bin/env python3
"""
修正台北捷運軌道上車站處的折角問題
"""

import json
import math
from pathlib import Path
from typing import NamedTuple
import shutil
from datetime import datetime


class FixResult(NamedTuple):
    station_id: str
    name: str
    original_angle: float
    new_angle: float
    distance_moved: float


def calculate_bearing(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    dx = lon2 - lon1
    dy = lat2 - lat1
    angle = math.degrees(math.atan2(dx, dy))
    return (angle + 360) % 360


def angle_difference(bearing1: float, bearing2: float) -> float:
    diff = abs(bearing2 - bearing1)
    if diff > 180:
        diff = 360 - diff
    return diff


def euclidean_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    dx = lon2 - lon1
    dy = lat2 - lat1
    return math.sqrt(dx * dx + dy * dy)


def haversine_distance_meters(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    R = 6371000
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat, delta_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_coord_index(track_coords: list, station_coord: tuple, tolerance: float = 0.00001) -> int:
    for i, coord in enumerate(track_coords):
        if abs(coord[0] - station_coord[0]) < tolerance and abs(coord[1] - station_coord[1]) < tolerance:
            return i
    return -1


def find_nearest_coord_index(track_coords: list, station_coord: tuple, max_distance: float = 0.0005) -> int:
    min_dist = float('inf')
    nearest_idx = -1
    for i, coord in enumerate(track_coords):
        dist = euclidean_distance(coord[0], coord[1], station_coord[0], station_coord[1])
        if dist < min_dist:
            min_dist = dist
            nearest_idx = i
    return nearest_idx if min_dist <= max_distance else -1


def project_point_to_line(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return ax, ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return ax + t * dx, ay + t * dy


def find_search_range(track_coords: list, station_idx: int, search_distance_meters: float = 100) -> tuple[int, int]:
    start_idx = station_idx
    accumulated_dist = 0
    for i in range(station_idx - 1, -1, -1):
        dist = haversine_distance_meters(track_coords[i][0], track_coords[i][1], track_coords[i + 1][0], track_coords[i + 1][1])
        accumulated_dist += dist
        if accumulated_dist >= search_distance_meters:
            start_idx = i
            break
    else:
        start_idx = max(0, station_idx - 1)

    end_idx = station_idx
    accumulated_dist = 0
    for i in range(station_idx + 1, len(track_coords)):
        dist = haversine_distance_meters(track_coords[i - 1][0], track_coords[i - 1][1], track_coords[i][0], track_coords[i][1])
        accumulated_dist += dist
        if accumulated_dist >= search_distance_meters:
            end_idx = i
            break
    else:
        end_idx = min(len(track_coords) - 1, station_idx + 1)

    return start_idx, end_idx


def calculate_angle_at_index(track_coords: list, idx: int) -> float:
    if idx <= 0 or idx >= len(track_coords) - 1:
        return 0
    prev, curr, next_c = track_coords[idx - 1], track_coords[idx], track_coords[idx + 1]
    b_before = calculate_bearing(prev[0], prev[1], curr[0], curr[1])
    b_after = calculate_bearing(curr[0], curr[1], next_c[0], next_c[1])
    return angle_difference(b_before, b_after)


def fix_station_angle(track_coords: list, station_idx: int, search_distance: float = 100, max_move: float = 30):
    original_coord = track_coords[station_idx]
    start_idx, end_idx = find_search_range(track_coords, station_idx, search_distance)

    if start_idx >= station_idx:
        start_idx = max(0, station_idx - 1)
    if end_idx <= station_idx:
        end_idx = min(len(track_coords) - 1, station_idx + 1)

    start_coord, end_coord = track_coords[start_idx], track_coords[end_idx]
    new_lon, new_lat = project_point_to_line(original_coord[0], original_coord[1], start_coord[0], start_coord[1], end_coord[0], end_coord[1])

    move_distance = haversine_distance_meters(original_coord[0], original_coord[1], new_lon, new_lat)

    if move_distance > max_move:
        return track_coords, tuple(original_coord), 0

    new_coords = track_coords.copy()
    del new_coords[start_idx + 1:end_idx]
    new_coords.insert(start_idx + 1, [new_lon, new_lat])

    return new_coords, (new_lon, new_lat), move_distance


TRACK_LINES = {'R': '紅線', 'BL': '藍線', 'G': '綠線', 'O': '橘線', 'BR': '棕線', 'A': '機場捷運', 'Y': '環狀線', 'V': '淡海輕軌', 'K': '安坑輕軌', 'MK': '貓空纜車'}


def get_line_name(track_id: str) -> str:
    return TRACK_LINES.get(track_id.split('-')[0], track_id.split('-')[0])


def load_all_stations(data_dir: Path) -> dict:
    stations = {}
    station_files = ['red_line_stations.geojson', 'blue_line_stations.geojson', 'green_line_stations.geojson',
                     'orange_line_stations.geojson', 'brown_line_stations.geojson', 'tymc_stations.geojson',
                     'ntmc_stations.geojson', 'danhai_lrt_stations.geojson', 'ankeng_lrt_stations.geojson', 'maokong_stations.geojson']

    for filename in station_files:
        filepath = data_dir / filename
        if not filepath.exists():
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for feature in data['features']:
            props = feature['properties']
            sid = props.get('station_id') or props.get('id')
            name = props.get('name_zh') or props.get('name') or sid
            coords = feature['geometry']['coordinates']
            stations[sid] = {'name': name, 'coords': tuple(coords), 'file': filename, 'feature': feature, 'data': data, 'filepath': filepath}
    return stations


def main():
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "public" / "data" / "trtc"
    TRACKS_DIR = DATA_DIR / "tracks"
    BACKUP_DIR = PROJECT_ROOT / "scripts" / "backup_trtc"

    print("=" * 70)
    print("台北捷運軌道折角修正")
    print("=" * 70)

    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 備份所有車站檔案
    print(f"\n📁 備份原始檔案到 {BACKUP_DIR}")
    for f in DATA_DIR.glob("*_stations.geojson"):
        shutil.copy(f, BACKUP_DIR / f"{f.stem}_{timestamp}.geojson")

    # 載入所有車站
    stations = load_all_stations(DATA_DIR)
    print(f"載入 {len(stations)} 個車站")

    track_files = sorted(TRACKS_DIR.glob("*.geojson"))

    # 備份所有軌道檔案
    for track_file in track_files:
        shutil.copy(track_file, BACKUP_DIR / f"{track_file.stem}_{timestamp}.geojson")

    total_fixes = 0
    fixed_stations = set()
    updated_station_files = set()

    current_line = None

    for track_file in track_files:
        track_id = track_file.stem
        line_name = get_line_name(track_id)

        if line_name != current_line:
            current_line = line_name
            print(f"\n{'=' * 70}")
            print(f"🔧 {line_name}")
            print("=" * 70)

        # 讀取軌道
        with open(track_file, 'r', encoding='utf-8') as f:
            track_data = json.load(f)
        track_coords = track_data['features'][0]['geometry']['coordinates']

        # 找問題站
        stations_to_fix = []
        for sid, sdata in stations.items():
            idx = find_coord_index(track_coords, sdata['coords'])
            if idx == -1:
                idx = find_nearest_coord_index(track_coords, sdata['coords'])
            if idx == -1 or idx == 0 or idx >= len(track_coords) - 1:
                continue
            angle = calculate_angle_at_index(track_coords, idx)
            if angle >= 10.0:
                stations_to_fix.append((idx, sid, sdata, angle))

        if not stations_to_fix:
            continue

        stations_to_fix.sort(key=lambda x: x[0], reverse=True)
        track_results = []

        for idx, sid, sdata, original_angle in stations_to_fix:
            current_idx = find_coord_index(track_coords, sdata['coords'])
            if current_idx == -1:
                current_idx = find_nearest_coord_index(track_coords, sdata['coords'])
            if current_idx == -1:
                continue

            track_coords, new_coord, move_dist = fix_station_angle(track_coords, current_idx, 100, 30)

            if move_dist > 0:
                # 更新車站座標
                sdata['feature']['geometry']['coordinates'] = list(new_coord)
                sdata['coords'] = new_coord
                updated_station_files.add(sdata['filepath'])

                new_idx = find_coord_index(track_coords, new_coord)
                new_angle = calculate_angle_at_index(track_coords, new_idx) if new_idx != -1 else 0

                track_results.append(FixResult(sid, sdata['name'], original_angle, new_angle, move_dist))
                fixed_stations.add(sid)
                total_fixes += 1

        if track_results:
            print(f"\n軌道: {track_id}")
            print("-" * 50)
            for r in track_results:
                status = "✅" if r.new_angle < 10 else "⚠️"
                print(f"  {r.station_id:10s} {r.name:14s} {r.original_angle:5.1f}° → {r.new_angle:4.1f}° ({r.distance_moved:.1f}m) {status}")

        # 儲存軌道
        track_data['features'][0]['geometry']['coordinates'] = track_coords
        with open(track_file, 'w', encoding='utf-8') as f:
            json.dump(track_data, f, indent=2, ensure_ascii=False)

    # 儲存車站檔案
    saved_files = set()
    for filepath in updated_station_files:
        if filepath in saved_files:
            continue
        # 重新讀取整個檔案並更新
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 更新座標
        for feature in data['features']:
            sid = feature['properties'].get('station_id') or feature['properties'].get('id')
            if sid in stations:
                feature['geometry']['coordinates'] = list(stations[sid]['coords'])
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        saved_files.add(filepath)

    print("\n" + "=" * 70)
    print("修正摘要")
    print("=" * 70)
    print(f"共修正 {total_fixes} 處 ({len(fixed_stations)} 個車站)")
    print(f"更新 {len(saved_files)} 個車站檔案")
    print(f"\n✅ 已覆蓋原始檔案")
    print(f"📁 備份已儲存至: {BACKUP_DIR}")


if __name__ == '__main__':
    main()
