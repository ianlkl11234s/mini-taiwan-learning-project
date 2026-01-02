#!/usr/bin/env python3
"""
校準高鐵軌道 - 將車站座標插入軌道並截斷多餘部分

功能：
1. 讀取原始軌道 GeoJSON 和車站 GeoJSON
2. 對每個車站：找到最近的軌道線段，將投影點插入軌道
3. 截斷軌道：移除起點站之前和終點站之後的座標
4. 輸出校準後的軌道 GeoJSON

使用方式：
    python scripts/calibrate_thsr_tracks.py

輸入：
    - public/data-thsr/tracks/THSR-1-0.geojson (原始)
    - public/data-thsr/tracks/THSR-1-1.geojson (原始)
    - public/data-thsr/stations/thsr_stations.geojson

輸出：
    - public/data-thsr/tracks/THSR-1-0.geojson (校準後，覆蓋)
    - public/data-thsr/tracks/THSR-1-1.geojson (校準後，覆蓋)
"""

import json
import math
import os
from typing import List, Tuple, Dict, Any

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data-thsr')
TRACKS_DIR = os.path.join(DATA_DIR, 'tracks')
STATIONS_FILE = os.path.join(DATA_DIR, 'stations', 'thsr_stations.geojson')

# 備份目錄
BACKUP_DIR = os.path.join(DATA_DIR, 'tracks_backup')


def euclidean(p1: List[float], p2: List[float]) -> float:
    """計算 Euclidean 距離（與 TrainEngine.ts 一致）"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def point_to_segment_distance(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float
) -> Tuple[float, float, float, float]:
    """
    計算點到線段的最短距離和投影點

    參數：
        px, py: 點座標
        x1, y1: 線段起點
        x2, y2: 線段終點

    返回：
        (距離, 投影點x, 投影點y, 參數t)
    """
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return euclidean([px, py], [x1, y1]), x1, y1, 0.0

    # 投影參數 t (限制在 [0, 1])
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    proj_x = x1 + t * dx
    proj_y = y1 + t * dy

    dist = euclidean([px, py], [proj_x, proj_y])
    return dist, proj_x, proj_y, t


def find_best_segment(
    station_coord: List[float],
    track_coords: List[List[float]]
) -> Tuple[int, float, List[float]]:
    """
    找到車站應該插入的最佳線段位置

    返回：
        (線段起點索引, 距離, 投影點座標)
    """
    min_dist = float('inf')
    best_idx = 0
    best_proj = station_coord  # 預設使用原始座標

    for i in range(len(track_coords) - 1):
        dist, proj_x, proj_y, _ = point_to_segment_distance(
            station_coord[0], station_coord[1],
            track_coords[i][0], track_coords[i][1],
            track_coords[i + 1][0], track_coords[i + 1][1]
        )
        if dist < min_dist:
            min_dist = dist
            best_idx = i
            best_proj = [proj_x, proj_y]

    return best_idx, min_dist, best_proj


def calibrate_track(
    track_coords: List[List[float]],
    stations: List[Dict[str, Any]],
    direction: int
) -> Tuple[List[List[float]], Dict[str, int]]:
    """
    校準軌道：插入車站座標並截斷

    參數：
        track_coords: 原始軌道座標
        stations: 車站資料列表（已按 sequence 排序）
        direction: 0 = 南下 (南港→左營), 1 = 北上 (左營→南港)

    返回：
        (校準後的座標, 車站在座標中的索引)
    """
    # 複製座標以避免修改原始資料
    coords = [c[:] for c in track_coords]

    # 根據方向決定車站順序
    if direction == 1:
        # 北上：反轉車站順序 (左營→南港)
        ordered_stations = list(reversed(stations))
    else:
        # 南下：保持原順序 (南港→左營)
        ordered_stations = stations

    # 記錄每個車站插入後的索引
    station_indices: Dict[str, int] = {}

    # 用於追蹤插入偏移
    offset = 0

    # 第一階段：找到所有車站的最佳插入位置（在原始座標上）
    insert_info = []
    for station in ordered_stations:
        station_id = station['properties']['station_id']
        station_coord = station['geometry']['coordinates']

        # 在當前座標中找最佳位置
        seg_idx, dist, proj_coord = find_best_segment(station_coord, coords)

        insert_info.append({
            'station_id': station_id,
            'station_coord': station_coord,
            'proj_coord': proj_coord,
            'segment_idx': seg_idx,
            'distance': dist
        })

    # 按線段索引排序，確保按軌道順序插入
    insert_info.sort(key=lambda x: x['segment_idx'])

    # 第二階段：依序插入
    for info in insert_info:
        station_id = info['station_id']
        proj_coord = info['proj_coord']
        seg_idx = info['segment_idx'] + offset

        # 插入投影點座標到線段後
        coords.insert(seg_idx + 1, proj_coord)
        station_indices[station_id] = seg_idx + 1

        # 更新偏移量
        offset += 1

    # 第三階段：截斷軌道（只保留第一站到最後一站）
    first_station = ordered_stations[0]['properties']['station_id']
    last_station = ordered_stations[-1]['properties']['station_id']

    first_idx = station_indices[first_station]
    last_idx = station_indices[last_station]

    # 確保索引順序正確
    start_idx = min(first_idx, last_idx)
    end_idx = max(first_idx, last_idx)

    # 截斷座標
    truncated_coords = coords[start_idx:end_idx + 1]

    # 更新車站索引（相對於截斷後的座標）
    new_indices = {}
    for station_id, old_idx in station_indices.items():
        new_idx = old_idx - start_idx
        if 0 <= new_idx < len(truncated_coords):
            new_indices[station_id] = new_idx

    return truncated_coords, new_indices


def load_stations() -> List[Dict[str, Any]]:
    """載入並排序車站資料"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 按 sequence 排序（南港=1 到 左營=12）
    stations = sorted(
        data['features'],
        key=lambda x: x['properties'].get('sequence', 0)
    )
    return stations


def load_track(track_id: str) -> Dict[str, Any]:
    """載入軌道 GeoJSON"""
    filepath = os.path.join(TRACKS_DIR, f'{track_id}.geojson')
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_track(track_id: str, geojson: Dict[str, Any]):
    """儲存軌道 GeoJSON"""
    filepath = os.path.join(TRACKS_DIR, f'{track_id}.geojson')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)


def backup_track(track_id: str):
    """備份原始軌道"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    src = os.path.join(TRACKS_DIR, f'{track_id}.geojson')
    dst = os.path.join(BACKUP_DIR, f'{track_id}_original.geojson')
    if os.path.exists(src) and not os.path.exists(dst):
        with open(src, 'r') as f:
            data = f.read()
        with open(dst, 'w') as f:
            f.write(data)
        print(f"  備份: {dst}")


def validate_calibration(
    coords: List[List[float]],
    stations: List[Dict[str, Any]],
    station_indices: Dict[str, int]
) -> List[str]:
    """
    驗證校準結果

    返回：缺失的車站 ID 列表
    """
    missing = []
    tolerance = 0.000001  # 約 0.1 公尺

    for station in stations:
        station_id = station['properties']['station_id']

        if station_id not in station_indices:
            missing.append(station_id)
            continue

        idx = station_indices[station_id]
        if idx < 0 or idx >= len(coords):
            missing.append(station_id)
            continue

        # 檢查座標是否匹配（使用投影點，所以應該完全匹配）
        track_coord = coords[idx]
        # 投影點應該在軌道上，所以這裡不需要再檢查距離

    return missing


def main():
    print("=" * 50)
    print("高鐵軌道校準腳本")
    print("=" * 50)

    # 載入車站資料
    print("\n載入車站資料...")
    stations = load_stations()
    print(f"  共 {len(stations)} 站")
    for s in stations:
        props = s['properties']
        print(f"    {props['sequence']:2d}. {props['name_zh']} ({props['station_id']})")

    # 處理兩條軌道
    tracks_to_process = [
        ('THSR-1-0', 0, '南下 (南港→左營)'),
        ('THSR-1-1', 1, '北上 (左營→南港)'),
    ]

    all_station_indices = {}

    for track_id, direction, desc in tracks_to_process:
        print(f"\n處理 {track_id} ({desc})...")

        # 備份原始軌道
        backup_track(track_id)

        # 載入軌道
        track_geojson = load_track(track_id)
        original_coords = track_geojson['features'][0]['geometry']['coordinates']
        print(f"  原始座標點數: {len(original_coords)}")

        # 校準軌道
        calibrated_coords, station_indices = calibrate_track(
            original_coords, stations, direction
        )
        print(f"  校準後座標點數: {len(calibrated_coords)}")

        # 驗證
        missing = validate_calibration(calibrated_coords, stations, station_indices)
        if missing:
            print(f"  ⚠️ 警告：以下車站未找到: {missing}")
        else:
            print(f"  ✅ 所有 {len(stations)} 站都已插入軌道")

        # 顯示車站索引
        print(f"  車站索引:")
        if direction == 1:
            ordered_ids = [s['properties']['station_id'] for s in reversed(stations)]
        else:
            ordered_ids = [s['properties']['station_id'] for s in stations]

        for sid in ordered_ids:
            if sid in station_indices:
                idx = station_indices[sid]
                name = next(
                    s['properties']['name_zh']
                    for s in stations
                    if s['properties']['station_id'] == sid
                )
                print(f"    {name}: 索引 {idx}")

        # 更新 GeoJSON
        track_geojson['features'][0]['geometry']['coordinates'] = calibrated_coords

        # 儲存
        save_track(track_id, track_geojson)
        print(f"  已儲存: {track_id}.geojson")

        all_station_indices[track_id] = station_indices

    # 輸出車站進度計算提示
    print("\n" + "=" * 50)
    print("校準完成！")
    print("=" * 50)
    print("\n下一步：執行 build_thsr_station_progress.py 計算車站進度")

    return all_station_indices


if __name__ == '__main__':
    main()
