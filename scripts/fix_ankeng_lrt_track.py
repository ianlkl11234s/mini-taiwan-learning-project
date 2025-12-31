#!/usr/bin/env python3
"""
修復安坑輕軌軌道 - 使用車站座標為引導，過濾異常分段

問題: TDX MULTILINESTRING 包含多個分段，其中有些是側線或回頭路
解法: 以車站順序為引導，只保留沿著車站順序的分段
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


def find_segment_containing_station(segments: List[List[List[float]]], station_coord: List[float], threshold: float = 0.001) -> Tuple[int, int, float]:
    """找到包含某車站的分段及其在分段中的位置"""
    best_seg_idx = -1
    best_point_idx = -1
    min_dist = float('inf')

    for seg_idx, seg in enumerate(segments):
        for pt_idx, pt in enumerate(seg):
            dist = euclidean_distance(pt, station_coord)
            if dist < min_dist:
                min_dist = dist
                best_seg_idx = seg_idx
                best_point_idx = pt_idx

    return best_seg_idx, best_point_idx, min_dist


def order_segments_by_stations(segments: List[List[List[float]]], station_coords: List[List[float]]) -> List[List[float]]:
    """
    根據車站順序來排序和連接分段

    策略：
    1. 找到每個車站最近的分段
    2. 按車站順序連接這些分段
    3. 過濾掉不在主線上的分段（如回頭路）
    """
    if not segments or not station_coords:
        return []

    # 找到每個車站所在的分段
    station_segments = []
    for i, sc in enumerate(station_coords):
        seg_idx, pt_idx, dist = find_segment_containing_station(segments, sc)
        station_segments.append({
            'station_idx': i,
            'seg_idx': seg_idx,
            'pt_idx': pt_idx,
            'dist': dist
        })
        print(f"  車站 {i}: 分段 {seg_idx}, 點 {pt_idx}, 距離 {dist:.6f}")

    # 收集需要使用的分段（按車站順序）
    used_segments = set()
    for ss in station_segments:
        used_segments.add(ss['seg_idx'])

    print(f"\n  使用的分段索引: {sorted(used_segments)}")

    # 按車站順序連接分段
    result = []
    prev_seg_idx = -1

    for i, ss in enumerate(station_segments):
        seg_idx = ss['seg_idx']
        seg = segments[seg_idx]

        if seg_idx != prev_seg_idx:
            # 新的分段
            if not result:
                # 第一個分段，確定方向
                next_station_in_seg = None
                for j in range(i + 1, len(station_segments)):
                    if station_segments[j]['seg_idx'] == seg_idx:
                        next_station_in_seg = station_segments[j]
                        break

                if next_station_in_seg and next_station_in_seg['pt_idx'] < ss['pt_idx']:
                    # 需要反轉
                    seg = list(reversed(seg))
                    print(f"  反轉分段 {seg_idx}")

                result.extend(seg)
            else:
                # 後續分段，連接到現有結果
                # 檢查連接方向
                end_pt = result[-1]
                start_dist = euclidean_distance(end_pt, seg[0])
                end_dist = euclidean_distance(end_pt, seg[-1])

                if end_dist < start_dist:
                    seg = list(reversed(seg))
                    print(f"  反轉分段 {seg_idx} (連接)")

                # 避免重複點
                if euclidean_distance(result[-1], seg[0]) < 0.0001:
                    result.extend(seg[1:])
                else:
                    result.extend(seg)

            prev_seg_idx = seg_idx

    return result


def build_track_from_stations(station_coords: List[List[float]], segments: List[List[List[float]]]) -> List[List[float]]:
    """
    更簡單的方法：直接用車站座標連接，並從分段中補充細節

    這種方法確保軌道一定通過所有車站，且方向正確
    """
    result = []

    for i, start_coord in enumerate(station_coords[:-1]):
        end_coord = station_coords[i + 1]

        # 找到包含這兩個車站的分段
        start_seg_idx, start_pt_idx, _ = find_segment_containing_station(segments, start_coord)
        end_seg_idx, end_pt_idx, _ = find_segment_containing_station(segments, end_coord)

        print(f"  站 {i}→{i+1}: 分段 {start_seg_idx}[{start_pt_idx}] → 分段 {end_seg_idx}[{end_pt_idx}]")

        if start_seg_idx == end_seg_idx:
            # 同一分段
            seg = segments[start_seg_idx]
            if start_pt_idx <= end_pt_idx:
                section = seg[start_pt_idx:end_pt_idx + 1]
            else:
                section = list(reversed(seg[end_pt_idx:start_pt_idx + 1]))

            # 替換端點為精確車站座標
            if section:
                section[0] = start_coord[:]
                section[-1] = end_coord[:]

                if result:
                    if euclidean_distance(result[-1], section[0]) < 0.0001:
                        result.extend(section[1:])
                    else:
                        result.extend(section)
                else:
                    result.extend(section)
        else:
            # 跨分段 - 簡單地直接連接車站
            if not result:
                result.append(start_coord[:])
            elif euclidean_distance(result[-1], start_coord) > 0.0001:
                result.append(start_coord[:])
            result.append(end_coord[:])

    return result


def smooth_track_with_segments(track: List[List[float]], segments: List[List[List[float]]], threshold: float = 0.0005) -> List[List[float]]:
    """
    使用分段資料來平滑軌道

    對於軌道中每段車站之間的直線，嘗試從分段中補充中間點
    """
    result = [track[0][:]]

    for i in range(len(track) - 1):
        start = track[i]
        end = track[i + 1]

        # 找到最近的分段
        best_seg = None
        best_score = float('inf')

        for seg in segments:
            # 檢查這個分段是否在 start 和 end 之間
            start_dist = min(euclidean_distance(start, pt) for pt in seg)
            end_dist = min(euclidean_distance(end, pt) for pt in seg)

            if start_dist < threshold and end_dist < threshold:
                score = start_dist + end_dist
                if score < best_score:
                    best_score = score
                    best_seg = seg

        if best_seg:
            # 從這個分段中取得 start 到 end 的路徑
            start_idx = min(range(len(best_seg)), key=lambda j: euclidean_distance(best_seg[j], start))
            end_idx = min(range(len(best_seg)), key=lambda j: euclidean_distance(best_seg[j], end))

            if start_idx < end_idx:
                middle_pts = best_seg[start_idx + 1:end_idx]
            elif start_idx > end_idx:
                middle_pts = list(reversed(best_seg[end_idx + 1:start_idx]))
            else:
                middle_pts = []

            result.extend(middle_pts)

        result.append(end[:])

    return result


def remove_backtracking(track: List[List[float]], station_coords: List[List[float]]) -> List[List[float]]:
    """
    移除軌道中的回頭路段

    檢測方式：如果某段路的方向與整體趨勢相反，則移除
    """
    if len(track) < 3:
        return track

    # 計算整體方向（從第一站到最後一站）
    overall_dx = station_coords[-1][0] - station_coords[0][0]
    overall_dy = station_coords[-1][1] - station_coords[0][1]

    result = [track[0][:]]

    for i in range(1, len(track) - 1):
        prev = track[i - 1]
        curr = track[i]
        next_pt = track[i + 1]

        # 檢查 prev → curr → next 是否形成回頭路
        dx1 = curr[0] - prev[0]
        dy1 = curr[1] - prev[1]
        dx2 = next_pt[0] - curr[0]
        dy2 = next_pt[1] - curr[1]

        # 如果方向突然反轉超過 90 度，可能是回頭路
        dot = dx1 * dx2 + dy1 * dy2
        mag1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
        mag2 = math.sqrt(dx2 * dx2 + dy2 * dy2)

        if mag1 > 0.0001 and mag2 > 0.0001:
            cos_angle = dot / (mag1 * mag2)
            if cos_angle < -0.5:  # 超過 120 度的反轉
                # 檢查是否靠近車站（車站附近的轉彎是正常的）
                near_station = False
                for sc in station_coords:
                    if euclidean_distance(curr, sc) < 0.001:
                        near_station = True
                        break

                if not near_station:
                    print(f"  跳過回頭點: {curr} (角度 cos={cos_angle:.2f})")
                    continue

        result.append(curr[:])

    result.append(track[-1][:])
    return result


def calculate_progress(track_coords: List[List[float]], station_coords: List[Tuple[str, List[float]]]) -> Dict[str, float]:
    """計算車站在軌道上的進度值 (0-1)"""
    total_length = 0
    for i in range(len(track_coords) - 1):
        total_length += euclidean_distance(track_coords[i], track_coords[i+1])

    progress = {}

    for station_id, coord in station_coords:
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
    print("修復安坑輕軌軌道")
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
    station_coords = [s['coordinates'] for s in stations]
    station_ids = [s['station_id'] for s in stations]

    print(f"  車站數量: {len(stations)}")
    for s in stations:
        print(f"    {s['station_id']}: {s['name']} {s['coordinates']}")

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
    print(f"  分段數量: {len(segments)}")
    for i, seg in enumerate(segments):
        print(f"    分段 {i}: {len(seg)} 點, 起點 {seg[0]}, 終點 {seg[-1]}")

    # 方法 1：直接用車站座標建立軌道框架
    print("\n🔧 建立軌道框架...")
    track_coords = build_track_from_stations(station_coords, segments)
    print(f"  框架點數: {len(track_coords)}")

    # 方法 2：使用分段資料平滑軌道
    print("\n🔧 平滑軌道...")
    track_coords = smooth_track_with_segments(track_coords, segments, threshold=0.002)
    print(f"  平滑後點數: {len(track_coords)}")

    # 移除回頭路
    print("\n🔧 移除回頭路...")
    track_coords = remove_backtracking(track_coords, station_coords)
    print(f"  清理後點數: {len(track_coords)}")

    # 確保軌道通過所有車站
    print("\n🔧 確保軌道通過所有車站...")
    for i, s in enumerate(stations):
        coord = s['coordinates']
        found = False
        for tc in track_coords:
            if abs(tc[0] - coord[0]) < 0.00001 and abs(tc[1] - coord[1]) < 0.00001:
                found = True
                break

        if not found:
            # 找到最佳插入位置
            best_idx = 0
            min_dist = float('inf')
            for j in range(len(track_coords) - 1):
                x1, y1 = track_coords[j]
                x2, y2 = track_coords[j+1]
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
                    best_idx = j

            track_coords.insert(best_idx + 1, coord[:])
            print(f"  插入 {s['station_id']} 在索引 {best_idx + 1}")

    print(f"\n  最終軌道點數: {len(track_coords)}")

    # 建立 K-1-0 (往十四張) 和 K-1-1 (往雙城) 軌道
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
        print(f"  ✅ {filepath}")

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

    print(f"  ✅ K-1-0 進度: {progress_0}")
    print(f"  ✅ K-1-1 進度: {progress_1}")

    print("\n" + "=" * 60)
    print("✅ 安坑輕軌軌道修復完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
