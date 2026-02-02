#!/usr/bin/env python3
"""
apply_handdrawn_to_display.py - 套用手繪軌道到顯示軌道

將手繪的彰化出發段軌道套用到顯示軌道的開頭部分。
"""

import json
import math
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
HANDDRAWN_FILE = os.path.join(DATA_DIR, 'tracks_handdrawn', 'CH-north-draft.geojson')
GOLDEN_DIR = os.path.join(DATA_DIR, 'tracks_golden')

# 需要修復的顯示軌道（從彰化往北）
DISPLAY_TRACKS_TO_FIX = [
    'WL-M-CH-ZN-1',  # 山線 彰化→竹南
]


def euclidean_dist(c1, c2):
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)


def find_nearest_index(coords, target):
    min_dist = float('inf')
    min_idx = 0
    for i, c in enumerate(coords):
        d = euclidean_dist(c[:2], target[:2])
        if d < min_dist:
            min_dist = d
            min_idx = i
    return min_idx, min_dist


def main():
    print('=== 套用手繪軌道到顯示軌道 ===\n')

    # 載入手繪軌道
    with open(HANDDRAWN_FILE, 'r', encoding='utf-8') as f:
        handdrawn = json.load(f)
    handdrawn_coords = handdrawn['features'][0]['geometry']['coordinates']
    handdrawn_end = handdrawn_coords[-1]
    print(f'手繪軌道: {len(handdrawn_coords)} 點')
    print(f'終點: {handdrawn_end}')
    print()

    for track_id in DISPLAY_TRACKS_TO_FIX:
        track_file = os.path.join(GOLDEN_DIR, f'{track_id}.geojson')

        if not os.path.exists(track_file):
            print(f'{track_id}: 檔案不存在')
            continue

        with open(track_file, 'r', encoding='utf-8') as f:
            track_data = json.load(f)

        # 取得座標
        if 'geometry' in track_data:
            old_coords = track_data['geometry']['coordinates']
            is_feature = False
        else:
            old_coords = track_data['features'][0]['geometry']['coordinates']
            is_feature = True

        # 找現有軌道中最接近手繪終點的座標
        match_idx, match_dist = find_nearest_index(old_coords, handdrawn_end)

        if match_dist * 111 > 0.1:  # 超過 100m
            print(f'{track_id}: 無法對接（距離 {match_dist*111*1000:.0f}m）')
            continue

        # 拼接：手繪軌道 + 現有軌道（從對接點之後）
        new_coords = handdrawn_coords + old_coords[match_idx + 1:]

        # 更新軌道
        if is_feature:
            track_data['features'][0]['geometry']['coordinates'] = new_coords
        else:
            track_data['geometry']['coordinates'] = new_coords

        with open(track_file, 'w', encoding='utf-8') as f:
            json.dump(track_data, f, ensure_ascii=False)

        print(f'{track_id}:')
        print(f'  原座標數: {len(old_coords)}')
        print(f'  新座標數: {len(new_coords)}')
        print(f'  對接點: 索引 {match_idx}')

    print(f'\n完成！')


if __name__ == '__main__':
    main()
