#!/usr/bin/env python3
"""
桃園機場捷運 (Taoyuan Airport MRT) 完整建置腳本

路線結構：
- 普通車 (A-1): A1-A22 全線 22 站
- 直達車 (A-2): A1-A3-A8-A12-A13-A18-A21 跳站 7 站
- 區間車 (A-3): A13-A22 深夜區間 10 站

TDX 系統代碼: TYMC (Taoyuan Metro Corporation)

輸出：
- tymc_stations.geojson
- tracks/A-1-0.geojson, A-1-1.geojson (普通車)
- tracks/A-2-0.geojson, A-2-1.geojson (直達車)
- tracks/A-3-0.geojson, A-3-1.geojson (區間車)
- schedules/A-1-0.json, A-1-1.json, A-2-0.json, A-2-1.json, A-3-1.json
- station_progress.json (更新)
"""

import json
import re
import math
import os
import sys
from collections import deque
from typing import List, Dict, Tuple, Any, Optional, Set

# 專案根目錄
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# TDX 資料目錄
TDX_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "tdx_tymc")

# 輸出檔案
STATION_FILE = os.path.join(PROJECT_ROOT, "public/data/tymc_stations.geojson")
TRACK_DIR = os.path.join(PROJECT_ROOT, "public/data/tracks")
SCHEDULE_DIR = os.path.join(PROJECT_ROOT, "public/data/schedules")
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "public/data/station_progress.json")

# 線路設定
LINE_ID = "A"
RAIL_SYSTEM = "TYMC"

# 顏色設定
# 軌道統一使用官方紫色
TRACK_COLOR = "#8246af"

# 列車顏色 (依車種與方向)
TRAIN_COLORS = {
    "A-1-0": "#9b66c2",  # 普通車去程
    "A-1-1": "#a778c9",  # 普通車回程
    "A-2-0": "#67378b",  # 直達車去程
    "A-2-1": "#8246af",  # 直達車回程
    "A-3-0": "#9b66c2",  # 區間車去程 (同普通車)
    "A-3-1": "#a778c9",  # 區間車回程 (同普通車)
}

# 車站順序 (A14 不存在，使用 A14a)
ALL_STATIONS = [
    "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9",
    "A10", "A11", "A12", "A13", "A14a", "A15", "A16", "A17",
    "A18", "A19", "A20", "A21", "A22"
]

# 直達車停靠站 (7 站)
EXPRESS_STATIONS = ["A1", "A3", "A8", "A12", "A13", "A18", "A21"]

# 區間車停靠站 (10 站: A13-A22)
LIMITED_STATIONS = ["A13", "A14a", "A15", "A16", "A17", "A18", "A19", "A20", "A21", "A22"]

# 預設站間行駛時間（秒）- 根據總行駛時間 84 分鐘分配
# 普通車全線 21 段，平均每段 4 分鐘
DEFAULT_TRAVEL_TIMES = {
    "A1-A2": 210,    # 3.5 分鐘
    "A2-A3": 210,    # 3.5 分鐘
    "A3-A4": 180,    # 3 分鐘
    "A4-A5": 150,    # 2.5 分鐘
    "A5-A6": 210,    # 3.5 分鐘
    "A6-A7": 300,    # 5 分鐘 (長距離)
    "A7-A8": 240,    # 4 分鐘
    "A8-A9": 180,    # 3 分鐘
    "A9-A10": 480,   # 8 分鐘 (最長距離)
    "A10-A11": 180,  # 3 分鐘
    "A11-A12": 210,  # 3.5 分鐘
    "A12-A13": 150,  # 2.5 分鐘
    "A13-A14a": 180, # 3 分鐘
    "A14a-A15": 180, # 3 分鐘
    "A15-A16": 180,  # 3 分鐘
    "A16-A17": 150,  # 2.5 分鐘
    "A17-A18": 150,  # 2.5 分鐘
    "A18-A19": 150,  # 2.5 分鐘
    "A19-A20": 210,  # 3.5 分鐘
    "A20-A21": 180,  # 3 分鐘
    "A21-A22": 150,  # 2.5 分鐘
}


def load_tdx_data() -> Dict[str, Any]:
    """載入 TDX 資料"""
    data = {}

    files = {
        "Station": "station.json",
        "Shape": "shape.json",
        "StationTimeTable": "stationtimetable.json",
    }

    for key, filename in files.items():
        filepath = os.path.join(TDX_DATA_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data[key] = json.load(f)
            print(f"  ✅ 載入 {filename}: {len(data[key])} 筆")
        else:
            print(f"  ❌ 找不到 {filepath}")
            data[key] = []

    return data


def parse_stations(station_data: List[Dict]) -> List[Dict]:
    """解析車站資料"""
    stations = []

    for s in station_data:
        station_id = s.get('StationID', '')
        name_zh = s.get('StationName', {}).get('Zh_tw', '')
        name_en = s.get('StationName', {}).get('En', '')
        lat = s.get('StationPosition', {}).get('PositionLat', 0)
        lon = s.get('StationPosition', {}).get('PositionLon', 0)

        if station_id and lat and lon:
            stations.append({
                'station_id': station_id,
                'name_zh': name_zh,
                'name_en': name_en,
                'coordinates': [lon, lat],
                'line_id': LINE_ID
            })

    return stations


def create_stations_geojson(stations: List[Dict]) -> Dict:
    """建立車站 GeoJSON"""
    features = []
    for s in stations:
        features.append({
            "type": "Feature",
            "properties": {
                "station_id": s['station_id'],
                "name_zh": s['name_zh'],
                "name_en": s['name_en'],
                "line_id": s['line_id']
            },
            "geometry": {
                "type": "Point",
                "coordinates": s['coordinates']
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


def euclidean_distance(p1: List[float], p2: List[float]) -> float:
    """計算 Euclidean 距離"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def parse_wkt_multilinestring(wkt: str) -> List[List[List[float]]]:
    """解析 WKT MULTILINESTRING 為分段座標陣列"""
    match = re.search(r'MULTILINESTRING\s*\(\s*\((.*)\)\s*\)', wkt, re.DOTALL)
    if not match:
        match = re.search(r'LINESTRING\s*\(\s*(.*)\s*\)', wkt, re.DOTALL)
        if match:
            coords = []
            points = match.group(1).strip().split(',')
            for point in points:
                parts = point.strip().split()
                if len(parts) >= 2:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    coords.append([lon, lat])
            return [coords] if coords else []
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


def find_closest_point_on_segments(point: List[float], segments: List[List[List[float]]]) -> Tuple[int, int, float]:
    """找到離指定點最近的分段和點索引"""
    best_seg_idx = -1
    best_pt_idx = -1
    min_dist = float('inf')

    for seg_idx, seg in enumerate(segments):
        for pt_idx, pt in enumerate(seg):
            d = euclidean_distance(pt, point)
            if d < min_dist:
                min_dist = d
                best_seg_idx = seg_idx
                best_pt_idx = pt_idx

    return best_seg_idx, best_pt_idx, min_dist


def build_segment_graph(segments: List[List[List[float]]], connection_threshold: float = 0.001) -> Dict[int, List[Tuple[int, str]]]:
    """建立分段之間的連接圖"""
    graph = {i: [] for i in range(len(segments))}

    for i, seg_i in enumerate(segments):
        for j, seg_j in enumerate(segments):
            if i >= j:
                continue

            connections = [
                (seg_i[0], seg_j[0], 'start-start'),
                (seg_i[0], seg_j[-1], 'start-end'),
                (seg_i[-1], seg_j[0], 'end-start'),
                (seg_i[-1], seg_j[-1], 'end-end'),
            ]

            for pt_i, pt_j, conn_type in connections:
                if euclidean_distance(pt_i, pt_j) < connection_threshold:
                    graph[i].append((j, conn_type))
                    reverse_type = conn_type.split('-')
                    reverse_conn = f"{reverse_type[1]}-{reverse_type[0]}"
                    graph[j].append((i, reverse_conn))

    return graph


def find_path_between_stations(start: List[float], end: List[float],
                                segments: List[List[List[float]]]) -> List[List[float]]:
    """找到兩個車站之間的路徑，使用 BFS"""
    start_seg_idx, start_pt_idx, _ = find_closest_point_on_segments(start, segments)
    end_seg_idx, end_pt_idx, _ = find_closest_point_on_segments(end, segments)

    if start_seg_idx == -1 or end_seg_idx == -1:
        return [start[:], end[:]]

    if start_seg_idx == end_seg_idx:
        seg = segments[start_seg_idx]
        if start_pt_idx <= end_pt_idx:
            path = seg[start_pt_idx:end_pt_idx + 1]
        else:
            path = list(reversed(seg[end_pt_idx:start_pt_idx + 1]))

        if path:
            path = [coord[:] for coord in path]
            path[0] = start[:]
            path[-1] = end[:]
        return path

    graph = build_segment_graph(segments)

    queue = deque([(start_seg_idx, [start_seg_idx], None)])
    visited = {start_seg_idx}

    found_path = None
    while queue:
        current_seg, seg_path, _ = queue.popleft()

        if current_seg == end_seg_idx:
            found_path = seg_path
            break

        for next_seg, conn_type in graph.get(current_seg, []):
            if next_seg not in visited:
                visited.add(next_seg)
                queue.append((next_seg, seg_path + [next_seg], conn_type))

    if not found_path:
        return [start[:], end[:]]

    result = []

    for i, seg_idx in enumerate(found_path):
        seg = segments[seg_idx]

        if i == 0:
            if len(found_path) == 1:
                if start_pt_idx <= end_pt_idx:
                    result.extend(seg[start_pt_idx:end_pt_idx + 1])
                else:
                    result.extend(list(reversed(seg[end_pt_idx:start_pt_idx + 1])))
            else:
                next_seg = segments[found_path[1]]
                seg_end_to_next = min(euclidean_distance(seg[-1], next_seg[0]),
                                      euclidean_distance(seg[-1], next_seg[-1]))
                seg_start_to_next = min(euclidean_distance(seg[0], next_seg[0]),
                                        euclidean_distance(seg[0], next_seg[-1]))

                if seg_end_to_next < seg_start_to_next:
                    result.extend(seg[start_pt_idx:])
                else:
                    result.extend(list(reversed(seg[:start_pt_idx + 1])))

        elif i == len(found_path) - 1:
            prev_seg = segments[found_path[i - 1]]
            seg_start_from_prev = min(euclidean_distance(seg[0], prev_seg[0]),
                                      euclidean_distance(seg[0], prev_seg[-1]))
            seg_end_from_prev = min(euclidean_distance(seg[-1], prev_seg[0]),
                                    euclidean_distance(seg[-1], prev_seg[-1]))

            if seg_start_from_prev < seg_end_from_prev:
                result.extend(seg[1:end_pt_idx + 1])
            else:
                result.extend(list(reversed(seg[end_pt_idx:]))[1:])

        else:
            prev_seg = segments[found_path[i - 1]]
            seg_start_from_prev = min(euclidean_distance(seg[0], prev_seg[0]),
                                      euclidean_distance(seg[0], prev_seg[-1]))
            seg_end_from_prev = min(euclidean_distance(seg[-1], prev_seg[0]),
                                    euclidean_distance(seg[-1], prev_seg[-1]))

            if seg_start_from_prev < seg_end_from_prev:
                result.extend(seg[1:])
            else:
                result.extend(list(reversed(seg))[1:])

    if result:
        result = [coord[:] for coord in result]
        result[0] = start[:]
        result[-1] = end[:]

    return result


def build_track_from_stations(station_coords: List[List[float]],
                               all_segments: List[List[List[float]]]) -> List[List[float]]:
    """根據車站座標順序建立軌道"""
    if len(station_coords) < 2:
        return station_coords

    result = [station_coords[0][:]]

    for i in range(len(station_coords) - 1):
        start = station_coords[i]
        end = station_coords[i + 1]

        best_path = find_path_between_stations(start, end, all_segments)

        if best_path and len(best_path) > 1:
            result.extend(best_path[1:])
        else:
            result.append(end[:])

    return result


def create_track_geojson(track_id: str, coords: List[List[float]], direction: int,
                         name: str, start_station: str, end_station: str,
                         travel_time: int) -> Dict:
    """建立軌道 GeoJSON"""
    # 軌道統一使用官方紫色，列車顏色在 schedule 中另存
    color = TRACK_COLOR

    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "color": color,
                "route_id": track_id.rsplit('-', 1)[0],
                "direction": direction,
                "name": name,
                "start_station": start_station,
                "end_station": end_station,
                "travel_time": travel_time,
                "line_id": LINE_ID
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }


def get_travel_time(from_station: str, to_station: str, is_express: bool = False) -> int:
    """取得站間行駛時間（秒）

    Args:
        from_station: 起站
        to_station: 迄站
        is_express: 是否為直達車（直達車速度較快）

    若為非連續站（跳站），會累加中間站的行駛時間。
    直達車速度約為普通車的 1.9 倍 (官方: 普通車 73min vs 直達車 36min)
    """
    # 直達車速度係數 (33min / 62.5min ≈ 0.53)
    EXPRESS_SPEED_FACTOR = 0.53

    key = f"{from_station}-{to_station}"
    if key in DEFAULT_TRAVEL_TIMES:
        base_time = DEFAULT_TRAVEL_TIMES[key]
        return int(base_time * EXPRESS_SPEED_FACTOR) if is_express else base_time

    reverse_key = f"{to_station}-{from_station}"
    if reverse_key in DEFAULT_TRAVEL_TIMES:
        base_time = DEFAULT_TRAVEL_TIMES[reverse_key]
        return int(base_time * EXPRESS_SPEED_FACTOR) if is_express else base_time

    # 處理跳站：累加中間站時間
    try:
        from_idx = ALL_STATIONS.index(from_station)
        to_idx = ALL_STATIONS.index(to_station)

        if from_idx > to_idx:
            from_idx, to_idx = to_idx, from_idx

        total_time = 0
        for i in range(from_idx, to_idx):
            seg_key = f"{ALL_STATIONS[i]}-{ALL_STATIONS[i+1]}"
            if seg_key in DEFAULT_TRAVEL_TIMES:
                total_time += DEFAULT_TRAVEL_TIMES[seg_key]
            else:
                total_time += 180  # 預設 3 分鐘

        # 直達車速度較快
        if is_express:
            return int(total_time * EXPRESS_SPEED_FACTOR)
        return total_time
    except ValueError:
        return 180  # 預設 3 分鐘


def get_travel_times_for_route(station_order: List[str], is_express: bool = False) -> List[int]:
    """取得路線的站間行駛時間列表"""
    times = []
    for i in range(len(station_order) - 1):
        times.append(get_travel_time(station_order[i], station_order[i + 1], is_express))
    return times


def parse_timetable_by_traintype(timetable_data: List[Dict],
                                  station_order: List[str],
                                  train_type: int,
                                  stopping_patterns: List[str],
                                  direction: int,
                                  dwell_time: int = 30,
                                  is_express: bool = False) -> Tuple[List[Dict], int]:
    """
    根據 TrainType 和 StoppingPattern 解析時刻表

    回傳: (departures, total_travel_time_seconds)
    """
    start_station = station_order[0]
    travel_times = get_travel_times_for_route(station_order, is_express)
    total_travel_time = sum(travel_times) + dwell_time * (len(station_order) - 1)

    # 收集起始站的發車時間
    departures_raw = set()

    for entry in timetable_data:
        if entry.get('StationID') != start_station:
            continue
        if entry.get('Direction') != direction:
            continue

        for tt in entry.get('Timetables', []):
            if tt.get('TrainType') != train_type:
                continue
            if tt.get('StoppingPatternID') not in stopping_patterns:
                continue

            dep_time = tt.get('DepartureTime', '')
            if dep_time:
                departures_raw.add(dep_time)

    departures_raw = sorted(departures_raw)

    # 建立發車資料
    departures = []
    route_id = f"A-{train_type}" if train_type <= 2 else "A-3"

    for idx, dep_time in enumerate(departures_raw):
        train_id = f"{LINE_ID}-{route_id.split('-')[1]}-{direction}-{idx+1:03d}"

        # 計算每站的到達/離站時間
        stations_info = []
        cumulative_time = 0

        for i, station_id in enumerate(station_order):
            arrival = cumulative_time
            departure = cumulative_time + dwell_time

            stations_info.append({
                "station_id": station_id,
                "arrival": arrival,
                "departure": departure
            })

            if i < len(travel_times):
                cumulative_time = departure + travel_times[i]

        formatted_dep_time = dep_time if len(dep_time) > 5 else f"{dep_time}:00"

        departures.append({
            "departure_time": formatted_dep_time,
            "train_id": train_id,
            "origin_station": station_order[0],
            "destination_station": station_order[-1],
            "total_travel_time": total_travel_time,
            "stations": stations_info
        })

    return departures, total_travel_time


def calculate_progress(track_coords: List[List[float]], stations: List[Dict],
                       station_order: List[str]) -> Dict[str, float]:
    """計算車站在軌道上的進度值 (0-1)"""
    station_coords = {s['station_id']: s['coordinates'] for s in stations}

    total_length = 0
    for i in range(len(track_coords) - 1):
        total_length += euclidean_distance(track_coords[i], track_coords[i+1])

    progress = {}

    for station_id in station_order:
        if station_id not in station_coords:
            continue

        coord = station_coords[station_id]

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
    print("桃園機場捷運建置腳本")
    print("=" * 60)

    # 載入資料
    print("\n📥 載入 TDX 資料...")
    data = load_tdx_data()

    if not data.get('Station'):
        print("❌ 無法取得車站資料")
        return

    # 解析車站資料
    print("\n🔧 解析車站資料...")
    stations = parse_stations(data['Station'])
    print(f"  車站數量: {len(stations)}")

    # 建立車站座標映射
    station_coords_map = {s['station_id']: s['coordinates'] for s in stations}
    station_names_map = {s['station_id']: s['name_zh'] for s in stations}

    # 驗證車站順序
    print("\n📋 車站順序:")
    for sid in ALL_STATIONS:
        name = station_names_map.get(sid, "???")
        coord = station_coords_map.get(sid, [0, 0])
        print(f"  {sid}: {name} [{coord[0]:.4f}, {coord[1]:.4f}]")

    # 建立車站 GeoJSON
    print("\n📝 建立車站 GeoJSON...")
    stations_geojson = create_stations_geojson(stations)
    with open(STATION_FILE, 'w', encoding='utf-8') as f:
        json.dump(stations_geojson, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {STATION_FILE}")

    # 解析軌道資料
    print("\n🔧 解析軌道資料...")
    all_segments = []
    for shape in data.get('Shape', []):
        wkt = shape.get('Geometry', '')
        if wkt:
            try:
                segments = parse_wkt_multilinestring(wkt)
                all_segments.extend(segments)
            except Exception as e:
                print(f"  解析失敗: {e}")

    print(f"  總分段數: {len(all_segments)}")
    total_points = sum(len(seg) for seg in all_segments)
    print(f"  總點數: {total_points}")

    # 確保輸出目錄存在
    os.makedirs(TRACK_DIR, exist_ok=True)
    os.makedirs(SCHEDULE_DIR, exist_ok=True)

    # ===== 建立普通車軌道 (A-1) =====
    print("\n🚃 建立普通車軌道 (A-1)...")

    commuter_coords = [station_coords_map.get(sid) for sid in ALL_STATIONS if sid in station_coords_map]
    commuter_ids = [sid for sid in ALL_STATIONS if sid in station_coords_map]

    commuter_track = build_track_from_stations(commuter_coords, all_segments)
    print(f"  軌道點數: {len(commuter_track)}")

    # A-1-0: 台北 → 老街溪
    geojson_0 = create_track_geojson(
        'A-1-0', commuter_track[:], 0,
        '台北車站 → 老街溪站', commuter_ids[0], commuter_ids[-1],
        84
    )
    with open(os.path.join(TRACK_DIR, 'A-1-0.geojson'), 'w', encoding='utf-8') as f:
        json.dump(geojson_0, f, ensure_ascii=False, indent=2)
    print(f"  ✅ A-1-0.geojson")

    # A-1-1: 老街溪 → 台北
    geojson_1 = create_track_geojson(
        'A-1-1', list(reversed(commuter_track)), 1,
        '老街溪站 → 台北車站', commuter_ids[-1], commuter_ids[0],
        84
    )
    with open(os.path.join(TRACK_DIR, 'A-1-1.geojson'), 'w', encoding='utf-8') as f:
        json.dump(geojson_1, f, ensure_ascii=False, indent=2)
    print(f"  ✅ A-1-1.geojson")

    # ===== 建立直達車軌道 (A-2) =====
    print("\n🚄 建立直達車軌道 (A-2)...")

    # 直達車使用普通車軌道，但只到 A21
    # 找到 A21 在軌道上的位置
    a21_coord = station_coords_map.get("A21")
    a21_idx = 0
    min_dist = float('inf')
    for i, pt in enumerate(commuter_track):
        d = euclidean_distance(pt, a21_coord)
        if d < min_dist:
            min_dist = d
            a21_idx = i

    # A-2 軌道：A1 到 A21
    express_track = commuter_track[:a21_idx + 1]
    print(f"  軌道點數: {len(express_track)}")

    # A-2-0: 台北 → 環北 (直達車)
    geojson_0 = create_track_geojson(
        'A-2-0', express_track[:], 0,
        '台北車站 → 環北站 (直達車)', "A1", "A21",
        36
    )
    with open(os.path.join(TRACK_DIR, 'A-2-0.geojson'), 'w', encoding='utf-8') as f:
        json.dump(geojson_0, f, ensure_ascii=False, indent=2)
    print(f"  ✅ A-2-0.geojson")

    # A-2-1: 環北 → 台北 (直達車)
    geojson_1 = create_track_geojson(
        'A-2-1', list(reversed(express_track)), 1,
        '環北站 → 台北車站 (直達車)', "A21", "A1",
        36
    )
    with open(os.path.join(TRACK_DIR, 'A-2-1.geojson'), 'w', encoding='utf-8') as f:
        json.dump(geojson_1, f, ensure_ascii=False, indent=2)
    print(f"  ✅ A-2-1.geojson")

    # ===== 建立區間車軌道 (A-3) =====
    print("\n🚃 建立區間車軌道 (A-3)...")

    # 找到 A13 在軌道上的位置
    a13_coord = station_coords_map.get("A13")
    a13_idx = 0
    min_dist = float('inf')
    for i, pt in enumerate(commuter_track):
        d = euclidean_distance(pt, a13_coord)
        if d < min_dist:
            min_dist = d
            a13_idx = i

    # A-3 軌道：A13 到 A22
    limited_track = commuter_track[a13_idx:]
    print(f"  軌道點數: {len(limited_track)}")

    # A-3-0: 機場T2 → 老街溪
    geojson_0 = create_track_geojson(
        'A-3-0', limited_track[:], 0,
        '機場第二航廈站 → 老街溪站', "A13", "A22",
        33
    )
    with open(os.path.join(TRACK_DIR, 'A-3-0.geojson'), 'w', encoding='utf-8') as f:
        json.dump(geojson_0, f, ensure_ascii=False, indent=2)
    print(f"  ✅ A-3-0.geojson")

    # A-3-1: 老街溪 → 機場T2
    geojson_1 = create_track_geojson(
        'A-3-1', list(reversed(limited_track)), 1,
        '老街溪站 → 機場第二航廈站', "A22", "A13",
        33
    )
    with open(os.path.join(TRACK_DIR, 'A-3-1.geojson'), 'w', encoding='utf-8') as f:
        json.dump(geojson_1, f, ensure_ascii=False, indent=2)
    print(f"  ✅ A-3-1.geojson")

    # ===== 建立時刻表 =====
    print("\n📅 建立時刻表...")
    timetable_data = data.get('StationTimeTable', [])

    # 普通車時刻表 (A-1)
    # A-1-0: 台北 → 老街溪 (TrainType=1, SP1, Direction=0)
    departures_0, travel_time_0 = parse_timetable_by_traintype(
        timetable_data, ALL_STATIONS, 1, ['SP1'], 0
    )
    schedule_0 = {
        "track_id": "A-1-0",
        "route_id": "A-1",
        "name": "台北車站 → 老街溪站",
        "train_type": "commuter",
        "train_color": TRAIN_COLORS["A-1-0"],
        "origin": ALL_STATIONS[0],
        "destination": ALL_STATIONS[-1],
        "stations": ALL_STATIONS,
        "travel_time_minutes": travel_time_0 // 60,
        "dwell_time_seconds": 30,
        "is_weekday": True,
        "departure_count": len(departures_0),
        "departures": departures_0
    }
    with open(os.path.join(SCHEDULE_DIR, 'A-1-0.json'), 'w', encoding='utf-8') as f:
        json.dump(schedule_0, f, ensure_ascii=False, indent=2)
    print(f"  ✅ A-1-0.json ({len(departures_0)} 班次)")

    # A-1-1: 老街溪 → 台北 (TrainType=1, SP1, Direction=1)
    reversed_stations = list(reversed(ALL_STATIONS))
    departures_1, travel_time_1 = parse_timetable_by_traintype(
        timetable_data, reversed_stations, 1, ['SP1'], 1
    )
    schedule_1 = {
        "track_id": "A-1-1",
        "route_id": "A-1",
        "name": "老街溪站 → 台北車站",
        "train_type": "commuter",
        "train_color": TRAIN_COLORS["A-1-1"],
        "origin": reversed_stations[0],
        "destination": reversed_stations[-1],
        "stations": reversed_stations,
        "travel_time_minutes": travel_time_1 // 60,
        "dwell_time_seconds": 30,
        "is_weekday": True,
        "departure_count": len(departures_1),
        "departures": departures_1
    }
    with open(os.path.join(SCHEDULE_DIR, 'A-1-1.json'), 'w', encoding='utf-8') as f:
        json.dump(schedule_1, f, ensure_ascii=False, indent=2)
    print(f"  ✅ A-1-1.json ({len(departures_1)} 班次)")

    # 直達車時刻表 (A-2)
    # A-2-0: 台北 → 機場 (TrainType=2, SP2/SP5, Direction=0)
    # 注意：直達車時刻表從 A1 出發，停靠 EXPRESS_STATIONS
    departures_0, travel_time_0 = parse_timetable_by_traintype(
        timetable_data, EXPRESS_STATIONS, 2, ['SP2', 'SP5'], 0, is_express=True
    )
    schedule_0 = {
        "track_id": "A-2-0",
        "route_id": "A-2",
        "name": "台北車站 → 環北站 (直達車)",
        "train_type": "express",
        "train_color": TRAIN_COLORS["A-2-0"],
        "origin": EXPRESS_STATIONS[0],
        "destination": EXPRESS_STATIONS[-1],
        "stations": EXPRESS_STATIONS,
        "travel_time_minutes": 36,
        "dwell_time_seconds": 30,
        "is_weekday": True,
        "departure_count": len(departures_0),
        "departures": departures_0
    }
    with open(os.path.join(SCHEDULE_DIR, 'A-2-0.json'), 'w', encoding='utf-8') as f:
        json.dump(schedule_0, f, ensure_ascii=False, indent=2)
    print(f"  ✅ A-2-0.json ({len(departures_0)} 班次)")

    # A-2-1: 機場 → 台北 (TrainType=2, SP2, Direction=1, 從 A13 出發)
    # 直達車回程從 A13 出發
    reversed_express = list(reversed(EXPRESS_STATIONS))

    # 特殊處理：回程從 A13 開始統計
    express_return_departures = set()
    for entry in timetable_data:
        if entry.get('StationID') != 'A13':
            continue
        if entry.get('Direction') != 1:
            continue

        for tt in entry.get('Timetables', []):
            if tt.get('TrainType') != 2:
                continue
            if tt.get('StoppingPatternID') not in ['SP2', 'SP5']:
                continue

            dep_time = tt.get('DepartureTime', '')
            if dep_time:
                express_return_departures.add(dep_time)

    express_return_departures = sorted(express_return_departures)
    travel_times = get_travel_times_for_route(reversed_express, is_express=True)
    total_travel = sum(travel_times) + 30 * (len(reversed_express) - 1)

    departures_1 = []
    for idx, dep_time in enumerate(express_return_departures):
        train_id = f"{LINE_ID}-2-1-{idx+1:03d}"

        stations_info = []
        cumulative_time = 0

        for i, station_id in enumerate(reversed_express):
            arrival = cumulative_time
            departure = cumulative_time + 30

            stations_info.append({
                "station_id": station_id,
                "arrival": arrival,
                "departure": departure
            })

            if i < len(travel_times):
                cumulative_time = departure + travel_times[i]

        formatted_dep_time = dep_time if len(dep_time) > 5 else f"{dep_time}:00"

        departures_1.append({
            "departure_time": formatted_dep_time,
            "train_id": train_id,
            "origin_station": reversed_express[0],
            "destination_station": reversed_express[-1],
            "total_travel_time": total_travel,
            "stations": stations_info
        })

    schedule_1 = {
        "track_id": "A-2-1",
        "route_id": "A-2",
        "name": "環北站 → 台北車站 (直達車)",
        "train_type": "express",
        "train_color": TRAIN_COLORS["A-2-1"],
        "origin": reversed_express[0],
        "destination": reversed_express[-1],
        "stations": reversed_express,
        "travel_time_minutes": 36,
        "dwell_time_seconds": 30,
        "is_weekday": True,
        "departure_count": len(departures_1),
        "departures": departures_1
    }
    with open(os.path.join(SCHEDULE_DIR, 'A-2-1.json'), 'w', encoding='utf-8') as f:
        json.dump(schedule_1, f, ensure_ascii=False, indent=2)
    print(f"  ✅ A-2-1.json ({len(departures_1)} 班次)")

    # 區間車時刻表 (A-3)
    # A-3-1: 老街溪 → 機場T2 (TrainType=1, SP4, Direction=1)
    reversed_limited = list(reversed(LIMITED_STATIONS))
    departures_1, travel_time_1 = parse_timetable_by_traintype(
        timetable_data, reversed_limited, 1, ['SP4'], 1
    )
    schedule_1 = {
        "track_id": "A-3-1",
        "route_id": "A-3",
        "name": "老街溪站 → 機場第二航廈站 (區間車)",
        "train_type": "limited",
        "train_color": TRAIN_COLORS["A-3-1"],
        "origin": reversed_limited[0],
        "destination": reversed_limited[-1],
        "stations": reversed_limited,
        "travel_time_minutes": travel_time_1 // 60,
        "dwell_time_seconds": 30,
        "is_weekday": True,
        "departure_count": len(departures_1),
        "departures": departures_1
    }
    with open(os.path.join(SCHEDULE_DIR, 'A-3-1.json'), 'w', encoding='utf-8') as f:
        json.dump(schedule_1, f, ensure_ascii=False, indent=2)
    print(f"  ✅ A-3-1.json ({len(departures_1)} 班次)")

    # ===== 更新 station_progress.json =====
    print("\n📝 更新 station_progress.json...")

    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        progress_data = json.load(f)

    # 普通車進度
    progress_data['A-1-0'] = calculate_progress(commuter_track, stations, ALL_STATIONS)
    progress_data['A-1-1'] = calculate_progress(list(reversed(commuter_track)), stations, list(reversed(ALL_STATIONS)))
    print(f"  ✅ A-1-0, A-1-1 (22 站)")

    # 直達車進度
    progress_data['A-2-0'] = calculate_progress(express_track, stations, EXPRESS_STATIONS)
    progress_data['A-2-1'] = calculate_progress(list(reversed(express_track)), stations, list(reversed(EXPRESS_STATIONS)))
    print(f"  ✅ A-2-0, A-2-1 (7 站)")

    # 區間車進度
    progress_data['A-3-0'] = calculate_progress(limited_track, stations, LIMITED_STATIONS)
    progress_data['A-3-1'] = calculate_progress(list(reversed(limited_track)), stations, list(reversed(LIMITED_STATIONS)))
    print(f"  ✅ A-3-0, A-3-1 (10 站)")

    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("✅ 桃園機場捷運建置完成")
    print("=" * 60)
    print("\n📊 統計:")
    print(f"  車站: 22 站")
    print(f"  軌道: 6 條 (A-1-0/1, A-2-0/1, A-3-0/1)")
    print(f"  時刻表: 5 個檔案")
    print("\n下一步：更新前端程式碼 (useData.ts, App.tsx, LineFilter.tsx)")


if __name__ == '__main__':
    main()
