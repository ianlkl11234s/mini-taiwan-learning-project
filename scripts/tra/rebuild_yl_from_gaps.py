#!/usr/bin/env python3
"""
rebuild_yl_from_gaps.py - 從手繪資料重建 YL 軌道

將 yl_gaps_to_fill.geojson 中的手繪區段整合回 all_tracks.geojson 中的 YL 軌道。

手繪區段：
1. 貢寮 (7300) → 雙溪 (7310)
2. 雙溪 (7310) → 牡丹 (7320)
3. 猴硐 (7350) → 瑞芳 (7360)
"""

import json
import os
import math
from typing import List, Tuple, Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACKS_FILE = os.path.join(BASE_DIR, 'public', 'data', 'tra', 'tracks_official', 'all_tracks.geojson')
GAPS_FILE = os.path.join(BASE_DIR, 'public', 'data', 'tra', 'tracks_official', 'yl_gaps_to_fill.geojson')
STATIONS_FILE = os.path.join(BASE_DIR, 'public', 'data', 'tra', 'stations_snapped.geojson')


def euclidean_distance(p1: List[float], p2: List[float]) -> float:
    """計算兩點間的歐幾里得距離"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def find_closest_index(coords: List[List[float]], target: List[float], tolerance: float = 0.001) -> int:
    """找出最接近目標點的座標索引"""
    min_dist = float('inf')
    min_idx = -1
    for i, coord in enumerate(coords):
        dist = euclidean_distance(coord, target)
        if dist < min_dist:
            min_dist = dist
            min_idx = i
    return min_idx


def load_station_coords() -> Dict[str, List[float]]:
    """載入車站座標"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stations = {}
    for feature in data['features']:
        sid = feature['properties'].get('station_id', '')
        if sid:
            coords = feature['geometry']['coordinates']
            stations[sid] = coords
    return stations


def load_gap_segments() -> Dict[str, List[List[float]]]:
    """載入手繪區段"""
    with open(GAPS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    segments = {}
    for feature in data['features']:
        props = feature['properties']
        if props.get('segment_id'):
            segment_id = props['segment_id']
            coords = feature['geometry']['coordinates']
            segments[segment_id] = coords
            print(f"  載入手繪區段: {segment_id} ({len(coords)} 點)")

    return segments


def replace_segment(
    coords: List[List[float]],
    from_station: List[float],
    to_station: List[float],
    new_segment: List[List[float]],
    direction: int
) -> List[List[float]]:
    """替換軌道中的某區段

    Args:
        coords: 原始軌道座標
        from_station: 起點車站座標
        to_station: 終點車站座標
        new_segment: 新的手繪座標
        direction: 軌道方向 (0=南下, 1=北上)

    Returns:
        替換後的軌道座標
    """
    # 找出起終點在原始軌道中的位置
    from_idx = find_closest_index(coords, from_station)
    to_idx = find_closest_index(coords, to_station)

    print(f"    原始軌道: from_idx={from_idx}, to_idx={to_idx}")

    # 確保 from_idx < to_idx
    if from_idx > to_idx:
        from_idx, to_idx = to_idx, from_idx
        # 如果交換了順序，需要反轉新區段
        new_segment = list(reversed(new_segment))

    # 根據軌道方向決定是否反轉新區段
    # 檢查新區段的方向是否與軌道方向一致
    new_start = new_segment[0]
    new_end = new_segment[-1]

    dist_start_to_from = euclidean_distance(new_start, from_station)
    dist_end_to_from = euclidean_distance(new_end, from_station)

    if dist_end_to_from < dist_start_to_from:
        # 新區段是反向的，需要反轉
        new_segment = list(reversed(new_segment))
        print(f"    反轉新區段以匹配軌道方向")

    # 建立新座標列表
    new_coords = coords[:from_idx]  # 保留起點之前的座標
    new_coords.extend(new_segment)   # 加入手繪區段
    new_coords.extend(coords[to_idx + 1:])  # 保留終點之後的座標

    print(f"    替換完成: {len(coords)} 點 → {len(new_coords)} 點")

    return new_coords


def rebuild_yl_tracks():
    """重建 YL 軌道"""
    print("=" * 60)
    print("從手繪資料重建 YL 軌道")
    print("=" * 60)

    # 載入車站座標
    print("\n載入車站座標...")
    stations = load_station_coords()

    # 載入手繪區段
    print("\n載入手繪區段...")
    gap_segments = load_gap_segments()

    # 定義需要替換的區段
    replacements = [
        {'from': '7290', 'to': '7300', 'segment_id': 'YL-7290-7300', 'name': '福隆-貢寮'},
        {'from': '7300', 'to': '7310', 'segment_id': 'YL-7300-7310', 'name': '貢寮-雙溪'},
        {'from': '7310', 'to': '7320', 'segment_id': 'YL-7310-7320', 'name': '雙溪-牡丹'},
        {'from': '7350', 'to': '7360', 'segment_id': 'YL-7350-7360', 'name': '猴硐-瑞芳'},
    ]

    # 載入軌道資料
    print("\n載入軌道資料...")
    with open(TRACKS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 處理 YL-0 和 YL-1
    for feature in data['features']:
        track_id = feature['properties'].get('track_id', '')

        if track_id not in ['YL-0', 'YL-1']:
            continue

        direction = int(track_id.split('-')[1])
        coords = feature['geometry']['coordinates']

        print(f"\n處理 {track_id} (方向 {direction})")
        print(f"  原始座標點數: {len(coords)}")

        # 依序替換每個區段
        for rep in replacements:
            segment_id = rep['segment_id']
            if segment_id not in gap_segments:
                print(f"  警告: 找不到手繪區段 {segment_id}")
                continue

            from_station = stations.get(rep['from'])
            to_station = stations.get(rep['to'])

            if not from_station or not to_station:
                print(f"  警告: 找不到車站座標 {rep['from']} 或 {rep['to']}")
                continue

            print(f"  替換 {rep['name']}...")
            coords = replace_segment(
                coords,
                from_station,
                to_station,
                gap_segments[segment_id],
                direction
            )

        # 更新座標
        feature['geometry']['coordinates'] = coords
        feature['properties']['rebuilt_from_gaps'] = True
        print(f"  最終座標點數: {len(coords)}")

    # 儲存
    print("\n儲存軌道資料...")
    with open(TRACKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n已儲存到 {TRACKS_FILE}")
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)
    print("\n下一步:")
    print("1. 執行 build_yl_bh_od_tracks.py 重新生成 O-D 軌道")
    print("2. 執行 npm run dev 驗證列車路徑")


if __name__ == '__main__':
    rebuild_yl_tracks()
