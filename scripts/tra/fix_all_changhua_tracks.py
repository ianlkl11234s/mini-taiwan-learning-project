#!/usr/bin/env python3
"""
fix_all_changhua_tracks.py - 修復所有經過彰化區域的軌道

將手繪的彰化軌道套用到所有經過彰化區域的軌道。
"""

import json
import math
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
HANDDRAWN_FILE = os.path.join(DATA_DIR, 'tracks_handdrawn', 'CH-north-draft.geojson')
BUNDLE_FILE = os.path.join(TRACKS_OD_DIR, 'tracks_od_bundle.json')

# 彰化區域的緯度範圍
CH_LAT_MIN = 24.07
CH_LAT_MAX = 24.10

# 手繪軌道的起終點緯度
HANDDRAWN_START_LAT = 24.081859  # 彰化站
HANDDRAWN_END_LAT = 24.092675    # 手繪終點


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


def has_jump_problem(coords, start_idx, end_idx):
    """檢查座標範圍內是否有大跳躍問題"""
    for i in range(start_idx + 1, min(end_idx, len(coords))):
        diff = abs(coords[i][1] - coords[i-1][1]) * 111 * 1000
        if diff > 500:  # > 500m
            return True
    return False


def fix_track(coords, handdrawn_coords, handdrawn_coords_reversed):
    """
    修復單一軌道

    策略：
    1. 找到軌道進入和離開彰化區域的點
    2. 判斷軌道在彰化區域的行進方向
    3. 用手繪軌道替換彰化區域內的座標
    """
    # 找彰化區域內的座標索引
    ch_indices = [i for i, c in enumerate(coords) if CH_LAT_MIN < c[1] < CH_LAT_MAX]

    if not ch_indices:
        return coords, False, "不經過彰化"

    # 擴展範圍以包含邊界
    region_start = max(0, ch_indices[0] - 5)
    region_end = min(len(coords), ch_indices[-1] + 5)

    # 檢查是否有問題
    if not has_jump_problem(coords, region_start, region_end):
        return coords, False, "無跳躍問題"

    # 判斷軌道方向（進入彰化區域時是往北還是往南）
    if region_start > 0:
        before_lat = coords[region_start - 1][1] if region_start > 0 else coords[0][1]
    else:
        before_lat = coords[0][1]

    if region_end < len(coords):
        after_lat = coords[region_end][1] if region_end < len(coords) else coords[-1][1]
    else:
        after_lat = coords[-1][1]

    # 判斷是北上還是南下經過彰化
    # 如果進入彰化時緯度較低，離開時較高 → 北上
    # 如果進入彰化時緯度較高，離開時較低 → 南下
    going_north = after_lat > before_lat

    # 選擇正確方向的手繪軌道
    if going_north:
        hand = handdrawn_coords
    else:
        hand = handdrawn_coords_reversed

    hand_start = hand[0]
    hand_end = hand[-1]

    # 找軌道中最接近手繪起點和終點的座標
    start_idx, start_dist = find_nearest_index(coords, hand_start, 0, region_end)
    end_idx, end_dist = find_nearest_index(coords, hand_end, region_start, len(coords))

    # 確保順序正確
    if start_idx >= end_idx:
        # 交換
        start_idx, end_idx = end_idx, start_idx
        start_dist, end_dist = end_dist, start_dist
        # 也需要反轉手繪軌道
        hand = hand[::-1]

    # 檢查對接距離是否合理
    if start_dist * 111 > 0.5 or end_dist * 111 > 0.5:  # > 500m
        return coords, False, f"對接距離過大: start={start_dist*111*1000:.0f}m, end={end_dist*111*1000:.0f}m"

    # 拼接：原軌道前段 + 手繪軌道 + 原軌道後段
    new_coords = coords[:start_idx] + hand + coords[end_idx + 1:]

    return new_coords, True, f"已修復 ({start_idx}-{end_idx})"


def main():
    print('=== 修復所有經過彰化區域的軌道 ===\n')

    # 載入手繪軌道
    with open(HANDDRAWN_FILE, 'r', encoding='utf-8') as f:
        handdrawn = json.load(f)
    handdrawn_coords = handdrawn['features'][0]['geometry']['coordinates']
    handdrawn_coords_reversed = handdrawn_coords[::-1]
    print(f'手繪軌道: {len(handdrawn_coords)} 點')

    # 載入 bundle
    with open(BUNDLE_FILE, 'r', encoding='utf-8') as f:
        bundle = json.load(f)
    print(f'軌道總數: {len(bundle)}')
    print()

    fixed_count = 0
    skipped_count = 0
    error_count = 0

    for track_id in sorted(bundle.keys()):
        coords = bundle[track_id]['coordinates']

        new_coords, fixed, message = fix_track(
            coords, handdrawn_coords, handdrawn_coords_reversed
        )

        if fixed:
            bundle[track_id]['coordinates'] = new_coords
            fixed_count += 1
            print(f'✅ {track_id}: {message}')
        elif "不經過" in message or "無跳躍" in message:
            skipped_count += 1
        else:
            error_count += 1
            print(f'❌ {track_id}: {message}')

    # 儲存 bundle
    with open(BUNDLE_FILE, 'w', encoding='utf-8') as f:
        json.dump(bundle, f, ensure_ascii=False)

    print()
    print(f'完成！')
    print(f'  修復: {fixed_count}')
    print(f'  跳過: {skipped_count}')
    print(f'  錯誤: {error_count}')


if __name__ == '__main__':
    main()
