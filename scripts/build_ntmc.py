#!/usr/bin/env python3
"""
新北環狀線 (Circular Line) 完整建置腳本

路線結構：
- Y-1: 大坪林 ↔ 新北產業園區 (14 站)

TDX 系統代碼: NTMC (New Taipei Metro Corporation)

輸出：
- ntmc_stations.geojson
- tracks/Y-1-0.geojson, Y-1-1.geojson
- schedules/Y-1-0.json, Y-1-1.json
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
TDX_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "tdx_ntmc")

# 輸出檔案
STATION_FILE = os.path.join(PROJECT_ROOT, "public/data/ntmc_stations.geojson")
TRACK_DIR = os.path.join(PROJECT_ROOT, "public/data/tracks")
SCHEDULE_DIR = os.path.join(PROJECT_ROOT, "public/data/schedules")
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "public/data/station_progress.json")

# 線路設定
LINE_ID = "Y"
RAIL_SYSTEM = "NTMC"

# 顏色設定
# 軌道使用官方黃色
TRACK_COLOR = "#fedb00"

# 列車顏色 (依方向)
TRAIN_COLORS = {
    "Y-1-0": "#fedb00",  # 去程（往新北產業園區）- 黃色
    "Y-1-1": "#ffe566",  # 回程（往大坪林）- 淡黃色
}

# 車站順序 (Y07 到 Y20)
ALL_STATIONS = [
    "Y07", "Y08", "Y09", "Y10", "Y11", "Y12", "Y13",
    "Y14", "Y15", "Y16", "Y17", "Y18", "Y19", "Y20"
]

# 站間行駛時間（秒）- 來自 TDX s2straveltime.json (Y20→Y07 方向)
# 這裡用 Y07→Y20 方向排列
TRAVEL_TIMES = {
    "Y07-Y08": 145,  # 2:25
    "Y08-Y09": 111,  # 1:51
    "Y09-Y10": 79,   # 1:19
    "Y10-Y11": 84,   # 1:24
    "Y11-Y12": 194,  # 3:14
    "Y12-Y13": 104,  # 1:44
    "Y13-Y14": 72,   # 1:12
    "Y14-Y15": 111,  # 1:51
    "Y15-Y16": 153,  # 2:33
    "Y16-Y17": 191,  # 3:11
    "Y17-Y18": 143,  # 2:23
    "Y18-Y19": 95,   # 1:35
    "Y19-Y20": 135,  # 2:15
}

# 停站時間（秒）- 來自 TDX s2straveltime.json
DWELL_TIMES = {
    "Y07": 0,   # 起站
    "Y08": 23,
    "Y09": 23,
    "Y10": 25,
    "Y11": 35,
    "Y12": 25,
    "Y13": 25,
    "Y14": 25,
    "Y15": 25,
    "Y16": 40,
    "Y17": 25,
    "Y18": 35,
    "Y19": 23,
    "Y20": 0,   # 終站
}

# 班距設定（分鐘）
HEADWAYS = {
    "peak": 5,      # 尖峰時段平均班距
    "off_peak": 7,  # 離峰時段平均班距
    "night": 13,    # 深夜時段平均班距
}

# 營運時段
OPERATION_HOURS = {
    "first_train": "06:00",
    "last_train": "00:00",
    "peak_morning_start": "07:00",
    "peak_morning_end": "09:00",
    "peak_evening_start": "17:00",
    "peak_evening_end": "19:30",
    "night_start": "23:00",
}


def load_tdx_data() -> Dict[str, Any]:
    """載入 TDX 資料"""
    data = {}

    files = {
        "Station": "station.json",
        "Shape": "shape.json",
        "S2STravelTime": "s2straveltime.json",
        "Frequency": "frequency.json",
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
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "color": TRACK_COLOR,
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


def get_travel_time(from_station: str, to_station: str) -> int:
    """取得站間行駛時間（秒）"""
    key = f"{from_station}-{to_station}"
    if key in TRAVEL_TIMES:
        return TRAVEL_TIMES[key]

    reverse_key = f"{to_station}-{from_station}"
    if reverse_key in TRAVEL_TIMES:
        return TRAVEL_TIMES[reverse_key]

    return 120  # 預設 2 分鐘


def get_dwell_time(station_id: str) -> int:
    """取得停站時間（秒）"""
    return DWELL_TIMES.get(station_id, 25)


def time_to_minutes(time_str: str) -> int:
    """將時間字串轉換為分鐘數（從 00:00 起算）"""
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    return hours * 60 + minutes


def minutes_to_time(minutes: int) -> str:
    """將分鐘數轉換為時間字串"""
    # 處理跨日
    if minutes >= 24 * 60:
        minutes -= 24 * 60
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}:00"


def get_headway_for_time(time_minutes: int) -> int:
    """根據時間取得班距（分鐘）"""
    # 轉換為 24 小時內
    if time_minutes >= 24 * 60:
        time_minutes -= 24 * 60

    hour = time_minutes // 60

    # 深夜 (23:00-00:00)
    if hour >= 23:
        return HEADWAYS["night"]

    # 早尖峰 (07:00-09:00)
    if 7 <= hour < 9:
        return HEADWAYS["peak"]

    # 晚尖峰 (17:00-19:30)
    if 17 <= hour < 20:
        if hour == 19 and (time_minutes % 60) >= 30:
            return HEADWAYS["off_peak"]
        return HEADWAYS["peak"]

    # 離峰
    return HEADWAYS["off_peak"]


def generate_schedule(station_order: List[str], direction: int,
                      track_id: str) -> Tuple[List[Dict], int]:
    """
    基於班距產生時刻表

    回傳: (departures, total_travel_time_seconds)
    """
    # 計算站間行駛時間
    travel_times = []
    for i in range(len(station_order) - 1):
        travel_times.append(get_travel_time(station_order[i], station_order[i + 1]))

    # 計算總行駛時間
    total_travel_time = sum(travel_times)
    for station in station_order[1:-1]:  # 中間站的停站時間
        total_travel_time += get_dwell_time(station)

    # 產生發車時間
    first_train = time_to_minutes(OPERATION_HOURS["first_train"])
    last_train = time_to_minutes(OPERATION_HOURS["last_train"])
    if last_train == 0:
        last_train = 24 * 60  # 00:00 視為 24:00

    departures = []
    current_time = first_train
    train_idx = 1

    while current_time <= last_train:
        train_id = f"{LINE_ID}-1-{direction}-{train_idx:03d}"

        # 計算每站的到達/離站時間
        stations_info = []
        cumulative_time = 0

        for i, station_id in enumerate(station_order):
            arrival = cumulative_time
            dwell = get_dwell_time(station_id) if i > 0 and i < len(station_order) - 1 else 0
            departure = cumulative_time + dwell

            stations_info.append({
                "station_id": station_id,
                "arrival": arrival,
                "departure": departure
            })

            if i < len(travel_times):
                cumulative_time = departure + travel_times[i]

        dep_time_str = minutes_to_time(current_time)

        departures.append({
            "departure_time": dep_time_str,
            "train_id": train_id,
            "origin_station": station_order[0],
            "destination_station": station_order[-1],
            "total_travel_time": total_travel_time,
            "stations": stations_info
        })

        # 下一班次
        headway = get_headway_for_time(current_time)
        current_time += headway
        train_idx += 1

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
    print("新北環狀線建置腳本")
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

    # ===== 建立軌道 (Y-1) =====
    print("\n🚃 建立環狀線軌道 (Y-1)...")

    # Y07 到 Y20 的座標
    station_coords = [station_coords_map.get(sid) for sid in ALL_STATIONS if sid in station_coords_map]
    station_ids = [sid for sid in ALL_STATIONS if sid in station_coords_map]

    track = build_track_from_stations(station_coords, all_segments)
    print(f"  軌道點數: {len(track)}")

    # 計算總行駛時間
    total_time_seconds = sum(TRAVEL_TIMES.values())
    total_time_minutes = total_time_seconds // 60

    # Y-1-0: 大坪林 → 新北產業園區
    geojson_0 = create_track_geojson(
        'Y-1-0', track[:], 0,
        '大坪林站 → 新北產業園區站', station_ids[0], station_ids[-1],
        total_time_minutes
    )
    with open(os.path.join(TRACK_DIR, 'Y-1-0.geojson'), 'w', encoding='utf-8') as f:
        json.dump(geojson_0, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Y-1-0.geojson")

    # Y-1-1: 新北產業園區 → 大坪林
    geojson_1 = create_track_geojson(
        'Y-1-1', list(reversed(track)), 1,
        '新北產業園區站 → 大坪林站', station_ids[-1], station_ids[0],
        total_time_minutes
    )
    with open(os.path.join(TRACK_DIR, 'Y-1-1.geojson'), 'w', encoding='utf-8') as f:
        json.dump(geojson_1, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Y-1-1.geojson")

    # ===== 建立時刻表 =====
    print("\n📅 建立時刻表...")

    # Y-1-0: 大坪林 → 新北產業園區
    departures_0, travel_time_0 = generate_schedule(ALL_STATIONS, 0, 'Y-1-0')
    schedule_0 = {
        "track_id": "Y-1-0",
        "route_id": "Y-1",
        "name": "大坪林站 → 新北產業園區站",
        "train_type": "local",
        "train_color": TRAIN_COLORS["Y-1-0"],
        "origin": ALL_STATIONS[0],
        "destination": ALL_STATIONS[-1],
        "stations": ALL_STATIONS,
        "travel_time_minutes": travel_time_0 // 60,
        "dwell_time_seconds": 25,
        "is_weekday": True,
        "departure_count": len(departures_0),
        "departures": departures_0
    }
    with open(os.path.join(SCHEDULE_DIR, 'Y-1-0.json'), 'w', encoding='utf-8') as f:
        json.dump(schedule_0, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Y-1-0.json ({len(departures_0)} 班次)")

    # Y-1-1: 新北產業園區 → 大坪林
    reversed_stations = list(reversed(ALL_STATIONS))
    departures_1, travel_time_1 = generate_schedule(reversed_stations, 1, 'Y-1-1')
    schedule_1 = {
        "track_id": "Y-1-1",
        "route_id": "Y-1",
        "name": "新北產業園區站 → 大坪林站",
        "train_type": "local",
        "train_color": TRAIN_COLORS["Y-1-1"],
        "origin": reversed_stations[0],
        "destination": reversed_stations[-1],
        "stations": reversed_stations,
        "travel_time_minutes": travel_time_1 // 60,
        "dwell_time_seconds": 25,
        "is_weekday": True,
        "departure_count": len(departures_1),
        "departures": departures_1
    }
    with open(os.path.join(SCHEDULE_DIR, 'Y-1-1.json'), 'w', encoding='utf-8') as f:
        json.dump(schedule_1, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Y-1-1.json ({len(departures_1)} 班次)")

    # ===== 更新 station_progress.json =====
    print("\n📝 更新 station_progress.json...")

    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        progress_data = json.load(f)

    # Y-1 進度
    progress_data['Y-1-0'] = calculate_progress(track, stations, ALL_STATIONS)
    progress_data['Y-1-1'] = calculate_progress(list(reversed(track)), stations, list(reversed(ALL_STATIONS)))
    print(f"  ✅ Y-1-0, Y-1-1 (14 站)")

    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("✅ 新北環狀線建置完成")
    print("=" * 60)
    print("\n📊 統計:")
    print(f"  車站: 14 站")
    print(f"  軌道: 2 條 (Y-1-0, Y-1-1)")
    print(f"  時刻表: 2 個檔案")
    print(f"  班次數: {len(departures_0) + len(departures_1)} 班/日")
    print(f"  全程時間: 約 {total_time_minutes} 分鐘")
    print("\n下一步：更新前端程式碼 (useData.ts, App.tsx, LineFilter.tsx)")


if __name__ == '__main__':
    main()
