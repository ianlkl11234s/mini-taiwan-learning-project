#!/usr/bin/env python3
"""
建立南迴線軌道

問題：許多西部南段↔東部的車次被分配到北迴軌道，但應該走南迴。
解決：建立正確的南迴軌道並更新時刻表。

南迴路線組成：
- 新左營→台東：SK-ZY-TT-1（南迴線）
- 台東→花蓮：TL-TT-HL（台東線）
- 台南→新左營：從 WL-CH-ZY-0 擷取

需要建立的軌道：
1. BB-ZY-HL-SK-1（新左營→花蓮，經南迴）
2. BB-HL-ZY-SK-0（花蓮→新左營，經南迴）
3. OD-TN-HL-SK（台南→花蓮，經南迴）
4. OD-HL-TN-SK（花蓮→台南，經南迴）
5. OD-CZ-HL-SK（潮州→花蓮，經南迴）
6. OD-HL-CZ-SK（花蓮→潮州，經南迴）
"""

import json
import os
from pathlib import Path

# 路徑設定
TRACKS_OD_DIR = Path('public/data/tra/tracks_od')
SCHEDULE_FILE = Path('public/data/tra/schedules_real/master_schedule.json')


def load_track(filename: str) -> list:
    """載入軌道座標"""
    with open(TRACKS_OD_DIR / filename, 'r') as f:
        data = json.load(f)
    return data['features'][0]['geometry']['coordinates']


def find_closest_idx(coords: list, target: tuple) -> int:
    """找到最接近目標點的索引"""
    min_dist = float('inf')
    min_idx = 0
    for i, c in enumerate(coords):
        dist = (c[0] - target[0])**2 + (c[1] - target[1])**2
        if dist < min_dist:
            min_dist = dist
            min_idx = i
    return min_idx


def save_track(filename: str, coords: list, properties: dict):
    """儲存軌道為 GeoJSON"""
    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": properties,
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }
    with open(TRACKS_OD_DIR / filename, 'w') as f:
        json.dump(geojson, f)
    print(f'  ✅ 已建立: {filename} ({len(coords)} 點)')


def build_south_link_tracks():
    """建立南迴軌道"""
    print('=== 建立南迴軌道 ===\n')

    # 載入基礎軌道
    print('載入基礎軌道...')
    sk_zy_tt = load_track('SK-ZY-TT-1.geojson')  # 新左營→台東
    sk_tt_zy = load_track('SK-TT-ZY-0.geojson')  # 台東→新左營
    tl_tt_hl = load_track('TL-TT-HL.geojson')    # 台東→花蓮
    tl_hl_tt = load_track('TL-HL-TT.geojson')    # 花蓮→台東
    wl_ch_zy = load_track('WL-CH-ZY-0.geojson')  # 彰化→新左營（含台南）
    wl_zy_ch = load_track('WL-ZY-CH-1.geojson')  # 新左營→彰化（含台南）

    # 關鍵站點座標
    TAINAN = (120.2130, 22.9968)
    ZUOYING = (120.3070, 22.6873)
    CHAOZHOU = (120.5361, 22.5502)

    # 1. BB-ZY-HL-SK-1（新左營→花蓮，經南迴）
    print('\n1. 建立 BB-ZY-HL-SK-1（新左營→花蓮）')
    coords_zy_hl = sk_zy_tt + tl_tt_hl[1:]  # 跳過重複的台東站點
    save_track('BB-ZY-HL-SK-1.geojson', coords_zy_hl, {
        'track_id': 'BB-ZY-HL-SK-1',
        'name': '新左營-花蓮(南迴)',
        'route': 'south_link'
    })

    # 2. BB-HL-ZY-SK-0（花蓮→新左營，經南迴）
    print('\n2. 建立 BB-HL-ZY-SK-0（花蓮→新左營）')
    coords_hl_zy = tl_hl_tt + sk_tt_zy[1:]
    save_track('BB-HL-ZY-SK-0.geojson', coords_hl_zy, {
        'track_id': 'BB-HL-ZY-SK-0',
        'name': '花蓮-新左營(南迴)',
        'route': 'south_link'
    })

    # 3. 擷取台南→新左營段
    print('\n3. 擷取台南→新左營段')
    tainan_idx = find_closest_idx(wl_ch_zy, TAINAN)
    zuoying_idx = find_closest_idx(wl_ch_zy, ZUOYING)
    # WL-CH-ZY-0 是彰化→新左營，所以 tainan_idx < zuoying_idx
    tn_zy_segment = wl_ch_zy[tainan_idx:zuoying_idx+1]
    print(f'  台南→新左營段: {len(tn_zy_segment)} 點')

    # 4. 擷取新左營→台南段（反向）
    zy_tainan_idx = find_closest_idx(wl_zy_ch, ZUOYING)
    zy_tainan_idx_end = find_closest_idx(wl_zy_ch, TAINAN)
    zy_tn_segment = wl_zy_ch[zy_tainan_idx:zy_tainan_idx_end+1]
    print(f'  新左營→台南段: {len(zy_tn_segment)} 點')

    # 5. OD-TN-HL-SK（台南→花蓮，經南迴）
    print('\n4. 建立 OD-TN-HL-SK（台南→花蓮）')
    coords_tn_hl = tn_zy_segment + sk_zy_tt[1:] + tl_tt_hl[1:]
    save_track('OD-TN-HL-SK.geojson', coords_tn_hl, {
        'track_id': 'OD-TN-HL-SK',
        'name': '台南-花蓮(南迴)',
        'route': 'south_link'
    })

    # 6. OD-HL-TN-SK（花蓮→台南，經南迴）
    print('\n5. 建立 OD-HL-TN-SK（花蓮→台南）')
    coords_hl_tn = tl_hl_tt + sk_tt_zy[1:] + zy_tn_segment[1:]
    save_track('OD-HL-TN-SK.geojson', coords_hl_tn, {
        'track_id': 'OD-HL-TN-SK',
        'name': '花蓮-台南(南迴)',
        'route': 'south_link'
    })

    # 7. 擷取潮州→新左營段（從 SK 軌道）
    print('\n6. 擷取潮州相關段')
    chaozhou_idx_sk = find_closest_idx(sk_zy_tt, CHAOZHOU)
    cz_tt_segment = sk_zy_tt[chaozhou_idx_sk:]  # 潮州→台東
    print(f'  潮州→台東段: {len(cz_tt_segment)} 點')

    chaozhou_idx_sk_rev = find_closest_idx(sk_tt_zy, CHAOZHOU)
    tt_cz_segment = sk_tt_zy[:chaozhou_idx_sk_rev+1]  # 台東→潮州
    print(f'  台東→潮州段: {len(tt_cz_segment)} 點')

    # 8. OD-CZ-HL-SK（潮州→花蓮，經南迴）
    print('\n7. 建立 OD-CZ-HL-SK（潮州→花蓮）')
    coords_cz_hl = cz_tt_segment + tl_tt_hl[1:]
    save_track('OD-CZ-HL-SK.geojson', coords_cz_hl, {
        'track_id': 'OD-CZ-HL-SK',
        'name': '潮州-花蓮(南迴)',
        'route': 'south_link'
    })

    # 9. OD-HL-CZ-SK（花蓮→潮州，經南迴）
    print('\n8. 建立 OD-HL-CZ-SK（花蓮→潮州）')
    coords_hl_cz = tl_hl_tt + tt_cz_segment[1:]
    save_track('OD-HL-CZ-SK.geojson', coords_hl_cz, {
        'track_id': 'OD-HL-CZ-SK',
        'name': '花蓮-潮州(南迴)',
        'route': 'south_link'
    })

    print('\n✅ 南迴軌道建立完成!')
    return True


def update_schedule():
    """更新時刻表，將錯誤的北迴軌道改為南迴軌道"""
    print('\n=== 更新時刻表 ===\n')

    with open(SCHEDULE_FILE, 'r') as f:
        data = json.load(f)

    # 軌道對映：北迴 → 南迴
    track_mapping = {
        'OD-TN-HL': 'OD-TN-HL-SK',
        'OD-HL-TN': 'OD-HL-TN-SK',
        'OD-CZ-HL': 'OD-CZ-HL-SK',
        'OD-HL-CZ': 'OD-HL-CZ-SK',
        'BB-ZY-HL-1': 'BB-ZY-HL-SK-1',
        'BB-HL-ZY-0': 'BB-HL-ZY-SK-0',
    }

    updated_count = 0
    for schedule in data['schedules']:
        old_track = schedule.get('od_track_id', '')
        if old_track in track_mapping:
            new_track = track_mapping[old_track]
            print(f"  {schedule['train_no']:>5} ({schedule['train_type'][:8]:8}): {old_track} → {new_track}")
            schedule['od_track_id'] = new_track
            updated_count += 1

    # 儲存更新後的時刻表
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'\n✅ 已更新 {updated_count} 班車次的軌道')
    return updated_count


def verify_tracks():
    """驗證新建軌道"""
    print('\n=== 驗證新建軌道 ===\n')

    new_tracks = [
        'BB-ZY-HL-SK-1.geojson',
        'BB-HL-ZY-SK-0.geojson',
        'OD-TN-HL-SK.geojson',
        'OD-HL-TN-SK.geojson',
        'OD-CZ-HL-SK.geojson',
        'OD-HL-CZ-SK.geojson',
    ]

    for fname in new_tracks:
        filepath = TRACKS_OD_DIR / fname
        if not filepath.exists():
            print(f'  ❌ {fname}: 檔案不存在')
            continue

        coords = load_track(fname)
        max_lat = max(c[1] for c in coords)
        min_lat = min(c[1] for c in coords)

        # 南迴軌道不應該經過宜蘭以北（lat > 24.5）
        if max_lat > 24.5:
            print(f'  ⚠️ {fname}: 最北 lat={max_lat:.4f}，可能仍走北迴')
        else:
            print(f'  ✅ {fname}: 最北 lat={max_lat:.4f}，最南 lat={min_lat:.4f}')


if __name__ == '__main__':
    os.chdir(Path(__file__).parent.parent.parent)

    build_south_link_tracks()
    verify_tracks()
    update_schedule()
