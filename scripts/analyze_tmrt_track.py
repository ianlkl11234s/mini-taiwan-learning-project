#!/usr/bin/env python3
"""
分析 TMRT 軌道幾何 - 找出可能導致列車跳躍的問題區段
"""

import json
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "public" / "data-tmrt"


def euclidean_distance(lon1, lat1, lon2, lat2):
    dx = lon2 - lon1
    dy = lat2 - lat1
    return math.sqrt(dx * dx + dy * dy)


def calculate_bearing(lon1, lat1, lon2, lat2):
    """計算從點1到點2的方位角（度）"""
    dx = lon2 - lon1
    dy = lat2 - lat1
    angle = math.degrees(math.atan2(dx, dy))  # 以北為 0 度
    return (angle + 360) % 360


def analyze_track(track_id):
    """分析軌道的方向變化"""
    track_file = DATA_DIR / "tracks" / f"{track_id}.geojson"
    with open(track_file, 'r', encoding='utf-8') as f:
        track_data = json.load(f)

    coords = track_data['features'][0]['geometry']['coordinates']

    print(f"\n{'=' * 60}")
    print(f"軌道分析: {track_id}")
    print(f"{'=' * 60}")
    print(f"總點數: {len(coords)}")

    # 讀取車站座標
    stations_file = DATA_DIR / "stations" / "tmrt_stations.geojson"
    with open(stations_file, 'r', encoding='utf-8') as f:
        stations_data = json.load(f)

    stations = {}
    for feature in stations_data['features']:
        station_id = feature['properties']['station_id']
        scoords = feature['geometry']['coordinates']
        stations[station_id] = {
            'name': feature['properties']['name_zh'],
            'lon': scoords[0],
            'lat': scoords[1]
        }

    # 計算每個線段的方向
    bearings = []
    for i in range(len(coords) - 1):
        bearing = calculate_bearing(
            coords[i][0], coords[i][1],
            coords[i + 1][0], coords[i + 1][1]
        )
        dist = euclidean_distance(
            coords[i][0], coords[i][1],
            coords[i + 1][0], coords[i + 1][1]
        )
        bearings.append({
            'index': i,
            'bearing': bearing,
            'distance': dist,
            'start': coords[i],
            'end': coords[i + 1]
        })

    # 找出方向急劇變化的點（可能導致跳躍）
    print("\n方向急劇變化的點 (>45度):")
    print("-" * 60)

    sharp_turns = []
    for i in range(1, len(bearings)):
        prev_bearing = bearings[i - 1]['bearing']
        curr_bearing = bearings[i]['bearing']

        # 計算角度差
        diff = abs(curr_bearing - prev_bearing)
        if diff > 180:
            diff = 360 - diff

        if diff > 45:
            sharp_turns.append({
                'index': i,
                'coord': coords[i],
                'angle_change': diff,
                'prev_bearing': prev_bearing,
                'curr_bearing': curr_bearing
            })

            # 找最近的車站
            min_dist = float('inf')
            nearest_station = None
            for sid, sdata in stations.items():
                d = euclidean_distance(coords[i][0], coords[i][1], sdata['lon'], sdata['lat'])
                if d < min_dist:
                    min_dist = d
                    nearest_station = (sid, sdata['name'])

            print(f"  點 {i:3d}: 角度變化 {diff:5.1f}° 座標 [{coords[i][0]:.5f}, {coords[i][1]:.5f}]")
            print(f"          最近車站: {nearest_station[0]} {nearest_station[1]} (距離: {min_dist:.6f})")

    print(f"\n共 {len(sharp_turns)} 個急轉彎點")

    # 檢查問題車站周圍的軌道點
    problem_stations = ['G8', 'G9', 'G10', 'G7', 'G8a', 'G11', 'G12', 'G13', 'G6']
    print(f"\n\n問題車站周圍分析:")
    print("-" * 60)

    for sid in problem_stations:
        if sid not in stations:
            continue

        sdata = stations[sid]
        print(f"\n{sid} {sdata['name']} @ [{sdata['lon']:.5f}, {sdata['lat']:.5f}]")

        # 找到最近的軌道點
        min_dist = float('inf')
        nearest_idx = 0
        for i, coord in enumerate(coords):
            d = euclidean_distance(coord[0], coord[1], sdata['lon'], sdata['lat'])
            if d < min_dist:
                min_dist = d
                nearest_idx = i

        # 顯示周圍的軌道點
        start_idx = max(0, nearest_idx - 3)
        end_idx = min(len(coords), nearest_idx + 4)

        print(f"  最近軌道點: {nearest_idx} (距離: {min_dist:.6f})")
        print(f"  周圍軌道點:")

        for i in range(start_idx, end_idx):
            marker = ">>>" if i == nearest_idx else "   "
            print(f"    {marker} [{i:3d}] [{coords[i][0]:.5f}, {coords[i][1]:.5f}]", end="")

            if i < len(coords) - 1:
                bearing = calculate_bearing(
                    coords[i][0], coords[i][1],
                    coords[i + 1][0], coords[i + 1][1]
                )
                print(f" -> 方向 {bearing:5.1f}°", end="")

            print()


def main():
    analyze_track('TMRT-G-0')
    analyze_track('TMRT-G-1')


if __name__ == '__main__':
    main()
