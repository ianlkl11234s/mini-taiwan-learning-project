#!/usr/bin/env python3
"""
偵測台北捷運軌道上車站處的折角問題
"""

import json
import math
from pathlib import Path
from typing import NamedTuple


class StationAngle(NamedTuple):
    station_id: str
    name: str
    angle_change: float
    coord_index: int
    coords: tuple[float, float]
    bearing_before: float
    bearing_after: float


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
    if min_dist <= max_distance:
        return nearest_idx
    return -1


def load_all_stations(data_dir: Path) -> dict:
    """載入所有車站資料"""
    stations = {}
    station_files = [
        'red_line_stations.geojson',
        'blue_line_stations.geojson',
        'green_line_stations.geojson',
        'orange_line_stations.geojson',
        'brown_line_stations.geojson',
        'tymc_stations.geojson',  # 桃園機場捷運
        'ntmc_stations.geojson',  # 環狀線
        'danhai_lrt_stations.geojson',  # 淡海輕軌
        'ankeng_lrt_stations.geojson',  # 安坑輕軌
        'maokong_stations.geojson',  # 貓空纜車
    ]

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
            stations[sid] = {'name': name, 'coords': tuple(coords), 'file': filename}

    return stations


def analyze_track_angles(track_file: Path, stations: dict) -> list[StationAngle]:
    """分析單一軌道的折角"""
    with open(track_file, 'r', encoding='utf-8') as f:
        track_data = json.load(f)

    track_coords = track_data['features'][0]['geometry']['coordinates']

    results = []
    for sid, sdata in stations.items():
        idx = find_coord_index(track_coords, sdata['coords'])
        if idx == -1:
            idx = find_nearest_coord_index(track_coords, sdata['coords'])
        if idx == -1 or idx == 0 or idx >= len(track_coords) - 1:
            continue

        prev_coord = track_coords[idx - 1]
        curr_coord = track_coords[idx]
        next_coord = track_coords[idx + 1]

        bearing_before = calculate_bearing(prev_coord[0], prev_coord[1], curr_coord[0], curr_coord[1])
        bearing_after = calculate_bearing(curr_coord[0], curr_coord[1], next_coord[0], next_coord[1])
        angle_change = angle_difference(bearing_before, bearing_after)

        results.append(StationAngle(
            station_id=sid, name=sdata['name'], angle_change=angle_change,
            coord_index=idx, coords=sdata['coords'],
            bearing_before=bearing_before, bearing_after=bearing_after
        ))

    results.sort(key=lambda x: x.angle_change, reverse=True)
    return results


# 軌道與線路的對應關係
TRACK_LINES = {
    'R': '紅線',
    'BL': '藍線',
    'G': '綠線',
    'O': '橘線',
    'BR': '棕線',
    'A': '機場捷運',
    'Y': '環狀線',
    'V': '淡海輕軌',
    'K': '安坑輕軌',
    'MK': '貓空纜車',
}


def get_line_name(track_id: str) -> str:
    """從軌道 ID 取得線路名稱"""
    parts = track_id.split('-')
    line_code = parts[0]
    return TRACK_LINES.get(line_code, line_code)


def main():
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "public" / "data" / "trtc"
    TRACKS_DIR = DATA_DIR / "tracks"

    print("=" * 70)
    print("台北捷運軌道折角偵測")
    print("=" * 70)

    # 載入所有車站
    stations = load_all_stations(DATA_DIR)
    print(f"\n載入 {len(stations)} 個車站")

    # 取得所有軌道檔案
    track_files = sorted(TRACKS_DIR.glob("*.geojson"))

    total_problems = 0
    total_warnings = 0
    all_problems = []
    seen_stations = set()

    # 依線路分組處理
    current_line = None

    for track_file in track_files:
        track_id = track_file.stem
        line_name = get_line_name(track_id)

        # 印出線路標題
        if line_name != current_line:
            current_line = line_name
            print(f"\n{'=' * 70}")
            print(f"📍 {line_name}")
            print("=" * 70)

        results = analyze_track_angles(track_file, stations)

        if not results:
            continue

        # 只顯示有問題的軌道
        problems = [r for r in results if r.angle_change >= 10]
        if not problems:
            continue

        print(f"\n軌道: {track_id}")
        print("-" * 50)
        print(f"{'站號':10s} {'站名':14s} {'角度':8s} {'狀態'}")
        print("-" * 50)

        for r in results:
            if r.angle_change >= 15:
                status = "❌ 嚴重"
                total_problems += 1
            elif r.angle_change >= 10:
                status = "⚠️ 警告"
                total_warnings += 1
            else:
                continue  # 只顯示問題站

            print(f"{r.station_id:10s} {r.name:14s} {r.angle_change:6.1f}° {status}")

            if r.station_id not in seen_stations:
                seen_stations.add(r.station_id)
                all_problems.append((track_id, r))

    # 總結
    print("\n" + "=" * 70)
    print("修正摘要")
    print("=" * 70)
    print(f"嚴重問題 (>=15°): {total_problems} 處")
    print(f"警告 (>=10°): {total_warnings} 處")
    print(f"需修正車站數: {len(all_problems)} 站")

    if all_problems:
        print("\n需要修正的車站：")
        for track_id, r in sorted(all_problems, key=lambda x: x[1].angle_change, reverse=True)[:20]:
            print(f"  - {r.station_id} {r.name}: {r.angle_change:.1f}° ({get_line_name(track_id)})")

        if len(all_problems) > 20:
            print(f"  ... 還有 {len(all_problems) - 20} 個")


if __name__ == '__main__':
    main()
