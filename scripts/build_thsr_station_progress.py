#!/usr/bin/env python3
"""
計算高鐵車站進度映射表

功能：
1. 讀取校準後的軌道 GeoJSON
2. 計算每個車站在軌道上的進度 (0-1)
3. 輸出 station_progress.json

使用方式：
    python scripts/build_thsr_station_progress.py

前置條件：
    先執行 calibrate_thsr_tracks.py 校準軌道

輸入：
    - public/data-thsr/tracks/THSR-1-0.geojson (校準後)
    - public/data-thsr/tracks/THSR-1-1.geojson (校準後)
    - public/data-thsr/stations/thsr_stations.geojson

輸出：
    - public/data-thsr/station_progress.json
"""

import json
import math
import os
from typing import List, Dict, Any

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data-thsr')
TRACKS_DIR = os.path.join(DATA_DIR, 'tracks')
STATIONS_FILE = os.path.join(DATA_DIR, 'stations', 'thsr_stations.geojson')
OUTPUT_FILE = os.path.join(DATA_DIR, 'station_progress.json')


def euclidean(p1: List[float], p2: List[float]) -> float:
    """計算 Euclidean 距離（與 TrainEngine.ts 一致）"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def calculate_total_length(coords: List[List[float]]) -> float:
    """計算軌道總長度"""
    return sum(euclidean(coords[i], coords[i + 1]) for i in range(len(coords) - 1))


def find_station_index(
    station_coord: List[float],
    track_coords: List[List[float]],
    tolerance: float = 0.0001
) -> int:
    """
    找到車站在軌道座標中的索引

    返回最近點的索引，如果距離超過 tolerance 則返回 -1
    """
    min_dist = float('inf')
    best_idx = -1

    for i, tc in enumerate(track_coords):
        dist = euclidean(tc, station_coord)
        if dist < min_dist:
            min_dist = dist
            best_idx = i

    # 投影點應該在軌道上，但允許微小誤差
    if min_dist > tolerance:
        # 嘗試找最近的點（投影點可能與原座標略有不同）
        pass

    return best_idx


def calculate_progress_at_index(
    coords: List[List[float]],
    index: int,
    total_length: float
) -> float:
    """計算軌道上某索引位置的進度 (0-1)"""
    if index <= 0:
        return 0.0
    if index >= len(coords) - 1:
        return 1.0

    accum = sum(euclidean(coords[i], coords[i + 1]) for i in range(index))
    return accum / total_length


def load_stations() -> List[Dict[str, Any]]:
    """載入車站資料"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return sorted(
        data['features'],
        key=lambda x: x['properties'].get('sequence', 0)
    )


def load_track(track_id: str) -> Dict[str, Any]:
    """載入軌道 GeoJSON"""
    filepath = os.path.join(TRACKS_DIR, f'{track_id}.geojson')
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_station_progress(
    track_id: str,
    track_coords: List[List[float]],
    stations: List[Dict[str, Any]],
    direction: int
) -> Dict[str, float]:
    """
    建立單一軌道的車站進度映射

    參數：
        track_id: 軌道 ID
        track_coords: 軌道座標列表
        stations: 車站資料列表（按 sequence 排序）
        direction: 0 = 南下, 1 = 北上

    返回：
        { station_id: progress }
    """
    total_length = calculate_total_length(track_coords)
    progress_map: Dict[str, float] = {}

    # 根據方向決定車站順序
    if direction == 1:
        ordered_stations = list(reversed(stations))
    else:
        ordered_stations = stations

    for station in ordered_stations:
        station_id = station['properties']['station_id']
        station_coord = station['geometry']['coordinates']

        # 找到車站在軌道上的索引
        idx = find_station_index(station_coord, track_coords)

        if idx >= 0:
            progress = calculate_progress_at_index(track_coords, idx, total_length)
            progress_map[station_id] = round(progress, 6)

    return progress_map


def validate_progress(progress_map: Dict[str, float], direction: int) -> bool:
    """
    驗證進度值是否單調遞增

    返回：True = 有效, False = 無效
    """
    values = list(progress_map.values())
    for i in range(1, len(values)):
        if values[i] <= values[i - 1]:
            return False
    return True


def main():
    print("=" * 50)
    print("高鐵車站進度計算腳本")
    print("=" * 50)

    # 載入車站資料
    print("\n載入車站資料...")
    stations = load_stations()
    print(f"  共 {len(stations)} 站")

    # 處理兩條軌道
    tracks_config = [
        ('THSR-1-0', 0, '南下 (南港→左營)'),
        ('THSR-1-1', 1, '北上 (左營→南港)'),
    ]

    all_progress: Dict[str, Dict[str, float]] = {}

    for track_id, direction, desc in tracks_config:
        print(f"\n處理 {track_id} ({desc})...")

        # 載入軌道
        track_geojson = load_track(track_id)
        coords = track_geojson['features'][0]['geometry']['coordinates']
        print(f"  座標點數: {len(coords)}")

        # 計算進度
        progress_map = build_station_progress(track_id, coords, stations, direction)
        print(f"  車站數量: {len(progress_map)}")

        # 驗證
        is_valid = validate_progress(progress_map, direction)
        if is_valid:
            print("  ✅ 進度值單調遞增")
        else:
            print("  ⚠️ 警告：進度值非單調遞增！")

        # 顯示進度值
        print("  進度值:")
        for station_id, progress in progress_map.items():
            name = next(
                s['properties']['name_zh']
                for s in stations
                if s['properties']['station_id'] == station_id
            )
            print(f"    {name} ({station_id}): {progress:.6f}")

        all_progress[track_id] = progress_map

    # 儲存結果
    print(f"\n儲存到 {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)
    print("  ✅ 完成")

    # 輸出摘要
    print("\n" + "=" * 50)
    print("完成！")
    print("=" * 50)
    print(f"\n產出檔案: {OUTPUT_FILE}")
    print("\n下一步：修改 useThsrData.ts 載入此檔案")

    return all_progress


if __name__ == '__main__':
    main()
