#!/usr/bin/env python3
"""
TRA 車站進度值計算工具
自動計算車站在軌道上的 progress 值
"""

import json
import math
import sys
from pathlib import Path

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent.parent
STATIONS_FILE = PROJECT_ROOT / "public/data/tra/stations_snapped.geojson"
TRACKS_OD_DIR = PROJECT_ROOT / "public/data/tra/tracks_od"
PROGRESS_FILE = PROJECT_ROOT / "public/data/tra/tracks_od/od_station_progress.json"


def euclidean_distance(p1, p2):
    """計算兩點間的歐幾里得距離 (度)"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def find_nearest_progress(coords, target_point):
    """計算目標點在軌道上的 progress 值"""
    total_length = 0
    segment_lengths = []

    for i in range(len(coords) - 1):
        d = euclidean_distance(coords[i], coords[i+1])
        segment_lengths.append(d)
        total_length += d

    if total_length == 0:
        return 0, 0

    min_dist = float('inf')
    best_progress = 0
    cumulative = 0

    for i in range(len(coords) - 1):
        p1 = coords[i]
        p2 = coords[i+1]

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        seg_len_sq = dx*dx + dy*dy

        if seg_len_sq == 0:
            t = 0
        else:
            t = max(0, min(1, ((target_point[0] - p1[0])*dx + (target_point[1] - p1[1])*dy) / seg_len_sq))

        proj_x = p1[0] + t * dx
        proj_y = p1[1] + t * dy
        dist = euclidean_distance(target_point, [proj_x, proj_y])

        if dist < min_dist:
            min_dist = dist
            best_progress = (cumulative + t * segment_lengths[i]) / total_length

        cumulative += segment_lengths[i]

    return best_progress, min_dist


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
    return data['features']


def load_progress():
    """載入進度值資料"""
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_progress(progress_data):
    """儲存進度值資料"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)


def calc_station_progress(track_id, station_ids, dry_run=True):
    """
    計算指定車站在指定軌道上的進度值

    Args:
        track_id: 軌道 ID (如 WL-M-ZN-CH-0)
        station_ids: 車站 ID 列表
        dry_run: 如果為 True，只顯示結果不實際修改

    Returns:
        dict: {station_id: progress}
    """
    # 載入軌道
    track_file = TRACKS_OD_DIR / f"{track_id}.geojson"
    if not track_file.exists():
        print(f"❌ 軌道檔案不存在: {track_file}")
        return {}

    track_coords = load_track(track_file)

    # 載入車站
    stations = load_stations()
    station_coords = {}
    station_names = {}
    for feat in stations:
        sid = feat['properties']['station_id']
        if sid in station_ids:
            station_coords[sid] = feat['geometry']['coordinates']
            station_names[sid] = feat['properties'].get('name', '?')

    # 計算進度值
    results = {}
    print(f"=== 計算軌道 {track_id} 的車站進度值 ===")
    print()

    for sid in station_ids:
        if sid not in station_coords:
            print(f"⚠️ 找不到車站 {sid}")
            continue

        progress, dist = find_nearest_progress(track_coords, station_coords[sid])
        dist_m = dist * 111000
        results[sid] = round(progress, 6)

        flag = '⚠️' if dist_m > 50 else '✅'
        print(f"{flag} {sid} {station_names[sid]}: progress={progress:.6f}, 距離={dist_m:.1f}m")

    print()

    if not dry_run:
        # 更新進度值檔案
        progress_data = load_progress()

        if track_id not in progress_data:
            progress_data[track_id] = {}

        progress_data[track_id].update(results)

        # 如果是方向 0，同時計算方向 1
        if track_id.endswith('-0'):
            reverse_id = track_id[:-1] + '1'
            if reverse_id not in progress_data:
                progress_data[reverse_id] = {}
            for sid, prog in results.items():
                progress_data[reverse_id][sid] = round(1 - prog, 6)
            print(f"✅ 同時更新反向軌道 {reverse_id}")

        save_progress(progress_data)
        print(f"✅ 已更新 {PROGRESS_FILE}")

    return results


def recalc_all_progress(track_id, dry_run=True):
    """
    重新計算軌道上所有已設定車站的進度值

    Args:
        track_id: 軌道 ID
        dry_run: 如果為 True，只顯示結果不實際修改
    """
    progress_data = load_progress()

    if track_id not in progress_data:
        print(f"❌ 找不到軌道 {track_id} 的進度值設定")
        return

    station_ids = list(progress_data[track_id].keys())
    print(f"找到 {len(station_ids)} 個車站")

    return calc_station_progress(track_id, station_ids, dry_run)


def main():
    """主程式"""
    import argparse
    parser = argparse.ArgumentParser(description='TRA 車站進度值計算工具')
    parser.add_argument('track_id', type=str, help='軌道 ID (如 WL-M-ZN-CH-0)')
    parser.add_argument('station_ids', type=str, nargs='*', help='車站 ID 列表 (留空則重算所有)')
    parser.add_argument('--apply', action='store_true', help='實際修改檔案')
    args = parser.parse_args()

    if args.station_ids:
        results = calc_station_progress(
            args.track_id,
            args.station_ids,
            dry_run=not args.apply
        )
    else:
        results = recalc_all_progress(
            args.track_id,
            dry_run=not args.apply
        )

    if not args.apply:
        print("💡 使用 --apply 參數來實際修改檔案")


if __name__ == "__main__":
    main()
