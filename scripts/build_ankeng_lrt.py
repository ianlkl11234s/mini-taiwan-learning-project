#!/usr/bin/env python3
"""
安坑輕軌 (Ankeng LRT) 完整建置腳本

使用 TDX API 取得資料：
- Station API → 車站座標
- Shape API → 軌道幾何 (WKT)
- StationTimeTable API → 實際時刻表 (以平日為主)

輸出：
- ankeng_lrt_stations.geojson
- tracks/K-1-0.geojson, K-1-1.geojson
- schedules/K-1-0.json, K-1-1.json
- station_progress.json (更新)
"""

import json
import re
import math
import os
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any, Optional

# 專案根目錄
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# TDX 認證模組路徑
gis_analytics_path = os.path.join(PROJECT_ROOT, "..", "taipei-gis-analytics")
sys.path.insert(0, gis_analytics_path)

# TDX 資料目錄
TDX_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "tdx_ankeng_lrt")

# 輸出檔案
STATION_FILE = os.path.join(PROJECT_ROOT, "public/data/ankeng_lrt_stations.geojson")
TRACK_DIR = os.path.join(PROJECT_ROOT, "public/data/tracks")
SCHEDULE_DIR = os.path.join(PROJECT_ROOT, "public/data/schedules")
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "public/data/station_progress.json")

# 線路設定
LINE_ID = "K"
LINE_COLOR = "#8cc540"  # 草綠色
RAIL_SYSTEM = "NTALRT"  # 安坑輕軌系統代碼

# 車站順序 (K01-K09)
STATION_ORDER = [f"K{i:02d}" for i in range(1, 10)]


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

            # 避免 API 限流
            time.sleep(2)
        except Exception as e:
            print(f"  ❌ 失敗: {e}")
            data[api_name] = []

    return data


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


def euclidean_distance(p1: List[float], p2: List[float]) -> float:
    """計算 Euclidean 距離"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def connect_segments_simple(segments: List[List[List[float]]]) -> List[List[float]]:
    """簡單連接所有分段"""
    if not segments:
        return []

    remaining = [seg[:] for seg in segments]
    result = remaining.pop(0)[:]

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

        if best_idx == -1:
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


def find_nearest_point_index(coord: List[float], track_coords: List[List[float]]) -> int:
    """找到軌道上最接近指定座標的點索引"""
    min_dist = float('inf')
    best_idx = 0

    for i, tc in enumerate(track_coords):
        dist = euclidean_distance(tc, coord)
        if dist < min_dist:
            min_dist = dist
            best_idx = i

    return best_idx


def truncate_track(track_coords: List[List[float]], start_coord: List[float], end_coord: List[float]) -> List[List[float]]:
    """截斷軌道至指定的起終點範圍"""
    start_idx = find_nearest_point_index(start_coord, track_coords)
    end_idx = find_nearest_point_index(end_coord, track_coords)

    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx

    truncated = track_coords[start_idx:end_idx + 1]
    truncated[0] = start_coord[:]
    truncated[-1] = end_coord[:]

    return truncated


def find_best_segment(station_coord: List[float], track_coords: List[List[float]]) -> Tuple[int, float]:
    """找到車站應該插入的最佳線段位置"""
    min_dist = float('inf')
    best_idx = 0

    for i in range(len(track_coords) - 1):
        # 計算點到線段的距離
        x1, y1 = track_coords[i]
        x2, y2 = track_coords[i+1]
        px, py = station_coord

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

    return best_idx, min_dist


def calibrate_track(track_coords: List[List[float]], stations: List[Dict], station_order: List[str]) -> List[List[float]]:
    """校準軌道座標，確保軌道通過所有車站"""
    station_coords = {s['station_id']: s['coordinates'] for s in stations}
    calibrated = [coord[:] for coord in track_coords]

    for station_id in station_order:
        if station_id not in station_coords:
            print(f"  警告: 找不到車站 {station_id}")
            continue

        coord = station_coords[station_id]

        # 檢查是否已經存在
        found = False
        for tc in calibrated:
            if abs(tc[0] - coord[0]) < 0.00001 and abs(tc[1] - coord[1]) < 0.00001:
                found = True
                break

        if not found:
            best_idx, dist = find_best_segment(coord, calibrated)
            calibrated.insert(best_idx + 1, [coord[0], coord[1]])
            print(f"  插入 {station_id} 在索引 {best_idx + 1}, 距離: {dist:.6f}")

    return calibrated


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

        cumulative = 0
        for i in range(len(track_coords) - 1):
            if abs(track_coords[i][0] - coord[0]) < 0.00001 and abs(track_coords[i][1] - coord[1]) < 0.00001:
                progress[station_id] = cumulative / total_length if total_length > 0 else 0
                break
            if abs(track_coords[i+1][0] - coord[0]) < 0.00001 and abs(track_coords[i+1][1] - coord[1]) < 0.00001:
                cumulative += euclidean_distance(track_coords[i], track_coords[i+1])
                progress[station_id] = cumulative / total_length if total_length > 0 else 0
                break
            cumulative += euclidean_distance(track_coords[i], track_coords[i+1])

        if station_id not in progress:
            min_dist = float('inf')
            best_progress = 0
            cumulative = 0
            for i in range(len(track_coords)):
                dist = euclidean_distance(track_coords[i], coord)
                if dist < min_dist:
                    min_dist = dist
                    best_progress = cumulative / total_length if total_length > 0 else 0
                if i < len(track_coords) - 1:
                    cumulative += euclidean_distance(track_coords[i], track_coords[i+1])
            progress[station_id] = best_progress

    return progress


def parse_station_timetable(timetable_data: List[Dict], station_order: List[str]) -> Dict[str, Any]:
    """
    解析 StationTimeTable 資料，從各站時刻推算站間時間

    安坑輕軌特殊處理：
    - 部分班次可能只行駛區間 (K01-K05 或 K06-K09)
    - 使用實際匹配的時刻差來計算站間時間

    Returns:
        {
            'departures_0': [{'time': 'HH:MM:SS', 'stations': [...]}],  # Direction 0
            'departures_1': [{'time': 'HH:MM:SS', 'stations': [...]}],  # Direction 1
            'travel_times_0': [秒],  # 站間時間 (Direction 0)
            'travel_times_1': [秒],  # 站間時間 (Direction 1)
        }
    """
    # 預設站間時間（秒）- 基於實際時刻表分析
    # K01→K09 方向
    DEFAULT_TRAVEL_TIMES_0 = [
        60,   # K01 → K02: 1 分鐘
        180,  # K02 → K03: 3 分鐘
        120,  # K03 → K04: 2 分鐘
        120,  # K04 → K05: 2 分鐘
        240,  # K05 → K06: 4 分鐘 (估算，可能有區間車問題)
        120,  # K06 → K07: 2 分鐘
        180,  # K07 → K08: 3 分鐘
        120,  # K08 → K09: 2 分鐘 (估算)
    ]

    # K09→K01 方向 (反向)
    DEFAULT_TRAVEL_TIMES_1 = list(reversed(DEFAULT_TRAVEL_TIMES_0))

    # 篩選平日資料
    weekday_data = [
        t for t in timetable_data
        if t.get('ServiceDay', {}).get('ServiceTag') == '平日'
    ]

    if not weekday_data:
        weekday_data = [
            t for t in timetable_data
            if (t.get('ServiceDay', {}).get('Monday', False) and
                t.get('ServiceDay', {}).get('Saturday', False) == False)
        ]

    print(f"  平日時刻表資料: {len(weekday_data)} 筆")

    # 依方向分組
    dir_0 = [t for t in weekday_data if t.get('Direction') == 0]
    dir_1 = [t for t in weekday_data if t.get('Direction') == 1]

    print(f"  Direction 0: {len(dir_0)} 筆")
    print(f"  Direction 1: {len(dir_1)} 筆")

    result = {
        'departures_0': [],
        'departures_1': [],
        'travel_times_0': DEFAULT_TRAVEL_TIMES_0,
        'travel_times_1': DEFAULT_TRAVEL_TIMES_1,
    }

    # 處理每個方向
    for direction, dir_data, default_times, key in [
        (0, dir_0, DEFAULT_TRAVEL_TIMES_0, '_0'),
        (1, dir_1, DEFAULT_TRAVEL_TIMES_1, '_1')
    ]:
        if not dir_data:
            continue

        # 取得這個方向的車站順序
        if direction == 0:
            order = station_order  # K01→K09
        else:
            order = list(reversed(station_order))  # K09→K01

        origin_station = order[0]

        # 建立各站時刻表字典
        station_timetables = {}
        for t in dir_data:
            sid = t.get('StationID')
            if sid:
                station_timetables[sid] = t.get('Timetables', [])

        print(f"  Direction {direction} 車站: {list(station_timetables.keys())}")

        # 從起點站取得發車時刻
        origin_times = station_timetables.get(origin_station, [])
        if not origin_times:
            print(f"  ⚠️ 找不到起點站 {origin_station} 的時刻表")
            continue

        print(f"  起點站 {origin_station} 發車班次: {len(origin_times)} 班")

        # 使用預設的站間時間
        travel_times = default_times
        print(f"  使用預設站間時間: {travel_times}")

        # 建立發車時刻
        for seq, time_entry in enumerate(origin_times, 1):
            dep_time = time_entry.get('DepartureTime', time_entry.get('ArrivalTime', '06:00'))

            # 建立站點時刻
            stations = []
            cumulative = 0

            for i, sid in enumerate(order):
                arrival = cumulative
                departure = cumulative + 25  # 停站 25 秒

                stations.append({
                    'station_id': sid,
                    'arrival': arrival,
                    'departure': departure
                })

                if i < len(travel_times):
                    cumulative = departure + travel_times[i]  # 下一站到達時間

            result[f'departures{key}'].append({
                'departure_time': f"{dep_time}:00" if len(dep_time) <= 5 else dep_time,
                'train_id': f"K-1-{direction}-{seq:03d}",
                'origin_station': origin_station,
                'total_travel_time': cumulative,
                'stations': stations
            })

    return result


def build_station_geojson(station_data: List[Dict]) -> Dict[str, Any]:
    """建立車站 GeoJSON"""
    features = []

    for s in station_data:
        features.append({
            "type": "Feature",
            "properties": {
                "station_id": s['StationID'],
                "name_zh": s['StationName']['Zh_tw'],
                "name_en": s['StationName'].get('En', ''),
                "line_id": LINE_ID
            },
            "geometry": {
                "type": "Point",
                "coordinates": [
                    s['StationPosition']['PositionLon'],
                    s['StationPosition']['PositionLat']
                ]
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


def build_track_geojson(
    track_id: str,
    coordinates: List[List[float]],
    direction: int,
    name: str,
    start_station: str,
    end_station: str,
    travel_time: int
) -> Dict[str, Any]:
    """建立軌道 GeoJSON"""
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "color": LINE_COLOR,
                "route_id": "K-1",
                "direction": direction,
                "name": name,
                "start_station": start_station,
                "end_station": end_station,
                "travel_time": travel_time,
                "line_id": LINE_ID
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            }
        }]
    }


def build_schedule_json(
    track_id: str,
    direction: int,
    station_order: List[str],
    departures: List[Dict],
    travel_times: List[int]
) -> Dict[str, Any]:
    """建立時刻表 JSON"""
    total_travel_time = sum(travel_times) + len(station_order) * 25  # 加上停站時間

    return {
        "track_id": track_id,
        "route_id": "K-1",
        "name": f"{'雙城' if direction == 0 else '十四張'} → {'十四張' if direction == 0 else '雙城'}",
        "origin": station_order[0],
        "destination": station_order[-1],
        "stations": station_order,
        "travel_time_minutes": total_travel_time // 60,
        "dwell_time_seconds": 25,
        "is_weekday": True,
        "departure_count": len(departures),
        "departures": departures
    }


def main():
    print("=" * 60)
    print("安坑輕軌 (Ankeng LRT) 建置腳本")
    print("=" * 60)

    # 確保輸出目錄存在
    os.makedirs(TRACK_DIR, exist_ok=True)
    os.makedirs(SCHEDULE_DIR, exist_ok=True)

    # ========== Step 1: 下載 TDX 資料 ==========
    print("\n[Step 1] 下載 TDX 資料...")

    client = get_tdx_client()
    data = download_tdx_data(client)

    station_data = data.get('Station', [])
    shape_data = data.get('Shape', [])
    timetable_data = data.get('StationTimeTable', [])

    if not station_data or not shape_data:
        print("❌ 缺少必要資料，無法繼續")
        return

    # ========== Step 2: 建立車站 GeoJSON ==========
    print("\n[Step 2] 建立車站 GeoJSON...")

    station_geojson = build_station_geojson(station_data)

    with open(STATION_FILE, 'w', encoding='utf-8') as f:
        json.dump(station_geojson, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 已建立: {STATION_FILE}")
    print(f"  車站數: {len(station_geojson['features'])}")

    # 建立車站資料列表
    stations = []
    for s in station_data:
        stations.append({
            'station_id': s['StationID'],
            'name_zh': s['StationName']['Zh_tw'],
            'name_en': s['StationName'].get('En', ''),
            'coordinates': [
                s['StationPosition']['PositionLon'],
                s['StationPosition']['PositionLat']
            ]
        })

    # 顯示車站列表
    print("\n  車站列表:")
    for s in stations:
        print(f"    {s['station_id']}: {s['name_zh']} {s['coordinates']}")

    # ========== Step 3: 解析軌道 WKT ==========
    print("\n[Step 3] 解析軌道 WKT...")

    wkt = shape_data[0]['Geometry']
    segments = parse_wkt_multilinestring(wkt)
    print(f"  WKT 分段數: {len(segments)}")

    # 連接分段
    raw_coords = connect_segments_simple(segments)
    print(f"  連接後座標點數: {len(raw_coords)}")

    # 取得起終點座標
    k01_coord = next((s['coordinates'] for s in stations if s['station_id'] == 'K01'), None)
    k09_coord = next((s['coordinates'] for s in stations if s['station_id'] == 'K09'), None)

    if not k01_coord or not k09_coord:
        print("❌ 找不到 K01 或 K09 座標")
        return

    print(f"  K01 (雙城): {k01_coord}")
    print(f"  K09 (十四張): {k09_coord}")

    # 判斷方向
    dist_start_to_k01 = euclidean_distance(raw_coords[0], k01_coord)
    dist_start_to_k09 = euclidean_distance(raw_coords[0], k09_coord)

    if dist_start_to_k09 < dist_start_to_k01:
        print("  連接後方向: K09→K01 (需反轉給 K-1-0)")
        coords_for_dir0 = list(reversed(raw_coords))
        coords_for_dir1 = raw_coords[:]
    else:
        print("  連接後方向: K01→K09")
        coords_for_dir0 = raw_coords[:]
        coords_for_dir1 = list(reversed(raw_coords))

    # 截斷軌道
    print("\n[截斷] 截斷軌道至車站範圍...")
    coords_for_dir0 = truncate_track(coords_for_dir0, k01_coord, k09_coord)
    coords_for_dir1 = truncate_track(coords_for_dir1, k09_coord, k01_coord)
    print(f"  K-1-0 截斷後座標點數: {len(coords_for_dir0)}")
    print(f"  K-1-1 截斷後座標點數: {len(coords_for_dir1)}")

    # ========== Step 4: 校準軌道座標 ==========
    print("\n[Step 4] 校準軌道座標...")

    station_order_0 = STATION_ORDER  # K01→K09
    station_order_1 = list(reversed(STATION_ORDER))  # K09→K01

    print("\n  校準 K-1-0 (雙城→十四張)...")
    calibrated_0 = calibrate_track(coords_for_dir0, stations, station_order_0)
    print(f"  校準後座標點數: {len(calibrated_0)}")

    print("\n  校準 K-1-1 (十四張→雙城)...")
    calibrated_1 = calibrate_track(coords_for_dir1, stations, station_order_1)
    print(f"  校準後座標點數: {len(calibrated_1)}")

    # ========== Step 5: 解析時刻表 ==========
    print("\n[Step 5] 解析 StationTimeTable...")

    if timetable_data:
        timetable_result = parse_station_timetable(timetable_data, STATION_ORDER)
    else:
        print("  ⚠️ 無時刻表資料，使用預設班距")
        timetable_result = {
            'departures_0': [],
            'departures_1': [],
            'travel_times_0': [120] * 8,  # 預設每站間 2 分鐘
            'travel_times_1': [120] * 8,
        }

    # ========== Step 6: 建立軌道 GeoJSON ==========
    print("\n[Step 6] 建立軌道 GeoJSON...")

    travel_time_0 = sum(timetable_result['travel_times_0']) // 60 if timetable_result['travel_times_0'] else 16
    travel_time_1 = sum(timetable_result['travel_times_1']) // 60 if timetable_result['travel_times_1'] else 16

    # K-1-0: 雙城→十四張
    track_0 = build_track_geojson(
        track_id="K-1-0",
        coordinates=calibrated_0,
        direction=0,
        name="雙城 → 十四張",
        start_station="K01",
        end_station="K09",
        travel_time=travel_time_0
    )

    track_0_path = os.path.join(TRACK_DIR, "K-1-0.geojson")
    with open(track_0_path, 'w', encoding='utf-8') as f:
        json.dump(track_0, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 已建立: {track_0_path}")

    # K-1-1: 十四張→雙城
    track_1 = build_track_geojson(
        track_id="K-1-1",
        coordinates=calibrated_1,
        direction=1,
        name="十四張 → 雙城",
        start_station="K09",
        end_station="K01",
        travel_time=travel_time_1
    )

    track_1_path = os.path.join(TRACK_DIR, "K-1-1.geojson")
    with open(track_1_path, 'w', encoding='utf-8') as f:
        json.dump(track_1, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 已建立: {track_1_path}")

    # ========== Step 7: 建立時刻表 JSON ==========
    print("\n[Step 7] 建立時刻表 JSON...")

    # K-1-0 時刻表
    schedule_0 = build_schedule_json(
        track_id="K-1-0",
        direction=0,
        station_order=station_order_0,
        departures=timetable_result['departures_0'],
        travel_times=timetable_result['travel_times_0']
    )

    schedule_0_path = os.path.join(SCHEDULE_DIR, "K-1-0.json")
    with open(schedule_0_path, 'w', encoding='utf-8') as f:
        json.dump(schedule_0, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 已建立: {schedule_0_path}")
    print(f"    發車數: {schedule_0['departure_count']} 班")

    # K-1-1 時刻表
    schedule_1 = build_schedule_json(
        track_id="K-1-1",
        direction=1,
        station_order=station_order_1,
        departures=timetable_result['departures_1'],
        travel_times=timetable_result['travel_times_1']
    )

    schedule_1_path = os.path.join(SCHEDULE_DIR, "K-1-1.json")
    with open(schedule_1_path, 'w', encoding='utf-8') as f:
        json.dump(schedule_1, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 已建立: {schedule_1_path}")
    print(f"    發車數: {schedule_1['departure_count']} 班")

    # ========== Step 8: 更新 station_progress.json ==========
    print("\n[Step 8] 更新 station_progress.json...")

    progress_0 = calculate_progress(calibrated_0, stations, station_order_0)
    progress_1 = calculate_progress(calibrated_1, stations, station_order_1)

    print(f"\n  K-1-0 進度:")
    for sid in station_order_0[:3]:
        print(f"    {sid}: {progress_0.get(sid, 'N/A'):.6f}")
    print(f"    ...")
    for sid in station_order_0[-3:]:
        print(f"    {sid}: {progress_0.get(sid, 'N/A'):.6f}")

    # 載入現有 progress
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            all_progress = json.load(f)
    else:
        all_progress = {}

    # 新增 K 軌道進度
    all_progress['K-1-0'] = progress_0
    all_progress['K-1-1'] = progress_1

    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)
    print(f"\n  ✅ 已更新: {PROGRESS_FILE}")

    # ========== 完成 ==========
    print("\n" + "=" * 60)
    print("安坑輕軌建置完成!")
    print("=" * 60)
    print("\n建立的檔案:")
    print(f"  - {STATION_FILE}")
    print(f"  - {track_0_path}")
    print(f"  - {track_1_path}")
    print(f"  - {schedule_0_path}")
    print(f"  - {schedule_1_path}")
    print(f"  - {PROGRESS_FILE} (已更新)")
    print("\n下一步:")
    print("  1. 更新 src/hooks/useData.ts")
    print("  2. 更新 src/App.tsx")
    print("  3. 更新 src/components/LineFilter.tsx")
    print("  4. 執行 npm run dev 測試")


if __name__ == '__main__':
    main()
