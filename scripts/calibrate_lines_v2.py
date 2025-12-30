#!/usr/bin/env python3
"""
綠線/橘線/藍線軌道校準腳本 v2

修正版：正確處理插入位置，避免繞道問題

關鍵改進：
- 找到車站最接近的「線段」而非「頂點」
- 在該線段的兩個端點之間插入車站座標
- 確保軌道方向一致，不會產生 180° 轉彎
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional

BASE_DIR = Path(__file__).parent.parent / "public" / "data"
TRACKS_DIR = BASE_DIR / "tracks"
PROGRESS_FILE = BASE_DIR / "station_progress.json"

LINE_CONFIG = {
    'G': {'stations_file': 'green_line_stations.geojson', 'track_prefix': 'G-'},
    'O': {'stations_file': 'orange_line_stations.geojson', 'track_prefix': 'O-'},
    'BL': {'stations_file': 'blue_line_stations.geojson', 'track_prefix': 'BL-'},
}


def euclidean(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Euclidean 距離（與 TrainEngine.ts 相同）"""
    dx = lon2 - lon1
    dy = lat2 - lat1
    return math.sqrt(dx * dx + dy * dy)


def point_to_segment_distance(px: float, py: float,
                               x1: float, y1: float,
                               x2: float, y2: float) -> Tuple[float, float, float]:
    """
    計算點到線段的最短距離，並返回投影點座標
    返回：(距離, 投影點x, 投影點y)
    """
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        # 線段長度為 0
        return euclidean(px, py, x1, y1), x1, y1

    # 計算投影參數 t
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)

    # 限制 t 在 [0, 1] 範圍內
    t = max(0, min(1, t))

    # 計算投影點
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy

    dist = euclidean(px, py, proj_x, proj_y)
    return dist, proj_x, proj_y


def find_best_segment_for_station(station_coord: Tuple[float, float],
                                   coords: List[List[float]]) -> Tuple[int, float]:
    """
    找到車站最接近的線段
    返回：(線段起點索引, 距離)

    例如返回 (5, 0.001) 表示車站最接近 coords[5] 到 coords[6] 這條線段
    """
    min_dist = float('inf')
    best_segment_idx = 0

    for i in range(len(coords) - 1):
        dist, _, _ = point_to_segment_distance(
            station_coord[0], station_coord[1],
            coords[i][0], coords[i][1],
            coords[i+1][0], coords[i+1][1]
        )
        if dist < min_dist:
            min_dist = dist
            best_segment_idx = i

    return best_segment_idx, min_dist


def load_stations(line_id: str) -> Dict[str, Tuple[float, float]]:
    """載入車站座標"""
    config = LINE_CONFIG.get(line_id)
    if not config:
        return {}

    filepath = BASE_DIR / config['stations_file']
    if not filepath.exists():
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


def calculate_progress_euclidean(coords: List[List[float]],
                                  station_list: List[str],
                                  stations: Dict[str, Tuple[float, float]]) -> Dict[str, float]:
    """使用 Euclidean 計算 station_progress"""
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
        station_idx = find_station_in_track(station_coord, coords)

        if station_idx is None:
            # 找最近的頂點
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


def calibrate_track(track_id: str,
                    stations: Dict[str, Tuple[float, float]],
                    station_list: List[str]) -> Tuple[List[List[float]], Dict[str, float], int]:
    """
    校準單一軌道（v2 改進版）
    """
    coords = load_track(track_id)
    if not coords:
        return [], {}, 0

    valid_stations = [s for s in station_list if s in stations]
    if not valid_stations:
        return coords, {}, 0

    # 收集需要插入的車站
    insertions = []
    for station_id in valid_stations:
        station_coord = stations[station_id]
        existing_idx = find_station_in_track(station_coord, coords)

        if existing_idx is None:
            # 找到最接近的線段
            segment_idx, dist = find_best_segment_for_station(station_coord, coords)
            dist_m = dist * 111000

            # 只處理距離在合理範圍內的（< 500m）
            if dist_m < 500:
                insertions.append((segment_idx, station_id, station_coord, dist_m))

    # 按線段索引排序（從後往前插入避免索引偏移）
    # 關鍵：在 segment_idx + 1 的位置插入，這樣就是在線段的兩個端點之間
    insertions.sort(key=lambda x: x[0], reverse=True)

    for segment_idx, station_id, station_coord, dist_m in insertions:
        # 在 segment_idx 和 segment_idx+1 之間插入
        # 也就是在索引 segment_idx + 1 處插入
        insert_pos = segment_idx + 1
        coords.insert(insert_pos, [station_coord[0], station_coord[1]])

    # 計算新的 progress
    new_progress = calculate_progress_euclidean(coords, valid_stations, stations)

    return coords, new_progress, len(insertions)


def calibrate_line(line_id: str, all_progress: Dict) -> Tuple[int, int, int]:
    """校準整條線路"""
    config = LINE_CONFIG.get(line_id)
    if not config:
        return 0, 0, 0

    stations = load_stations(line_id)
    if not stations:
        return 0, 0, 0

    print(f"\n{'='*50}")
    print(f"{line_id} 線校準 (v2)")
    print(f"{'='*50}")
    print(f"載入 {len(stations)} 個車站座標")

    track_files = list(TRACKS_DIR.glob(f"{config['track_prefix']}*.geojson"))
    track_ids = sorted([f.stem for f in track_files])

    total_tracks = 0
    modified_tracks = 0
    total_insertions = 0

    for track_id in track_ids:
        if track_id not in all_progress:
            continue

        station_list = list(all_progress[track_id].keys())
        new_coords, new_progress, insertions = calibrate_track(
            track_id, stations, station_list
        )

        if not new_coords:
            continue

        total_tracks += 1

        if insertions > 0:
            save_track(track_id, new_coords)
            modified_tracks += 1
            total_insertions += insertions
            print(f"  ✅ {track_id}: 插入 {insertions} 個車站座標")

        if new_progress:
            max_diff = 0
            for sid, new_val in new_progress.items():
                old_val = all_progress[track_id].get(sid, 0)
                diff = abs(new_val - old_val)
                if diff > max_diff:
                    max_diff = diff

            if max_diff > 0.001:
                all_progress[track_id] = new_progress

    return total_tracks, modified_tracks, total_insertions


def verify_no_zigzag(track_id: str, station_id: str, station_coord: Tuple[float, float]):
    """驗證沒有 zigzag 問題"""
    coords = load_track(track_id)

    # 找車站位置
    station_idx = find_station_in_track(station_coord, coords)
    if station_idx is None or station_idx < 2 or station_idx >= len(coords) - 2:
        return True

    # 檢查前後點的方向變化
    def angle(c1, c2):
        return math.atan2(c2[1] - c1[1], c2[0] - c1[0])

    angle_before = angle(coords[station_idx-1], coords[station_idx])
    angle_after = angle(coords[station_idx], coords[station_idx+1])

    diff = abs(math.degrees(angle_after - angle_before))
    if diff > 180:
        diff = 360 - diff

    if diff > 90:
        print(f"  ⚠️ {track_id} {station_id}: 轉彎角度 {diff:.0f}°")
        return False

    return True


def main():
    print("=" * 60)
    print("綠線/橘線/藍線軌道校準腳本 v2")
    print("改進：正確處理線段插入，避免繞道問題")
    print("=" * 60)

    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        all_progress = json.load(f)

    total_modified = 0
    total_insertions = 0

    for line_id in ['G', 'O', 'BL']:
        tracks, modified, insertions = calibrate_line(line_id, all_progress)
        total_modified += modified
        total_insertions += insertions
        print(f"\n{line_id} 線: 處理 {tracks} 條軌道, 修改 {modified} 條, 插入 {insertions} 個座標")

    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)

    # 驗證關鍵站點
    print(f"\n{'='*60}")
    print("驗證關鍵站點（檢查是否有 zigzag）")
    print("=" * 60)

    test_cases = [
        ('O-1-0', 'O14', (121.491451, 25.059808)),  # 菜寮
        ('G-1-0', 'G13', (121.510184, 25.049554)),  # 北門
        ('BL-1-0', 'BL12', None),  # 忠孝新生
    ]

    # 載入 BL12 座標
    bl_stations = load_stations('BL')
    if 'BL12' in bl_stations:
        test_cases[2] = ('BL-1-0', 'BL12', bl_stations['BL12'])

    for track_id, station_id, station_coord in test_cases:
        if station_coord:
            verify_no_zigzag(track_id, station_id, station_coord)

    print(f"\n{'='*60}")
    print(f"✅ 校準完成！修改 {total_modified} 條軌道, 插入 {total_insertions} 個車站座標")
    print("=" * 60)


if __name__ == "__main__":
    main()
