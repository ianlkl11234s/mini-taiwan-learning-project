#!/usr/bin/env python3
"""
rebuild_od_bundle.py - 重新產生 tracks_od_bundle.json

從所有 tracks_od/*.geojson 檔案重新產生 bundle 檔案。
"""

import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
TRACKS_OD_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra', 'tracks_od')
BUNDLE_FILE = os.path.join(TRACKS_OD_DIR, 'tracks_od_bundle.json')


def main():
    print('=== 重新產生 tracks_od_bundle.json ===\n')

    bundle = {}
    count = 0

    # 遍歷所有 geojson 檔案
    for filename in sorted(os.listdir(TRACKS_OD_DIR)):
        if not filename.endswith('.geojson'):
            continue

        filepath = os.path.join(TRACKS_OD_DIR, filename)
        track_id = filename.replace('.geojson', '')

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 取得座標
            if 'features' in data and len(data['features']) > 0:
                geometry = data['features'][0]['geometry']
            elif 'geometry' in data:
                geometry = data['geometry']
            else:
                print(f'  {track_id}: 無法解析結構，跳過')
                continue

            coords = geometry.get('coordinates', [])

            if not coords:
                print(f'  {track_id}: 無座標，跳過')
                continue

            # 加入 bundle
            bundle[track_id] = {
                'type': 'LineString',
                'coordinates': coords
            }
            count += 1

        except Exception as e:
            print(f'  {track_id}: 錯誤 - {e}')

    # 儲存 bundle
    with open(BUNDLE_FILE, 'w', encoding='utf-8') as f:
        json.dump(bundle, f, ensure_ascii=False)

    print(f'\n完成！產生 {count} 條軌道到 bundle')

    # 驗證關鍵軌道
    print('\n=== 驗證關鍵軌道 ===')
    for track_id in ['OD-CH-HC', 'OD-CH-HL', 'OD-CH-KL']:
        if track_id in bundle:
            coords = bundle[track_id]['coordinates']
            print(f'{track_id}:')
            print(f'  座標數: {len(coords)}')
            print(f'  座標 0: lat={coords[0][1]:.6f}')
            print(f'  座標 1: lat={coords[1][1]:.6f}')
            diff = (coords[1][1] - coords[0][1]) * 111
            direction = '往北 ✅' if diff > 0 else '往南 ❌'
            print(f'  方向: {direction} ({diff*1000:.0f}m)')


if __name__ == '__main__':
    main()
