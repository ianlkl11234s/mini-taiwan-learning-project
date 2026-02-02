#!/usr/bin/env python3
"""
fix_display_tracks_changhua.py - 修復彰化區域的顯示軌道

將手繪的彰化軌道套用到所有經過彰化區域的顯示軌道。
"""

import json
import math
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
GOLDEN_DIR = os.path.join(DATA_DIR, 'tracks_golden')
HANDDRAWN_FILE = os.path.join(DATA_DIR, 'tracks_handdrawn', 'CH-north-draft.geojson')

# 需要修復的顯示軌道
TRACKS_TO_FIX = [
    # 山線
    'WL-M-ZN-CH-0',  # 竹南→彰化（南下）
    'WL-M-ZN-CH-1',  # 竹南→彰化（北上）
    # 西部幹線南段
    'WL-S-CH-ZY-0',  # 彰化→左營（南下）
    'WL-S-CH-ZY-1',  # 左營→彰化（北上）
]


def euclidean_dist(c1, c2):
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)


def find_nearest_index(coords, target, start_idx=0, end_idx=None):
    """找座標列表中最接近目標點的索引"""
    if end_idx is None:
        end_idx = len(coords)

    min_dist = float('inf')
    min_idx = start_idx
    for i in range(start_idx, end_idx):
        d = euclidean_dist(coords[i][:2], target[:2])
        if d < min_dist:
            min_dist = d
            min_idx = i
    return min_idx, min_dist


def load_track(filepath):
    """載入軌道，支援兩種格式"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'features' in data:
        return data, data['features'][0]['geometry']['coordinates'], 'features'
    else:
        return data, data['geometry']['coordinates'], 'geometry'


def save_track(filepath, data, coords, format_type):
    """儲存軌道"""
    if format_type == 'features':
        data['features'][0]['geometry']['coordinates'] = coords
    else:
        data['geometry']['coordinates'] = coords

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


def fix_track(track_id, hand_coords, hand_coords_rev):
    """修復單一軌道"""
    track_file = os.path.join(GOLDEN_DIR, f'{track_id}.geojson')

    if not os.path.exists(track_file):
        return False, "檔案不存在"

    data, coords, fmt = load_track(track_file)

    # 彰化站座標
    ch_station = [120.538402, 24.081859]
    hand_start = hand_coords[0]   # 彰化站
    hand_end = hand_coords[-1]    # 北邊終點

    # 找彰化站在軌道中的位置
    ch_idx, ch_dist = find_nearest_index(coords, ch_station)

    if ch_dist * 111 > 0.1:  # > 100m
        return False, f"找不到彰化站（最近距離 {ch_dist*111*1000:.0f}m）"

    print(f"  彰化站索引: {ch_idx} / {len(coords)-1}")
    print(f"  軌道座標數: {len(coords)}")

    # 判斷彰化站在軌道的哪一端
    ch_at_start = ch_idx < len(coords) / 2
    print(f"  彰化站位置: {'軌道前段' if ch_at_start else '軌道後段'}")

    if ch_at_start:
        # 彰化站在軌道前段（如 WL-S-CH-ZY：彰化→左營）
        # 需要把軌道開頭（彰化站以北的部分）用手繪軌道替換

        # 找軌道中最接近手繪終點（北邊）的座標
        search_end = min(ch_idx + 50, len(coords))
        match_idx, match_dist = find_nearest_index(coords, hand_end, 0, search_end)

        if match_dist * 111 > 0.5:  # > 500m
            return False, f"無法對接手繪終點（距離 {match_dist*111*1000:.0f}m）"

        print(f"  對接點索引: {match_idx}, 距離: {match_dist*111*1000:.0f}m")

        # 拼接：手繪軌道反向（北→彰化）+ 原軌道（從彰化站之後）
        new_coords = hand_coords_rev + coords[ch_idx + 1:]

    else:
        # 彰化站在軌道後段（如 WL-M-ZN-CH：竹南→彰化）
        # 需要把軌道末端（彰化站附近）用手繪軌道替換

        # 找軌道中最接近手繪終點（北邊）的座標
        search_start = max(ch_idx - 50, 0)
        match_idx, match_dist = find_nearest_index(coords, hand_end, search_start, len(coords))

        if match_dist * 111 > 0.5:  # > 500m
            return False, f"無法對接手繪終點（距離 {match_dist*111*1000:.0f}m）"

        print(f"  對接點索引: {match_idx}, 距離: {match_dist*111*1000:.0f}m")

        # 拼接：原軌道（到對接點）+ 手繪軌道反向（北→彰化）
        new_coords = coords[:match_idx] + hand_coords_rev

    save_track(track_file, data, new_coords, fmt)

    return True, f"座標數 {len(coords)} → {len(new_coords)}"


def main():
    print('=== 修復彰化區域的顯示軌道 ===\n')

    # 載入手繪軌道
    with open(HANDDRAWN_FILE, 'r', encoding='utf-8') as f:
        handdrawn = json.load(f)
    hand_coords = handdrawn['features'][0]['geometry']['coordinates']
    hand_coords_rev = hand_coords[::-1]
    print(f'手繪軌道: {len(hand_coords)} 點')
    print(f'  起點: {hand_coords[0]}')
    print(f'  終點: {hand_coords[-1]}')
    print()

    fixed = 0
    failed = 0

    for track_id in TRACKS_TO_FIX:
        print(f'{track_id}:')
        success, msg = fix_track(track_id, hand_coords, hand_coords_rev)
        if success:
            print(f'  ✅ {msg}')
            fixed += 1
        else:
            print(f'  ❌ {msg}')
            failed += 1
        print()

    print(f'完成！修復: {fixed}, 失敗: {failed}')


if __name__ == '__main__':
    main()
