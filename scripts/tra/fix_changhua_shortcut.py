#!/usr/bin/env python3
"""
fix_changhua_shortcut.py - 修復彰化直線捷徑問題

在 junction 點 [120.545746, 24.088135] 和 彰化站 [120.538402, 24.081859] 之間
插入正確的彎曲軌道座標（來自 WL-S2-0）。
"""

import json
import os
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
TRACKS_OFFICIAL_DIR = os.path.join(DATA_DIR, 'tracks_official')

# 關鍵座標
JUNCTION = [120.545746, 24.088135]
CHANGHUA = [120.538402, 24.081859]
TOLERANCE = 0.0005


def load_curve_from_wl_s2():
    """從 WL-S2-0 載入彎曲軌道座標"""
    filepath = os.path.join(TRACKS_OFFICIAL_DIR, 'WL-S2-0.geojson')
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    geom = data['features'][0]['geometry']
    coords = geom['coordinates']
    
    if geom['type'] == 'MultiLineString':
        all_coords = []
        for line in coords:
            all_coords.extend(line)
        coords = all_coords
    
    # 找 junction 到 changhua 之間的座標 (idx 1350-1374)
    # idx 1349 是 changhua 附近，idx 1375 是 junction
    # 我們要的是 1350-1374（不含兩端點，因為端點已經在軌道中）
    curve_junc_to_ch = coords[1350:1375]  # junction → changhua 方向
    curve_ch_to_junc = list(reversed(curve_junc_to_ch))  # changhua → junction 方向
    
    return curve_junc_to_ch, curve_ch_to_junc


def coord_near(c1, c2):
    """檢查兩座標是否接近"""
    return abs(c1[0] - c2[0]) < TOLERANCE and abs(c1[1] - c2[1]) < TOLERANCE


def fix_track(filepath, curve_junc_to_ch, curve_ch_to_junc, dry_run=False):
    """修復單一軌道"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    coords = data['features'][0]['geometry']['coordinates']
    original_len = len(coords)
    
    # 找直線跳躍的位置
    for i in range(len(coords) - 1):
        c1 = coords[i]
        c2 = coords[i + 1]
        
        # junction → changhua
        if coord_near(c1, JUNCTION) and coord_near(c2, CHANGHUA):
            # 在 idx i+1 前插入 curve_junc_to_ch
            new_coords = coords[:i+1] + curve_junc_to_ch + coords[i+1:]
            
            if dry_run:
                return True, f"junction→彰化 @ {i}→{i+1}, 插入 {len(curve_junc_to_ch)} 點"
            
            data['features'][0]['geometry']['coordinates'] = new_coords
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            
            return True, f"junction→彰化 @ {i}→{i+1}, 插入 {len(curve_junc_to_ch)} 點 ({original_len}→{len(new_coords)})"
        
        # changhua → junction
        if coord_near(c1, CHANGHUA) and coord_near(c2, JUNCTION):
            # 在 idx i+1 前插入 curve_ch_to_junc
            new_coords = coords[:i+1] + curve_ch_to_junc + coords[i+1:]
            
            if dry_run:
                return True, f"彰化→junction @ {i}→{i+1}, 插入 {len(curve_ch_to_junc)} 點"
            
            data['features'][0]['geometry']['coordinates'] = new_coords
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            
            return True, f"彰化→junction @ {i}→{i+1}, 插入 {len(curve_ch_to_junc)} 點 ({original_len}→{len(new_coords)})"
    
    return False, "無直線跳躍"


def main():
    import argparse
    parser = argparse.ArgumentParser(description='修復彰化直線捷徑')
    parser.add_argument('--dry-run', action='store_true', help='只顯示會做什麼')
    args = parser.parse_args()
    
    print('=== 修復彰化直線捷徑 ===\n')
    
    if args.dry_run:
        print('[Dry run 模式]\n')
    
    # 載入正確的彎曲軌道
    print('載入 WL-S2-0 彎曲軌道...')
    curve_junc_to_ch, curve_ch_to_junc = load_curve_from_wl_s2()
    print(f'  曲線長度: {len(curve_junc_to_ch)} 點\n')
    
    fixed_count = 0
    
    # 處理所有 OD 軌道
    for filepath in sorted(glob.glob(os.path.join(TRACKS_OD_DIR, '*.geojson'))):
        filename = os.path.basename(filepath)
        
        try:
            fixed, msg = fix_track(filepath, curve_junc_to_ch, curve_ch_to_junc, args.dry_run)
            if fixed:
                print(f'✓ {filename}: {msg}')
                fixed_count += 1
        except Exception as e:
            print(f'✗ {filename}: {e}')
    
    print(f'\n=== 完成: 修復 {fixed_count} 條軌道 ===')


if __name__ == '__main__':
    main()
