#!/usr/bin/env python3
"""
merge_tracks.py - 合併多條軌道建立新的 O-D 軌道

功能：
1. 合併多條連續的軌道
2. 重新計算 station_progress
3. 輸出新的完整軌道

使用方式：
    python scripts/tra/prepare_real_timetable/merge_tracks.py \\
        --tracks WL-ZN-SL-0 WL-SL-BD-0 KL-BD-KL-0 \\
        --output-id WL-HC-KL-0

設計考量：
    - 軌道必須首尾相連（終點接起點）
    - 合併時去除重複的連接點
    - 重新計算累積距離和 station_progress
"""

import json
import os
import argparse
import math
from typing import Dict, List, Optional

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
PROGRESS_FILE = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')


def load_station_progress() -> Dict[str, Dict[str, float]]:
    """載入車站進度表"""
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_station_progress(data: Dict[str, Dict[str, float]]):
    """儲存車站進度表"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_track_geojson(track_id: str) -> Optional[Dict]:
    """載入軌道 GeoJSON"""
    filepath = os.path.join(TRACKS_OD_DIR, f"{track_id}.geojson")
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_coordinates(geojson: Dict) -> List[List[float]]:
    """從 GeoJSON 取得座標"""
    features = geojson.get('features', [])
    if not features:
        return []
    geometry = features[0].get('geometry', {})
    return geometry.get('coordinates', [])


def euclidean_distance(coord1: List[float], coord2: List[float]) -> float:
    """計算歐幾里得距離"""
    dx = coord2[0] - coord1[0]
    dy = coord2[1] - coord1[1]
    return math.sqrt(dx * dx + dy * dy)


def merge_coordinates(tracks_coords: List[List[List[float]]]) -> List[List[float]]:
    """
    合併多條軌道的座標

    自動偵測方向並反轉座標，去除連接點附近的重複座標
    """
    if not tracks_coords:
        return []

    # 第一條軌道：檢查是否需要反轉
    first_coords = list(tracks_coords[0])
    if len(tracks_coords) > 1:
        next_coords = tracks_coords[1]
        if next_coords:
            # 比較第一條軌道尾端與第二條軌道的兩端距離
            d_normal = euclidean_distance(first_coords[-1], next_coords[0])
            d_next_rev = euclidean_distance(first_coords[-1], next_coords[-1])
            d_self_rev = euclidean_distance(first_coords[0], next_coords[0])
            d_both_rev = euclidean_distance(first_coords[0], next_coords[-1])
            # 如果反轉第一條後接正向第二條更近，就反轉第一條
            if d_self_rev < d_normal and d_self_rev < d_next_rev:
                first_coords.reverse()

    merged = first_coords

    for coords in tracks_coords[1:]:
        if not coords:
            continue

        last_point = merged[-1]
        first_point = coords[0]
        last_point_rev = coords[-1]

        dist_normal = euclidean_distance(last_point, first_point)
        dist_reversed = euclidean_distance(last_point, last_point_rev)

        # 如果反轉後更接近，就反轉座標
        if dist_reversed < dist_normal:
            coords = list(reversed(coords))
            dist_normal = dist_reversed

        # 如果距離很近（<100m），跳過第一個點避免重複
        if dist_normal < 0.001:  # 約 100m in degree
            merged.extend(coords[1:])
        else:
            merged.extend(coords)

    return merged


def calculate_station_progress(
    merged_coords: List[List[float]],
    tracks_progress: List[Dict[str, float]],
    tracks_coords: List[List[List[float]]]
) -> Dict[str, float]:
    """
    計算合併後的 station_progress

    方法：將所有車站座標投影到合併後的軌道上，計算 progress
    這樣無論原始軌道方向如何，都能得到正確的單調遞增 progress
    """
    if not merged_coords or len(merged_coords) < 2:
        return {}

    # 計算合併軌道的累積距離
    cum_distances = [0.0]
    for i in range(1, len(merged_coords)):
        dist = euclidean_distance(merged_coords[i-1], merged_coords[i])
        cum_distances.append(cum_distances[-1] + dist)

    total_length = cum_distances[-1]
    if total_length == 0:
        return {}

    # 收集所有不重複的車站 ID（從所有來源軌道）
    all_station_ids = set()
    for progress_map in tracks_progress:
        all_station_ids.update(progress_map.keys())

    # 載入車站座標（從 stations_snapped.geojson）
    stations_file = os.path.join(DATA_DIR, 'stations_snapped.geojson')
    station_coords = {}
    if os.path.exists(stations_file):
        with open(stations_file, 'r', encoding='utf-8') as f:
            stations_data = json.load(f)
        for feature in stations_data.get('features', []):
            sid = feature.get('properties', {}).get('station_id', '')
            coord = feature.get('geometry', {}).get('coordinates', [])
            if sid and coord:
                station_coords[sid] = coord

    # 將車站投影到合併軌道上
    merged_progress = {}

    for station_id in all_station_ids:
        if station_id not in station_coords:
            continue

        sc = station_coords[station_id]

        # 找到最近的軌道線段
        min_dist_sq = float('inf')
        best_progress = 0.0

        for i in range(len(merged_coords) - 1):
            a = merged_coords[i]
            b = merged_coords[i + 1]

            # 計算點到線段的投影
            dx = b[0] - a[0]
            dy = b[1] - a[1]
            seg_len_sq = dx * dx + dy * dy

            if seg_len_sq == 0:
                t = 0
            else:
                t = ((sc[0] - a[0]) * dx + (sc[1] - a[1]) * dy) / seg_len_sq
                t = max(0, min(1, t))

            proj_x = a[0] + t * dx
            proj_y = a[1] + t * dy
            dist_sq = (sc[0] - proj_x) ** 2 + (sc[1] - proj_y) ** 2

            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                # 計算投影點的累積距離
                seg_start_dist = cum_distances[i]
                seg_length = math.sqrt(seg_len_sq)
                best_progress = (seg_start_dist + t * seg_length) / total_length

        merged_progress[station_id] = round(best_progress, 6)

    # 確保起點是 0.0，終點是 1.0
    if merged_progress:
        min_prog = min(merged_progress.values())
        max_prog = max(merged_progress.values())

        if max_prog > min_prog:
            for station_id in merged_progress:
                normalized = (merged_progress[station_id] - min_prog) / (max_prog - min_prog)
                merged_progress[station_id] = round(normalized, 6)

    return merged_progress


def create_merged_geojson(
    coords: List[List[float]],
    track_id: str,
    source_tracks: List[str]
) -> Dict:
    """建立合併後的 GeoJSON"""
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "source_tracks": source_tracks,
                "point_count": len(coords),
                "generated_by": "merge_tracks.py"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }


def main():
    parser = argparse.ArgumentParser(description='合併多條軌道')
    parser.add_argument('--tracks', nargs='+', required=True, help='要合併的軌道 ID 列表')
    parser.add_argument('--output-id', required=True, help='輸出軌道 ID')
    parser.add_argument('--dry-run', action='store_true', help='只顯示會做什麼')

    args = parser.parse_args()

    print(f"合併軌道: {' + '.join(args.tracks)}")
    print(f"輸出 ID: {args.output_id}")

    # 載入 station_progress
    station_progress = load_station_progress()

    # 載入各軌道資料
    tracks_coords = []
    tracks_progress = []

    for track_id in args.tracks:
        geojson = load_track_geojson(track_id)
        if not geojson:
            print(f"錯誤: 找不到軌道 {track_id}")
            return False

        coords = get_coordinates(geojson)
        progress = station_progress.get(track_id, {})

        if not coords:
            print(f"錯誤: 軌道 {track_id} 沒有座標")
            return False

        print(f"  {track_id}: {len(coords)} 點, {len(progress)} 站")
        tracks_coords.append(coords)
        tracks_progress.append(progress)

    # 合併座標
    merged_coords = merge_coordinates(tracks_coords)
    print(f"\n合併後: {len(merged_coords)} 點")

    # 計算 station_progress
    merged_progress = calculate_station_progress(
        merged_coords, tracks_progress, tracks_coords
    )
    print(f"車站數: {len(merged_progress)} 站")

    # 顯示車站列表
    sorted_stations = sorted(merged_progress.items(), key=lambda x: x[1])
    print("\n車站進度 (前5+後5):")
    for sid, prog in sorted_stations[:5]:
        print(f"  {sid}: {prog:.6f}")
    print("  ...")
    for sid, prog in sorted_stations[-5:]:
        print(f"  {sid}: {prog:.6f}")

    if args.dry_run:
        print("\n[Dry run] 不實際寫入檔案")
        return True

    # 建立並儲存 GeoJSON
    geojson = create_merged_geojson(merged_coords, args.output_id, args.tracks)
    output_path = os.path.join(TRACKS_OD_DIR, f"{args.output_id}.geojson")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 儲存 GeoJSON: {output_path}")

    # 更新 station_progress
    station_progress[args.output_id] = merged_progress
    save_station_progress(station_progress)
    print(f"✓ 更新 station_progress")

    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
