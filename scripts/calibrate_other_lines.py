#!/usr/bin/env python3
"""
綠線/橘線/藍線軌道校準腳本

與紅線相同的方法：
1. 以 *_line_stations.geojson 中的座標為標準
2. 將車站座標插入軌道的最佳位置
3. 使用 Euclidean 距離重新計算 station_progress（與 TrainEngine.ts 一致）
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional

BASE_DIR = Path(__file__).parent.parent / "public" / "data"
TRACKS_DIR = BASE_DIR / "tracks"
PROGRESS_FILE = BASE_DIR / "station_progress.json"

# 線路設定
LINE_CONFIG = {
    'G': {
        'stations_file': 'green_line_stations.geojson',
        'track_prefix': 'G-',
    },
    'O': {
        'stations_file': 'orange_line_stations.geojson',
        'track_prefix': 'O-',
    },
    'BL': {
        'stations_file': 'blue_line_stations.geojson',
        'track_prefix': 'BL-',
    },
}


def euclidean(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Euclidean 距離（與 TrainEngine.ts 相同）"""
    dx = lon2 - lon1
    dy = lat2 - lat1
    return math.sqrt(dx * dx + dy * dy)


def euclidean_meters(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Euclidean 距離轉換為公尺（近似）"""
    return euclidean(lon1, lat1, lon2, lat2) * 111000


def load_stations(line_id: str) -> Dict[str, Tuple[float, float]]:
    """載入車站座標"""
    config = LINE_CONFIG.get(line_id)
    if not config:
        return {}

    filepath = BASE_DIR / config['stations_file']
    if not filepath.exists():
        print(f"⚠️ 找不到 {config['stations_file']}")
        return {}

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stations = {}
    for feature in data['features']:
        station_id = feature['properties']['station_id']
        coords = feature['geometry']['coordinates']
        stations[station_id] = (coords[0], coords[1])

    return stations


def load_track(track_id: str) -> List[List[float]]:
    """載入軌道座標"""
    track_file = TRACKS_DIR / f"{track_id}.geojson"
    if not track_file.exists():
        return []

    with open(track_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data['features'][0]['geometry']['coordinates']


def save_track(track_id: str, coords: List[List[float]]):
    """儲存軌道座標"""
    track_file = TRACKS_DIR / f"{track_id}.geojson"

    with open(track_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data['features'][0]['geometry']['coordinates'] = coords

    with open(track_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_station_in_track(station_coord: Tuple[float, float],
                          coords: List[List[float]],
                          tolerance: float = 0.00001) -> Optional[int]:
    """檢查車站座標是否已在軌道中"""
    for i, c in enumerate(coords):
        if abs(c[0] - station_coord[0]) < tolerance and abs(c[1] - station_coord[1]) < tolerance:
            return i
    return None


def find_nearest_point(station_coord: Tuple[float, float],
                       coords: List[List[float]]) -> Tuple[int, float]:
    """找出軌道中最接近車站的點及其距離"""
    min_dist = float('inf')
    min_idx = 0

    for i, c in enumerate(coords):
        dist = euclidean_meters(station_coord[0], station_coord[1], c[0], c[1])
        if dist < min_dist:
            min_dist = dist
            min_idx = i

    return min_idx, min_dist


def find_best_insertion_index(station_coord: Tuple[float, float],
                               coords: List[List[float]]) -> int:
    """
    找出車站座標應該插入的最佳位置
    在最近點附近找到讓軌道最平滑的插入位置
    """
    nearest_idx, _ = find_nearest_point(station_coord, coords)

    # 在最近點附近搜尋
    search_range = 15
    start_idx = max(0, nearest_idx - search_range)
    end_idx = min(len(coords) - 1, nearest_idx + search_range)

    best_idx = nearest_idx
    min_total_dist = float('inf')

    for i in range(start_idx, end_idx):
        # 計算在 i 和 i+1 之間插入的總距離
        dist_before = euclidean_meters(coords[i][0], coords[i][1],
                                       station_coord[0], station_coord[1])
        dist_after = euclidean_meters(station_coord[0], station_coord[1],
                                      coords[i+1][0], coords[i+1][1])
        total = dist_before + dist_after

        if total < min_total_dist:
            min_total_dist = total
            best_idx = i + 1

    return best_idx


def calculate_progress_euclidean(coords: List[List[float]],
                                  station_list: List[str],
                                  stations: Dict[str, Tuple[float, float]]) -> Dict[str, float]:
    """使用 Euclidean 計算 station_progress"""
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
        station_idx = find_station_in_track(station_coord, coords)
        if station_idx is None:
            # 找最近點
            station_idx, _ = find_nearest_point(station_coord, coords)

        # 計算累積距離
        cumulative = 0
        for i in range(station_idx):
            cumulative += euclidean(coords[i][0], coords[i][1],
                                    coords[i+1][0], coords[i+1][1])

        progress[station_id] = cumulative / total_length

    return progress


def calibrate_track(track_id: str,
                    stations: Dict[str, Tuple[float, float]],
                    station_list: List[str]) -> Tuple[List[List[float]], Dict[str, float], int]:
    """
    校準單一軌道
    返回：(更新後的座標, station_progress, 插入的車站數)
    """
    coords = load_track(track_id)
    if not coords:
        return [], {}, 0

    # 過濾有效車站
    valid_stations = [s for s in station_list if s in stations]
    if not valid_stations:
        return coords, {}, 0

    # 檢查每個車站，收集需要插入的
    insertions = []
    for station_id in valid_stations:
        station_coord = stations[station_id]
        existing_idx = find_station_in_track(station_coord, coords)

        if existing_idx is None:
            nearest_idx, dist = find_nearest_point(station_coord, coords)
            # 只處理距離在合理範圍內的（< 500m）
            if dist < 500:
                insert_idx = find_best_insertion_index(station_coord, coords)
                insertions.append((insert_idx, station_id, station_coord, dist))

    # 按索引排序後從後往前插入（避免索引偏移）
    insertions.sort(key=lambda x: x[0], reverse=True)

    for insert_idx, station_id, station_coord, dist in insertions:
        coords.insert(insert_idx, [station_coord[0], station_coord[1]])

    # 計算新的 progress
    new_progress = calculate_progress_euclidean(coords, valid_stations, stations)

    return coords, new_progress, len(insertions)


def calibrate_line(line_id: str, all_progress: Dict) -> Tuple[int, int, int]:
    """
    校準整條線路
    返回：(處理的軌道數, 修改的軌道數, 插入的車站總數)
    """
    config = LINE_CONFIG.get(line_id)
    if not config:
        return 0, 0, 0

    # 載入車站座標
    stations = load_stations(line_id)
    if not stations:
        return 0, 0, 0

    print(f"\n{'='*50}")
    print(f"{line_id} 線校準")
    print(f"{'='*50}")
    print(f"載入 {len(stations)} 個車站座標")

    # 找出該線路的所有軌道
    track_files = list(TRACKS_DIR.glob(f"{config['track_prefix']}*.geojson"))
    track_ids = sorted([f.stem for f in track_files])

    total_tracks = 0
    modified_tracks = 0
    total_insertions = 0

    for track_id in track_ids:
        if track_id not in all_progress:
            continue

        station_list = list(all_progress[track_id].keys())

        # 校準
        new_coords, new_progress, insertions = calibrate_track(
            track_id, stations, station_list
        )

        if not new_coords:
            continue

        total_tracks += 1

        if insertions > 0:
            # 儲存修改後的軌道
            save_track(track_id, new_coords)
            modified_tracks += 1
            total_insertions += insertions
            print(f"  ✅ {track_id}: 插入 {insertions} 個車站座標")

        # 更新 progress
        if new_progress:
            # 檢查是否有明顯變化
            max_diff = 0
            for sid, new_val in new_progress.items():
                old_val = all_progress[track_id].get(sid, 0)
                diff = abs(new_val - old_val)
                if diff > max_diff:
                    max_diff = diff

            if max_diff > 0.001:
                all_progress[track_id] = new_progress
                if insertions == 0:
                    print(f"  📊 {track_id}: progress 更新 (max diff: {max_diff*100:.2f}%)")

    return total_tracks, modified_tracks, total_insertions


def verify_line(line_id: str, all_progress: Dict):
    """驗證線路校準結果"""
    config = LINE_CONFIG.get(line_id)
    if not config:
        return

    stations = load_stations(line_id)
    if not stations:
        return

    print(f"\n--- {line_id} 線驗證 ---")

    # 檢查主要軌道（-1-0 或 -1-1）
    main_track_id = f"{config['track_prefix']}1-0"
    coords = load_track(main_track_id)

    if not coords:
        print(f"  ⚠️ 找不到主軌道 {main_track_id}")
        return

    errors = []
    for station_id, station_coord in stations.items():
        idx = find_station_in_track(station_coord, coords)
        if idx is None:
            _, dist = find_nearest_point(station_coord, coords)
            if dist > 5:
                errors.append((station_id, dist))

    if errors:
        print(f"  ⚠️ {len(errors)} 個站點仍有誤差 > 5m:")
        for sid, dist in sorted(errors, key=lambda x: -x[1])[:5]:
            print(f"      {sid}: {dist:.0f}m")
    else:
        print(f"  ✅ 主軌道所有站點誤差 < 5m")


def main():
    print("=" * 60)
    print("綠線/橘線/藍線軌道校準腳本")
    print("方法：將車站座標插入軌道，使用 Euclidean 計算 progress")
    print("=" * 60)

    # 載入現有 station_progress
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        all_progress = json.load(f)

    total_modified = 0
    total_insertions = 0

    # 校準各線路
    for line_id in ['G', 'O', 'BL']:
        tracks, modified, insertions = calibrate_line(line_id, all_progress)
        total_modified += modified
        total_insertions += insertions
        print(f"\n{line_id} 線: 處理 {tracks} 條軌道, 修改 {modified} 條, 插入 {insertions} 個座標")

    # 儲存更新後的 progress
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print("驗證結果")
    print("=" * 60)

    # 驗證
    for line_id in ['G', 'O', 'BL']:
        verify_line(line_id, all_progress)

    print(f"\n{'='*60}")
    print(f"✅ 校準完成！修改 {total_modified} 條軌道, 插入 {total_insertions} 個車站座標")
    print("=" * 60)


if __name__ == "__main__":
    main()
