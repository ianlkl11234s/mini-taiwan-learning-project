#!/usr/bin/env python3
"""
fix_track_backjumps.py - 修復軌道回跳問題

偵測同一座標在非相鄰位置重複出現的情況，並移除中間的重複段落。
"""

import json
import os
import glob
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
TRACKS_OFFICIAL_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra', 'tracks_official')
TRACKS_OD_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra', 'tracks_od')


def flatten_coords(geom):
    """展平 MultiLineString 為單一座標列表"""
    coords = geom['coordinates']
    if geom['type'] == 'MultiLineString':
        all_coords = []
        for line in coords:
            all_coords.extend(line)
        return all_coords
    return coords


def find_duplicate_segments(coords, min_gap=5, max_gap=50):
    """
    找出所有需要移除的重複段落
    
    參數:
        min_gap: 最小間隔 (避免相鄰重複)
        max_gap: 最大間隔 (避免太大的段落)
    
    返回: [(start_idx, end_idx), ...] 要刪除的範圍（不含 end_idx）
    """
    # 建立座標→位置的索引
    coord_positions = defaultdict(list)
    for i, c in enumerate(coords):
        key = (round(c[0], 6), round(c[1], 6))
        coord_positions[key].append(i)
    
    # 找出重複段落
    segments_to_remove = []
    
    for coord, positions in coord_positions.items():
        if len(positions) < 2:
            continue
        
        # 找間隔在 min_gap ~ max_gap 之間的相鄰出現
        for i in range(len(positions) - 1):
            first = positions[i]
            second = positions[i + 1]
            gap = second - first
            
            if min_gap < gap <= max_gap:
                # 移除 first+1 到 second-1 的段落
                segments_to_remove.append((first + 1, second))
    
    # 移除重疊的段落（保留第一個）
    if not segments_to_remove:
        return []
    
    segments_to_remove.sort(key=lambda x: x[0])
    
    filtered = [segments_to_remove[0]]
    for seg in segments_to_remove[1:]:
        # 如果和前一個段落不重疊
        if seg[0] >= filtered[-1][1]:
            filtered.append(seg)
    
    # 按起始位置排序（從後往前刪除）
    return sorted(filtered, key=lambda x: x[0], reverse=True)


def fix_track_file(filepath, dry_run=False):
    """修復單一軌道檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    geom = data['features'][0]['geometry']
    coords = flatten_coords(geom)
    original_len = len(coords)
    
    segments = find_duplicate_segments(coords)
    
    if not segments:
        return False, "無重複段落"
    
    # 計算最終長度
    total_removed = sum(end - start for start, end in segments)
    final_len = original_len - total_removed
    
    # 安全檢查：不要刪除太多
    if final_len < original_len * 0.5:
        return False, f"刪除過多 ({original_len} → {final_len})，跳過"
    
    # 從後往前刪除（避免索引偏移）
    new_coords = list(coords)
    removed_ranges = []
    
    for start, end in segments:
        removed_ranges.append(f"{start}-{end-1}")
        del new_coords[start:end]
    
    if dry_run:
        return True, f"會刪除 {removed_ranges} ({original_len} → {len(new_coords)} 點)"
    
    # 更新並儲存
    geom['type'] = 'LineString'
    geom['coordinates'] = new_coords
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    
    return True, f"刪除 {removed_ranges} ({original_len} → {len(new_coords)} 點)"


def main():
    import argparse
    parser = argparse.ArgumentParser(description='修復軌道回跳問題')
    parser.add_argument('--dry-run', action='store_true', help='只顯示會做什麼')
    parser.add_argument('--official', action='store_true', help='修復 tracks_official')
    parser.add_argument('--od', action='store_true', help='修復 tracks_od')
    args = parser.parse_args()
    
    if not args.official and not args.od:
        args.official = True
        args.od = True
    
    print('=== 修復軌道回跳問題 ===\n')
    
    if args.dry_run:
        print('[Dry run 模式]\n')
    
    fixed_count = 0
    
    # 處理 tracks_official
    if args.official:
        print('--- tracks_official ---')
        for filepath in sorted(glob.glob(os.path.join(TRACKS_OFFICIAL_DIR, '*.geojson'))):
            filename = os.path.basename(filepath)
            try:
                fixed, msg = fix_track_file(filepath, args.dry_run)
                if fixed:
                    print(f'✓ {filename}: {msg}')
                    fixed_count += 1
            except Exception as e:
                print(f'✗ {filename}: {e}')
        print()
    
    # 處理 tracks_od
    if args.od:
        print('--- tracks_od ---')
        for filepath in sorted(glob.glob(os.path.join(TRACKS_OD_DIR, '*.geojson'))):
            filename = os.path.basename(filepath)
            try:
                fixed, msg = fix_track_file(filepath, args.dry_run)
                if fixed:
                    print(f'✓ {filename}: {msg}')
                    fixed_count += 1
            except Exception as e:
                print(f'✗ {filename}: {e}')
    
    print(f'\n=== 完成: 修復 {fixed_count} 條軌道 ===')


if __name__ == '__main__':
    main()
