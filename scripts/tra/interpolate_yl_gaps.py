#!/usr/bin/env python3
"""
interpolate_yl_gaps.py - 自動插值填補 YL 軌道的座標跳躍

在座標跳躍超過閾值的地方，自動插入線性插值的中間點。
這不是完美的解決方案，但可以讓列車移動更平滑。

注意：這只是直線插值，不會沿實際鐵路彎曲。
"""

import json
import os
import math
from typing import List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACKS_FILE = os.path.join(BASE_DIR, 'public', 'data', 'tra', 'tracks_official', 'all_tracks.geojson')

# 跳躍閾值（公尺）- 超過這個距離的會被插值
GAP_THRESHOLD_M = 150

# 目標間距（公尺）- 插值後每個點之間的距離
TARGET_SPACING_M = 50


def euclidean_distance_m(p1: List[float], p2: List[float]) -> float:
    """計算兩點間的距離（公尺）"""
    # 簡單的度轉公尺（在台灣緯度約 111km/度）
    dx = (p1[0] - p2[0]) * 111000 * math.cos(math.radians(p1[1]))
    dy = (p1[1] - p2[1]) * 111000
    return math.sqrt(dx * dx + dy * dy)


def interpolate_segment(p1: List[float], p2: List[float], target_spacing_m: float) -> List[List[float]]:
    """在兩點之間插入線性插值點"""
    dist = euclidean_distance_m(p1, p2)
    num_points = max(2, int(dist / target_spacing_m) + 1)

    result = []
    for i in range(num_points):
        t = i / (num_points - 1)
        lng = p1[0] + t * (p2[0] - p1[0])
        lat = p1[1] + t * (p2[1] - p1[1])
        result.append([lng, lat])

    return result


def process_track(coords: List[List[float]], track_id: str) -> List[List[float]]:
    """處理軌道，填補大跳躍"""
    new_coords = [coords[0]]
    interpolated_count = 0

    for i in range(1, len(coords)):
        dist = euclidean_distance_m(coords[i-1], coords[i])

        if dist > GAP_THRESHOLD_M:
            # 插值
            interp_points = interpolate_segment(coords[i-1], coords[i], TARGET_SPACING_M)
            # 跳過第一個點（已經在 new_coords 裡了）
            new_coords.extend(interp_points[1:])
            interpolated_count += 1
            print(f"    插值 {i-1}→{i}: {dist:.0f}m → {len(interp_points)-1} 個新點")
        else:
            new_coords.append(coords[i])

    print(f"  共插值 {interpolated_count} 處")
    return new_coords


def main():
    print("=" * 60)
    print("YL 軌道座標跳躍插值")
    print(f"閾值: {GAP_THRESHOLD_M}m, 目標間距: {TARGET_SPACING_M}m")
    print("=" * 60)

    with open(TRACKS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    modified = False

    for feature in data['features']:
        track_id = feature['properties'].get('track_id', '')

        if track_id not in ['YL-0', 'YL-1']:
            continue

        coords = feature['geometry']['coordinates']
        print(f"\n處理 {track_id}")
        print(f"  原始點數: {len(coords)}")

        new_coords = process_track(coords, track_id)

        print(f"  新點數: {len(new_coords)}")

        if len(new_coords) != len(coords):
            feature['geometry']['coordinates'] = new_coords
            modified = True

    if modified:
        with open(TRACKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n已儲存到 {TRACKS_FILE}")
    else:
        print("\n無需修改")

    print("\n" + "=" * 60)
    print("完成！請執行:")
    print("  python scripts/tra/build_yl_bh_od_tracks.py")
    print("=" * 60)


if __name__ == '__main__':
    main()
