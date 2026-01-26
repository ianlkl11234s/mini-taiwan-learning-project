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

    去除連接點附近的重複座標
    """
    if not tracks_coords:
        return []

    merged = list(tracks_coords[0])

    for coords in tracks_coords[1:]:
        if not coords:
            continue

        # 檢查連接點距離
        last_point = merged[-1]
        first_point = coords[0]
        dist = euclidean_distance(last_point, first_point)

        # 如果距離很近（<100m），跳過第一個點避免重複
        if dist < 0.001:  # 約 100m in degree
            merged.extend(coords[1:])
        else:
            merged.extend(coords)

    return merged


def calculate_station_progress(
    coords: List[List[float]],
    tracks_progress: List[Dict[str, float]],
    tracks_coords: List[List[List[float]]]
) -> Dict[str, float]:
    """
    計算合併後的 station_progress

    方法：
    1. 計算每條軌道在合併後的長度佔比
    2. 根據佔比重新計算各站的 progress
    """
    # 計算各軌道長度
    track_lengths = []
    for track_coords in tracks_coords:
        length = 0.0
        for i in range(1, len(track_coords)):
            length += euclidean_distance(track_coords[i-1], track_coords[i])
        track_lengths.append(length)

    total_length = sum(track_lengths)
    if total_length == 0:
        return {}

    # 計算各軌道的起點 offset
    offsets = [0.0]
    for i, length in enumerate(track_lengths[:-1]):
        offsets.append(offsets[-1] + length / total_length)

    # 合併各軌道的 station_progress
    merged_progress = {}

    for i, (progress_map, track_length) in enumerate(zip(tracks_progress, track_lengths)):
        scale = track_length / total_length
        offset = offsets[i]

        for station_id, prog in progress_map.items():
            new_prog = offset + prog * scale
            # 如果車站已存在，取較小的值（靠近起點）
            if station_id not in merged_progress:
                merged_progress[station_id] = round(new_prog, 6)

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
