#!/usr/bin/env python3
"""
偵測軌道上車站處的折角問題

分析軌道幾何，找出車站位置的方向變化角度，
標記可能導致列車停站時旋轉的問題站點。
"""

import json
import math
from pathlib import Path
from typing import NamedTuple


class StationAngle(NamedTuple):
    station_id: str
    name: str
    angle_change: float  # 角度變化（度）
    coord_index: int  # 在軌道座標中的索引
    coords: tuple[float, float]
    bearing_before: float  # 前一段方向
    bearing_after: float  # 後一段方向


def calculate_bearing(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """計算從點1到點2的方位角（度）"""
    dx = lon2 - lon1
    dy = lat2 - lat1
    angle = math.degrees(math.atan2(dx, dy))  # 以北為 0 度
    return (angle + 360) % 360


def angle_difference(bearing1: float, bearing2: float) -> float:
    """計算兩個方位角之間的最小差異（0-180度）"""
    diff = abs(bearing2 - bearing1)
    if diff > 180:
        diff = 360 - diff
    return diff


def find_coord_index(track_coords: list, station_coord: tuple, tolerance: float = 0.00001) -> int:
    """找到車站座標在軌道中的索引"""
    for i, coord in enumerate(track_coords):
        if abs(coord[0] - station_coord[0]) < tolerance and abs(coord[1] - station_coord[1]) < tolerance:
            return i
    return -1


def analyze_track_angles(
    track_file: Path,
    stations_file: Path,
    angle_threshold: float = 10.0
) -> list[StationAngle]:
    """
    分析軌道上各車站的角度變化

    Args:
        track_file: 軌道 GeoJSON 檔案路徑
        stations_file: 車站 GeoJSON 檔案路徑
        angle_threshold: 角度閾值（度），超過此值視為問題站

    Returns:
        所有車站的角度分析結果
    """
    # 讀取資料
    with open(track_file, 'r', encoding='utf-8') as f:
        track_data = json.load(f)

    with open(stations_file, 'r', encoding='utf-8') as f:
        stations_data = json.load(f)

    track_coords = track_data['features'][0]['geometry']['coordinates']

    # 建立車站座標對照
    stations = {}
    for feature in stations_data['features']:
        sid = feature['properties']['station_id']
        coords = feature['geometry']['coordinates']
        name = feature['properties']['name_zh']
        stations[sid] = {'name': name, 'coords': tuple(coords)}

    results = []

    for sid, sdata in stations.items():
        station_coord = sdata['coords']
        idx = find_coord_index(track_coords, station_coord)

        if idx == -1:
            print(f"  ⚠️  {sid} {sdata['name']}: 找不到對應的軌道點")
            continue

        # 需要前後都有點才能計算角度
        if idx == 0 or idx >= len(track_coords) - 1:
            continue

        # 計算前後方位角
        prev_coord = track_coords[idx - 1]
        curr_coord = track_coords[idx]
        next_coord = track_coords[idx + 1]

        bearing_before = calculate_bearing(
            prev_coord[0], prev_coord[1],
            curr_coord[0], curr_coord[1]
        )
        bearing_after = calculate_bearing(
            curr_coord[0], curr_coord[1],
            next_coord[0], next_coord[1]
        )

        angle_change = angle_difference(bearing_before, bearing_after)

        results.append(StationAngle(
            station_id=sid,
            name=sdata['name'],
            angle_change=angle_change,
            coord_index=idx,
            coords=station_coord,
            bearing_before=bearing_before,
            bearing_after=bearing_after
        ))

    # 按角度排序
    results.sort(key=lambda x: x.angle_change, reverse=True)

    return results


def main():
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "public" / "data" / "klrt"

    print("=" * 70)
    print("高雄輕軌軌道折角偵測")
    print("=" * 70)

    stations_file = DATA_DIR / "stations" / "klrt_stations.geojson"

    for track_id in ['KLRT-C-0', 'KLRT-C-1']:
        track_file = DATA_DIR / "tracks" / f"{track_id}.geojson"

        print(f"\n📍 軌道: {track_id}")
        print("-" * 70)

        results = analyze_track_angles(track_file, stations_file)

        # 統計
        problem_count = 0
        warning_count = 0

        print(f"\n{'站號':8s} {'站名':12s} {'角度變化':10s} {'狀態':6s} {'前方位':8s} {'後方位':8s}")
        print("-" * 70)

        for r in results:
            if r.angle_change >= 15:
                status = "❌ 嚴重"
                problem_count += 1
            elif r.angle_change >= 10:
                status = "⚠️ 警告"
                warning_count += 1
            elif r.angle_change >= 5:
                status = "📍 輕微"
            else:
                status = "✅ 正常"

            print(f"{r.station_id:8s} {r.name:12s} {r.angle_change:8.2f}° {status:6s} "
                  f"{r.bearing_before:7.1f}° {r.bearing_after:7.1f}°")

        print("-" * 70)
        print(f"統計: 嚴重問題 {problem_count} 站 | 警告 {warning_count} 站 | 總計 {len(results)} 站")

    # 輸出需要修正的車站清單
    print("\n" + "=" * 70)
    print("需要修正的車站（角度 >= 10°）")
    print("=" * 70)

    all_problems = []
    for track_id in ['KLRT-C-0', 'KLRT-C-1']:
        track_file = DATA_DIR / "tracks" / f"{track_id}.geojson"
        results = analyze_track_angles(track_file, stations_file)

        for r in results:
            if r.angle_change >= 10:
                all_problems.append((track_id, r))

    # 去重（兩個方向可能都有同一站）
    seen = set()
    unique_problems = []
    for track_id, r in all_problems:
        if r.station_id not in seen:
            seen.add(r.station_id)
            unique_problems.append((track_id, r))

    print(f"\n共 {len(unique_problems)} 個問題站需要修正：")
    for track_id, r in unique_problems:
        print(f"  - {r.station_id} {r.name}: {r.angle_change:.1f}°")


if __name__ == '__main__':
    main()
