#!/usr/bin/env python3
"""
所有線路 station_progress 校準腳本

使用 Euclidean 距離計算，確保與 TrainEngine.ts 一致。
支援紅線 (R)、藍線 (BL)、綠線 (G)、橘線 (O)。
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional

BASE_DIR = Path(__file__).parent.parent / "public" / "data"
TRACKS_DIR = BASE_DIR / "tracks"
PROGRESS_FILE = BASE_DIR / "station_progress.json"

# 各線路車站檔案
STATION_FILES = {
    'R': 'red_line_stations.geojson',
    'BL': 'blue_line_stations.geojson',
    'G': 'green_line_stations.geojson',
    'O': 'orange_line_stations.geojson',
}

def euclidean(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Euclidean 距離（與 TrainEngine.ts 相同）"""
    dx = lon2 - lon1
    dy = lat2 - lat1
    return math.sqrt(dx * dx + dy * dy)

def load_all_stations() -> Dict[str, Tuple[float, float]]:
    """載入所有線路的標準車站座標"""
    stations = {}

    for line_prefix, filename in STATION_FILES.items():
        filepath = BASE_DIR / filename
        if not filepath.exists():
            print(f"⚠️ 找不到 {filename}")
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for feature in data['features']:
            station_id = feature['properties']['station_id']
            coords = feature['geometry']['coordinates']
            stations[station_id] = (coords[0], coords[1])

    return stations

def find_station_in_track(station_coord: Tuple[float, float], coords: List, tolerance: float = 0.0001) -> Optional[int]:
    """找到車站在軌道中的索引"""
    for i, c in enumerate(coords):
        if abs(c[0] - station_coord[0]) < tolerance and abs(c[1] - station_coord[1]) < tolerance:
            return i
    return None

def find_nearest_point(station_coord: Tuple[float, float], coords: List) -> Tuple[int, float]:
    """找最近點"""
    min_dist = float('inf')
    min_idx = 0
    for i, c in enumerate(coords):
        dist = euclidean(station_coord[0], station_coord[1], c[0], c[1])
        if dist < min_dist:
            min_dist = dist
            min_idx = i
    return min_idx, min_dist

def calculate_progress_euclidean(track_id: str, station_list: List[str],
                                  standard_stations: Dict[str, Tuple[float, float]]) -> Dict[str, float]:
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

    if total_length == 0:
        return {}

    # 計算每個車站的累積距離
    progress = {}

    for station_id in station_list:
        if station_id not in standard_stations:
            continue

        station_coord = standard_stations[station_id]

        # 找車站在軌道中的位置
        station_idx = find_station_in_track(station_coord, coords)
        if station_idx is None:
            station_idx, dist = find_nearest_point(station_coord, coords)
            # 如果最近點距離太遠，跳過
            if dist > 0.01:  # 約 1km
                continue

        # 計算到該點的累積距離（Euclidean）
        cumulative = 0
        for i in range(station_idx):
            cumulative += euclidean(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])

        progress[station_id] = cumulative / total_length

    return progress

def main():
    print("=" * 60)
    print("所有線路 station_progress 校準腳本")
    print("=" * 60)

    # 載入所有標準車站座標
    standard_stations = load_all_stations()
    print(f"\n載入 {len(standard_stations)} 個標準車站座標")

    # 載入現有 station_progress
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        all_progress = json.load(f)

    # 列出所有軌道
    all_tracks = [f.stem for f in TRACKS_DIR.glob("*.geojson")]
    all_tracks.sort()
    print(f"找到 {len(all_tracks)} 條軌道")

    # 按線路分組
    lines = {'R': [], 'BL': [], 'G': [], 'O': []}
    for track in all_tracks:
        if track.startswith('R-'):
            lines['R'].append(track)
        elif track.startswith('BL-'):
            lines['BL'].append(track)
        elif track.startswith('G-'):
            lines['G'].append(track)
        elif track.startswith('O-'):
            lines['O'].append(track)

    # 重新計算每條軌道
    updated_count = 0

    for line_name, tracks in lines.items():
        print(f"\n--- {line_name} 線 ({len(tracks)} 條軌道) ---")

        for track_id in tracks:
            if track_id not in all_progress:
                continue

            station_list = list(all_progress[track_id].keys())
            new_progress = calculate_progress_euclidean(track_id, station_list, standard_stations)

            if not new_progress:
                continue

            # 比較差異
            max_diff = 0
            for sid, new_val in new_progress.items():
                old_val = all_progress[track_id].get(sid, 0)
                diff = abs(new_val - old_val)
                if diff > max_diff:
                    max_diff = diff

            if max_diff > 0.001:  # 只更新有明顯差異的
                print(f"  {track_id}: 最大進度差 {max_diff:.4f} ({max_diff*100:.2f}%)")
                all_progress[track_id] = new_progress
                updated_count += 1

    # 儲存
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)

    print(f"\n" + "=" * 60)
    print(f"✅ 更新了 {updated_count} 條軌道的 station_progress")
    print("=" * 60)

if __name__ == "__main__":
    main()
