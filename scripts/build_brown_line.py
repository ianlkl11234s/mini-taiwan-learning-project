#!/usr/bin/env python3
"""
文湖線 (Brown Line) 完整建置腳本
處理 Task 2-6:
- Task 2: 轉換 WKT 軌道為 GeoJSON
- Task 3: 校準軌道座標
- Task 4: 建立雙向軌道檔案
- Task 5: 生成時刻表 JSON
- Task 6: 計算並更新 station_progress.json
"""

import json
import re
import math
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any

# 專案根目錄
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 輸入檔案
STATION_FILE = os.path.join(PROJECT_ROOT, "data/tdx_metro_test/metro_station_BR_20251231.json")
SHAPE_FILE = os.path.join(PROJECT_ROOT, "data/tdx_metro_test/metro_shape_BR_20251231.json")
TRAVEL_TIME_FILE = os.path.join(PROJECT_ROOT, "data/tdx_metro_test/metro_s2s_travel_time_BR_20251231.json")
FREQUENCY_FILE = os.path.join(PROJECT_ROOT, "data/tdx_metro_test/metro_frequency_BR_20251231.json")
FIRST_LAST_FILE = os.path.join(PROJECT_ROOT, "data/tdx_metro_test/metro_first_last_BR_20251231.json")

# 輸出檔案
TRACK_DIR = os.path.join(PROJECT_ROOT, "public/data/tracks")
SCHEDULE_DIR = os.path.join(PROJECT_ROOT, "public/data/schedules")
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "public/data/station_progress.json")

# 線路設定
LINE_COLOR = "#c48c31"

# 轉乘站座標修正 - 使用軌道上的正確位置而非 TDX 共用座標
# TDX 會將轉乘站設為同一座標，導致軌道彎曲至其他線路
STATION_COORD_OVERRIDES = {
    'BR09': [121.543596, 25.033311],  # 大安 - 軌道經度，避免彎向紅線
    'BR11': [121.544034, 25.052044],  # 南京復興 - 軌道經度，避免彎向綠線
}


def parse_wkt_multilinestring(wkt: str) -> List[List[List[float]]]:
    """解析 WKT MULTILINESTRING 為分段座標陣列（返回多個分段）"""
    # 移除 MULTILINESTRING(( 和 ))
    match = re.search(r'MULTILINESTRING\s*\(\s*\((.*)\)\s*\)', wkt, re.DOTALL)
    if not match:
        raise ValueError("Invalid WKT format")

    content = match.group(1)

    # 分割多個線段 (以 ),( 分隔)
    segment_strs = re.split(r'\)\s*,\s*\(', content)

    segments = []
    for segment_str in segment_strs:
        coords = []
        # 解析每個座標點
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


def connect_segments_simple(segments: List[List[List[float]]]) -> List[List[float]]:
    """
    簡單連接所有分段（按端點連接）
    """
    if not segments:
        return []

    # 複製分段以避免修改原始資料
    remaining = [seg[:] for seg in segments]

    # 從第一個分段開始
    result = remaining.pop(0)[:]

    while remaining:
        # 找到與當前結果最接近的分段
        best_idx = -1
        best_dist = float('inf')
        should_reverse = False
        connect_to_end = True  # True = 連接到 result 尾端, False = 連接到 result 開頭

        current_start = result[0]
        current_end = result[-1]

        for i, seg in enumerate(remaining):
            seg_start = seg[0]
            seg_end = seg[-1]

            # 檢查四種連接方式
            # 1. result 尾端 -> seg 開頭
            d1 = euclidean_distance(current_end, seg_start)
            # 2. result 尾端 -> seg 尾端 (需反轉 seg)
            d2 = euclidean_distance(current_end, seg_end)
            # 3. result 開頭 -> seg 尾端
            d3 = euclidean_distance(current_start, seg_end)
            # 4. result 開頭 -> seg 開頭 (需反轉 seg)
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
                else:  # d4
                    should_reverse = True
                    connect_to_end = False

        if best_idx == -1:
            break

        seg = remaining.pop(best_idx)
        if should_reverse:
            seg = list(reversed(seg))

        # 連接分段
        if connect_to_end:
            # 跳過重複的起點
            if euclidean_distance(result[-1], seg[0]) < 0.0001:
                result.extend(seg[1:])
            else:
                result.extend(seg)
        else:
            # 連接到開頭
            if euclidean_distance(result[0], seg[-1]) < 0.0001:
                result = seg[:-1] + result
            else:
                result = seg + result

    return result


def euclidean_distance(p1: List[float], p2: List[float]) -> float:
    """計算 Euclidean 距離 (與 TrainEngine.ts 一致)"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def point_to_segment_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float, float]:
    """計算點到線段的最短距離，返回 (距離, 投影點x, 投影點y)"""
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return euclidean_distance([px, py], [x1, y1]), x1, y1

    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))

    proj_x = x1 + t * dx
    proj_y = y1 + t * dy

    return euclidean_distance([px, py], [proj_x, proj_y]), proj_x, proj_y


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
    """
    截斷軌道至指定的起終點範圍
    確保軌道只包含車站範圍內的座標
    """
    start_idx = find_nearest_point_index(start_coord, track_coords)
    end_idx = find_nearest_point_index(end_coord, track_coords)

    # 確保 start_idx < end_idx
    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx

    # 截斷並加入起終點座標
    truncated = track_coords[start_idx:end_idx + 1]

    # 確保起終點座標精確
    truncated[0] = start_coord[:]
    truncated[-1] = end_coord[:]

    return truncated


def find_best_segment(station_coord: List[float], track_coords: List[List[float]]) -> Tuple[int, float]:
    """找到車站應該插入的最佳線段位置"""
    min_dist = float('inf')
    best_idx = 0

    for i in range(len(track_coords) - 1):
        dist, _, _ = point_to_segment_distance(
            station_coord[0], station_coord[1],
            track_coords[i][0], track_coords[i][1],
            track_coords[i+1][0], track_coords[i+1][1]
        )
        if dist < min_dist:
            min_dist = dist
            best_idx = i

    return best_idx, min_dist


def calibrate_track(track_coords: List[List[float]], stations: List[Dict], station_order: List[str]) -> List[List[float]]:
    """
    校準軌道座標，確保軌道通過所有車站
    使用 calibrate_lines_v2.py 演算法
    """
    # 建立車站座標字典
    station_coords = {s['station_id']: s['coordinates'] for s in stations}

    # 複製軌道座標
    calibrated = [coord[:] for coord in track_coords]

    # 追蹤已插入的偏移量
    offset = 0

    for station_id in station_order:
        if station_id not in station_coords:
            print(f"  警告: 找不到車站 {station_id}")
            continue

        coord = station_coords[station_id]

        # 檢查是否需要覆蓋座標（轉乘站修正）
        if station_id in STATION_COORD_OVERRIDES:
            original = coord[:]
            coord = STATION_COORD_OVERRIDES[station_id]
            print(f"  {station_id} 座標覆蓋: {original} → {coord}")

        # 檢查是否已經存在
        found = False
        for tc in calibrated:
            if abs(tc[0] - coord[0]) < 0.00001 and abs(tc[1] - coord[1]) < 0.00001:
                found = True
                break

        if not found:
            # 找最佳插入位置
            best_idx, dist = find_best_segment(coord, calibrated)
            # 插入車站座標
            calibrated.insert(best_idx + 1, [coord[0], coord[1]])
            print(f"  插入 {station_id} 在索引 {best_idx + 1}, 距離: {dist:.6f}")

    return calibrated


def calculate_progress(track_coords: List[List[float]], stations: List[Dict], station_order: List[str]) -> Dict[str, float]:
    """計算車站在軌道上的進度值 (0-1)"""
    # 建立車站座標字典
    station_coords = {s['station_id']: s['coordinates'] for s in stations}

    # 計算總長度
    total_length = 0
    for i in range(len(track_coords) - 1):
        total_length += euclidean_distance(track_coords[i], track_coords[i+1])

    progress = {}

    for station_id in station_order:
        if station_id not in station_coords:
            continue

        coord = station_coords[station_id]

        # 檢查是否需要覆蓋座標（轉乘站修正）
        if station_id in STATION_COORD_OVERRIDES:
            coord = STATION_COORD_OVERRIDES[station_id]

        # 找到車站在軌道中的位置
        cumulative = 0
        for i in range(len(track_coords) - 1):
            # 檢查是否在這個線段上
            if abs(track_coords[i][0] - coord[0]) < 0.00001 and abs(track_coords[i][1] - coord[1]) < 0.00001:
                progress[station_id] = cumulative / total_length if total_length > 0 else 0
                break
            if abs(track_coords[i+1][0] - coord[0]) < 0.00001 and abs(track_coords[i+1][1] - coord[1]) < 0.00001:
                cumulative += euclidean_distance(track_coords[i], track_coords[i+1])
                progress[station_id] = cumulative / total_length if total_length > 0 else 0
                break
            cumulative += euclidean_distance(track_coords[i], track_coords[i+1])

        # 如果沒找到精確匹配，找最近的點
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


def generate_schedule(
    track_id: str,
    route_id: str,
    name: str,
    station_order: List[str],
    travel_times: List[Dict],
    is_weekday: bool = True
) -> Dict[str, Any]:
    """生成時刻表 JSON"""

    # 計算站間時間 (秒)
    # travel_times 是 BR24→BR01 方向，需要根據 station_order 調整
    station_times = {}  # station_id -> (arrival_offset, departure_offset)

    # 判斷方向
    if station_order[0] == 'BR01':
        # BR01→BR24 方向，需要反向使用 travel_times
        cumulative = 0
        station_times[station_order[0]] = (0, 25)  # 起點站停站 25 秒
        cumulative = 25

        # 反向遍歷 travel_times (因為原始是 BR24→BR01)
        reversed_times = list(reversed(travel_times))

        for i, tt in enumerate(reversed_times):
            # 這個 travel_time 是從 ToStation 到 FromStation 的 (反向後)
            # 原始: FromStationID → ToStationID (BR24→BR23, etc.)
            # 反向後: ToStationID → FromStationID 的反向
            from_station = tt['ToStationID']
            to_station = tt['FromStationID']
            run_time = tt['RunTime']
            stop_time = tt['StopTime'] if i < len(reversed_times) - 1 else 0

            # 到達時間
            arrival = cumulative + run_time
            departure = arrival + stop_time
            station_times[to_station] = (arrival, departure)
            cumulative = departure
    else:
        # BR24→BR01 方向，直接使用 travel_times
        cumulative = 0
        station_times[station_order[0]] = (0, 0)  # 起點站不停

        for i, tt in enumerate(travel_times):
            run_time = tt['RunTime']
            stop_time = tt['StopTime']
            to_station = tt['ToStationID']

            arrival = cumulative + run_time
            departure = arrival + stop_time
            station_times[to_station] = (arrival, departure)
            cumulative = departure

    # 總行駛時間
    total_travel_time = max(t[1] for t in station_times.values())

    # 生成發車時刻
    # 平日班距: 尖峰 2-4分, 離峰 4-10分, 深夜 12分
    # 假日班距: 全天 4-10分, 深夜 12分

    departures = []
    train_count = 0

    # 營運時間 06:00 - 24:00
    current_time = datetime.strptime("06:00:00", "%H:%M:%S")
    end_time = datetime.strptime("23:59:59", "%H:%M:%S")

    while current_time <= end_time:
        hour = current_time.hour + current_time.minute / 60

        # 決定班距
        if is_weekday:
            if 7 <= hour < 9 or 17 <= hour < 19.5:
                # 尖峰: 平均 3 分鐘
                headway = 3
            elif 23 <= hour:
                # 深夜: 12 分鐘
                headway = 12
            else:
                # 離峰: 平均 7 分鐘
                headway = 7
        else:
            if 23 <= hour:
                headway = 12
            else:
                headway = 7

        train_count += 1
        train_id = f"{track_id}-{train_count:03d}"

        # 建立站點時刻
        station_schedule = []
        for station_id in station_order:
            if station_id in station_times:
                arr, dep = station_times[station_id]
                station_schedule.append({
                    "station_id": station_id,
                    "arrival": arr,
                    "departure": dep
                })

        departures.append({
            "departure_time": current_time.strftime("%H:%M:%S"),
            "train_id": train_id,
            "origin_station": station_order[0],
            "total_travel_time": total_travel_time,
            "stations": station_schedule
        })

        current_time += timedelta(minutes=headway)

    return {
        "track_id": track_id,
        "route_id": route_id,
        "name": name,
        "origin": station_order[0],
        "destination": station_order[-1],
        "stations": station_order,
        "travel_time_minutes": total_travel_time // 60,
        "dwell_time_seconds": 25,
        "is_weekday": is_weekday,
        "departure_count": len(departures),
        "departures": departures
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
                "route_id": "BR-1",
                "direction": direction,
                "name": name,
                "start_station": start_station,
                "end_station": end_station,
                "travel_time": travel_time,
                "line_id": "BR"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            }
        }]
    }


def main():
    print("=" * 60)
    print("文湖線 (Brown Line) 建置腳本")
    print("=" * 60)

    # 確保輸出目錄存在
    os.makedirs(TRACK_DIR, exist_ok=True)
    os.makedirs(SCHEDULE_DIR, exist_ok=True)

    # ========== Task 2: 載入並轉換 WKT ==========
    print("\n[Task 2] 載入並轉換 WKT 軌道資料...")

    with open(SHAPE_FILE, 'r', encoding='utf-8') as f:
        shape_data = json.load(f)

    wkt = shape_data[0]['Geometry']
    segments = parse_wkt_multilinestring(wkt)
    print(f"  WKT 分段數: {len(segments)}")
    for i, seg in enumerate(segments):
        print(f"    分段 {i}: {len(seg)} 點, 起點 {seg[0]}, 終點 {seg[-1]}")

    # ========== 載入車站資料 ==========
    print("\n[載入] 車站資料...")

    with open(STATION_FILE, 'r', encoding='utf-8') as f:
        station_data = json.load(f)

    stations = []
    for s in station_data:
        stations.append({
            'station_id': s['StationID'],
            'name_zh': s['StationName']['Zh_tw'],
            'name_en': s['StationName']['En'],
            'coordinates': [s['StationPosition']['PositionLon'], s['StationPosition']['PositionLat']]
        })

    print(f"  車站數: {len(stations)}")

    # 車站順序 (BR01-BR24)
    station_order_0 = [f"BR{i:02d}" for i in range(1, 25)]  # BR01→BR24 (往南港展覽館)
    station_order_1 = list(reversed(station_order_0))       # BR24→BR01 (往動物園)

    # BR01 (動物園): 121.579501, 24.998205
    # BR24 (南港展覽館): 121.616861, 25.054919
    br01_coord = [121.579501, 24.998205]
    br24_coord = [121.616861, 25.054919]

    # 簡單連接分段
    print("\n[連接] 連接分段...")
    raw_coords = connect_segments_simple(segments)
    print(f"  連接後座標點數: {len(raw_coords)}")

    # 判斷連接後的方向
    dist_start_to_br01 = euclidean_distance(raw_coords[0], br01_coord)
    dist_start_to_br24 = euclidean_distance(raw_coords[0], br24_coord)

    print(f"  起點座標: {raw_coords[0]}")
    print(f"  終點座標: {raw_coords[-1]}")
    print(f"  起點到 BR01 距離: {dist_start_to_br01:.6f}")
    print(f"  起點到 BR24 距離: {dist_start_to_br24:.6f}")

    if dist_start_to_br24 < dist_start_to_br01:
        print("  連接後方向: BR24→BR01 (需反轉給 BR-1-0)")
        coords_for_dir0 = list(reversed(raw_coords))  # BR01→BR24
        coords_for_dir1 = raw_coords[:]                # BR24→BR01
    else:
        print("  連接後方向: BR01→BR24")
        coords_for_dir0 = raw_coords[:]
        coords_for_dir1 = list(reversed(raw_coords))

    # 截斷軌道至車站範圍 (移除延伸至機廠的軌道)
    print("\n[截斷] 截斷軌道至車站範圍...")
    coords_for_dir0 = truncate_track(coords_for_dir0, br01_coord, br24_coord)
    coords_for_dir1 = truncate_track(coords_for_dir1, br24_coord, br01_coord)
    print(f"  BR-1-0 截斷後座標點數: {len(coords_for_dir0)}")
    print(f"  BR-1-1 截斷後座標點數: {len(coords_for_dir1)}")

    # ========== 載入站間時間資料 ==========
    print("\n[載入] 站間時間資料...")

    with open(TRAVEL_TIME_FILE, 'r', encoding='utf-8') as f:
        travel_time_data = json.load(f)

    travel_times = travel_time_data[0]['TravelTimes']
    print(f"  站間區段數: {len(travel_times)}")

    # 計算總行駛時間
    total_run = sum(tt['RunTime'] for tt in travel_times)
    total_stop = sum(tt['StopTime'] for tt in travel_times)
    print(f"  總行駛時間: {total_run}秒 ({total_run//60}分{total_run%60}秒)")
    print(f"  總停站時間: {total_stop}秒 ({total_stop//60}分{total_stop%60}秒)")
    print(f"  全程時間: {(total_run+total_stop)//60}分{(total_run+total_stop)%60}秒")

    # ========== Task 3: 校準軌道座標 ==========
    print("\n[Task 3] 校準軌道座標...")

    print("\n  校準 BR-1-0 (動物園→南港展覽館)...")
    calibrated_0 = calibrate_track(coords_for_dir0, stations, station_order_0)
    print(f"  校準後座標點數: {len(calibrated_0)}")

    print("\n  校準 BR-1-1 (南港展覽館→動物園)...")
    calibrated_1 = calibrate_track(coords_for_dir1, stations, station_order_1)
    print(f"  校準後座標點數: {len(calibrated_1)}")

    # ========== Task 4: 建立軌道檔案 ==========
    print("\n[Task 4] 建立軌道 GeoJSON 檔案...")

    travel_time_minutes = (total_run + total_stop) // 60

    # BR-1-0: 動物園→南港展覽館
    track_0 = build_track_geojson(
        track_id="BR-1-0",
        coordinates=calibrated_0,
        direction=0,
        name="動物園 → 南港展覽館",
        start_station="BR01",
        end_station="BR24",
        travel_time=travel_time_minutes
    )

    track_0_path = os.path.join(TRACK_DIR, "BR-1-0.geojson")
    with open(track_0_path, 'w', encoding='utf-8') as f:
        json.dump(track_0, f, ensure_ascii=False, indent=2)
    print(f"  已建立: {track_0_path}")

    # BR-1-1: 南港展覽館→動物園
    track_1 = build_track_geojson(
        track_id="BR-1-1",
        coordinates=calibrated_1,
        direction=1,
        name="南港展覽館 → 動物園",
        start_station="BR24",
        end_station="BR01",
        travel_time=travel_time_minutes
    )

    track_1_path = os.path.join(TRACK_DIR, "BR-1-1.geojson")
    with open(track_1_path, 'w', encoding='utf-8') as f:
        json.dump(track_1, f, ensure_ascii=False, indent=2)
    print(f"  已建立: {track_1_path}")

    # ========== Task 5: 生成時刻表 ==========
    print("\n[Task 5] 生成時刻表...")

    # BR-1-0 時刻表 (平日)
    schedule_0 = generate_schedule(
        track_id="BR-1-0",
        route_id="BR-1",
        name="動物園 → 南港展覽館",
        station_order=station_order_0,
        travel_times=travel_times,
        is_weekday=True
    )

    schedule_0_path = os.path.join(SCHEDULE_DIR, "BR-1-0.json")
    with open(schedule_0_path, 'w', encoding='utf-8') as f:
        json.dump(schedule_0, f, ensure_ascii=False, indent=2)
    print(f"  已建立: {schedule_0_path}")
    print(f"    發車數: {schedule_0['departure_count']} 班")

    # BR-1-1 時刻表 (平日)
    schedule_1 = generate_schedule(
        track_id="BR-1-1",
        route_id="BR-1",
        name="南港展覽館 → 動物園",
        station_order=station_order_1,
        travel_times=travel_times,
        is_weekday=True
    )

    schedule_1_path = os.path.join(SCHEDULE_DIR, "BR-1-1.json")
    with open(schedule_1_path, 'w', encoding='utf-8') as f:
        json.dump(schedule_1, f, ensure_ascii=False, indent=2)
    print(f"  已建立: {schedule_1_path}")
    print(f"    發車數: {schedule_1['departure_count']} 班")

    # ========== Task 6: 計算並更新 station_progress.json ==========
    print("\n[Task 6] 計算車站進度映射...")

    # 計算進度
    progress_0 = calculate_progress(calibrated_0, stations, station_order_0)
    progress_1 = calculate_progress(calibrated_1, stations, station_order_1)

    print(f"\n  BR-1-0 進度:")
    for sid in station_order_0[:3]:
        print(f"    {sid}: {progress_0.get(sid, 'N/A'):.6f}")
    print(f"    ...")
    for sid in station_order_0[-3:]:
        print(f"    {sid}: {progress_0.get(sid, 'N/A'):.6f}")

    print(f"\n  BR-1-1 進度:")
    for sid in station_order_1[:3]:
        print(f"    {sid}: {progress_1.get(sid, 'N/A'):.6f}")
    print(f"    ...")
    for sid in station_order_1[-3:]:
        print(f"    {sid}: {progress_1.get(sid, 'N/A'):.6f}")

    # 載入現有 station_progress.json
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            all_progress = json.load(f)
    else:
        all_progress = {}

    # 新增 BR 軌道進度
    all_progress['BR-1-0'] = progress_0
    all_progress['BR-1-1'] = progress_1

    # 儲存
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)
    print(f"\n  已更新: {PROGRESS_FILE}")

    # ========== 完成 ==========
    print("\n" + "=" * 60)
    print("文湖線建置完成!")
    print("=" * 60)
    print("\n建立的檔案:")
    print(f"  - {track_0_path}")
    print(f"  - {track_1_path}")
    print(f"  - {schedule_0_path}")
    print(f"  - {schedule_1_path}")
    print(f"  - {PROGRESS_FILE} (已更新)")
    print("\n下一步:")
    print("  1. 更新 src/hooks/useData.ts")
    print("  2. 更新 src/App.tsx")
    print("  3. 執行 npm run dev 測試")


if __name__ == '__main__':
    main()
