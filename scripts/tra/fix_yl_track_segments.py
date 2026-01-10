#!/usr/bin/env python3
"""
fix_yl_track_segments.py - 修正 YL 宜蘭線軌道 MultiLineString 段落順序

問題：YL-0 和 YL-1 軌道的 MultiLineString 段落順序不連續，
導致座標有跳躍，車站進度計算錯誤。

解決：按地理位置重新排序段落，確保段落之間連續。
"""

import json
import os
import math
from typing import List, Tuple, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACKS_FILE = os.path.join(BASE_DIR, 'public', 'data', 'tra', 'tracks_official', 'all_tracks.geojson')


def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """計算兩點間的歐幾里得距離"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def analyze_segment(segment: List[List[float]], idx: int) -> Dict[str, Any]:
    """分析單一段落的起點、終點和長度"""
    start = tuple(segment[0])
    end = tuple(segment[-1])
    length = 0
    for i in range(len(segment) - 1):
        length += euclidean_distance(tuple(segment[i]), tuple(segment[i+1]))

    return {
        'index': idx,
        'start': start,
        'end': end,
        'start_lat': start[1],
        'end_lat': end[1],
        'length': length,
        'points': len(segment),
        'coords': segment
    }


def find_best_connection(current_end: Tuple[float, float],
                         remaining: List[Dict],
                         threshold: float = 0.01) -> Tuple[int, bool]:
    """
    找出與當前終點最接近的段落

    Returns:
        (index, reversed): 段落索引和是否需要反轉
    """
    best_idx = -1
    best_dist = float('inf')
    best_reversed = False

    for i, seg in enumerate(remaining):
        # 檢查正向連接（段落起點接當前終點）
        dist_start = euclidean_distance(current_end, seg['start'])
        if dist_start < best_dist:
            best_dist = dist_start
            best_idx = i
            best_reversed = False

        # 檢查反向連接（段落終點接當前終點，需要反轉）
        dist_end = euclidean_distance(current_end, seg['end'])
        if dist_end < best_dist:
            best_dist = dist_end
            best_idx = i
            best_reversed = True

    if best_dist > threshold:
        print(f"  ⚠️ 警告：最近段落距離 {best_dist:.6f} 度 (≈{best_dist * 111:.1f} km)")

    return best_idx, best_reversed


def find_best_bidirectional_connection(
    chain_start: Tuple[float, float],
    chain_end: Tuple[float, float],
    remaining: List[Dict],
    threshold: float = 0.02
) -> Tuple[int, bool, str]:
    """
    找出與鏈的任一端最接近的段落

    Returns:
        (index, reversed, position): 段落索引、是否需要反轉、連接位置 ('start' or 'end')
    """
    best_idx = -1
    best_dist = float('inf')
    best_reversed = False
    best_position = 'end'

    for i, seg in enumerate(remaining):
        # 檢查連接到鏈的末端
        dist_end_to_start = euclidean_distance(chain_end, seg['start'])
        if dist_end_to_start < best_dist:
            best_dist = dist_end_to_start
            best_idx = i
            best_reversed = False
            best_position = 'end'

        dist_end_to_end = euclidean_distance(chain_end, seg['end'])
        if dist_end_to_end < best_dist:
            best_dist = dist_end_to_end
            best_idx = i
            best_reversed = True
            best_position = 'end'

        # 檢查連接到鏈的起始端
        dist_start_to_end = euclidean_distance(chain_start, seg['end'])
        if dist_start_to_end < best_dist:
            best_dist = dist_start_to_end
            best_idx = i
            best_reversed = False
            best_position = 'start'

        dist_start_to_start = euclidean_distance(chain_start, seg['start'])
        if dist_start_to_start < best_dist:
            best_dist = dist_start_to_start
            best_idx = i
            best_reversed = True
            best_position = 'start'

    if best_dist > threshold:
        print(f"  ⚠️ 警告：最近段落距離 {best_dist:.6f} 度 (≈{best_dist * 111:.1f} km)")

    return best_idx, best_reversed, best_position


def reorder_segments(segments: List[List[List[float]]], direction: int) -> List[List[float]]:
    """
    重新排序 MultiLineString 段落，確保連續

    使用雙向串接演算法：可以從鏈的任一端添加新段落

    Args:
        segments: MultiLineString 的 coordinates
        direction: 0=南下(臺北→花蓮), 1=北上(花蓮→臺北)

    Returns:
        合併後的單一 LineString coordinates
    """
    if len(segments) <= 1:
        return segments[0] if segments else []

    # 分析所有段落
    analyzed = [analyze_segment(seg, i) for i, seg in enumerate(segments)]

    print(f"\n  原始段落分析:")
    for seg in analyzed:
        print(f"    段落 {seg['index']}: "
              f"起點緯度={seg['start_lat']:.4f}, "
              f"終點緯度={seg['end_lat']:.4f}, "
              f"點數={seg['points']}")

    # 找最長的段落作為種子（通常是主軌道）
    start_seg = max(analyzed, key=lambda s: s['points'])
    print(f"\n  種子段落: {start_seg['index']} (最長, {start_seg['points']} 點)")

    # 建立排序後的座標鏈
    ordered_coords = list(start_seg['coords'])
    remaining = [s for s in analyzed if s['index'] != start_seg['index']]

    while remaining:
        chain_start = tuple(ordered_coords[0])
        chain_end = tuple(ordered_coords[-1])

        best_idx, reversed_seg, position = find_best_bidirectional_connection(
            chain_start, chain_end, remaining
        )

        if best_idx < 0:
            print(f"  ❌ 無法找到連接的段落！剩餘 {len(remaining)} 段落")
            break

        next_seg = remaining.pop(best_idx)

        if reversed_seg:
            coords_to_add = list(reversed(next_seg['coords']))
        else:
            coords_to_add = list(next_seg['coords'])

        if position == 'end':
            # 添加到鏈的末端
            # 如果起點和當前終點很接近，跳過重複點
            if euclidean_distance(tuple(coords_to_add[0]), chain_end) < 0.0001:
                coords_to_add = coords_to_add[1:]
            ordered_coords.extend(coords_to_add)
            direction_str = "末端" if not reversed_seg else "末端(反轉)"
        else:
            # 添加到鏈的起始端
            # 如果終點和當前起點很接近，跳過重複點
            if euclidean_distance(tuple(coords_to_add[-1]), chain_start) < 0.0001:
                coords_to_add = coords_to_add[:-1]
            ordered_coords = coords_to_add + ordered_coords
            direction_str = "起始" if not reversed_seg else "起始(反轉)"

        print(f"  連接段落 {next_seg['index']} → {direction_str}")

    # 根據方向決定是否需要反轉整條軌道
    start_lat = ordered_coords[0][1]
    end_lat = ordered_coords[-1][1]

    if direction == 0:
        # 南下：應該從北到南（緯度遞減）
        if start_lat < end_lat:
            print(f"\n  反轉軌道以符合方向 0 (南下)")
            ordered_coords = list(reversed(ordered_coords))
    else:
        # 北上：應該從南到北（緯度遞增）
        if start_lat > end_lat:
            print(f"\n  反轉軌道以符合方向 1 (北上)")
            ordered_coords = list(reversed(ordered_coords))

    return ordered_coords


def fix_yl_tracks():
    """修正 YL 軌道"""
    print("=" * 60)
    print("修正 YL 宜蘭線軌道 MultiLineString 段落順序")
    print("=" * 60)

    # 讀取軌道資料
    with open(TRACKS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    modified = False

    for feature in data['features']:
        props = feature['properties']
        track_id = props.get('track_id', '')

        if not track_id.startswith('YL-'):
            continue

        geom = feature['geometry']

        if geom['type'] != 'MultiLineString':
            print(f"\n{track_id}: 已經是 LineString，跳過")
            continue

        direction = int(track_id.split('-')[1])
        print(f"\n處理 {track_id} (方向 {direction}, MultiLineString, {len(geom['coordinates'])} 段落)")

        # 重新排序並合併
        ordered_coords = reorder_segments(geom['coordinates'], direction)

        # 驗證結果
        print(f"\n  結果: {len(ordered_coords)} 點")

        # 檢查連續性
        max_jump = 0
        jump_count = 0
        for i in range(len(ordered_coords) - 1):
            dist = euclidean_distance(tuple(ordered_coords[i]), tuple(ordered_coords[i+1]))
            if dist > 0.005:  # 約 500m
                jump_count += 1
                if dist > max_jump:
                    max_jump = dist

        if jump_count > 0:
            print(f"  ⚠️ 仍有 {jump_count} 個大跳躍 (最大 {max_jump:.6f} 度 ≈ {max_jump * 111:.1f} km)")
        else:
            print(f"  ✅ 座標連續，無大跳躍")

        # 更新為 LineString
        feature['geometry'] = {
            'type': 'LineString',
            'coordinates': ordered_coords
        }
        modified = True

    if modified:
        # 備份原檔案
        backup_file = TRACKS_FILE.replace('.geojson', '_backup.geojson')
        if not os.path.exists(backup_file):
            import shutil
            shutil.copy2(TRACKS_FILE, backup_file)
            print(f"\n已備份原檔案至: {backup_file}")

        # 儲存修正後的資料
        with open(TRACKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n已儲存修正後的軌道至: {TRACKS_FILE}")

    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)
    print("\n下一步: 執行 build_yl_bh_od_tracks.py 重新生成 O-D 軌道")


if __name__ == '__main__':
    fix_yl_tracks()
