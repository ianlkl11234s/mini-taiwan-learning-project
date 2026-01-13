#!/usr/bin/env python3
"""
smooth_yl_track.py - 平滑化 YL 軌道，移除小迴圈

問題：YL 軌道在貢寮/雙溪區域有座標往回退的情況，
導致列車看起來會倒退或繞圈。

解決：移除緯度不單調的座標點，確保北上軌道緯度遞增。
"""

import json
import os
from typing import List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACKS_FILE = os.path.join(BASE_DIR, 'public', 'data', 'tra', 'tracks_official', 'all_tracks.geojson')


def smooth_coordinates(coords: List[List[float]], direction: int) -> List[List[float]]:
    """
    平滑化座標，移除不單調的點

    direction=0: 南下，緯度應遞減
    direction=1: 北上，緯度應遞增
    """
    if len(coords) < 2:
        return coords

    smoothed = [coords[0]]

    for i in range(1, len(coords)):
        curr_lat = coords[i][1]
        prev_lat = smoothed[-1][1]

        if direction == 0:
            # 南下：允許緯度遞減或微小遞增（軌道彎曲）
            # 只跳過大幅度的遞增（往回走超過 50m）
            if curr_lat - prev_lat > 0.0005:  # ~55m
                continue
        else:
            # 北上：允許緯度遞增或微小遞減
            # 只跳過大幅度的遞減（往回走超過 50m）
            if prev_lat - curr_lat > 0.0005:  # ~55m
                continue

        smoothed.append(coords[i])

    return smoothed


def fix_yl_tracks():
    """修正 YL 軌道的小迴圈"""
    print("=" * 60)
    print("平滑化 YL 軌道 - 移除小迴圈")
    print("=" * 60)

    with open(TRACKS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    modified = False

    for feature in data['features']:
        props = feature['properties']
        track_id = props.get('track_id', '')

        if not track_id.startswith('YL-'):
            continue

        geom = feature['geometry']
        if geom['type'] != 'LineString':
            print(f"\n{track_id}: 跳過（非 LineString）")
            continue

        direction = int(track_id.split('-')[1])
        coords = geom['coordinates']

        print(f"\n處理 {track_id} (方向 {direction})")
        print(f"  原始座標點數: {len(coords)}")

        # 平滑化
        smoothed = smooth_coordinates(coords, direction)

        removed = len(coords) - len(smoothed)
        print(f"  移除點數: {removed}")
        print(f"  平滑後點數: {len(smoothed)}")

        if removed > 0:
            feature['geometry']['coordinates'] = smoothed
            modified = True

    if modified:
        with open(TRACKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n已儲存修正後的軌道")

    print("\n" + "=" * 60)
    print("完成！請重新執行 build_yl_bh_od_tracks.py")
    print("=" * 60)


if __name__ == '__main__':
    fix_yl_tracks()
