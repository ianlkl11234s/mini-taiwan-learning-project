#!/usr/bin/env python3
"""
軌道校準腳本：將車站座標插入軌道檔案

此腳本會：
1. 讀取各線路的車站座標檔案
2. 將車站座標插入到對應軌道的正確位置
3. 重新計算 station_progress（使用 Euclidean 距離）

這與紅線的校準方式相同。
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
    'G': 'green_line_stations.geojson',
    'O': 'orange_line_stations.geojson',
    'BL': 'blue_line_stations.geojson',
}


def euclidean(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Euclidean 距離（與 TrainEngine.ts 相同）"""
    dx = lon2 - lon1
    dy = lat2 - lat1
    return math.sqrt(dx * dx + dy * dy)


def load_stations(line_prefix: str) -> Dict[str, Tuple[float, float]]:
    """載入指定線路的車站座標"""
    filename = STATION_FILES.get(line_prefix)
    if not filename:
        return {}

    filepath = BASE_DIR / filename
    if not filepath.exists():
        print(f"⚠️ 找不到 {filename}")
        return {}

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stations = {}
    for feature in data['features']:
        station_id = feature['properties']['station_id']
        coords = feature['geometry']['coordinates']
        stations[station_id] = (coords[0], coords[1])

    return stations


def find_insertion_point(station_coord: Tuple[float, float],
                         coords: List,
                         tolerance: float = 0.0001) -> Tuple[int, float]:
    """
    找到車站在軌道中應該插入的位置
    返回 (插入索引, 與最近點的距離)
    """
    # 首先檢查是否已存在精確座標
    for i, c in enumerate(coords):
        if abs(c[0] - station_coord[0]) < 0.00001 and abs(c[1] - station_coord[1]) < 0.00001:
            return i, 0.0  # 已存在，不需插入

    # 找最近點
    min_dist = float('inf')
    min_idx = 0
    for i, c in enumerate(coords):
        dist = euclidean(station_coord[0], station_coord[1], c[0], c[1])
        if dist < min_dist:
            min_dist = dist
            min_idx = i

    return min_idx, min_dist


def insert_station_into_track(track_coords: List,
                               station_coord: Tuple[float, float],
                               station_id: str) -> Tuple[List, bool]:
    """
    將車站座標插入軌道
    返回 (新軌道座標, 是否有修改)
    """
    idx, dist = find_insertion_point(station_coord, track_coords)

    # 如果距離為 0，表示已存在
    if dist == 0:
        return track_coords, False

    # 如果距離太遠（> 500m），可能不在這條軌道上
    if dist > 0.005:  # 約 500m
        return track_coords, False

    # 插入車站座標到最近點的位置
    new_coords = track_coords.copy()
    new_coords.insert(idx, [station_coord[0], station_coord[1]])

    return new_coords, True


def calculate_progress_euclidean(coords: List,
                                  station_list: List[str],
                                  stations: Dict[str, Tuple[float, float]]) -> Dict[str, float]:
    """使用 Euclidean 計算車站進度"""
    # 計算軌道總長度
    total_length = 0
    for i in range(len(coords) - 1):
        total_length += euclidean(coords[i][0], coords[i][1],
                                  coords[i+1][0], coords[i+1][1])

    if total_length == 0:
        return {}

    progress = {}
    for station_id in station_list:
        if station_id not in stations:
            continue

        station_coord = stations[station_id]

        # 找車站在軌道中的位置
        station_idx = None
        for i, c in enumerate(coords):
            if abs(c[0] - station_coord[0]) < 0.00001 and abs(c[1] - station_coord[1]) < 0.00001:
                station_idx = i
                break

        if station_idx is None:
            # 找最近點
            min_dist = float('inf')
            for i, c in enumerate(coords):
                dist = euclidean(station_coord[0], station_coord[1], c[0], c[1])
                if dist < min_dist:
                    min_dist = dist
                    station_idx = i

        # 計算累積距離
        cumulative = 0
        for i in range(station_idx):
            cumulative += euclidean(coords[i][0], coords[i][1],
                                    coords[i+1][0], coords[i+1][1])

        progress[station_id] = cumulative / total_length

    return progress


def process_line(line_prefix: str, stations: Dict[str, Tuple[float, float]],
                 all_progress: Dict) -> Tuple[int, int]:
    """
    處理指定線路的所有軌道
    返回 (修改的軌道數, 更新的 progress 數)
    """
    # 找出該線路的所有軌道
    track_files = list(TRACKS_DIR.glob(f"{line_prefix}-*.geojson"))

    modified_tracks = 0
    updated_progress = 0

    for track_file in sorted(track_files):
        track_id = track_file.stem

        # 讀取軌道
        with open(track_file, 'r', encoding='utf-8') as f:
            track_data = json.load(f)

        coords = track_data['features'][0]['geometry']['coordinates']
        original_len = len(coords)

        # 取得該軌道的車站列表
        if track_id not in all_progress:
            continue

        station_list = list(all_progress[track_id].keys())

        # 插入所有車站座標
        track_modified = False
        for station_id in station_list:
            if station_id not in stations:
                continue

            station_coord = stations[station_id]
            coords, modified = insert_station_into_track(coords, station_coord, station_id)
            if modified:
                track_modified = True

        # 如果軌道有修改，儲存
        if track_modified:
            track_data['features'][0]['geometry']['coordinates'] = coords
            with open(track_file, 'w', encoding='utf-8') as f:
                json.dump(track_data, f, ensure_ascii=False, indent=2)

            new_len = len(coords)
            print(f"  ✅ {track_id}: 插入 {new_len - original_len} 個車站座標")
            modified_tracks += 1

        # 重新計算 progress
        new_progress = calculate_progress_euclidean(coords, station_list, stations)
        if new_progress:
            # 比較差異
            max_diff = 0
            for sid, new_val in new_progress.items():
                old_val = all_progress[track_id].get(sid, 0)
                diff = abs(new_val - old_val)
                if diff > max_diff:
                    max_diff = diff

            if max_diff > 0.001:
                all_progress[track_id] = new_progress
                updated_progress += 1
                if not track_modified:
                    print(f"  📊 {track_id}: progress 最大修正 {max_diff*100:.2f}%")

    return modified_tracks, updated_progress


def main():
    print("=" * 60)
    print("軌道校準腳本：將車站座標插入軌道檔案")
    print("=" * 60)

    # 載入現有 station_progress
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        all_progress = json.load(f)

    total_modified = 0
    total_updated = 0

    for line_prefix in ['G', 'O', 'BL']:
        print(f"\n--- {line_prefix} 線 ---")

        # 載入車站座標
        stations = load_stations(line_prefix)
        if not stations:
            print(f"  ⚠️ 無法載入 {line_prefix} 線車站資料")
            continue

        print(f"  載入 {len(stations)} 個車站座標")

        # 處理軌道
        modified, updated = process_line(line_prefix, stations, all_progress)
        total_modified += modified
        total_updated += updated

        print(f"  修改 {modified} 條軌道, 更新 {updated} 條 progress")

    # 儲存 progress
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)

    print(f"\n" + "=" * 60)
    print(f"✅ 完成！修改 {total_modified} 條軌道, 更新 {total_updated} 條 progress")
    print("=" * 60)


if __name__ == "__main__":
    main()
