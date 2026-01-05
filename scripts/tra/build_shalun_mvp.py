#!/usr/bin/env python3
"""
沙崙線 MVP 資料建置腳本

產出檔案:
- public/data-tra/shalun_stations.geojson
- public/data-tra/tracks/SH-0.geojson
- public/data-tra/tracks/SH-1.geojson
- public/data-tra/schedules/SH-0.json
- public/data-tra/schedules/SH-1.json
- public/data-tra/station_progress.json
"""

import json
import math
import sys
from pathlib import Path

# 加入 TDX 客戶端路徑
TDX_PATH = Path(__file__).parent.parent.parent.parent / "tdx_api_docs"
sys.path.insert(0, str(TDX_PATH))

from src import TDXAuth, TDXClient

# 輸出路徑
OUTPUT_DIR = Path(__file__).parent.parent.parent / "public" / "data-tra"
TRACKS_DIR = OUTPUT_DIR / "tracks"
SCHEDULES_DIR = OUTPUT_DIR / "schedules"

# 台鐵顏色
TRA_COLOR = "#0066b3"

# =============================================================================
# 工具函數
# =============================================================================

def euclidean_distance(coord1, coord2):
    """計算 Euclidean 距離（與 TrainEngine 一致）"""
    dx = coord2[0] - coord1[0]
    dy = coord2[1] - coord1[1]
    return math.sqrt(dx * dx + dy * dy)


def point_to_segment_distance(px, py, x1, y1, x2, y2):
    """
    計算點到線段的最短距離
    返回: (距離, 投影點x, 投影點y)
    """
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return euclidean_distance([px, py], [x1, y1]), x1, y1

    # 投影參數 t
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))  # 限制在 [0,1]

    proj_x = x1 + t * dx
    proj_y = y1 + t * dy

    dist = euclidean_distance([px, py], [proj_x, proj_y])
    return dist, proj_x, proj_y


def find_best_segment(station_coord, track_coords):
    """找到車站應該插入的線段位置"""
    min_dist = float('inf')
    best_idx = 0

    for i in range(len(track_coords) - 1):
        dist, _, _ = point_to_segment_distance(
            station_coord[0], station_coord[1],
            track_coords[i][0], track_coords[i][1],
            track_coords[i + 1][0], track_coords[i + 1][1]
        )
        if dist < min_dist:
            min_dist = dist
            best_idx = i

    return best_idx, min_dist


def parse_wkt_linestring(geometry_str):
    """解析 WKT LINESTRING 座標"""
    coords_str = geometry_str.replace("LINESTRING (", "").replace(")", "")
    coords = []
    for pair in coords_str.split(", "):
        lng, lat = pair.strip().split(" ")
        coords.append([float(lng), float(lat)])
    return coords


def time_to_seconds(time_str):
    """將 HH:MM 轉為秒數"""
    parts = time_str.split(":")
    h = int(parts[0])
    m = int(parts[1])
    s = int(parts[2]) if len(parts) > 2 else 0
    return h * 3600 + m * 60 + s


# =============================================================================
# 資料取得
# =============================================================================

def fetch_shalun_data():
    """從 TDX 取得沙崙線資料"""
    print("📡 連接 TDX API...")
    auth = TDXAuth()
    client = TDXClient(auth)

    # 1. 取得沙崙線車站
    print("📍 取得沙崙線車站...")
    stations_data = client.get('basic', '/v3/Rail/TRA/Station', {
        '$filter': "StationID ge '4220' and StationID le '4280'"
    })
    stations = {s['StationID']: s for s in stations_data.get('Stations', [])}

    # 沙崙線相關車站: 4220(臺南), 4250(保安), 4260(仁德), 4270(中洲), 4271(長榮大學), 4272(沙崙)
    shalun_station_ids = ['4220', '4250', '4260', '4270', '4271', '4272']
    shalun_stations = {sid: stations[sid] for sid in shalun_station_ids if sid in stations}

    print(f"  找到 {len(shalun_stations)} 個車站")

    # 2. 取得沙崙線 Shape
    print("🛤️ 取得沙崙線軌道...")
    shape_data = client.get('basic', '/v3/Rail/TRA/Shape', {
        '$filter': "LineID eq 'SH'"
    })
    shapes = shape_data.get('Shapes', [])

    # 3. 取得 LineNetwork (站間距離)
    print("📏 取得站間距離...")
    network_data = client.get('basic', '/v3/Rail/TRA/LineNetwork', {
        '$filter': "LineID eq 'SH'"
    })
    line_network = network_data.get('LineNetworks', [])

    # 4. 取得今日時刻表
    print("📅 取得今日時刻表...")
    timetable_data = client.get('basic', '/v3/Rail/TRA/DailyTrainTimetable/Today', {})
    all_trains = timetable_data.get('TrainTimetables', [])

    # 過濾沙崙線車次
    shalun_only = {'4271', '4272'}  # 沙崙線專屬車站
    shalun_trains = []
    for train in all_trains:
        stops = train.get('StopTimes', [])
        stop_ids = {s['StationID'] for s in stops}
        if stop_ids & shalun_only:
            shalun_trains.append(train)

    print(f"  找到 {len(shalun_trains)} 班沙崙線車次")

    return {
        'stations': shalun_stations,
        'shapes': shapes,
        'line_network': line_network,
        'trains': shalun_trains
    }


# =============================================================================
# 車站 GeoJSON
# =============================================================================

def build_stations_geojson(stations):
    """建立車站 GeoJSON"""
    features = []

    for sid, station in stations.items():
        pos = station['StationPosition']
        features.append({
            "type": "Feature",
            "properties": {
                "station_id": sid,
                "name_zh": station['StationName']['Zh_tw'],
                "name_en": station['StationName']['En'],
                "station_class": station.get('StationClass', ''),
                "line_id": "SH" if sid in ['4271', '4272'] else "WL"
            },
            "geometry": {
                "type": "Point",
                "coordinates": [pos['PositionLon'], pos['PositionLat']]
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


# =============================================================================
# 軌道 GeoJSON
# =============================================================================

def build_track_geojson(shapes, stations, line_network, direction):
    """
    建立軌道 GeoJSON

    direction 0: 沙崙 → 臺南
    direction 1: 臺南 → 沙崙
    """
    if not shapes:
        print("  ⚠️ 沒有找到沙崙線 Shape，使用車站座標建立軌道")
        return build_track_from_stations(stations, direction)

    # 解析 Shape 座標
    shape = shapes[0]
    coords = parse_wkt_linestring(shape['Geometry'])

    # 沙崙線站序（從支線端到幹線端）
    if direction == 0:
        # 沙崙 → 臺南
        station_order = ['4272', '4271', '4270', '4260', '4250', '4220']
    else:
        # 臺南 → 沙崙
        station_order = ['4220', '4250', '4260', '4270', '4271', '4272']

    # 校準：將車站座標插入軌道
    calibrated_coords = calibrate_track(coords, stations, station_order)

    # 計算旅行時間（分鐘）
    if line_network:
        segments = line_network[0].get('LineSegments', [])
        total_distance = sum(seg['Distance'] for seg in segments)
        # 假設平均時速 40km/h
        travel_time = int(total_distance / 40 * 60)
    else:
        travel_time = 24  # 預設

    track_id = f"SH-{direction}"
    start_station = station_order[0]
    end_station = station_order[-1]

    start_name = stations[start_station]['StationName']['Zh_tw']
    end_name = stations[end_station]['StationName']['Zh_tw']

    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "line_id": "SH",
                "direction": direction,
                "name": f"{start_name} → {end_name}",
                "start_station": start_station,
                "end_station": end_station,
                "travel_time": travel_time,
                "color": TRA_COLOR
            },
            "geometry": {
                "type": "LineString",
                "coordinates": calibrated_coords
            }
        }]
    }


def build_track_from_stations(stations, direction):
    """當沒有 Shape 時，使用車站座標建立軌道"""
    if direction == 0:
        station_order = ['4272', '4271', '4270', '4260', '4250', '4220']
    else:
        station_order = ['4220', '4250', '4260', '4270', '4271', '4272']

    coords = []
    for sid in station_order:
        if sid in stations:
            pos = stations[sid]['StationPosition']
            coords.append([pos['PositionLon'], pos['PositionLat']])

    track_id = f"SH-{direction}"
    start_station = station_order[0]
    end_station = station_order[-1]

    start_name = stations[start_station]['StationName']['Zh_tw']
    end_name = stations[end_station]['StationName']['Zh_tw']

    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "line_id": "SH",
                "direction": direction,
                "name": f"{start_name} → {end_name}",
                "start_station": start_station,
                "end_station": end_station,
                "travel_time": 24,
                "color": TRA_COLOR
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }


def calibrate_track(coords, stations, station_order):
    """
    校準軌道座標，確保軌道經過所有車站

    使用「點到線段距離」演算法，避免 zigzag 問題
    """
    calibrated = coords.copy()

    for sid in station_order:
        if sid not in stations:
            continue

        pos = stations[sid]['StationPosition']
        station_coord = [pos['PositionLon'], pos['PositionLat']]

        # 檢查是否已經在軌道上
        for c in calibrated:
            if abs(c[0] - station_coord[0]) < 0.00001 and abs(c[1] - station_coord[1]) < 0.00001:
                break
        else:
            # 找到最佳插入位置
            best_idx, dist = find_best_segment(station_coord, calibrated)
            # 插入車站座標
            calibrated.insert(best_idx + 1, station_coord)

    return calibrated


# =============================================================================
# 進度映射
# =============================================================================

def build_station_progress(coords, stations, station_order):
    """
    計算車站進度映射

    使用距離基準，不是索引基準！
    """
    # 計算軌道總長度
    total_length = 0
    for i in range(len(coords) - 1):
        total_length += euclidean_distance(coords[i], coords[i + 1])

    # 找每個車站在軌道上的位置
    progress_map = {}

    for sid in station_order:
        if sid not in stations:
            continue

        pos = stations[sid]['StationPosition']
        station_coord = [pos['PositionLon'], pos['PositionLat']]

        # 找到車站在軌道座標中的索引
        station_idx = None
        for i, c in enumerate(coords):
            if abs(c[0] - station_coord[0]) < 0.00001 and abs(c[1] - station_coord[1]) < 0.00001:
                station_idx = i
                break

        if station_idx is None:
            print(f"  ⚠️ 車站 {sid} 未在軌道上找到")
            continue

        # 計算從起點到該站的累積距離
        cumulative = 0
        for i in range(station_idx):
            cumulative += euclidean_distance(coords[i], coords[i + 1])

        # 進度 = 累積距離 / 總距離
        progress = cumulative / total_length if total_length > 0 else 0
        progress_map[sid] = round(progress, 6)

    return progress_map


# =============================================================================
# 時刻表
# =============================================================================

def build_schedule(trains, direction, stations, station_order):
    """建立時刻表 JSON"""
    track_id = f"SH-{direction}"

    # 過濾該方向的班次
    filtered_trains = []
    for train in trains:
        info = train['TrainInfo']
        # 用起終站判斷方向
        start_id = info['StartingStationID']
        end_id = info['EndingStationID']

        if direction == 0:
            # 沙崙 → 臺南 (station_id 大→小)
            if start_id in ['4272', '4271'] or end_id in ['4220', '4250', '4260']:
                filtered_trains.append(train)
        else:
            # 臺南 → 沙崙 (station_id 小→大)
            if end_id in ['4272', '4271'] or start_id in ['4220', '4250', '4260']:
                filtered_trains.append(train)

    # 建立 departures
    departures = []

    for train in filtered_trains:
        info = train['TrainInfo']
        stops = train['StopTimes']

        if not stops:
            continue

        # 計算相對秒數
        base_time = time_to_seconds(stops[0]['DepartureTime'])

        station_times = []
        for stop in stops:
            arr_time = time_to_seconds(stop.get('ArrivalTime', stop['DepartureTime']))
            dep_time = time_to_seconds(stop['DepartureTime'])

            station_times.append({
                "station_id": stop['StationID'],
                "station_name": stop['StationName']['Zh_tw'],
                "arrival": arr_time - base_time,
                "departure": dep_time - base_time
            })

        departures.append({
            "departure_time": stops[0]['DepartureTime'] + ":00",
            "train_id": f"TRA-{info['TrainNo']}",
            "train_no": info['TrainNo'],
            "train_type": info['TrainTypeName']['Zh_tw'],
            "origin_station": stops[0]['StationID'],
            "stations": station_times,
            "total_travel_time": station_times[-1]['arrival'] if station_times else 0
        })

    # 依發車時間排序
    departures.sort(key=lambda x: x['departure_time'])

    # 取得起終站名稱
    start_station = station_order[0]
    end_station = station_order[-1]
    start_name = stations[start_station]['StationName']['Zh_tw'] if start_station in stations else start_station
    end_name = stations[end_station]['StationName']['Zh_tw'] if end_station in stations else end_station

    return {
        "track_id": track_id,
        "line_id": "SH",
        "name": f"{start_name} → {end_name}",
        "origin": start_station,
        "destination": end_station,
        "stations": station_order,
        "travel_time_minutes": 24,
        "dwell_time_seconds": 30,
        "is_weekday": True,
        "departure_count": len(departures),
        "departures": departures
    }


# =============================================================================
# 主程式
# =============================================================================

def main():
    print("=" * 60)
    print("🚂 沙崙線 MVP 資料建置")
    print("=" * 60)

    # 1. 取得資料
    data = fetch_shalun_data()

    stations = data['stations']
    shapes = data['shapes']
    line_network = data['line_network']
    trains = data['trains']

    print(f"\n📊 資料統計:")
    print(f"  車站: {len(stations)} 個")
    print(f"  Shape: {len(shapes)} 條")
    print(f"  班次: {len(trains)} 班")

    # 2. 建立車站 GeoJSON
    print("\n📍 建立車站 GeoJSON...")
    stations_geojson = build_stations_geojson(stations)
    stations_path = OUTPUT_DIR / "shalun_stations.geojson"
    with open(stations_path, 'w', encoding='utf-8') as f:
        json.dump(stations_geojson, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {stations_path}")

    # 3. 建立軌道 GeoJSON (雙向)
    print("\n🛤️ 建立軌道 GeoJSON...")

    station_order_0 = ['4272', '4271', '4270', '4260', '4250', '4220']  # 沙崙→臺南
    station_order_1 = ['4220', '4250', '4260', '4270', '4271', '4272']  # 臺南→沙崙

    track_0 = build_track_geojson(shapes, stations, line_network, 0)
    track_0_path = TRACKS_DIR / "SH-0.geojson"
    with open(track_0_path, 'w', encoding='utf-8') as f:
        json.dump(track_0, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {track_0_path}")

    track_1 = build_track_geojson(shapes, stations, line_network, 1)
    track_1_path = TRACKS_DIR / "SH-1.geojson"
    with open(track_1_path, 'w', encoding='utf-8') as f:
        json.dump(track_1, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {track_1_path}")

    # 4. 建立進度映射
    print("\n📏 建立進度映射...")
    coords_0 = track_0['features'][0]['geometry']['coordinates']
    coords_1 = track_1['features'][0]['geometry']['coordinates']

    progress_0 = build_station_progress(coords_0, stations, station_order_0)
    progress_1 = build_station_progress(coords_1, stations, station_order_1)

    station_progress = {
        "SH-0": progress_0,
        "SH-1": progress_1
    }

    progress_path = OUTPUT_DIR / "station_progress.json"
    with open(progress_path, 'w', encoding='utf-8') as f:
        json.dump(station_progress, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {progress_path}")

    print(f"\n  SH-0 進度: {progress_0}")
    print(f"  SH-1 進度: {progress_1}")

    # 5. 建立時刻表
    print("\n📅 建立時刻表...")

    schedule_0 = build_schedule(trains, 0, stations, station_order_0)
    schedule_0_path = SCHEDULES_DIR / "SH-0.json"
    with open(schedule_0_path, 'w', encoding='utf-8') as f:
        json.dump(schedule_0, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {schedule_0_path} ({schedule_0['departure_count']} 班)")

    schedule_1 = build_schedule(trains, 1, stations, station_order_1)
    schedule_1_path = SCHEDULES_DIR / "SH-1.json"
    with open(schedule_1_path, 'w', encoding='utf-8') as f:
        json.dump(schedule_1, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {schedule_1_path} ({schedule_1['departure_count']} 班)")

    # 6. 驗證
    print("\n" + "=" * 60)
    print("✅ 沙崙線 MVP 資料建置完成！")
    print("=" * 60)

    print("\n📁 產出檔案:")
    print(f"  - {stations_path}")
    print(f"  - {track_0_path}")
    print(f"  - {track_1_path}")
    print(f"  - {progress_path}")
    print(f"  - {schedule_0_path}")
    print(f"  - {schedule_1_path}")

    print("\n📊 統計:")
    print(f"  - 車站: {len(stations)} 個")
    print(f"  - 軌道: 2 條")
    print(f"  - 班次: SH-0={schedule_0['departure_count']} 班, SH-1={schedule_1['departure_count']} 班")

    return 0


if __name__ == "__main__":
    sys.exit(main())
