#!/usr/bin/env python3
"""
修復安坑輕軌軌道 v2 - 精確移除有問題的分段

問題分析：
TDX Shape 的分段 3 是回頭路段：
  起點 [121.51754760873519, 24.96595090970675]
  終點 [121.51704053589208, 24.964490609454117]
這個分段會造成列車先往北走再往南回頭

解決方案：
1. 重新執行原始建置腳本的邏輯
2. 但排除分段 3（回頭路）
3. 保留其他細節
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


def is_backtracking_segment(seg: List[List[float]], overall_direction: Tuple[float, float]) -> bool:
    """
    檢查分段是否是回頭路

    安坑輕軌整體方向是從西南 (K01 雙城) 到東北 (K09 十四張)
    如果一個分段的整體方向與此相反，且長度短，則可能是回頭路
    """
    if len(seg) < 2:
        return False

    dx = seg[-1][0] - seg[0][0]
    dy = seg[-1][1] - seg[0][1]

    # 計算與整體方向的點積
    dot = dx * overall_direction[0] + dy * overall_direction[1]

    # 如果點積為負，方向相反
    if dot < 0:
        seg_length = sum(euclidean_distance(seg[i], seg[i+1]) for i in range(len(seg)-1))
        if seg_length < 0.01:  # 短分段
            return True

    return False


def connect_segments_ordered(segments: List[List[List[float]]],
                             start_coord: List[float],
                             end_coord: List[float],
                             exclude_backtracking: bool = True) -> List[List[float]]:
    """
    按照正確順序連接分段

    策略：
    1. 從起點開始，找到最近的分段
    2. 沿著分段走到終點方向
    3. 跳過回頭路分段
    """
    if not segments:
        return []

    # 計算整體方向
    overall_dx = end_coord[0] - start_coord[0]
    overall_dy = end_coord[1] - start_coord[1]
    mag = math.sqrt(overall_dx**2 + overall_dy**2)
    if mag > 0:
        overall_direction = (overall_dx / mag, overall_dy / mag)
    else:
        overall_direction = (1, 0)

    # 篩選分段：排除回頭路
    filtered_segments = []
    for i, seg in enumerate(segments):
        if exclude_backtracking and is_backtracking_segment(seg, overall_direction):
            print(f"  排除回頭路分段 {i}: {seg[0]} → {seg[-1]}")
            continue
        filtered_segments.append(seg[:])

    print(f"  篩選後分段數量: {len(filtered_segments)}/{len(segments)}")

    # 貪婪連接
    remaining = [seg[:] for seg in filtered_segments]

    # 找到最接近起點的分段作為開始
    best_idx = 0
    best_dist = float('inf')
    should_reverse = False

    for i, seg in enumerate(remaining):
        d_start = euclidean_distance(start_coord, seg[0])
        d_end = euclidean_distance(start_coord, seg[-1])

        if d_start < best_dist:
            best_dist = d_start
            best_idx = i
            should_reverse = False
        if d_end < best_dist:
            best_dist = d_end
            best_idx = i
            should_reverse = True

    first_seg = remaining.pop(best_idx)
    if should_reverse:
        first_seg = list(reversed(first_seg))

    result = first_seg[:]

    # 繼續連接剩餘分段
    while remaining:
        best_idx = -1
        best_dist = float('inf')
        should_reverse = False
        connect_to_end = True

        current_start = result[0]
        current_end = result[-1]

        for i, seg in enumerate(remaining):
            seg_start = seg[0]
            seg_end = seg[-1]

            d1 = euclidean_distance(current_end, seg_start)
            d2 = euclidean_distance(current_end, seg_end)
            d3 = euclidean_distance(current_start, seg_end)
            d4 = euclidean_distance(current_start, seg_start)

            min_d = min(d1, d2, d3, d4)

            if min_d < best_dist:
                best_dist = min_d
                best_idx = i
                if min_d == d1:
                    should_reverse = False
                    connect_to_end = True
                elif min_d == d2:
                    should_reverse = True
                    connect_to_end = True
                elif min_d == d3:
                    should_reverse = False
                    connect_to_end = False
                else:
                    should_reverse = True
                    connect_to_end = False

        if best_idx == -1 or best_dist > 0.01:
            # 沒有更多可連接的分段，或距離太遠
            break

        seg = remaining.pop(best_idx)
        if should_reverse:
            seg = list(reversed(seg))

        if connect_to_end:
            if euclidean_distance(result[-1], seg[0]) < 0.0001:
                result.extend(seg[1:])
            else:
                result.extend(seg)
        else:
            if euclidean_distance(result[0], seg[-1]) < 0.0001:
                result = seg[:-1] + result
            else:
                result = seg + result

    return result


def truncate_track(track_coords: List[List[float]], start_coord: List[float], end_coord: List[float]) -> List[List[float]]:
    """截斷軌道至指定的起終點範圍"""
    # 找到最接近起終點的索引
    start_idx = min(range(len(track_coords)), key=lambda i: euclidean_distance(track_coords[i], start_coord))
    end_idx = min(range(len(track_coords)), key=lambda i: euclidean_distance(track_coords[i], end_coord))

    if start_idx > end_idx:
        # 需要反轉
        track_coords = list(reversed(track_coords))
        start_idx = len(track_coords) - 1 - start_idx
        end_idx = len(track_coords) - 1 - end_idx

    truncated = track_coords[start_idx:end_idx + 1]
    if truncated:
        truncated[0] = start_coord[:]
        truncated[-1] = end_coord[:]

    return truncated


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
        # 找到最近的軌道點
        best_idx = 0
        min_dist = float('inf')
        for i, tc in enumerate(track_coords):
            dist = euclidean_distance(tc, coord)
            if dist < min_dist:
                min_dist = dist
                best_idx = i

        # 計算到該點的累積距離
        dist_to_station = 0
        for i in range(best_idx):
            dist_to_station += euclidean_distance(track_coords[i], track_coords[i+1])

        progress[station_id] = dist_to_station / total_length if total_length > 0 else 0

    return progress


def main():
    print("=" * 60)
    print("修復安坑輕軌軌道 v2")
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

    # 按車站 ID 排序
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
    if not shape_files:
        print("❌ 找不到 Shape 資料")
        return

    shape_file = os.path.join(TDX_DATA_DIR, shape_files[0])
    with open(shape_file, 'r', encoding='utf-8') as f:
        shape_data = json.load(f)

    # 解析 WKT
    wkt = shape_data[0].get('Geometry', '')
    segments = parse_wkt_multilinestring(wkt)
    print(f"  原始分段數量: {len(segments)}")
    for i, seg in enumerate(segments):
        seg_length = sum(euclidean_distance(seg[j], seg[j+1]) for j in range(len(seg)-1))
        print(f"    分段 {i}: {len(seg)} 點, 長度 {seg_length:.6f}, {seg[0]} → {seg[-1]}")

    # 連接分段（排除回頭路）
    print("\n🔧 連接分段...")
    track_coords = connect_segments_ordered(segments, start_coord, end_coord, exclude_backtracking=True)
    print(f"  連接後點數: {len(track_coords)}")

    # 截斷到起終點範圍
    print("\n🔧 截斷軌道...")
    track_coords = truncate_track(track_coords, start_coord, end_coord)
    print(f"  截斷後點數: {len(track_coords)}")

    # 校準軌道，確保通過所有車站
    print("\n🔧 校準軌道...")
    track_coords = calibrate_track(track_coords, stations, station_order)
    print(f"  校準後點數: {len(track_coords)}")

    # 建立 K-1-0 和 K-1-1 軌道
    print("\n📝 儲存軌道檔案...")

    # K-1-0: 雙城 → 十四張 (正向)
    track_0 = track_coords[:]

    # K-1-1: 十四張 → 雙城 (反向)
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

    # K-1-0 進度
    progress_0 = calculate_progress(track_0, [(s['station_id'], s['coordinates']) for s in stations])
    progress_data['K-1-0'] = progress_0

    # K-1-1 進度 (反向)
    reversed_stations = list(reversed(stations))
    progress_1 = calculate_progress(track_1, [(s['station_id'], s['coordinates']) for s in reversed_stations])
    progress_data['K-1-1'] = progress_1

    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)

    print(f"  K-1-0 進度: {progress_0}")
    print(f"  K-1-1 進度: {progress_1}")

    print("\n" + "=" * 60)
    print("✅ 安坑輕軌軌道修復完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
