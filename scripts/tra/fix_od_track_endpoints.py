#!/usr/bin/env python3
"""
fix_od_track_endpoints.py - 修正 OD 軌道的起點和終點

問題：OD 軌道的起點/終點可能不在站點的 snapped 座標上，
導致列車在 progress=0.0 或 progress=1.0 時顯示在錯誤的位置。

解法：在軌道的起點和終點插入站點的 snapped 座標。
"""

import json
import os
import glob
import math
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
PROGRESS_FILE = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')
STATIONS_FILE = os.path.join(DATA_DIR, 'stations_snapped.geojson')


def load_stations():
    """載入車站 snapped 座標"""
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


def load_progress():
    """載入 station_progress"""
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def euclidean_distance(c1, c2):
    """歐幾里得距離（公尺）"""
    dx = (c2[0] - c1[0]) * 111000  # 經度約 111km/度
    dy = (c2[1] - c1[1]) * 111000  # 緯度約 111km/度
    return math.sqrt(dx * dx + dy * dy)


def get_origin_dest_from_id(track_id, progress_data):
    """從 track_id 和 station_progress 取得起終站 ID"""
    if track_id not in progress_data:
        return None, None

    stations = progress_data[track_id]

    # 找 progress 最接近 0 和 1 的站
    origin = None
    dest = None
    min_origin_diff = float('inf')
    min_dest_diff = float('inf')

    for sid, prog in stations.items():
        origin_diff = abs(prog - 0.0)
        dest_diff = abs(prog - 1.0)

        if origin_diff < min_origin_diff:
            min_origin_diff = origin_diff
            origin = sid
        if dest_diff < min_dest_diff:
            min_dest_diff = dest_diff
            dest = sid

    return origin, dest


def fix_track(filepath, stations, progress_data, dry_run=False):
    """修正單一軌道的起終點"""
    track_id = os.path.basename(filepath).replace('.geojson', '')

    origin_id, dest_id = get_origin_dest_from_id(track_id, progress_data)

    if not origin_id or not dest_id:
        return False, "無法找到起終站"

    if origin_id not in stations:
        return False, f"起站 {origin_id} 無座標"
    if dest_id not in stations:
        return False, f"終站 {dest_id} 無座標"

    origin_coord = stations[origin_id]
    dest_coord = stations[dest_id]

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    coords = data['features'][0]['geometry']['coordinates']
    if len(coords) < 2:
        return False, "座標點太少"

    modified = False
    messages = []

    # 檢查起點
    first_coord = coords[0]
    origin_dist = euclidean_distance(first_coord, origin_coord)

    if origin_dist > 50:  # 超過 50 公尺
        # 插入起站座標
        coords.insert(0, origin_coord)
        modified = True
        messages.append(f"起點插入 {origin_id} ({origin_dist:.0f}m)")

    # 檢查終點
    last_coord = coords[-1]
    dest_dist = euclidean_distance(last_coord, dest_coord)

    if dest_dist > 50:  # 超過 50 公尺
        # 附加終站座標
        coords.append(dest_coord)
        modified = True
        messages.append(f"終點插入 {dest_id} ({dest_dist:.0f}m)")

    if not modified:
        return False, "無需修正"

    if dry_run:
        return True, ", ".join(messages)

    data['features'][0]['geometry']['coordinates'] = coords
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    return True, ", ".join(messages)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='修正 OD 軌道起終點')
    parser.add_argument('--dry-run', action='store_true', help='只顯示會做什麼')
    parser.add_argument('--track', type=str, help='只處理指定軌道')
    args = parser.parse_args()

    print('=== 修正 OD 軌道起終點 ===\n')

    if args.dry_run:
        print('[Dry run 模式]\n')

    # 載入資料
    print('載入車站座標...')
    stations = load_stations()
    print(f'  共 {len(stations)} 站\n')

    print('載入 station_progress...')
    progress_data = load_progress()
    print(f'  共 {len(progress_data)} 軌道\n')

    fixed_count = 0

    # 處理軌道
    if args.track:
        filepaths = [os.path.join(TRACKS_OD_DIR, f'{args.track}.geojson')]
    else:
        filepaths = sorted(glob.glob(os.path.join(TRACKS_OD_DIR, '*.geojson')))

    print('處理軌道...')
    for filepath in filepaths:
        if filepath.endswith('od_station_progress.json'):
            continue

        filename = os.path.basename(filepath)

        try:
            fixed, msg = fix_track(filepath, stations, progress_data, args.dry_run)
            if fixed:
                print(f'✓ {filename}: {msg}')
                fixed_count += 1
        except Exception as e:
            print(f'✗ {filename}: {e}')

    print(f'\n=== 完成: 修正 {fixed_count} 條軌道 ===')


if __name__ == '__main__':
    main()
