#!/usr/bin/env python3
"""
apply_handdrawn_ch_track.py - 套用手繪彰化北上軌道

將手繪的彰化出發段軌道套用到所有 OD-CH-* 軌道的開頭部分。
"""

import json
import math
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
HANDDRAWN_FILE = os.path.join(DATA_DIR, 'tracks_handdrawn', 'CH-north-draft.geojson')
PROGRESS_FILE = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')
STATIONS_FILE = os.path.join(DATA_DIR, 'stations_snapped.geojson')

# 需要修復的軌道（往北的）
TRACKS_TO_FIX = [
    'OD-CH-HC',
    'OD-CH-HL',
    'OD-CH-KL',
    'OD-CH-QD',
    'OD-CH-北湖',
    'OD-CH-竹北',
]


def euclidean_dist(c1, c2):
    """歐幾里得距離"""
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)


def find_nearest_index(coords, target):
    """找座標列表中最接近目標點的索引"""
    min_dist = float('inf')
    min_idx = 0
    for i, c in enumerate(coords):
        d = euclidean_dist(c[:2], target[:2])
        if d < min_dist:
            min_dist = d
            min_idx = i
    return min_idx, min_dist


def load_stations():
    """載入車站座標"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stations = {}
    for feature in data.get('features', []):
        props = feature.get('properties', {})
        sid = props.get('station_id', '')
        coord = feature.get('geometry', {}).get('coordinates', [])
        if sid and coord:
            stations[sid] = coord
    return stations


def calculate_cumulative_distances(coords):
    """計算軌道的累積距離"""
    distances = [0.0]
    for i in range(1, len(coords)):
        d = euclidean_dist(coords[i-1][:2], coords[i][:2])
        distances.append(distances[-1] + d)
    return distances


def calculate_station_progress(coords, station_ids, stations):
    """計算 station_progress"""
    cumulative_distances = calculate_cumulative_distances(coords)
    total_distance = cumulative_distances[-1]

    progress = {}
    for sid in station_ids:
        if sid not in stations:
            continue
        station_coord = stations[sid]
        idx, _ = find_nearest_index(coords, station_coord)
        prog = cumulative_distances[idx] / total_distance if total_distance > 0 else 0
        progress[sid] = round(prog, 6)

    # 確保起點是 0，終點是 1
    if progress:
        sorted_stations = sorted(progress.items(), key=lambda x: x[1])
        progress[sorted_stations[0][0]] = 0.0
        progress[sorted_stations[-1][0]] = 1.0

    return progress


def main():
    print('=== 套用手繪彰化北上軌道 ===\n')

    # 載入手繪軌道
    with open(HANDDRAWN_FILE, 'r', encoding='utf-8') as f:
        handdrawn = json.load(f)
    handdrawn_coords = handdrawn['features'][0]['geometry']['coordinates']
    handdrawn_end = handdrawn_coords[-1]
    print(f'手繪軌道: {len(handdrawn_coords)} 點')
    print(f'終點: {handdrawn_end}')
    print()

    # 載入車站座標
    stations = load_stations()

    # 載入現有的 station_progress
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        all_progress = json.load(f)

    # 修復每條軌道
    for track_id in TRACKS_TO_FIX:
        track_file = os.path.join(TRACKS_OD_DIR, f'{track_id}.geojson')

        if not os.path.exists(track_file):
            print(f'{track_id}: 檔案不存在')
            continue

        with open(track_file, 'r', encoding='utf-8') as f:
            track_data = json.load(f)

        old_coords = track_data['features'][0]['geometry']['coordinates']

        # 找現有軌道中最接近手繪終點的座標
        match_idx, match_dist = find_nearest_index(old_coords, handdrawn_end)

        if match_dist * 111 > 0.1:  # 超過 100m
            print(f'{track_id}: 無法對接（距離 {match_dist*111*1000:.0f}m）')
            continue

        # 拼接：手繪軌道 + 現有軌道（從對接點之後）
        new_coords = handdrawn_coords + old_coords[match_idx + 1:]

        # 更新軌道
        track_data['features'][0]['geometry']['coordinates'] = new_coords
        track_data['features'][0]['properties']['handdrawn_applied'] = True
        track_data['features'][0]['properties']['handdrawn_points'] = len(handdrawn_coords)
        track_data['features'][0]['properties']['original_splice_index'] = match_idx

        with open(track_file, 'w', encoding='utf-8') as f:
            json.dump(track_data, f, ensure_ascii=False)

        # 更新 station_progress
        if track_id in all_progress:
            station_ids = list(all_progress[track_id].keys())
            new_progress = calculate_station_progress(new_coords, station_ids, stations)
            all_progress[track_id] = new_progress

        print(f'{track_id}:')
        print(f'  原座標數: {len(old_coords)}')
        print(f'  新座標數: {len(new_coords)}')
        print(f'  對接點: 索引 {match_idx}')

    # 儲存 station_progress
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)

    print(f'\n完成！')


if __name__ == '__main__':
    main()
