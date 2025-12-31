#!/usr/bin/env python3
"""
修復安坑輕軌軌道 v3 - 手動指定正確的分段連接順序

TDX Shape 資料分析：
- 分段 8-10-11-1: K01 附近到 K05 的路徑（需反轉後連接）
- 分段 7-6-5-4-0: K05 到 K06 附近的路徑（需反轉後連接）
- 分段 2: K06 到 K09 的路徑（需反轉）
- 分段 3: 回頭路（排除）

手動指定連接順序：
K01 → 分段8反轉 → 分段9反轉 → 分段10反轉 → 分段11反轉 → 分段1反轉 →
分段7反轉 → 分段6反轉 → 分段5反轉 → 分段4反轉 → 分段0 → 分段2反轉 → K09
"""

import json
import re
import math
import os
from typing import List, Dict, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TDX_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "tdx_ankeng_lrt")
TRACK_DIR = os.path.join(PROJECT_ROOT, "public/data/tracks")
STATION_FILE = os.path.join(PROJECT_ROOT, "public/data/ankeng_lrt_stations.geojson")
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "public/data/station_progress.json")


def euclidean_distance(p1: List[float], p2: List[float]) -> float:
    """計算 Euclidean 距離"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def parse_wkt_multilinestring(wkt: str) -> List[List[List[float]]]:
    """解析 WKT MULTILINESTRING 為分段座標陣列"""
    match = re.search(r'MULTILINESTRING\s*\(\s*\((.*)\)\s*\)', wkt, re.DOTALL)
    if not match:
        raise ValueError("Invalid WKT format")

    content = match.group(1)
    segment_strs = re.split(r'\)\s*,\s*\(', content)

    segments = []
    for segment_str in segment_strs:
        coords = []
        points = segment_str.strip().split(',')
        for point in points:
            parts = point.strip().split()
            if len(parts) >= 2:
                lon = float(parts[0])
                lat = float(parts[1])
                coords.append([lon, lat])
        if coords:
            segments.append(coords)

    return segments


def connect_segments_manually(segments: List[List[List[float]]]) -> List[List[float]]:
    """
    手動指定分段連接順序

    基於對 TDX 資料的分析，正確的連接順序是：
    1. 分段 8 反轉（K01 附近的軌道起點）
    2. 分段 9 反轉
    3. 分段 10 反轉
    4. 分段 11 反轉
    5. 分段 1 反轉（經過 K02, K03, K04）
    6. 分段 7 反轉（K05 附近）
    7. 分段 6 反轉
    8. 分段 5 反轉
    9. 分段 4 反轉
    10. 分段 0（到達 K06 附近的高點）
    11. 分段 2 反轉（K06 到 K09）

    注意：跳過分段 3（回頭路）
    """
    # 定義連接順序：(分段索引, 是否反轉)
    connection_order = [
        (8, True),   # K01 附近 - 這段往東南，需反轉成往東北
        (9, True),
        (10, True),
        (11, True),
        (1, True),   # K02-K05 區段 - 原本是往西南，需反轉
        (7, True),   # K05 附近往 K06 - 原本往西南，需反轉
        (6, True),
        (5, True),
        (4, True),
        (0, False),  # 到達 K06 附近高點 - 原本就是往東北
        (2, True),   # K06 到 K09 - 原本是往西南(從K09往K06)，需反轉
    ]

    result = []
    prev_end = None

    for seg_idx, should_reverse in connection_order:
        if seg_idx >= len(segments):
            print(f"  警告: 分段 {seg_idx} 不存在")
            continue

        seg = segments[seg_idx][:]
        if should_reverse:
            seg = list(reversed(seg))

        # 檢查連接點距離
        if prev_end:
            dist = euclidean_distance(prev_end, seg[0])
            if dist > 0.005:
                print(f"  警告: 分段 {seg_idx} 連接距離較大: {dist:.6f}")

        # 避免重複點
        if result and euclidean_distance(result[-1], seg[0]) < 0.0001:
            result.extend(seg[1:])
        else:
            result.extend(seg)

        prev_end = result[-1]
        print(f"  添加分段 {seg_idx} ({'反轉' if should_reverse else '正向'}), 累計 {len(result)} 點")

    return result


def truncate_track(track_coords: List[List[float]], start_coord: List[float], end_coord: List[float]) -> List[List[float]]:
    """截斷軌道至指定的起終點範圍"""
    start_idx = min(range(len(track_coords)), key=lambda i: euclidean_distance(track_coords[i], start_coord))
    end_idx = min(range(len(track_coords)), key=lambda i: euclidean_distance(track_coords[i], end_coord))

    if start_idx > end_idx:
        track_coords = list(reversed(track_coords))
        start_idx = len(track_coords) - 1 - start_idx
        end_idx = len(track_coords) - 1 - end_idx

    truncated = track_coords[start_idx:end_idx + 1]
    if truncated:
        truncated[0] = start_coord[:]
        truncated[-1] = end_coord[:]

    return truncated


def remove_duplicate_points(coords: List[List[float]], threshold: float = 0.00001) -> List[List[float]]:
    """移除重複或非常接近的點"""
    if not coords:
        return []

    result = [coords[0]]
    for i in range(1, len(coords)):
        if euclidean_distance(coords[i], result[-1]) > threshold:
            result.append(coords[i])

    return result


def calibrate_track(track_coords: List[List[float]], stations: List[Dict], station_order: List[str]) -> List[List[float]]:
    """校準軌道座標，確保軌道通過所有車站"""
    station_coords = {s['station_id']: s['coordinates'] for s in stations}
    calibrated = [coord[:] for coord in track_coords]

    for station_id in station_order:
        if station_id not in station_coords:
            continue

        coord = station_coords[station_id]

        # 檢查是否已經存在
        found = False
        for tc in calibrated:
            if abs(tc[0] - coord[0]) < 0.00001 and abs(tc[1] - coord[1]) < 0.00001:
                found = True
                break

        if not found:
            # 找到最佳插入位置
            best_idx = 0
            min_dist = float('inf')

            for i in range(len(calibrated) - 1):
                x1, y1 = calibrated[i]
                x2, y2 = calibrated[i+1]
                px, py = coord

                dx = x2 - x1
                dy = y2 - y1

                if dx == 0 and dy == 0:
                    dist = euclidean_distance([px, py], [x1, y1])
                else:
                    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
                    proj_x = x1 + t * dx
                    proj_y = y1 + t * dy
                    dist = euclidean_distance([px, py], [proj_x, proj_y])

                if dist < min_dist:
                    min_dist = dist
                    best_idx = i

            calibrated.insert(best_idx + 1, [coord[0], coord[1]])
            print(f"  插入 {station_id} 在索引 {best_idx + 1}, 距離: {min_dist:.6f}")

    return calibrated


def calculate_progress(track_coords: List[List[float]], stations: List[Tuple[str, List[float]]]) -> Dict[str, float]:
    """計算車站在軌道上的進度值 (0-1)"""
    total_length = 0
    for i in range(len(track_coords) - 1):
        total_length += euclidean_distance(track_coords[i], track_coords[i+1])

    progress = {}

    for station_id, coord in stations:
        best_idx = 0
        min_dist = float('inf')
        for i, tc in enumerate(track_coords):
            dist = euclidean_distance(tc, coord)
            if dist < min_dist:
                min_dist = dist
                best_idx = i

        dist_to_station = 0
        for i in range(best_idx):
            dist_to_station += euclidean_distance(track_coords[i], track_coords[i+1])

        progress[station_id] = dist_to_station / total_length if total_length > 0 else 0

    return progress


def main():
    print("=" * 60)
    print("修復安坑輕軌軌道 v3 (手動指定分段順序)")
    print("=" * 60)

    # 載入車站資料
    print("\n📥 載入車站資料...")
    with open(STATION_FILE, 'r', encoding='utf-8') as f:
        stations_geojson = json.load(f)

    stations = []
    for feat in stations_geojson['features']:
        stations.append({
            'station_id': feat['properties']['station_id'],
            'name': feat['properties']['name_zh'],
            'coordinates': feat['geometry']['coordinates']
        })

    stations.sort(key=lambda s: s['station_id'])
    station_order = [s['station_id'] for s in stations]

    print(f"  車站數量: {len(stations)}")
    for s in stations:
        print(f"    {s['station_id']}: {s['name']} {s['coordinates']}")

    start_coord = stations[0]['coordinates']
    end_coord = stations[-1]['coordinates']

    # 載入 TDX Shape 資料
    print("\n📥 載入 TDX Shape 資料...")
    shape_files = [f for f in os.listdir(TDX_DATA_DIR) if f.startswith('shape_')]
    shape_file = os.path.join(TDX_DATA_DIR, shape_files[0])
    with open(shape_file, 'r', encoding='utf-8') as f:
        shape_data = json.load(f)

    wkt = shape_data[0].get('Geometry', '')
    segments = parse_wkt_multilinestring(wkt)

    print(f"  分段數量: {len(segments)}")
    for i, seg in enumerate(segments):
        print(f"    分段 {i}: {len(seg)} 點, 起點 {seg[0][:2]}, 終點 {seg[-1][:2]}")

    # 手動連接分段
    print("\n🔧 手動連接分段...")
    track_coords = connect_segments_manually(segments)
    print(f"  連接後點數: {len(track_coords)}")

    # 移除重複點
    print("\n🔧 移除重複點...")
    track_coords = remove_duplicate_points(track_coords)
    print(f"  清理後點數: {len(track_coords)}")

    # 截斷到起終點範圍
    print("\n🔧 截斷軌道...")
    track_coords = truncate_track(track_coords, start_coord, end_coord)
    print(f"  截斷後點數: {len(track_coords)}")

    # 校準軌道
    print("\n🔧 校準軌道...")
    track_coords = calibrate_track(track_coords, stations, station_order)
    print(f"  校準後點數: {len(track_coords)}")

    # 儲存軌道
    print("\n📝 儲存軌道檔案...")

    track_0 = track_coords[:]
    track_1 = list(reversed(track_coords))

    for track_id, coords, direction, name, start, end in [
        ('K-1-0', track_0, 0, '雙城 → 十四張', 'K01', 'K09'),
        ('K-1-1', track_1, 1, '十四張 → 雙城', 'K09', 'K01'),
    ]:
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "track_id": track_id,
                    "color": "#8cc540",
                    "route_id": "K-1",
                    "direction": direction,
                    "name": name,
                    "start_station": start,
                    "end_station": end,
                    "travel_time": 22,
                    "line_id": "K"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                }
            }]
        }

        filepath = os.path.join(TRACK_DIR, f"{track_id}.geojson")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        print(f"  ✅ {filepath} ({len(coords)} 點)")

    # 更新 station_progress.json
    print("\n📝 更新 station_progress.json...")

    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        progress_data = json.load(f)

    progress_0 = calculate_progress(track_0, [(s['station_id'], s['coordinates']) for s in stations])
    progress_data['K-1-0'] = progress_0

    reversed_stations = list(reversed(stations))
    progress_1 = calculate_progress(track_1, [(s['station_id'], s['coordinates']) for s in reversed_stations])
    progress_data['K-1-1'] = progress_1

    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)

    print(f"  K-1-0 進度: {list(progress_0.items())}")
    print(f"  K-1-1 進度: {list(progress_1.items())}")

    print("\n" + "=" * 60)
    print("✅ 安坑輕軌軌道修復完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
