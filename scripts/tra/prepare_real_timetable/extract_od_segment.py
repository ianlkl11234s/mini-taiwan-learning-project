#!/usr/bin/env python3
"""
extract_od_segment.py - 從現有軌道擷取 O-D 子區段

功能：
1. 根據起站 ID 和迄站 ID，找到包含這兩站的現有軌道
2. 擷取對應的座標區段
3. 計算新的 station_progress
4. 輸出新的 O-D 軌道 GeoJSON

使用方式：
    python scripts/tra/prepare_real_timetable/extract_od_segment.py \\
        --origin 1210 --dest 0900 --output-id WL-HC-KL

核心邏輯：
    - 找到包含起點和終點的軌道（檢查 station_progress）
    - 確認方向正確（起點 progress < 終點 progress）
    - 擷取座標和車站 progress
"""

import json
import os
import argparse
import math
from typing import Dict, List, Tuple, Optional

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
PROGRESS_FILE = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')


def load_station_progress() -> Dict[str, Dict[str, float]]:
    """載入車站進度表"""
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_track_geojson(track_id: str) -> Optional[Dict]:
    """載入軌道 GeoJSON"""
    filepath = os.path.join(TRACKS_OD_DIR, f"{track_id}.geojson")
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_covering_track(
    origin_id: str,
    dest_id: str,
    station_progress: Dict[str, Dict[str, float]]
) -> Optional[Tuple[str, float, float]]:
    """
    找到包含起點和終點的軌道

    Returns:
        (track_id, origin_progress, dest_progress) 或 None
    """
    candidates = []

    for track_id, progress_map in station_progress.items():
        if origin_id in progress_map and dest_id in progress_map:
            origin_prog = progress_map[origin_id]
            dest_prog = progress_map[dest_id]

            # 確認方向正確：起點 progress < 終點 progress
            if origin_prog < dest_prog:
                # 計算涵蓋的車站數（用於選擇最佳軌道）
                station_count = len(progress_map)
                candidates.append((track_id, origin_prog, dest_prog, station_count))

    if not candidates:
        return None

    # 優先選擇涵蓋車站數最多的軌道（通常是最完整的）
    best = max(candidates, key=lambda x: x[3])
    return (best[0], best[1], best[2])


def euclidean_distance(coord1: List[float], coord2: List[float]) -> float:
    """計算歐幾里得距離"""
    dx = coord2[0] - coord1[0]
    dy = coord2[1] - coord1[1]
    return math.sqrt(dx * dx + dy * dy)


def calculate_cumulative_distances(coords: List[List[float]]) -> List[float]:
    """計算累積距離"""
    distances = [0.0]
    for i in range(1, len(coords)):
        dist = euclidean_distance(coords[i-1], coords[i])
        distances.append(distances[-1] + dist)
    return distances


def extract_segment(
    geojson: Dict,
    start_progress: float,
    end_progress: float
) -> List[List[float]]:
    """
    從軌道中擷取指定 progress 範圍的座標
    """
    # 取得座標
    geometry = geojson.get('features', [{}])[0].get('geometry', {})
    coords = geometry.get('coordinates', [])

    if not coords:
        return []

    # 計算累積距離和總長度
    cum_distances = calculate_cumulative_distances(coords)
    total_length = cum_distances[-1]

    if total_length == 0:
        return coords

    # 計算起點和終點的目標距離
    start_dist = start_progress * total_length
    end_dist = end_progress * total_length

    # 擷取座標
    extracted = []

    for i, (coord, cum_dist) in enumerate(zip(coords, cum_distances)):
        if cum_dist >= start_dist and cum_dist <= end_dist:
            extracted.append(coord)
        elif cum_dist > end_dist:
            break

    # 確保至少有起點和終點
    if len(extracted) < 2:
        # 找最接近的點
        start_idx = 0
        end_idx = len(coords) - 1

        for i, cum_dist in enumerate(cum_distances):
            if cum_dist <= start_dist:
                start_idx = i
            if cum_dist <= end_dist:
                end_idx = i

        extracted = coords[start_idx:end_idx+1]

    return extracted


def extract_station_progress(
    original_progress: Dict[str, float],
    origin_id: str,
    dest_id: str
) -> Dict[str, float]:
    """
    擷取並重新計算車站 progress

    原始 progress 是相對於整條軌道的，需要轉換為相對於新區段的
    """
    origin_prog = original_progress[origin_id]
    dest_prog = original_progress[dest_id]
    segment_length = dest_prog - origin_prog

    if segment_length == 0:
        return {origin_id: 0.0, dest_id: 1.0}

    new_progress = {}

    for station_id, prog in original_progress.items():
        if prog >= origin_prog and prog <= dest_prog:
            # 轉換為新區段的相對 progress
            new_prog = (prog - origin_prog) / segment_length
            new_progress[station_id] = round(new_prog, 6)

    return new_progress


def create_od_geojson(
    coords: List[List[float]],
    track_id: str,
    origin_name: str,
    dest_name: str,
    source_track: str
) -> Dict:
    """建立新的 O-D 軌道 GeoJSON"""
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "name": f"{origin_name} → {dest_name}",
                "source_track": source_track,
                "point_count": len(coords),
                "generated_by": "extract_od_segment.py"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }


def main():
    parser = argparse.ArgumentParser(description='從現有軌道擷取 O-D 子區段')
    parser.add_argument('--origin', required=True, help='起站 ID (如 1210)')
    parser.add_argument('--dest', required=True, help='迄站 ID (如 0900)')
    parser.add_argument('--output-id', required=True, help='輸出軌道 ID (如 WL-HC-KL)')
    parser.add_argument('--origin-name', default='', help='起站名稱')
    parser.add_argument('--dest-name', default='', help='迄站名稱')
    parser.add_argument('--dry-run', action='store_true', help='只顯示會做什麼，不實際執行')

    args = parser.parse_args()

    print(f"擷取 O-D 軌道: {args.origin} → {args.dest}")

    # 載入資料
    station_progress = load_station_progress()

    # 找到覆蓋的軌道
    result = find_covering_track(args.origin, args.dest, station_progress)

    if not result:
        print(f"錯誤: 找不到包含 {args.origin} 和 {args.dest} 的軌道")
        print("可能原因:")
        print("  1. 起迄站不在同一條軌道上")
        print("  2. 方向相反（需要使用反向軌道）")
        return False

    source_track, origin_prog, dest_prog = result
    print(f"  找到來源軌道: {source_track}")
    print(f"  起點 progress: {origin_prog:.6f}")
    print(f"  終點 progress: {dest_prog:.6f}")

    # 載入來源軌道
    geojson = load_track_geojson(source_track)
    if not geojson:
        print(f"錯誤: 無法載入軌道 GeoJSON: {source_track}")
        return False

    # 擷取座標
    coords = extract_segment(geojson, origin_prog, dest_prog)
    print(f"  擷取座標: {len(coords)} 點")

    # 擷取車站 progress
    new_progress = extract_station_progress(
        station_progress[source_track],
        args.origin,
        args.dest
    )
    print(f"  擷取車站: {len(new_progress)} 站")

    # 顯示車站列表
    sorted_stations = sorted(new_progress.items(), key=lambda x: x[1])
    print("  車站進度:")
    for sid, prog in sorted_stations[:5]:
        print(f"    {sid}: {prog:.6f}")
    if len(sorted_stations) > 5:
        print(f"    ... (共 {len(sorted_stations)} 站)")

    if args.dry_run:
        print("\n[Dry run] 不實際寫入檔案")
        return True

    # 建立 GeoJSON
    new_geojson = create_od_geojson(
        coords,
        args.output_id,
        args.origin_name or args.origin,
        args.dest_name or args.dest,
        source_track
    )

    # 儲存 GeoJSON
    output_path = os.path.join(TRACKS_OD_DIR, f"{args.output_id}.geojson")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_geojson, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 儲存 GeoJSON: {output_path}")

    # 更新 station_progress
    station_progress[args.output_id] = new_progress
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(station_progress, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 更新 station_progress")

    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
