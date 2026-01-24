#!/usr/bin/env python3
"""
TRA 車站投影工具
自動將車站座標投影到最近的軌道點
"""

import json
import math
import sys
from pathlib import Path

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent.parent
STATIONS_FILE = PROJECT_ROOT / "public/data/tra/stations_snapped.geojson"
TRACKS_OD_DIR = PROJECT_ROOT / "public/data/tra/tracks_od"


def euclidean_distance(p1, p2):
    """計算兩點間的歐幾里得距離 (度)"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def project_point_to_segment(point, seg_start, seg_end):
    """將點投影到線段上，返回投影點和距離"""
    dx = seg_end[0] - seg_start[0]
    dy = seg_end[1] - seg_start[1]
    seg_len_sq = dx*dx + dy*dy

    if seg_len_sq == 0:
        return seg_start, euclidean_distance(point, seg_start)

    t = max(0, min(1, ((point[0] - seg_start[0])*dx + (point[1] - seg_start[1])*dy) / seg_len_sq))

    proj_x = seg_start[0] + t * dx
    proj_y = seg_start[1] + t * dy
    proj_point = [proj_x, proj_y]
    dist = euclidean_distance(point, proj_point)

    return proj_point, dist


def snap_to_track(station_coord, track_coords):
    """將車站投影到軌道上，返回投影點和距離"""
    min_dist = float('inf')
    best_point = station_coord

    for i in range(len(track_coords) - 1):
        proj_point, dist = project_point_to_segment(
            station_coord, track_coords[i], track_coords[i+1]
        )
        if dist < min_dist:
            min_dist = dist
            best_point = proj_point

    return best_point, min_dist


def load_track(filepath):
    """載入軌道資料"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if data.get('type') == 'FeatureCollection':
        return data['features'][0]['geometry']['coordinates']
    elif data.get('type') == 'Feature':
        return data['geometry']['coordinates']
    else:
        return data['geometry']['coordinates']


def load_stations():
    """載入車站資料"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def snap_stations_to_track(track_id, station_ids, dry_run=True, threshold_m=50):
    """
    將指定車站投影到指定軌道

    Args:
        track_id: 軌道 ID (如 WL-M-ZN-CH-0)
        station_ids: 要投影的車站 ID 列表
        dry_run: 如果為 True，只顯示結果不實際修改
        threshold_m: 超過此距離的車站需要人工確認

    Returns:
        dict: 投影結果 {station_id: {'new_coord': [...], 'distance_m': ...}}
    """
    # 載入軌道
    track_file = TRACKS_OD_DIR / f"{track_id}.geojson"
    if not track_file.exists():
        print(f"❌ 軌道檔案不存在: {track_file}")
        return {}

    track_coords = load_track(track_file)

    # 載入車站
    stations_data = load_stations()
    stations = stations_data['features']

    results = {}
    needs_review = []

    print(f"=== 車站投影到軌道 {track_id} ===")
    print()

    for feat in stations:
        sid = feat['properties']['station_id']
        if sid not in station_ids:
            continue

        name = feat['properties'].get('name', '?')
        old_coord = feat['geometry']['coordinates']

        # 投影
        new_coord, dist = snap_to_track(old_coord, track_coords)
        dist_m = dist * 111000

        results[sid] = {
            'name': name,
            'old_coord': old_coord,
            'new_coord': new_coord,
            'distance_m': dist_m
        }

        if dist_m > threshold_m:
            needs_review.append(sid)
            print(f"⚠️ {sid} {name}: 距離 {dist_m:.1f}m (需人工確認)")
        else:
            print(f"✅ {sid} {name}: 距離 {dist_m:.1f}m")

        if not dry_run:
            feat['geometry']['coordinates'] = new_coord

    print()

    if needs_review:
        print(f"⚠️ 有 {len(needs_review)} 個車站距離軌道超過 {threshold_m}m，需人工確認:")
        for sid in needs_review:
            r = results[sid]
            print(f"   {sid} {r['name']}: {r['distance_m']:.1f}m")
        print()

    if not dry_run:
        with open(STATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stations_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 已更新 {STATIONS_FILE}")

    return results


def main():
    """主程式"""
    import argparse
    parser = argparse.ArgumentParser(description='TRA 車站投影工具')
    parser.add_argument('track_id', type=str, help='軌道 ID (如 WL-M-ZN-CH-0)')
    parser.add_argument('station_ids', type=str, nargs='+', help='車站 ID 列表')
    parser.add_argument('--apply', action='store_true', help='實際修改檔案')
    parser.add_argument('--threshold', type=float, default=50, help='警告閾值 (公尺)')
    args = parser.parse_args()

    results = snap_stations_to_track(
        args.track_id,
        args.station_ids,
        dry_run=not args.apply,
        threshold_m=args.threshold
    )

    if not args.apply:
        print("💡 使用 --apply 參數來實際修改檔案")


if __name__ == "__main__":
    main()
