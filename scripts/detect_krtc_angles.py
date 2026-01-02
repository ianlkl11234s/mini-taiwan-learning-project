#!/usr/bin/env python3
"""
偵測高雄捷運軌道上車站處的折角問題
"""

import json
import math
from pathlib import Path
from typing import NamedTuple


class StationAngle(NamedTuple):
    station_id: str
    name: str
    angle_change: float
    coord_index: int
    coords: tuple[float, float]
    bearing_before: float
    bearing_after: float


def calculate_bearing(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """計算從點1到點2的方位角（度）"""
    dx = lon2 - lon1
    dy = lat2 - lat1
    angle = math.degrees(math.atan2(dx, dy))
    return (angle + 360) % 360


def angle_difference(bearing1: float, bearing2: float) -> float:
    """計算兩個方位角之間的最小差異（0-180度）"""
    diff = abs(bearing2 - bearing1)
    if diff > 180:
        diff = 360 - diff
    return diff


def euclidean_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """計算歐式距離"""
    dx = lon2 - lon1
    dy = lat2 - lat1
    return math.sqrt(dx * dx + dy * dy)


def find_coord_index(track_coords: list, station_coord: tuple, tolerance: float = 0.00001) -> int:
    """找到車站座標在軌道中的索引（精確匹配）"""
    for i, coord in enumerate(track_coords):
        if abs(coord[0] - station_coord[0]) < tolerance and abs(coord[1] - station_coord[1]) < tolerance:
            return i
    return -1


def find_nearest_coord_index(track_coords: list, station_coord: tuple, max_distance: float = 0.0005) -> int:
    """找到最接近車站座標的軌道點索引"""
    min_dist = float('inf')
    nearest_idx = -1

    for i, coord in enumerate(track_coords):
        dist = euclidean_distance(coord[0], coord[1], station_coord[0], station_coord[1])
        if dist < min_dist:
            min_dist = dist
            nearest_idx = i

    if min_dist <= max_distance:
        return nearest_idx
    return -1


def analyze_track_angles(
    track_file: Path,
    stations_file: Path,
    angle_threshold: float = 10.0
) -> list[StationAngle]:
    """分析軌道上各車站的角度變化"""
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
        # 先精確匹配，再嘗試最近點
        idx = find_coord_index(track_coords, station_coord)
        if idx == -1:
            idx = find_nearest_coord_index(track_coords, station_coord)

        if idx == -1:
            continue

        if idx == 0 or idx >= len(track_coords) - 1:
            continue

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

    results.sort(key=lambda x: x.angle_change, reverse=True)
    return results


def main():
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "public" / "data" / "krtc"

    print("=" * 70)
    print("高雄捷運軌道折角偵測")
    print("=" * 70)

    stations_file = DATA_DIR / "stations" / "krtc_stations.geojson"

    # 處理紅線和橘線
    for line_id in ['R', 'O']:
        line_name = '紅線' if line_id == 'R' else '橘線'

        for direction in ['0', '1']:
            track_id = f'KRTC-{line_id}-{direction}'
            track_file = DATA_DIR / "tracks" / f"{track_id}.geojson"

            if not track_file.exists():
                continue

            print(f"\n📍 軌道: {track_id} ({line_name})")
            print("-" * 70)

            results = analyze_track_angles(track_file, stations_file)

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
    seen = set()

    for line_id in ['R', 'O']:
        for direction in ['0', '1']:
            track_id = f'KRTC-{line_id}-{direction}'
            track_file = DATA_DIR / "tracks" / f"{track_id}.geojson"

            if not track_file.exists():
                continue

            results = analyze_track_angles(track_file, stations_file)

            for r in results:
                if r.angle_change >= 10 and r.station_id not in seen:
                    seen.add(r.station_id)
                    all_problems.append((track_id, r))

    print(f"\n共 {len(all_problems)} 個問題站需要修正：")
    for track_id, r in all_problems:
        print(f"  - {r.station_id} {r.name}: {r.angle_change:.1f}°")


if __name__ == '__main__':
    main()
