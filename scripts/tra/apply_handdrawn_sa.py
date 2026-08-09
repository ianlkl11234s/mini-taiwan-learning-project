#!/usr/bin/env python3
"""
apply_handdrawn_sa.py - 用手繪軌道替換深澳線 SA-RF-BD-0 / SA-BD-RF-1

使用方式：
1. 打開 https://geojson.io
2. 拖入 public/data/tra/tracks_handdrawn/SA-RF-BD.geojson
3. 編輯 LineString（瑞芳→海科館→八斗子 的路徑）
4. 確保座標順序是：瑞芳 → ... → 海科館 → ... → 八斗子
5. 存檔覆蓋原檔（Save > GeoJSON）
6. 執行此腳本：python3 scripts/tra/apply_handdrawn_sa.py

腳本會：
- 讀取手繪 LineString
- 產生 SA-RF-BD-0.geojson (瑞芳→八斗子)
- 產生 SA-BD-RF-1.geojson (八斗子→瑞芳，反向)
- 計算 station_progress (歐幾里得距離)
- 更新 od_station_progress.json
- 更新 tracks_od_bundle.json
- 同時更新 tracks_golden/ 下的顯示軌道
"""

import json
import os
import math

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
HANDDRAWN_FILE = os.path.join(DATA_DIR, 'tracks_handdrawn', 'SA-RF-BD.geojson')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
TRACKS_GOLDEN_DIR = os.path.join(DATA_DIR, 'tracks_golden')
PROGRESS_FILE = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')
BUNDLE_FILE = os.path.join(TRACKS_OD_DIR, 'tracks_od_bundle.json')

STATIONS = {
    '7360': ('瑞芳', [121.806254, 25.109005]),
    '7361': ('海科館', [121.799922, 25.137468]),
    '7362': ('八斗子', [121.802871, 25.135307]),
}


def euclidean(a, b):
    return math.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2)


def load_handdrawn_line():
    """從手繪檔案取出 LineString 座標"""
    with open(HANDDRAWN_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for feat in data['features']:
        geom = feat.get('geometry', {})
        if geom.get('type') == 'LineString':
            coords = geom['coordinates']
            if len(coords) >= 2:
                return coords
    raise ValueError('找不到 LineString 在手繪檔案中')


def find_nearest_point_index(coords, target):
    """找軌道上最接近 target 的座標索引"""
    min_d = float('inf')
    min_i = 0
    for i, c in enumerate(coords):
        d = euclidean(c, target)
        if d < min_d:
            min_d = d
            min_i = i
    return min_i, min_d


def calculate_progress(coords, station_coords):
    """計算每個車站在軌道上的 progress (0-1)"""
    # 累積距離
    cum_dist = [0.0]
    for i in range(1, len(coords)):
        cum_dist.append(cum_dist[-1] + euclidean(coords[i-1], coords[i]))
    total = cum_dist[-1]
    if total == 0:
        return {}

    progress = {}
    for sid, (name, coord) in station_coords.items():
        idx, _ = find_nearest_point_index(coords, coord)
        progress[sid] = round(cum_dist[idx] / total, 6)

    # 強制起點=0, 終點=1
    sorted_sids = sorted(progress.items(), key=lambda x: x[1])
    if sorted_sids:
        progress[sorted_sids[0][0]] = 0.0
        progress[sorted_sids[-1][0]] = 1.0

    return progress


def save_od_geojson(track_id, coords, stations):
    """儲存 O-D 軌道 geojson"""
    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "source": "handdrawn",
                "point_count": len(coords),
                "station_count": len(stations)
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }
    path = os.path.join(TRACKS_OD_DIR, f'{track_id}.geojson')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    print(f'  ✓ {path}')


def save_golden_geojson(track_id, coords, name, origin, destination, direction):
    """儲存顯示軌道 geojson (tracks_golden)"""
    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "name": name,
                "origin": origin,
                "destination": destination,
                "direction": direction
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }
    path = os.path.join(TRACKS_GOLDEN_DIR, f'{track_id}.geojson')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    print(f'  ✓ {path}')


def main():
    print('=' * 60)
    print('套用手繪深澳線軌道')
    print('=' * 60)

    # 1. 讀手繪軌道
    print(f'\n[1] 讀取手繪檔案: {HANDDRAWN_FILE}')
    coords_rf_bd = load_handdrawn_line()
    print(f'  座標數: {len(coords_rf_bd)}')
    print(f'  起點: {coords_rf_bd[0]}')
    print(f'  終點: {coords_rf_bd[-1]}')

    # 2. 驗證起點終點是否接近瑞芳/八斗子
    ruifang = STATIONS['7360'][1]
    badouzi = STATIONS['7362'][1]
    d_start = euclidean(coords_rf_bd[0], ruifang)
    d_end = euclidean(coords_rf_bd[-1], badouzi)
    print(f'  起點離瑞芳: {d_start:.6f}')
    print(f'  終點離八斗子: {d_end:.6f}')

    if d_start > 0.005:
        print(f'  ⚠️  警告: 起點離瑞芳超過 0.005 度 (~500m)')
    if d_end > 0.005:
        print(f'  ⚠️  警告: 終點離八斗子超過 0.005 度 (~500m)')

    # 3. 反向座標
    coords_bd_rf = list(reversed(coords_rf_bd))

    # 4. 計算 station_progress
    print(f'\n[2] 計算 station_progress')
    progress_rf_bd = calculate_progress(coords_rf_bd, STATIONS)
    progress_bd_rf = calculate_progress(coords_bd_rf, STATIONS)
    print(f'  SA-RF-BD-0:')
    for sid, p in sorted(progress_rf_bd.items(), key=lambda x: x[1]):
        print(f'    {sid} {STATIONS[sid][0]}: {p}')
    print(f'  SA-BD-RF-1:')
    for sid, p in sorted(progress_bd_rf.items(), key=lambda x: x[1]):
        print(f'    {sid} {STATIONS[sid][0]}: {p}')

    # 5. 存 O-D 軌道 geojson
    print(f'\n[3] 儲存 O-D 軌道')
    save_od_geojson('SA-RF-BD-0', coords_rf_bd, progress_rf_bd)
    save_od_geojson('SA-BD-RF-1', coords_bd_rf, progress_bd_rf)

    # 6. 存 Golden 顯示軌道
    print(f'\n[4] 儲存顯示軌道 (tracks_golden)')
    save_golden_geojson(
        'SA-RF-BD-0', coords_rf_bd,
        '深澳線 (瑞芳→八斗子)', '瑞芳', '八斗子', 0
    )
    save_golden_geojson(
        'SA-BD-RF-1', coords_bd_rf,
        '深澳線 (八斗子→瑞芳)', '八斗子', '瑞芳', 1
    )

    # 7. 更新 od_station_progress.json
    print(f'\n[5] 更新 od_station_progress.json')
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        all_progress = json.load(f)
    all_progress['SA-RF-BD-0'] = progress_rf_bd
    all_progress['SA-BD-RF-1'] = progress_bd_rf
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)
    print(f'  ✓ 已更新')

    # 8. 更新 tracks_od_bundle.json
    print(f'\n[6] 更新 tracks_od_bundle.json')
    with open(BUNDLE_FILE, 'r', encoding='utf-8') as f:
        bundle = json.load(f)
    bundle['SA-RF-BD-0'] = {'type': 'LineString', 'coordinates': coords_rf_bd}
    bundle['SA-BD-RF-1'] = {'type': 'LineString', 'coordinates': coords_bd_rf}
    with open(BUNDLE_FILE, 'w', encoding='utf-8') as f:
        json.dump(bundle, f, ensure_ascii=False)
    print(f'  ✓ 已更新 ({len(bundle)} 條軌道)')

    print('\n✅ 全部完成！重新整理瀏覽器就會看到新的深澳線軌道')
    print('\n⚠️  注意：PXSA 跨線軌道用了舊的 SA 座標，可能需要重跑:')
    print('   python3 scripts/tra/prepare_real_timetable/build_crossline_tracks.py')
    print('   python3 scripts/tra/rebuild_od_bundle.py')


if __name__ == '__main__':
    main()
