#!/usr/bin/env python3
"""
使用 Euclidean 距離重新計算 station_progress

關鍵：TrainEngine.ts 使用 Euclidean 距離進行插值，
因此 station_progress 也必須用 Euclidean 計算才能匹配。
"""

import json
import math
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent / "public" / "data"
STATIONS_FILE = BASE_DIR / "red_line_stations.geojson"
TRACKS_DIR = BASE_DIR / "tracks"
PROGRESS_FILE = BASE_DIR / "station_progress.json"

def euclidean(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Euclidean 距離（與 TrainEngine.ts 相同）"""
    dx = lon2 - lon1
    dy = lat2 - lat1
    return math.sqrt(dx * dx + dy * dy)

def load_standard_stations():
    """載入標準車站座標"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stations = {}
    for feature in data['features']:
        station_id = feature['properties']['station_id']
        coords = feature['geometry']['coordinates']
        stations[station_id] = (coords[0], coords[1])

    return stations

def find_station_in_track(station_coord, coords, tolerance=0.00001):
    """找到車站在軌道中的索引"""
    for i, c in enumerate(coords):
        if abs(c[0] - station_coord[0]) < tolerance and abs(c[1] - station_coord[1]) < tolerance:
            return i
    return None

def find_nearest_point(station_coord, coords):
    """找最近點"""
    min_dist = float('inf')
    min_idx = 0
    for i, c in enumerate(coords):
        dist = euclidean(station_coord[0], station_coord[1], c[0], c[1])
        if dist < min_dist:
            min_dist = dist
            min_idx = i
    return min_idx, min_dist

def calculate_progress_euclidean(track_id, station_list, standard_stations):
    """使用 Euclidean 計算車站進度"""
    track_file = TRACKS_DIR / f"{track_id}.geojson"
    if not track_file.exists():
        return {}

    with open(track_file, 'r', encoding='utf-8') as f:
        track_data = json.load(f)

    coords = track_data['features'][0]['geometry']['coordinates']

    # 計算軌道總長度（Euclidean）
    total_length = 0
    for i in range(len(coords) - 1):
        total_length += euclidean(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])

    # 計算每個車站的累積距離
    progress = {}

    for station_id in station_list:
        if station_id not in standard_stations:
            continue

        station_coord = standard_stations[station_id]

        # 找車站在軌道中的位置
        station_idx = find_station_in_track(station_coord, coords)
        if station_idx is None:
            station_idx, _ = find_nearest_point(station_coord, coords)

        # 計算到該點的累積距離（Euclidean）
        cumulative = 0
        for i in range(station_idx):
            cumulative += euclidean(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])

        progress[station_id] = cumulative / total_length if total_length > 0 else 0

    return progress

def main():
    print("=" * 60)
    print("使用 Euclidean 距離重新計算 station_progress")
    print("=" * 60)

    # 載入標準車站座標
    standard_stations = load_standard_stations()
    print(f"載入 {len(standard_stations)} 個標準車站座標")

    # 載入現有 station_progress
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        all_progress = json.load(f)

    # 列出所有紅線軌道
    red_tracks = [f.stem for f in TRACKS_DIR.glob("R-*.geojson")]
    red_tracks.sort()
    print(f"找到 {len(red_tracks)} 個紅線軌道")

    # 重新計算每條軌道
    updated_count = 0
    for track_id in red_tracks:
        if track_id not in all_progress:
            continue

        station_list = list(all_progress[track_id].keys())
        new_progress = calculate_progress_euclidean(track_id, station_list, standard_stations)

        if new_progress:
            # 比較差異
            max_diff = 0
            for sid, new_val in new_progress.items():
                old_val = all_progress[track_id].get(sid, 0)
                diff = abs(new_val - old_val)
                if diff > max_diff:
                    max_diff = diff

            if max_diff > 0.001:  # 只更新有明顯差異的
                print(f"{track_id}: 最大進度差 {max_diff:.4f} ({max_diff*100:.2f}%)")
                all_progress[track_id] = new_progress
                updated_count += 1

    # 儲存
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 更新了 {updated_count} 條軌道的 station_progress")

if __name__ == "__main__":
    main()
