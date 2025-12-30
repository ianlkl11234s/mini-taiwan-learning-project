#!/usr/bin/env python3
"""
紅線軌道校準腳本 v2

使用與其他線路相同的 v2 演算法：
- 找到車站最接近的「線段」而非「頂點」
- 在該線段的兩個端點之間插入車站座標
- 避免繞道問題
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional

BASE_DIR = Path(__file__).parent.parent / "public" / "data"
TRACKS_DIR = BASE_DIR / "tracks"
PROGRESS_FILE = BASE_DIR / "station_progress.json"
STATIONS_FILE = BASE_DIR / "red_line_stations.geojson"


def euclidean(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Euclidean 距離"""
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
        return euclidean(px, py, x1, y1), x1, y1

    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))

    proj_x = x1 + t * dx
    proj_y = y1 + t * dy

    dist = euclidean(px, py, proj_x, proj_y)
    return dist, proj_x, proj_y


def find_best_segment(station_coord: Tuple[float, float],
                      coords: List[List[float]]) -> Tuple[int, float]:
    """找到車站最接近的線段"""
    min_dist = float('inf')
    best_idx = 0

    for i in range(len(coords) - 1):
        dist, _, _ = point_to_segment_distance(
            station_coord[0], station_coord[1],
            coords[i][0], coords[i][1],
            coords[i+1][0], coords[i+1][1]
        )
        if dist < min_dist:
            min_dist = dist
            best_idx = i

    return best_idx, min_dist


def load_stations() -> Dict[str, Tuple[float, float]]:
    """載入車站座標"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stations = {}
    for feature in data['features']:
        station_id = feature['properties']['station_id']
        coords = feature['geometry']['coordinates']
        stations[station_id] = (coords[0], coords[1])

    return stations


def remove_station_from_track(coords: List[List[float]],
                               station_coord: Tuple[float, float]) -> List[List[float]]:
    """從軌道中移除車站座標（如果存在）"""
    new_coords = []
    for c in coords:
        if not (abs(c[0] - station_coord[0]) < 0.00001 and
                abs(c[1] - station_coord[1]) < 0.00001):
            new_coords.append(c)
    return new_coords


def check_zigzag(coords: List[List[float]], idx: int) -> float:
    """檢查指定位置的轉彎角度"""
    if idx < 1 or idx >= len(coords) - 1:
        return 0

    def angle(c1, c2):
        return math.atan2(c2[1] - c1[1], c2[0] - c1[0])

    a1 = angle(coords[idx-1], coords[idx])
    a2 = angle(coords[idx], coords[idx+1])
    diff = abs(math.degrees(a2 - a1))
    if diff > 180:
        diff = 360 - diff
    return diff


def calibrate_track(track_id: str, stations: Dict[str, Tuple[float, float]],
                    station_list: List[str]) -> Tuple[List[List[float]], Dict[str, float], int]:
    """校準單一軌道"""
    track_file = TRACKS_DIR / f"{track_id}.geojson"
    if not track_file.exists():
        return [], {}, 0

    with open(track_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    coords = data['features'][0]['geometry']['coordinates']

    valid_stations = [s for s in station_list if s in stations]
    if not valid_stations:
        return coords, {}, 0

    fixes = 0

    # 檢查每個車站
    for station_id in valid_stations:
        station_coord = stations[station_id]

        # 檢查車站是否已在軌道中
        existing_idx = None
        for i, c in enumerate(coords):
            if abs(c[0] - station_coord[0]) < 0.00001 and abs(c[1] - station_coord[1]) < 0.00001:
                existing_idx = i
                break

        if existing_idx is not None:
            # 檢查是否有 zigzag
            turn_angle = check_zigzag(coords, existing_idx)
            if turn_angle > 60:
                print(f"    {station_id}: 發現 {turn_angle:.0f}° 轉彎，重新定位...")

                # 移除錯誤位置的車站
                coords = remove_station_from_track(coords, station_coord)

                # 找正確的線段
                segment_idx, dist = find_best_segment(station_coord, coords)

                # 在正確位置插入
                coords.insert(segment_idx + 1, [station_coord[0], station_coord[1]])

                # 驗證
                new_idx = segment_idx + 1
                new_turn = check_zigzag(coords, new_idx)
                print(f"    {station_id}: 修正後轉彎 {new_turn:.0f}°")
                fixes += 1
        else:
            # 車站不在軌道中，需要插入
            segment_idx, dist = find_best_segment(station_coord, coords)
            dist_m = dist * 111000

            if dist_m < 500:
                coords.insert(segment_idx + 1, [station_coord[0], station_coord[1]])
                fixes += 1

    # 計算新的 progress
    total_length = 0
    for i in range(len(coords) - 1):
        total_length += euclidean(coords[i][0], coords[i][1],
                                  coords[i+1][0], coords[i+1][1])

    progress = {}
    for station_id in valid_stations:
        if station_id not in stations:
            continue

        station_coord = stations[station_id]
        station_idx = None
        for i, c in enumerate(coords):
            if abs(c[0] - station_coord[0]) < 0.00001 and abs(c[1] - station_coord[1]) < 0.00001:
                station_idx = i
                break

        if station_idx is None:
            min_dist = float('inf')
            for i, c in enumerate(coords):
                dist = euclidean(station_coord[0], station_coord[1], c[0], c[1])
                if dist < min_dist:
                    min_dist = dist
                    station_idx = i

        cumulative = 0
        for i in range(station_idx):
            cumulative += euclidean(coords[i][0], coords[i][1],
                                    coords[i+1][0], coords[i+1][1])

        progress[station_id] = cumulative / total_length if total_length > 0 else 0

    return coords, progress, fixes


def main():
    print("=" * 60)
    print("紅線軌道校準腳本 v2")
    print("修正 zigzag 問題")
    print("=" * 60)

    stations = load_stations()
    print(f"載入 {len(stations)} 個車站座標")

    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        all_progress = json.load(f)

    # 找出所有紅線軌道
    track_files = list(TRACKS_DIR.glob("R-*.geojson"))
    track_ids = sorted([f.stem for f in track_files])

    total_fixes = 0
    modified_tracks = []

    for track_id in track_ids:
        if track_id not in all_progress:
            continue

        station_list = list(all_progress[track_id].keys())
        new_coords, new_progress, fixes = calibrate_track(track_id, stations, station_list)

        if fixes > 0:
            # 儲存軌道
            track_file = TRACKS_DIR / f"{track_id}.geojson"
            with open(track_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['features'][0]['geometry']['coordinates'] = new_coords
            with open(track_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            all_progress[track_id] = new_progress
            modified_tracks.append(track_id)
            total_fixes += fixes
            print(f"  ✅ {track_id}: 修正 {fixes} 個站點")

    # 儲存 progress
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ 完成！修正 {len(modified_tracks)} 條軌道，共 {total_fixes} 個站點")
    print("=" * 60)


if __name__ == "__main__":
    main()
