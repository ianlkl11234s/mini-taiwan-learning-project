#!/usr/bin/env python3
"""
fix_yl_problem_segments.py - 修正 YL 軌道問題區段

問題區段：
1. 貢寮 → 雙溪 → 牡丹
2. 猴硐 → 瑞芳

解決方案：
1. 產生 gaps_to_fill.geojson 標示需要手繪的區域
2. 在問題區段用站點直線連接，移除有問題的座標
"""

import json
import os
import math
from typing import List, Tuple, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACKS_FILE = os.path.join(BASE_DIR, 'public', 'data', 'tra', 'tracks_official', 'all_tracks.geojson')
GAPS_FILE = os.path.join(BASE_DIR, 'public', 'data', 'tra', 'tracks_official', 'yl_gaps_to_fill.geojson')

# 問題區段的車站座標 (從 stations_snapped.geojson)
PROBLEM_STATIONS = {
    '7290': {'name': '福隆', 'coord': [121.944621, 25.015687]},
    '7300': {'name': '貢寮', 'coord': [121.908749, 25.021829]},
    '7310': {'name': '雙溪', 'coord': [121.866816, 25.038463]},
    '7320': {'name': '牡丹', 'coord': [121.851905, 25.058600]},
    '7350': {'name': '猴硐', 'coord': [121.827240, 25.087149]},
    '7360': {'name': '瑞芳', 'coord': [121.806254, 25.109005]},
}

# 問題區段定義 (需要手繪的區間)
PROBLEM_SEGMENTS = [
    {'from': '7290', 'to': '7300', 'name': '福隆-貢寮'},
    {'from': '7300', 'to': '7310', 'name': '貢寮-雙溪'},
    {'from': '7310', 'to': '7320', 'name': '雙溪-牡丹'},
    {'from': '7350', 'to': '7360', 'name': '猴硐-瑞芳'},
]


def euclidean_distance(p1: List[float], p2: List[float]) -> float:
    """計算兩點間的歐幾里得距離"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def find_closest_index(coords: List[List[float]], target: List[float]) -> int:
    """找出最接近目標點的座標索引"""
    min_dist = float('inf')
    min_idx = 0
    for i, coord in enumerate(coords):
        dist = euclidean_distance(coord, target)
        if dist < min_dist:
            min_dist = dist
            min_idx = i
    return min_idx


def generate_gaps_file():
    """產生需要填補的 GeoJSON 檔案"""
    features = []

    for seg in PROBLEM_SEGMENTS:
        from_station = PROBLEM_STATIONS[seg['from']]
        to_station = PROBLEM_STATIONS[seg['to']]

        # 建立標示線段（直線連接兩站）
        feature = {
            'type': 'Feature',
            'properties': {
                'segment_id': f"YL-{seg['from']}-{seg['to']}",
                'name': seg['name'],
                'from_station': seg['from'],
                'to_station': seg['to'],
                'from_name': from_station['name'],
                'to_name': to_station['name'],
                'status': 'needs_drawing',
                'description': f"請沿實際鐵路手繪 {from_station['name']} → {to_station['name']}"
            },
            'geometry': {
                'type': 'LineString',
                'coordinates': [
                    from_station['coord'],
                    to_station['coord']
                ]
            }
        }
        features.append(feature)

    # 加入車站點位作為參考
    for sid, info in PROBLEM_STATIONS.items():
        feature = {
            'type': 'Feature',
            'properties': {
                'station_id': sid,
                'name': info['name'],
                'type': 'reference_station'
            },
            'geometry': {
                'type': 'Point',
                'coordinates': info['coord']
            }
        }
        features.append(feature)

    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    with open(GAPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"已產生填補檔案: {GAPS_FILE}")
    print(f"包含 {len(PROBLEM_SEGMENTS)} 個需要手繪的區段:")
    for seg in PROBLEM_SEGMENTS:
        print(f"  - {seg['name']}")


def fix_yl_tracks():
    """修正 YL 軌道，在問題區段用站點直線連接"""
    print("\n修正 YL 軌道問題區段...")

    with open(TRACKS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for feature in data['features']:
        track_id = feature['properties'].get('track_id', '')

        if track_id not in ['YL-0', 'YL-1']:
            continue

        geom = feature['geometry']
        if geom['type'] != 'LineString':
            print(f"  {track_id}: 跳過（非 LineString）")
            continue

        coords = geom['coordinates']
        direction = int(track_id.split('-')[1])

        print(f"\n處理 {track_id} (方向 {direction})")
        print(f"  原始座標點數: {len(coords)}")

        # 找出各站點在軌道上的位置
        station_indices = {}
        for sid, info in PROBLEM_STATIONS.items():
            idx = find_closest_index(coords, info['coord'])
            station_indices[sid] = idx
            print(f"  {info['name']} ({sid}): idx={idx}")

        # 建立新座標，在問題區段用直線連接
        # 依照方向排序站點
        if direction == 0:
            # 南下：北→南，索引應遞增
            ordered_stations = sorted(station_indices.items(), key=lambda x: x[1])
        else:
            # 北上：南→北，索引應遞增
            ordered_stations = sorted(station_indices.items(), key=lambda x: x[1])

        # 找出需要替換的區段
        segments_to_fix = []
        for seg in PROBLEM_SEGMENTS:
            from_idx = station_indices[seg['from']]
            to_idx = station_indices[seg['to']]

            # 確保 from < to
            if from_idx > to_idx:
                from_idx, to_idx = to_idx, from_idx
                from_sid, to_sid = seg['to'], seg['from']
            else:
                from_sid, to_sid = seg['from'], seg['to']

            segments_to_fix.append({
                'from_idx': from_idx,
                'to_idx': to_idx,
                'from_coord': PROBLEM_STATIONS[from_sid]['coord'],
                'to_coord': PROBLEM_STATIONS[to_sid]['coord'],
                'name': seg['name']
            })

        # 按索引排序
        segments_to_fix.sort(key=lambda x: x['from_idx'])

        # 建立新座標列表
        new_coords = []
        last_idx = 0

        for seg in segments_to_fix:
            # 加入問題區段之前的座標
            if seg['from_idx'] > last_idx:
                new_coords.extend(coords[last_idx:seg['from_idx']])

            # 用直線連接（只加入兩個端點）
            new_coords.append(seg['from_coord'])
            new_coords.append(seg['to_coord'])

            print(f"  替換 {seg['name']}: idx {seg['from_idx']}-{seg['to_idx']} → 直線")

            last_idx = seg['to_idx'] + 1

        # 加入最後一段
        if last_idx < len(coords):
            new_coords.extend(coords[last_idx:])

        print(f"  新座標點數: {len(new_coords)}")

        # 更新座標
        feature['geometry']['coordinates'] = new_coords

    # 儲存
    with open(TRACKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n已儲存修正後的軌道")


def main():
    print("=" * 60)
    print("YL 軌道問題區段修正")
    print("=" * 60)

    # 1. 產生填補檔案
    generate_gaps_file()

    # 2. 修正軌道
    fix_yl_tracks()

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)
    print("\n下一步:")
    print(f"1. 開啟 {GAPS_FILE} 手繪問題區段")
    print("2. 完成後執行 rebuild_yl_from_gaps.py 整合手繪軌道")
    print("3. 重新執行 build_yl_bh_od_tracks.py")


if __name__ == '__main__':
    main()
