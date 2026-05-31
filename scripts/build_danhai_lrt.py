#!/usr/bin/env python3
"""
淡海輕軌 (Danhai LRT) 完整建置腳本

路線結構：
- 綠山線 (V-1): V01-V11 紅樹林 ↔ 崁頂 (11站)
- 藍海線 (V-2): V01-V09-V28-V27-V26 紅樹林 ↔ 淡水漁人碼頭 (12站)
  * 兩線共用 V01-V09 段
  * 在 V09 濱海沙崙站分岔

TDX 系統代碼: NTDLRT (新北捷運淡海輕軌)

輸出：
- danhai_lrt_stations.geojson
- tracks/V-1-0.geojson, V-1-1.geojson (綠山線)
- tracks/V-2-0.geojson, V-2-1.geojson (藍海線)
- schedules/V-1-0.json, V-1-1.json, V-2-0.json, V-2-1.json
- station_progress.json (更新)
"""

import json
import re
import math
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional

# 專案根目錄
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# TDX 認證模組路徑
gis_analytics_path = os.path.join(PROJECT_ROOT, "..", "taipei-gis-analytics")
sys.path.insert(0, gis_analytics_path)

# TDX 資料目錄
TDX_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "tdx_danhai_lrt")

# 輸出檔案
STATION_FILE = os.path.join(PROJECT_ROOT, "public/data/danhai_lrt_stations.geojson")
TRACK_DIR = os.path.join(PROJECT_ROOT, "public/data/tracks")
SCHEDULE_DIR = os.path.join(PROJECT_ROOT, "public/data/schedules")
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "public/data/station_progress.json")

# 線路設定
LINE_ID = "V"
LINE_COLOR = "#a4ce4e"  # 淡海輕軌綠色
RAIL_SYSTEM = "NTDLRT"  # 淡海輕軌系統代碼

# 綠山線車站順序 (V01-V11): 11站
GREEN_LINE_STATIONS = [f"V{i:02d}" for i in range(1, 12)]  # V01-V11

# 藍海線車站順序 (V01-V09-V28-V27-V26): 12站
# 與綠山線共用 V01-V09，在 V09 分岔往 V28-V27-V26
BLUE_LINE_STATIONS = [
    "V01", "V02", "V03", "V04", "V05", "V06", "V07", "V08", "V09",  # 共用段
    "V28", "V27", "V26"  # 藍海線專用段
]

# 預設站間行駛時間（秒）- 後續會從 S2STravelTime API 更新
# 綠山線 (V01-V11: 10站間隔，共10段)
DEFAULT_TRAVEL_TIMES_GREEN = [
    150,  # V01 → V02: 2.5 分鐘
    150,  # V02 → V03: 2.5 分鐘
    150,  # V03 → V04: 2.5 分鐘
    120,  # V04 → V05: 2 分鐘
    120,  # V05 → V06: 2 分鐘
    150,  # V06 → V07: 2.5 分鐘
    120,  # V07 → V08: 2 分鐘
    120,  # V08 → V09: 2 分鐘
    120,  # V09 → V10: 2 分鐘
    120,  # V10 → V11: 2 分鐘
]

# 藍海線 (V01-V09-V28-V27-V26: 12站，11段)
DEFAULT_TRAVEL_TIMES_BLUE = [
    150,  # V01 → V02: 2.5 分鐘 (共用段)
    150,  # V02 → V03: 2.5 分鐘
    150,  # V03 → V04: 2.5 分鐘
    120,  # V04 → V05: 2 分鐘
    120,  # V05 → V06: 2 分鐘
    150,  # V06 → V07: 2.5 分鐘
    120,  # V07 → V08: 2 分鐘
    120,  # V08 → V09: 2 分鐘
    120,  # V09 → V28: 2 分鐘 (分岔後)
    180,  # V28 → V27: 3 分鐘
    180,  # V27 → V26: 3 分鐘
]


def get_tdx_client():
    """取得 TDX 客戶端"""
    try:
        from src.tdx_auth import TDXAuth
        from src.tdx_client import TDXClient

        auth = TDXAuth()
        client = TDXClient(auth)
        return client
    except Exception as e:
        print(f"❌ TDX 認證失敗: {e}")
        print("請確認 taipei-gis-analytics/.env 檔案中已設定 TDX_APP_ID 和 TDX_APP_KEY")
        sys.exit(1)


def download_tdx_data(client) -> Dict[str, Any]:
    """下載 TDX 資料"""
    os.makedirs(TDX_DATA_DIR, exist_ok=True)

    data = {}
    today = datetime.now().strftime("%Y%m%d")

    # API 端點清單
    apis = [
        ("Station", f"/v2/Rail/Metro/Station/{RAIL_SYSTEM}"),
        ("Shape", f"/v2/Rail/Metro/Shape/{RAIL_SYSTEM}"),
        ("StationTimeTable", f"/v2/Rail/Metro/StationTimeTable/{RAIL_SYSTEM}"),
        ("S2STravelTime", f"/v2/Rail/Metro/S2STravelTime/{RAIL_SYSTEM}"),
    ]

    for api_name, endpoint in apis:
        print(f"📥 下載 {api_name}...")
        try:
            result = client.get(endpoint)
            data[api_name] = result

            # 儲存原始資料
            filename = f"{api_name.lower()}_{RAIL_SYSTEM}_{today}.json"
            filepath = os.path.join(TDX_DATA_DIR, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  ✅ 已儲存: {filepath} ({len(result)} 筆)")

            time.sleep(2)
        except Exception as e:
            print(f"  ❌ 失敗: {e}")
            data[api_name] = []

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


def parse_s2s_travel_times(s2s_data: List[Dict]) -> Dict[str, int]:
    """
    解析站間行駛時間資料
    返回: {(from_station, to_station): travel_time_seconds}
    """
    travel_times = {}

    for entry in s2s_data:
        from_station = entry.get('FromStationID', '')
        to_station = entry.get('ToStationID', '')
        travel_time = entry.get('TravelTime', 0)  # 秒

        if from_station and to_station and travel_time:
            travel_times[f"{from_station}-{to_station}"] = travel_time
            # 反向也儲存（通常行駛時間相同）
            if f"{to_station}-{from_station}" not in travel_times:
                travel_times[f"{to_station}-{from_station}"] = travel_time

    return travel_times


def get_travel_times_for_route(station_order: List[str], s2s_times: Dict[str, int],
                                default_times: List[int]) -> List[int]:
    """
    根據車站順序取得站間行駛時間
    優先使用 S2S API 資料，不足時使用預設值
    """
    travel_times = []

    for i in range(len(station_order) - 1):
        from_station = station_order[i]
        to_station = station_order[i + 1]
        key = f"{from_station}-{to_station}"

        if key in s2s_times:
            travel_times.append(s2s_times[key])
        elif i < len(default_times):
            travel_times.append(default_times[i])
        else:
            travel_times.append(120)  # 預設 2 分鐘

    return travel_times


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
        # 嘗試 LINESTRING
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


def build_track_from_stations(station_coords: List[List[float]], all_segments: List[List[List[float]]]) -> List[List[float]]:
    """
    根據車站座標順序建立軌道

    策略：
    1. 對於每對相鄰車站，找到連接它們的分段
    2. 按正確順序連接這些分段
    """
    if len(station_coords) < 2:
        return station_coords

    result = [station_coords[0][:]]

    for i in range(len(station_coords) - 1):
        start = station_coords[i]
        end = station_coords[i + 1]

        # 找到最佳的連接路徑
        best_path = find_path_between_stations(start, end, all_segments)

        if best_path and len(best_path) > 1:
            # 跳過起點（已在 result 中）
            result.extend(best_path[1:])
        else:
            # 沒找到路徑，直接連接
            result.append(end[:])

    return result


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
    """
    建立分段之間的連接圖
    返回: {segment_idx: [(connected_segment_idx, connection_type), ...]}
    connection_type: 'start-start', 'start-end', 'end-start', 'end-end'
    """
    graph = {i: [] for i in range(len(segments))}

    for i, seg_i in enumerate(segments):
        for j, seg_j in enumerate(segments):
            if i >= j:
                continue

            # 檢查所有端點組合
            connections = [
                (seg_i[0], seg_j[0], 'start-start'),
                (seg_i[0], seg_j[-1], 'start-end'),
                (seg_i[-1], seg_j[0], 'end-start'),
                (seg_i[-1], seg_j[-1], 'end-end'),
            ]

            for pt_i, pt_j, conn_type in connections:
                if euclidean_distance(pt_i, pt_j) < connection_threshold:
                    graph[i].append((j, conn_type))
                    # 反向連接
                    reverse_type = conn_type.split('-')
                    reverse_conn = f"{reverse_type[1]}-{reverse_type[0]}"
                    graph[j].append((i, reverse_conn))

    return graph


def find_path_between_stations(start: List[float], end: List[float], segments: List[List[List[float]]]) -> List[List[float]]:
    """
    找到兩個車站之間的路徑，支援跨分段搜尋
    使用 BFS 尋找連接起點和終點的分段路徑
    """
    # 找到起點和終點所在的分段
    start_seg_idx, start_pt_idx, _ = find_closest_point_on_segments(start, segments)
    end_seg_idx, end_pt_idx, _ = find_closest_point_on_segments(end, segments)

    if start_seg_idx == -1 or end_seg_idx == -1:
        return [start[:], end[:]]

    if start_seg_idx == end_seg_idx:
        # 同一分段
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

    # 跨分段 - 使用 BFS 尋找路徑
    graph = build_segment_graph(segments)

    # BFS 搜尋
    from collections import deque
    queue = deque([(start_seg_idx, [start_seg_idx], None)])  # (current_seg, path, last_connection_end)
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
        # 沒找到連接路徑，直接連接
        return [start[:], end[:]]

    # 根據找到的分段路徑建立實際座標路徑
    result = []

    for i, seg_idx in enumerate(found_path):
        seg = segments[seg_idx]

        if i == 0:
            # 第一個分段：從起點開始
            # 決定方向：看起點離分段的哪端更近
            dist_to_start = euclidean_distance(start, seg[0])
            dist_to_end = euclidean_distance(start, seg[-1])

            if len(found_path) == 1:
                # 只有一個分段
                if start_pt_idx <= end_pt_idx:
                    result.extend(seg[start_pt_idx:end_pt_idx + 1])
                else:
                    result.extend(list(reversed(seg[end_pt_idx:start_pt_idx + 1])))
            else:
                # 多個分段，需要決定方向
                next_seg = segments[found_path[1]]
                # 看這個分段的哪端連接到下一個分段
                seg_start_to_next = min(euclidean_distance(seg[0], next_seg[0]),
                                        euclidean_distance(seg[0], next_seg[-1]))
                seg_end_to_next = min(euclidean_distance(seg[-1], next_seg[0]),
                                      euclidean_distance(seg[-1], next_seg[-1]))

                if seg_end_to_next < seg_start_to_next:
                    # 分段終點連接到下一分段，從 start_pt_idx 到終點
                    result.extend(seg[start_pt_idx:])
                else:
                    # 分段起點連接到下一分段，從 start_pt_idx 到起點（反向）
                    result.extend(list(reversed(seg[:start_pt_idx + 1])))

        elif i == len(found_path) - 1:
            # 最後一個分段：到終點
            prev_seg = segments[found_path[i - 1]]
            # 看這個分段的哪端連接到前一個分段
            seg_start_from_prev = min(euclidean_distance(seg[0], prev_seg[0]),
                                      euclidean_distance(seg[0], prev_seg[-1]))
            seg_end_from_prev = min(euclidean_distance(seg[-1], prev_seg[0]),
                                    euclidean_distance(seg[-1], prev_seg[-1]))

            if seg_start_from_prev < seg_end_from_prev:
                # 分段起點連接自前一分段，從起點到 end_pt_idx
                result.extend(seg[1:end_pt_idx + 1])  # 跳過第一點（避免重複）
            else:
                # 分段終點連接自前一分段，從終點到 end_pt_idx（反向）
                result.extend(list(reversed(seg[end_pt_idx:]))[1:])  # 跳過第一點

        else:
            # 中間分段
            prev_seg = segments[found_path[i - 1]]
            next_seg = segments[found_path[i + 1]]

            # 決定遍歷方向
            seg_start_from_prev = min(euclidean_distance(seg[0], prev_seg[0]),
                                      euclidean_distance(seg[0], prev_seg[-1]))
            seg_end_from_prev = min(euclidean_distance(seg[-1], prev_seg[0]),
                                    euclidean_distance(seg[-1], prev_seg[-1]))

            if seg_start_from_prev < seg_end_from_prev:
                # 從起點到終點
                result.extend(seg[1:])  # 跳過第一點
            else:
                # 從終點到起點
                result.extend(list(reversed(seg))[1:])  # 跳過第一點

    # 替換端點為精確的車站座標
    if result:
        result = [coord[:] for coord in result]
        result[0] = start[:]
        result[-1] = end[:]

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
                "color": LINE_COLOR,
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


def parse_station_timetable(timetable_data: List[Dict], station_order: List[str],
                            default_times: List[int], direction: int,
                            route_num: int, dwell_time: int = 25) -> Tuple[List[Dict], int]:
    """
    解析時刻表資料，使用預設行駛時間

    格式須與安坑輕軌一致:
    - stations[i].arrival: 從發車開始的累計秒數
    - stations[i].departure: arrival + dwell_time

    回傳: (departures, total_travel_time_seconds)
    """
    # 篩選指定方向和起始站的班次
    start_station = station_order[0]

    # 收集起始站的發車時間
    departures_raw = []
    for entry in timetable_data:
        if entry.get('StationID') != start_station:
            continue
        if entry.get('Direction') != direction:
            continue

        timetables = entry.get('Timetables', [])
        for tt in timetables:
            dep_time = tt.get('DepartureTime', '')
            if dep_time:
                departures_raw.append(dep_time)

    # 去重並排序
    departures_raw = sorted(set(departures_raw))

    # 計算總行駛時間（包含停站時間）
    total_travel_time = sum(default_times) + dwell_time * (len(station_order) - 1)

    # 建立發車資料
    departures = []
    for idx, dep_time in enumerate(departures_raw):
        # train_id 必須以實際路線編號為前綴（不可用 direction 推導，
        # 否則綠山線方向1與藍海線方向0的車號會與另一線衝突）
        train_id = f"{LINE_ID}-{route_num}-{direction}-{idx+1:03d}"

        # 計算每站的到達/離站時間（秒數，從發車開始計算）
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

            if i < len(default_times):
                cumulative_time = departure + default_times[i]

        # 格式化 departure_time 為 HH:MM:SS
        formatted_dep_time = dep_time if len(dep_time) > 5 else f"{dep_time}:00"

        departures.append({
            "departure_time": formatted_dep_time,
            "train_id": train_id,
            "origin_station": station_order[0],
            "total_travel_time": total_travel_time,
            "stations": stations_info
        })

    return departures, total_travel_time


def calculate_progress(track_coords: List[List[float]], stations: List[Dict], station_order: List[str]) -> Dict[str, float]:
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

        # 找到最近的軌道點
        best_idx = 0
        min_dist = float('inf')
        for i, tc in enumerate(track_coords):
            dist = euclidean_distance(tc, coord)
            if dist < min_dist:
                min_dist = dist
                best_idx = i

        # 計算累積距離
        dist_to_station = 0
        for i in range(best_idx):
            dist_to_station += euclidean_distance(track_coords[i], track_coords[i+1])

        progress[station_id] = dist_to_station / total_length if total_length > 0 else 0

    return progress


def main():
    print("=" * 60)
    print("淡海輕軌建置腳本")
    print("=" * 60)

    # 取得 TDX 客戶端
    print("\n📡 連接 TDX API...")
    client = get_tdx_client()

    # 下載資料
    print("\n📥 下載 TDX 資料...")
    data = download_tdx_data(client)

    if not data.get('Station'):
        print("❌ 無法取得車站資料")
        return

    # 解析車站資料
    print("\n🔧 解析車站資料...")
    stations = parse_stations(data['Station'])
    print(f"  車站數量: {len(stations)}")

    for s in sorted(stations, key=lambda x: x['station_id']):
        print(f"    {s['station_id']}: {s['name_zh']} {s['coordinates']}")

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
                print(f"  {shape.get('LineName', {}).get('Zh_tw', '')}: {len(segments)} 分段")
            except Exception as e:
                print(f"  解析失敗: {e}")

    print(f"  總分段數: {len(all_segments)}")

    # 解析站間行駛時間
    print("\n🔧 解析站間行駛時間...")
    s2s_times = {}
    if data.get('S2STravelTime'):
        s2s_times = parse_s2s_travel_times(data['S2STravelTime'])
        print(f"  取得 {len(s2s_times)} 筆站間行駛時間")
        # 顯示範例
        for key, val in list(s2s_times.items())[:5]:
            print(f"    {key}: {val} 秒")
    else:
        print("  ⚠️ 無 S2S 資料，使用預設行駛時間")

    # 建立車站座標映射
    station_coords_map = {s['station_id']: s['coordinates'] for s in stations}

    # 取得實際行駛時間（優先使用 API 資料）
    green_travel_times = get_travel_times_for_route(GREEN_LINE_STATIONS, s2s_times, DEFAULT_TRAVEL_TIMES_GREEN)
    blue_travel_times = get_travel_times_for_route(BLUE_LINE_STATIONS, s2s_times, DEFAULT_TRAVEL_TIMES_BLUE)

    print(f"  綠山線行駛時間: {green_travel_times}")
    print(f"  藍海線行駛時間: {blue_travel_times}")

    # ===== 建立綠山線軌道 =====
    print("\n🚃 建立綠山線軌道 (V-1)...")

    green_station_coords = [station_coords_map.get(sid) for sid in GREEN_LINE_STATIONS if sid in station_coords_map]
    green_station_ids = [sid for sid in GREEN_LINE_STATIONS if sid in station_coords_map]

    if green_station_coords:
        # 建立軌道
        green_track = build_track_from_stations(green_station_coords, all_segments)
        print(f"  軌道點數: {len(green_track)}")

        # V-1-0: 紅樹林 → 崁頂
        track_0 = green_track[:]
        geojson_0 = create_track_geojson(
            'V-1-0', track_0, 0,
            '紅樹林 → 崁頂', green_station_ids[0], green_station_ids[-1],
            sum(green_travel_times) // 60
        )
        with open(os.path.join(TRACK_DIR, 'V-1-0.geojson'), 'w', encoding='utf-8') as f:
            json.dump(geojson_0, f, ensure_ascii=False, indent=2)
        print(f"  ✅ V-1-0.geojson")

        # V-1-1: 崁頂 → 紅樹林
        track_1 = list(reversed(green_track))
        geojson_1 = create_track_geojson(
            'V-1-1', track_1, 1,
            '崁頂 → 紅樹林', green_station_ids[-1], green_station_ids[0],
            sum(green_travel_times) // 60
        )
        with open(os.path.join(TRACK_DIR, 'V-1-1.geojson'), 'w', encoding='utf-8') as f:
            json.dump(geojson_1, f, ensure_ascii=False, indent=2)
        print(f"  ✅ V-1-1.geojson")

    # ===== 建立藍海線軌道 =====
    print("\n🚃 建立藍海線軌道 (V-2)...")
    print(f"  車站序列: {BLUE_LINE_STATIONS}")

    blue_station_coords = [station_coords_map.get(sid) for sid in BLUE_LINE_STATIONS if sid in station_coords_map]
    blue_station_ids = [sid for sid in BLUE_LINE_STATIONS if sid in station_coords_map]

    if blue_station_coords:
        # 建立軌道 (V01 → V09 → V28 → V27 → V26)
        blue_track = build_track_from_stations(blue_station_coords, all_segments)
        print(f"  軌道點數: {len(blue_track)}")

        # V-2-0: 紅樹林 → 淡水漁人碼頭 (V01 → V26)
        track_0 = blue_track[:]
        geojson_0 = create_track_geojson(
            'V-2-0', track_0, 0,
            '紅樹林 → 淡水漁人碼頭', blue_station_ids[0], blue_station_ids[-1],
            sum(blue_travel_times) // 60
        )
        with open(os.path.join(TRACK_DIR, 'V-2-0.geojson'), 'w', encoding='utf-8') as f:
            json.dump(geojson_0, f, ensure_ascii=False, indent=2)
        print(f"  ✅ V-2-0.geojson")

        # V-2-1: 淡水漁人碼頭 → 紅樹林 (V26 → V01)
        track_1 = list(reversed(blue_track))
        geojson_1 = create_track_geojson(
            'V-2-1', track_1, 1,
            '淡水漁人碼頭 → 紅樹林', blue_station_ids[-1], blue_station_ids[0],
            sum(blue_travel_times) // 60
        )
        with open(os.path.join(TRACK_DIR, 'V-2-1.geojson'), 'w', encoding='utf-8') as f:
            json.dump(geojson_1, f, ensure_ascii=False, indent=2)
        print(f"  ✅ V-2-1.geojson")

    # ===== 建立時刻表 =====
    print("\n📅 建立時刻表...")
    timetable_data = data.get('StationTimeTable', [])

    # 綠山線時刻表
    if green_station_ids:
        # V-1-0: 紅樹林 → 崁頂 (Direction 0)
        departures_0, travel_time_0 = parse_station_timetable(
            timetable_data, green_station_ids, green_travel_times, 0, route_num=1
        )
        schedule_0 = {
            "track_id": "V-1-0",
            "route_id": "V-1",
            "name": "紅樹林 → 崁頂",
            "origin": green_station_ids[0],
            "destination": green_station_ids[-1],
            "stations": green_station_ids,
            "travel_time_minutes": travel_time_0 // 60,
            "dwell_time_seconds": 25,
            "is_weekday": True,
            "departure_count": len(departures_0),
            "departures": departures_0
        }
        with open(os.path.join(SCHEDULE_DIR, 'V-1-0.json'), 'w', encoding='utf-8') as f:
            json.dump(schedule_0, f, ensure_ascii=False, indent=2)
        print(f"  ✅ V-1-0.json ({len(departures_0)} 班次)")

        # V-1-1: 崁頂 → 紅樹林 (Direction 1)
        reversed_green = list(reversed(green_station_ids))
        reversed_times_green = list(reversed(green_travel_times))
        departures_1, travel_time_1 = parse_station_timetable(
            timetable_data, reversed_green, reversed_times_green, 1, route_num=1
        )
        schedule_1 = {
            "track_id": "V-1-1",
            "route_id": "V-1",
            "name": "崁頂 → 紅樹林",
            "origin": reversed_green[0],
            "destination": reversed_green[-1],
            "stations": reversed_green,
            "travel_time_minutes": travel_time_1 // 60,
            "dwell_time_seconds": 25,
            "is_weekday": True,
            "departure_count": len(departures_1),
            "departures": departures_1
        }
        with open(os.path.join(SCHEDULE_DIR, 'V-1-1.json'), 'w', encoding='utf-8') as f:
            json.dump(schedule_1, f, ensure_ascii=False, indent=2)
        print(f"  ✅ V-1-1.json ({len(departures_1)} 班次)")

    # 藍海線時刻表
    # TDX V-2 路線方向定義：
    # Direction 0: V01 → V26 (紅樹林 → 淡水漁人碼頭)
    # Direction 1: V26 → V01 (淡水漁人碼頭 → 紅樹林)
    if blue_station_ids:
        # V-2-0: 紅樹林 → 淡水漁人碼頭 (Direction 0)
        departures_0, travel_time_0 = parse_station_timetable(
            timetable_data, blue_station_ids, blue_travel_times, 0, route_num=2
        )
        schedule_0 = {
            "track_id": "V-2-0",
            "route_id": "V-2",
            "name": "紅樹林 → 淡水漁人碼頭",
            "origin": blue_station_ids[0],
            "destination": blue_station_ids[-1],
            "stations": blue_station_ids,
            "travel_time_minutes": travel_time_0 // 60,
            "dwell_time_seconds": 25,
            "is_weekday": True,
            "departure_count": len(departures_0),
            "departures": departures_0
        }
        with open(os.path.join(SCHEDULE_DIR, 'V-2-0.json'), 'w', encoding='utf-8') as f:
            json.dump(schedule_0, f, ensure_ascii=False, indent=2)
        print(f"  ✅ V-2-0.json ({len(departures_0)} 班次)")

        # V-2-1: 淡水漁人碼頭 → 紅樹林 (Direction 1)
        reversed_blue = list(reversed(blue_station_ids))
        reversed_times_blue = list(reversed(blue_travel_times))
        departures_1, travel_time_1 = parse_station_timetable(
            timetable_data, reversed_blue, reversed_times_blue, 1, route_num=2  # Direction 1: V26 → V01
        )
        schedule_1 = {
            "track_id": "V-2-1",
            "route_id": "V-2",
            "name": "淡水漁人碼頭 → 紅樹林",
            "origin": reversed_blue[0],
            "destination": reversed_blue[-1],
            "stations": reversed_blue,
            "travel_time_minutes": travel_time_1 // 60,
            "dwell_time_seconds": 25,
            "is_weekday": True,
            "departure_count": len(departures_1),
            "departures": departures_1
        }
        with open(os.path.join(SCHEDULE_DIR, 'V-2-1.json'), 'w', encoding='utf-8') as f:
            json.dump(schedule_1, f, ensure_ascii=False, indent=2)
        print(f"  ✅ V-2-1.json ({len(departures_1)} 班次)")

    # ===== 更新 station_progress.json =====
    print("\n📝 更新 station_progress.json...")

    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        progress_data = json.load(f)

    # 綠山線進度
    if green_station_coords:
        progress_data['V-1-0'] = calculate_progress(green_track, stations, green_station_ids)
        progress_data['V-1-1'] = calculate_progress(list(reversed(green_track)), stations, list(reversed(green_station_ids)))
        print(f"  ✅ V-1-0, V-1-1")

    # 藍海線進度
    if blue_station_coords:
        progress_data['V-2-0'] = calculate_progress(blue_track, stations, blue_station_ids)
        progress_data['V-2-1'] = calculate_progress(list(reversed(blue_track)), stations, list(reversed(blue_station_ids)))
        print(f"  ✅ V-2-0, V-2-1")

    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("✅ 淡海輕軌建置完成")
    print("=" * 60)
    print("\n下一步：更新前端程式碼 (useData.ts, App.tsx, LineFilter.tsx)")


if __name__ == '__main__':
    main()
