#!/usr/bin/env python3
"""
修復 TMRT station_progress - 重新計算車站在軌道上的進度

問題：列車在多個車站附近會出現不自然的跳躍（坐過站又回來）
原因：station_progress 與實際軌道幾何不匹配

解決方案：
1. 讀取軌道 GeoJSON 座標
2. 為每個車站找到軌道上最近的點
3. 計算該點在軌道上的累積距離比例
"""

import json
import math
from pathlib import Path

# 專案路徑
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "public" / "data-tmrt"


def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """計算兩點之間的 Haversine 距離（公尺）"""
    R = 6371000  # 地球半徑（公尺）

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def euclidean_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """計算歐式距離（用於座標系統）"""
    dx = lon2 - lon1
    dy = lat2 - lat1
    return math.sqrt(dx * dx + dy * dy)


def point_to_segment_projection(
    px: float, py: float,
    ax: float, ay: float,
    bx: float, by: float
) -> tuple[float, float, float]:
    """
    計算點 P 在線段 AB 上的投影點

    Returns:
        (投影點x, 投影點y, 投影參數t)
        t=0 表示在 A 點，t=1 表示在 B 點
    """
    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy

    if length_sq == 0:
        return ax, ay, 0.0

    # 計算投影參數 t
    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    t = max(0, min(1, t))  # 限制在 [0, 1] 範圍內

    # 計算投影點
    proj_x = ax + t * dx
    proj_y = ay + t * dy

    return proj_x, proj_y, t


def find_closest_point_on_track(
    station_lon: float,
    station_lat: float,
    track_coords: list[list[float]]
) -> tuple[int, float, float]:
    """
    找到車站在軌道上最近的點

    Returns:
        (最近線段索引, 在該線段上的 t 值, 最小距離)
    """
    min_dist = float('inf')
    best_segment_idx = 0
    best_t = 0.0

    for i in range(len(track_coords) - 1):
        ax, ay = track_coords[i]
        bx, by = track_coords[i + 1]

        proj_x, proj_y, t = point_to_segment_projection(
            station_lon, station_lat,
            ax, ay, bx, by
        )

        dist = euclidean_distance(station_lon, station_lat, proj_x, proj_y)

        if dist < min_dist:
            min_dist = dist
            best_segment_idx = i
            best_t = t

    return best_segment_idx, best_t, min_dist


def calculate_cumulative_distances(track_coords: list[list[float]]) -> list[float]:
    """計算軌道上每個點的累積距離"""
    distances = [0.0]

    for i in range(1, len(track_coords)):
        prev = track_coords[i - 1]
        curr = track_coords[i]
        segment_dist = euclidean_distance(prev[0], prev[1], curr[0], curr[1])
        distances.append(distances[-1] + segment_dist)

    return distances


def calculate_station_progress(
    station_lon: float,
    station_lat: float,
    track_coords: list[list[float]],
    cumulative_distances: list[float]
) -> float:
    """計算車站在軌道上的進度 (0-1)"""
    total_length = cumulative_distances[-1]
    if total_length == 0:
        return 0.0

    # 找到最近的線段
    segment_idx, t, _ = find_closest_point_on_track(
        station_lon, station_lat, track_coords
    )

    # 計算在該線段上的距離
    segment_start_dist = cumulative_distances[segment_idx]
    segment_end_dist = cumulative_distances[segment_idx + 1]
    segment_length = segment_end_dist - segment_start_dist

    # 計算總進度
    progress_distance = segment_start_dist + t * segment_length
    progress = progress_distance / total_length

    return round(progress, 6)


def main():
    print("=" * 60)
    print("修復 TMRT station_progress")
    print("=" * 60)

    # 讀取車站資料
    stations_file = DATA_DIR / "stations" / "tmrt_stations.geojson"
    with open(stations_file, 'r', encoding='utf-8') as f:
        stations_data = json.load(f)

    # 建立車站座標對照表
    stations = {}
    for feature in stations_data['features']:
        station_id = feature['properties']['station_id']
        coords = feature['geometry']['coordinates']
        stations[station_id] = {
            'name': feature['properties']['name_zh'],
            'lon': coords[0],
            'lat': coords[1],
            'sequence': feature['properties']['sequence']
        }

    print(f"\n載入 {len(stations)} 個車站")

    # 車站順序 (G0 → G17 方向)
    station_order = ['G0', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G8a', 'G9',
                     'G10', 'G10a', 'G11', 'G12', 'G13', 'G14', 'G15', 'G16', 'G17']

    # 處理兩個方向的軌道
    result = {}

    for track_id in ['TMRT-G-0', 'TMRT-G-1']:
        print(f"\n處理軌道: {track_id}")

        # 讀取軌道資料
        track_file = DATA_DIR / "tracks" / f"{track_id}.geojson"
        with open(track_file, 'r', encoding='utf-8') as f:
            track_data = json.load(f)

        track_coords = track_data['features'][0]['geometry']['coordinates']
        print(f"  軌道點數: {len(track_coords)}")

        # 計算累積距離
        cumulative_distances = calculate_cumulative_distances(track_coords)
        total_length = cumulative_distances[-1]
        print(f"  軌道總長度: {total_length:.6f} (座標單位)")

        # 確定車站順序
        if track_id == 'TMRT-G-0':
            # 往高鐵台中站方向：G0 → G17
            ordered_stations = station_order
        else:
            # 往北屯總站方向：G17 → G0
            ordered_stations = list(reversed(station_order))

        # 計算每個車站的進度
        track_progress = {}
        print(f"\n  車站進度計算:")

        for i, station_id in enumerate(ordered_stations):
            station = stations[station_id]

            # 計算進度
            progress = calculate_station_progress(
                station['lon'],
                station['lat'],
                track_coords,
                cumulative_distances
            )

            track_progress[station_id] = progress

            # 找到最近點距離（用於除錯）
            _, _, min_dist = find_closest_point_on_track(
                station['lon'], station['lat'], track_coords
            )

            print(f"    {station_id:4s} {station['name']:10s}: {progress:.6f} (距軌道: {min_dist:.6f})")

        # 驗證進度是單調的
        prev_progress = -1
        monotonic = True
        for station_id in ordered_stations:
            curr_progress = track_progress[station_id]
            if curr_progress < prev_progress:
                print(f"  ⚠️  警告: {station_id} 進度 {curr_progress} < 前站 {prev_progress}")
                monotonic = False
            prev_progress = curr_progress

        if monotonic:
            print(f"  ✓ 進度單調遞增")

        result[track_id] = track_progress

    # 儲存結果
    output_file = DATA_DIR / "station_progress.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✓ 已儲存至 {output_file}")

    # 顯示對比
    print("\n" + "=" * 60)
    print("新舊進度對比 (TMRT-G-0)")
    print("=" * 60)

    # 讀取舊的進度
    old_progress = {
        "G0": 0.0, "G3": 0.058476, "G4": 0.098641, "G5": 0.195511,
        "G6": 0.246308, "G7": 0.333727, "G8": 0.396338, "G8a": 0.444773,
        "G9": 0.492026, "G10": 0.552274, "G10a": 0.603071, "G11": 0.634968,
        "G12": 0.686356, "G13": 0.781453, "G14": 0.835794, "G15": 0.876551,
        "G16": 0.937389, "G17": 1.0
    }

    print(f"{'車站':6s} {'舊進度':10s} {'新進度':10s} {'差異':10s}")
    print("-" * 40)
    for station_id in station_order:
        old = old_progress.get(station_id, 0)
        new = result['TMRT-G-0'].get(station_id, 0)
        diff = new - old
        diff_str = f"{diff:+.6f}" if diff != 0 else "0"
        print(f"{station_id:6s} {old:.6f}   {new:.6f}   {diff_str}")


if __name__ == '__main__':
    main()
