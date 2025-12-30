#!/usr/bin/env python3
"""
紅線軌道統一校準腳本

目標：所有紅線軌道都使用 red_line_stations.geojson 中的標準車站座標
新北投 (R22A) 例外 - 只用於 R-3-0/R-3-1

步驟：
1. 讀取標準車站座標
2. 分析每條軌道涵蓋哪些車站
3. 確保軌道座標中包含這些車站的精確位置
4. 重新計算 station_progress.json
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 路徑設定
BASE_DIR = Path(__file__).parent.parent / "public" / "data"
STATIONS_FILE = BASE_DIR / "red_line_stations.geojson"
TRACKS_DIR = BASE_DIR / "tracks"
PROGRESS_FILE = BASE_DIR / "station_progress.json"

def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """計算兩點間的球面距離（公尺）"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

def load_standard_stations() -> Dict[str, Tuple[float, float]]:
    """載入標準車站座標"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stations = {}
    for feature in data['features']:
        station_id = feature['properties']['station_id']
        coords = feature['geometry']['coordinates']
        stations[station_id] = (coords[0], coords[1])  # (lon, lat)

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

def calculate_track_length(coords: List[List[float]]) -> float:
    """計算軌道總長度"""
    total = 0
    for i in range(len(coords) - 1):
        total += haversine(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
    return total

def find_station_in_track(station_coord: Tuple[float, float], coords: List[List[float]], tolerance: float = 0.00001) -> Optional[int]:
    """檢查車站座標是否已在軌道中（使用精確座標匹配）"""
    for i, c in enumerate(coords):
        if abs(c[0] - station_coord[0]) < tolerance and abs(c[1] - station_coord[1]) < tolerance:
            return i
    return None

def find_nearest_point_in_track(station_coord: Tuple[float, float], coords: List[List[float]]) -> Tuple[int, float]:
    """找出軌道中最接近車站的點及其距離"""
    min_dist = float('inf')
    min_idx = 0

    for i, c in enumerate(coords):
        dist = haversine(station_coord[0], station_coord[1], c[0], c[1])
        if dist < min_dist:
            min_dist = dist
            min_idx = i

    return min_idx, min_dist

def find_insertion_index(station_coord: Tuple[float, float], coords: List[List[float]]) -> int:
    """
    找出車站座標應該插入的位置
    在最近點附近找到最佳插入位置（讓軌道平滑通過車站）
    """
    nearest_idx, _ = find_nearest_point_in_track(station_coord, coords)

    # 在最近點附近搜尋最佳插入位置
    search_range = 10
    start_idx = max(0, nearest_idx - search_range)
    end_idx = min(len(coords) - 1, nearest_idx + search_range)

    best_idx = nearest_idx
    min_total_dist = float('inf')

    for i in range(start_idx, end_idx):
        # 如果在 i 和 i+1 之間插入，計算總距離
        dist_before = haversine(coords[i][0], coords[i][1], station_coord[0], station_coord[1])
        dist_after = haversine(station_coord[0], station_coord[1], coords[i+1][0], coords[i+1][1])
        total = dist_before + dist_after

        if total < min_total_dist:
            min_total_dist = total
            best_idx = i + 1

    return best_idx

def get_track_station_coverage(track_id: str, progress: Dict) -> List[str]:
    """從 station_progress 取得軌道涵蓋的車站列表"""
    if track_id in progress:
        return list(progress[track_id].keys())
    return []

def calibrate_track(track_id: str, standard_stations: Dict[str, Tuple[float, float]],
                   station_list: List[str]) -> Tuple[List[List[float]], Dict[str, float]]:
    """
    校準單一軌道
    返回：(更新後的座標, 更新後的 station_progress)
    """
    coords = load_track(track_id)
    if not coords:
        print(f"  ⚠️ 找不到軌道檔案: {track_id}")
        return [], {}

    print(f"\n=== 校準 {track_id} ===")
    print(f"原始座標數: {len(coords)}")
    print(f"涵蓋車站: {station_list}")

    # 過濾出有效的車站（存在於標準座標中）
    valid_stations = [s for s in station_list if s in standard_stations]
    if not valid_stations:
        print(f"  ⚠️ 沒有有效車站")
        return coords, {}

    # 檢查每個車站
    modifications = []
    for station_id in valid_stations:
        station_coord = standard_stations[station_id]

        # 檢查是否已存在精確座標
        existing_idx = find_station_in_track(station_coord, coords)

        if existing_idx is not None:
            # 已存在，計算與最近軌道點的距離確認
            _, dist = find_nearest_point_in_track(station_coord, coords)
            print(f"  ✓ {station_id}: 已存在 (idx={existing_idx}, dist={dist:.1f}m)")
        else:
            # 需要插入
            nearest_idx, dist = find_nearest_point_in_track(station_coord, coords)
            print(f"  ⚠️ {station_id}: 需插入 (nearest_idx={nearest_idx}, dist={dist:.1f}m)")
            modifications.append((station_id, station_coord, dist))

    # 執行插入（從後往前插入避免索引偏移）
    if modifications:
        # 先計算所有插入位置
        insertions = []
        for station_id, station_coord, _ in modifications:
            insert_idx = find_insertion_index(station_coord, coords)
            insertions.append((insert_idx, station_id, station_coord))

        # 按索引排序後從後往前插入
        insertions.sort(key=lambda x: x[0], reverse=True)

        for insert_idx, station_id, station_coord in insertions:
            coords.insert(insert_idx, [station_coord[0], station_coord[1]])
            print(f"  → 插入 {station_id} 於索引 {insert_idx}")

    print(f"更新後座標數: {len(coords)}")

    # 重新計算 station_progress
    track_length = calculate_track_length(coords)
    print(f"軌道長度: {track_length:.0f}m")

    progress = {}
    cumulative = 0

    # 根據軌道方向決定進度計算方式
    is_reverse = track_id.endswith('-1')  # -1 表示逆向

    errors = []
    for station_id in valid_stations:
        station_coord = standard_stations[station_id]

        # 找到車站在軌道中的位置
        station_idx = find_station_in_track(station_coord, coords)
        if station_idx is None:
            # 找最近點
            station_idx, dist = find_nearest_point_in_track(station_coord, coords)
            if dist > 5:
                errors.append(f"{station_id}: {dist:.0f}m")

        # 計算到該點的累積距離
        cumulative = 0
        for i in range(station_idx):
            cumulative += haversine(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])

        progress[station_id] = cumulative / track_length if track_length > 0 else 0

    if errors:
        print(f"  ⚠️ 仍有誤差 > 5m: {', '.join(errors)}")
    else:
        print(f"  ✓ 所有車站誤差 < 5m")

    return coords, progress

def main():
    print("=" * 60)
    print("紅線軌道統一校準腳本")
    print("=" * 60)

    # 載入標準車站座標
    standard_stations = load_standard_stations()
    print(f"\n載入 {len(standard_stations)} 個標準車站座標:")
    for sid, coord in list(standard_stations.items())[:5]:
        print(f"  {sid}: ({coord[0]:.6f}, {coord[1]:.6f})")
    print("  ...")

    # 載入現有 station_progress
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        all_progress = json.load(f)

    # 列出所有紅線軌道
    red_tracks = [f.stem for f in TRACKS_DIR.glob("R-*.geojson")]
    red_tracks.sort()
    print(f"\n找到 {len(red_tracks)} 個紅線軌道:")
    print(f"  {red_tracks}")

    # 校準每條軌道
    updated_progress = {}
    for track_id in red_tracks:
        # 取得此軌道涵蓋的車站
        station_list = get_track_station_coverage(track_id, all_progress)

        if not station_list:
            print(f"\n⚠️ {track_id}: 無 station_progress 資料，跳過")
            continue

        # 校準
        new_coords, new_progress = calibrate_track(track_id, standard_stations, station_list)

        if new_coords:
            # 儲存更新後的軌道
            save_track(track_id, new_coords)

            # 更新 progress
            if new_progress:
                updated_progress[track_id] = new_progress

    # 合併並儲存 station_progress
    for track_id, progress in updated_progress.items():
        all_progress[track_id] = progress

    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"✅ 校準完成！更新了 {len(updated_progress)} 條軌道")
    print("=" * 60)

if __name__ == "__main__":
    main()
