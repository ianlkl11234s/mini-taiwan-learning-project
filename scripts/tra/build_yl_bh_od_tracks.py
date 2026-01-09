#!/usr/bin/env python3
"""
build_yl_bh_od_tracks.py - 建立 YL (宜蘭線) 和 BH (北迴線) O-D 專屬軌道

Phase 2.1 實作：環島東線第一批
"""

import json
import os
import math
from typing import List, Tuple, Dict
from dataclasses import dataclass

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_DIR = os.path.join(DATA_DIR, 'tracks_official')
OUTPUT_DIR = os.path.join(DATA_DIR, 'tracks_od')

# 座標類型
Coord = Tuple[float, float]
CoordList = List[Coord]


@dataclass
class Station:
    """車站資料"""
    station_id: str
    name: str
    coordinates: Coord


@dataclass
class ODRoute:
    """O-D 路由定義"""
    od_track_id: str
    origin_station_id: str
    destination_station_id: str
    origin_name: str
    destination_name: str
    segments: List[Tuple[str, str, str]]  # [(track_id, start_station_id, end_station_id), ...]


# ============================================================
# YL/BH 車站定義
# ============================================================

STATIONS = {
    # 西部幹線北段 (與 YL 共線)
    '1000': '臺北',
    '0990': '松山',
    '0980': '南港',
    '0970': '汐科',
    '0960': '汐止',
    '0950': '五堵',
    '0940': '百福',
    '0930': '七堵',
    '0920': '八堵',

    # YL 宜蘭線 (八堵 → 蘇澳)
    '7390': '暖暖',
    '7380': '四腳亭',
    '7360': '瑞芳',
    '7350': '猴硐',
    '7330': '三貂嶺',  # PX 平溪線分岔點
    '7320': '牡丹',
    '7310': '雙溪',
    '7300': '貢寮',
    '7290': '福隆',
    '7280': '石城',
    '7270': '大里',
    '7260': '大溪',
    '7250': '龜山',
    '7240': '外澳',
    '7230': '頭城',
    '7220': '頂埔',
    '7210': '礁溪',
    '7200': '四城',
    '7190': '宜蘭',
    '7180': '二結',
    '7170': '中里',
    '7160': '羅東',
    '7150': '冬山',
    '7140': '新馬',
    '7130': '蘇澳新',  # BH 北迴線分岔點
    '7120': '蘇澳',

    # BH 北迴線 (蘇澳新 → 花蓮)
    '7110': '永樂',
    '7100': '東澳',
    '7090': '南澳',
    '7080': '武塔',
    '7070': '漢本',
    '7060': '和平',
    '7050': '和仁',
    '7040': '崇德',
    '7030': '新城',
    '7020': '景美',
    '7010': '北埔',
    '7000': '花蓮',
}

# YL 宜蘭線車站順序 (八堵 → 蘇澳)
YL_STATIONS = [
    '0920',  # 八堵
    '7390',  # 暖暖
    '7380',  # 四腳亭
    '7360',  # 瑞芳
    '7350',  # 猴硐
    '7330',  # 三貂嶺
    '7320',  # 牡丹
    '7310',  # 雙溪
    '7300',  # 貢寮
    '7290',  # 福隆
    '7280',  # 石城
    '7270',  # 大里
    '7260',  # 大溪
    '7250',  # 龜山
    '7240',  # 外澳
    '7230',  # 頭城
    '7220',  # 頂埔
    '7210',  # 礁溪
    '7200',  # 四城
    '7190',  # 宜蘭
    '7180',  # 二結
    '7170',  # 中里
    '7160',  # 羅東
    '7150',  # 冬山
    '7140',  # 新馬
    '7130',  # 蘇澳新
    '7120',  # 蘇澳
]

# BH 北迴線車站順序 (蘇澳新 → 花蓮)
BH_STATIONS = [
    '7130',  # 蘇澳新
    '7110',  # 永樂
    '7100',  # 東澳
    '7090',  # 南澳
    '7080',  # 武塔
    '7070',  # 漢本
    '7060',  # 和平
    '7050',  # 和仁
    '7040',  # 崇德
    '7030',  # 新城
    '7020',  # 景美
    '7010',  # 北埔
    '7000',  # 花蓮
]

# 臺北到八堵的車站順序 (WL-N 西部幹線)
WL_N_STATIONS = [
    '1000',  # 臺北
    '0990',  # 松山
    '0980',  # 南港
    '0970',  # 汐科
    '0960',  # 汐止
    '0950',  # 五堵
    '0940',  # 百福
    '0930',  # 七堵
    '0920',  # 八堵
]

# ============================================================
# O-D 路由定義 (按實際列車運行區間)
# ============================================================

OD_ROUTES = [
    # 臺北 → 花蓮 (跨線: WL-N + YL + BH)
    ODRoute(
        od_track_id='YL-TP-HL',
        origin_station_id='1000',
        destination_station_id='7000',
        origin_name='臺北',
        destination_name='花蓮',
        segments=[
            ('WL-N-0', '1000', '0920'),  # 臺北→八堵 (西部幹線)
            ('YL-0', '0920', '7130'),    # 八堵→蘇澳新 (宜蘭線)
            ('BH-0', '7130', '7000'),    # 蘇澳新→花蓮 (北迴線)
        ]
    ),
    # 花蓮 → 臺北 (跨線: BH + YL + WL-N)
    ODRoute(
        od_track_id='YL-HL-TP',
        origin_station_id='7000',
        destination_station_id='1000',
        origin_name='花蓮',
        destination_name='臺北',
        segments=[
            ('BH-1', '7000', '7130'),    # 花蓮→蘇澳新 (北迴線)
            ('YL-1', '7130', '0920'),    # 蘇澳新→八堵 (宜蘭線)
            ('WL-N-1', '0920', '1000'),  # 八堵→臺北 (西部幹線)
        ]
    ),
    # 臺北 → 宜蘭 (WL-N + YL)
    ODRoute(
        od_track_id='YL-TP-YL',
        origin_station_id='1000',
        destination_station_id='7190',
        origin_name='臺北',
        destination_name='宜蘭',
        segments=[
            ('WL-N-0', '1000', '0920'),  # 臺北→八堵
            ('YL-0', '0920', '7190'),    # 八堵→宜蘭
        ]
    ),
    # 宜蘭 → 臺北
    ODRoute(
        od_track_id='YL-YL-TP',
        origin_station_id='7190',
        destination_station_id='1000',
        origin_name='宜蘭',
        destination_name='臺北',
        segments=[
            ('YL-1', '7190', '0920'),    # 宜蘭→八堵
            ('WL-N-1', '0920', '1000'),  # 八堵→臺北
        ]
    ),
    # 臺北 → 蘇澳 (WL-N + YL 全線)
    ODRoute(
        od_track_id='YL-TP-SA',
        origin_station_id='1000',
        destination_station_id='7120',
        origin_name='臺北',
        destination_name='蘇澳',
        segments=[
            ('WL-N-0', '1000', '0920'),  # 臺北→八堵
            ('YL-0', '0920', '7120'),    # 八堵→蘇澳
        ]
    ),
    # 蘇澳 → 臺北
    ODRoute(
        od_track_id='YL-SA-TP',
        origin_station_id='7120',
        destination_station_id='1000',
        origin_name='蘇澳',
        destination_name='臺北',
        segments=[
            ('YL-1', '7120', '0920'),    # 蘇澳→八堵
            ('WL-N-1', '0920', '1000'),  # 八堵→臺北
        ]
    ),
    # 花蓮 → 蘇澳新 (BH 單線)
    ODRoute(
        od_track_id='BH-HL-SX',
        origin_station_id='7000',
        destination_station_id='7130',
        origin_name='花蓮',
        destination_name='蘇澳新',
        segments=[
            ('BH-1', '7000', '7130'),    # 花蓮→蘇澳新
        ]
    ),
    # 蘇澳新 → 花蓮 (BH 單線)
    ODRoute(
        od_track_id='BH-SX-HL',
        origin_station_id='7130',
        destination_station_id='7000',
        origin_name='蘇澳新',
        destination_name='花蓮',
        segments=[
            ('BH-0', '7130', '7000'),    # 蘇澳新→花蓮
        ]
    ),
]


def euclidean_distance(coord1: Coord, coord2: Coord) -> float:
    """計算兩點間的歐幾里得距離 (度為單位)"""
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)


def haversine_distance(coord1: Coord, coord2: Coord) -> float:
    """計算兩點間的 Haversine 距離 (公尺) - 僅用於驗證"""
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def find_closest_point_index(coords: CoordList, target: Coord) -> int:
    """找到座標列表中最接近目標的點索引"""
    min_dist = float('inf')
    min_idx = 0
    for i, coord in enumerate(coords):
        dist = euclidean_distance(coord, target)
        if dist < min_dist:
            min_dist = dist
            min_idx = i
    return min_idx


def calculate_cumulative_distances(coords: CoordList) -> List[float]:
    """計算累積距離 - 使用歐幾里得距離以匹配 TypeScript 引擎"""
    distances = [0.0]
    for i in range(1, len(coords)):
        dx = coords[i][0] - coords[i-1][0]
        dy = coords[i][1] - coords[i-1][1]
        d = math.sqrt(dx * dx + dy * dy)
        distances.append(distances[-1] + d)
    return distances


def extract_segment(
    coords: CoordList,
    start_coord: Coord,
    end_coord: Coord,
    start_name: str,
    end_name: str
) -> CoordList:
    """從軌道座標中提取指定段落"""
    start_idx = find_closest_point_index(coords, start_coord)
    end_idx = find_closest_point_index(coords, end_coord)

    print(f"    提取段落: {start_name}(idx={start_idx}) → {end_name}(idx={end_idx})")

    if start_idx <= end_idx:
        segment = coords[start_idx:end_idx+1]
    else:
        segment = coords[end_idx:start_idx+1][::-1]

    # 確保起終點座標準確
    segment = list(segment)
    segment[0] = start_coord
    segment[-1] = end_coord

    return segment


def load_tracks() -> Dict[str, CoordList]:
    """載入所有軌道資料"""
    tracks = {}
    all_tracks_path = os.path.join(TRACKS_DIR, 'all_tracks.geojson')

    with open(all_tracks_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for feature in data['features']:
        track_id = feature['properties']['track_id']
        geom = feature['geometry']

        if geom['type'] == 'LineString':
            coords = [tuple(c) for c in geom['coordinates']]
        elif geom['type'] == 'MultiLineString':
            # 合併所有段落為一條連續線
            coords = []
            for segment in geom['coordinates']:
                if coords:
                    if tuple(segment[0]) != coords[-1]:
                        coords.append(tuple(segment[0]))
                coords.extend([tuple(c) for c in segment[1:]] if coords else [tuple(c) for c in segment])
        else:
            print(f"警告: 未知幾何類型 {geom['type']} for {track_id}")
            continue

        tracks[track_id] = coords

        # 只印出 YL/BH 相關軌道
        if track_id.startswith(('YL', 'BH', 'WL-N')):
            print(f"載入軌道 {track_id}: {len(coords)} 點")

    return tracks


def load_stations() -> Dict[str, Station]:
    """載入車站資料"""
    stations = {}
    stations_path = os.path.join(DATA_DIR, 'stations_snapped.geojson')

    with open(stations_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for feature in data['features']:
        props = feature['properties']
        station_id = props['station_id']
        stations[station_id] = Station(
            station_id=station_id,
            name=props.get('name') or props.get('station_name', ''),
            coordinates=tuple(feature['geometry']['coordinates'])
        )

    print(f"載入 {len(stations)} 個車站")
    return stations


def get_all_stations_for_route(route: ODRoute) -> List[str]:
    """取得路由經過的所有車站 ID"""
    all_stations = []

    for track_id, start_id, end_id in route.segments:
        if track_id.startswith('WL-N'):
            station_list = WL_N_STATIONS
        elif track_id.startswith('YL'):
            station_list = YL_STATIONS
        elif track_id.startswith('BH'):
            station_list = BH_STATIONS
        else:
            continue

        try:
            start_idx = station_list.index(start_id)
            end_idx = station_list.index(end_id)
        except ValueError:
            continue

        if start_idx <= end_idx:
            segment_stations = station_list[start_idx:end_idx+1]
        else:
            segment_stations = station_list[end_idx:start_idx+1][::-1]

        # 合併時跳過重複的接合站
        if all_stations and segment_stations and segment_stations[0] == all_stations[-1]:
            all_stations.extend(segment_stations[1:])
        else:
            all_stations.extend(segment_stations)

    return all_stations


def build_od_track(
    route: ODRoute,
    tracks: Dict[str, CoordList],
    stations: Dict[str, Station]
) -> Tuple[CoordList, Dict[str, float]]:
    """建立單一 O-D 專屬軌道"""
    print(f"\n建立 O-D 軌道: {route.od_track_id} ({route.origin_name} → {route.destination_name})")

    combined_coords: CoordList = []
    station_positions: Dict[str, int] = {}

    for seg_idx, (track_id, start_station_id, end_station_id) in enumerate(route.segments):
        print(f"  段落 {seg_idx + 1}: {track_id} ({start_station_id} → {end_station_id})")

        if track_id not in tracks:
            print(f"    錯誤: 軌道 {track_id} 不存在")
            continue

        track_coords = tracks[track_id]
        start_station = stations.get(start_station_id)
        end_station = stations.get(end_station_id)

        if not start_station:
            print(f"    錯誤: 車站 {start_station_id} 不存在")
            continue
        if not end_station:
            print(f"    錯誤: 車站 {end_station_id} 不存在")
            continue

        segment = extract_segment(
            track_coords,
            start_station.coordinates,
            end_station.coordinates,
            start_station.name,
            end_station.name
        )

        print(f"    段落座標點數: {len(segment)}")

        # 記錄起點車站位置
        if seg_idx == 0:
            station_positions[start_station_id] = 0
        else:
            station_positions[start_station_id] = len(combined_coords) - 1

        # 合併座標
        if combined_coords:
            combined_coords.extend(segment[1:])
        else:
            combined_coords.extend(segment)

        station_positions[end_station_id] = len(combined_coords) - 1

    print(f"  合併後座標點數: {len(combined_coords)}")

    # 計算各站進度值
    cum_distances = calculate_cumulative_distances(combined_coords)
    total_length = cum_distances[-1]

    station_progress: Dict[str, float] = {}

    # 先處理已記錄位置的車站
    for station_id, idx in station_positions.items():
        progress = cum_distances[idx] / total_length if total_length > 0 else 0
        station_progress[station_id] = round(progress, 6)

    # 補充中間車站
    all_station_ids = get_all_stations_for_route(route)
    for station_id in all_station_ids:
        if station_id in station_progress:
            continue
        if station_id not in stations:
            continue

        station = stations[station_id]
        idx = find_closest_point_index(combined_coords, station.coordinates)
        progress = cum_distances[idx] / total_length if total_length > 0 else 0
        station_progress[station_id] = round(progress, 6)

    # 印出所有車站進度（按進度排序）
    sorted_progress = sorted(station_progress.items(), key=lambda x: x[1])
    for station_id, progress in sorted_progress:
        station_name = stations[station_id].name if station_id in stations else station_id
        print(f"    {station_name} ({station_id}): 進度 {progress:.4f}")

    return combined_coords, station_progress


def verify_station_alignment(
    combined_coords: CoordList,
    station_progress: Dict[str, float],
    stations: Dict[str, Station]
):
    """驗證車站進度值的準確性"""
    print("\n  驗證車站對齊:")
    cum_distances = calculate_cumulative_distances(combined_coords)
    total_length = cum_distances[-1]

    errors = []
    for station_id, progress in station_progress.items():
        if station_id not in stations:
            continue

        station = stations[station_id]

        # 根據進度值計算位置
        target_distance = progress * total_length

        # 找到對應的座標點
        for i in range(len(cum_distances) - 1):
            if cum_distances[i] <= target_distance <= cum_distances[i + 1]:
                t = (target_distance - cum_distances[i]) / (cum_distances[i + 1] - cum_distances[i]) if cum_distances[i + 1] != cum_distances[i] else 0
                calc_lng = combined_coords[i][0] + t * (combined_coords[i + 1][0] - combined_coords[i][0])
                calc_lat = combined_coords[i][1] + t * (combined_coords[i + 1][1] - combined_coords[i][1])
                break
        else:
            calc_lng, calc_lat = combined_coords[-1]

        # 計算誤差（公尺）
        error_m = haversine_distance(station.coordinates, (calc_lng, calc_lat))
        errors.append((station.name, station_id, error_m))

        if error_m > 50:
            print(f"    ⚠️ {station.name} ({station_id}): 誤差 {error_m:.1f}m (超過 50m)")

    avg_error = sum(e[2] for e in errors) / len(errors) if errors else 0
    max_error = max(e[2] for e in errors) if errors else 0
    print(f"  平均誤差: {avg_error:.1f}m, 最大誤差: {max_error:.1f}m")


def save_od_track(
    route: ODRoute,
    coords: CoordList,
    station_progress: Dict[str, float],
    stations: Dict[str, Station]
):
    """儲存 O-D 軌道到 GeoJSON"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    feature = {
        "type": "Feature",
        "properties": {
            "track_id": route.od_track_id,
            "origin": route.origin_name,
            "destination": route.destination_name,
            "origin_station_id": route.origin_station_id,
            "destination_station_id": route.destination_station_id,
            "source_tracks": [seg[0] for seg in route.segments],
            "stations": [
                {
                    "station_id": sid,
                    "name": stations[sid].name if sid in stations else sid,
                    "progress": progress
                }
                for sid, progress in sorted(station_progress.items(), key=lambda x: x[1])
            ]
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[c[0], c[1]] for c in coords]
        }
    }

    geojson = {
        "type": "FeatureCollection",
        "features": [feature]
    }

    output_path = os.path.join(OUTPUT_DIR, f"{route.od_track_id}.geojson")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"  儲存: {output_path}")


def update_station_progress_file(all_progress: Dict[str, Dict[str, float]]):
    """更新統一的進度映射表"""
    progress_path = os.path.join(OUTPUT_DIR, 'od_station_progress.json')

    # 讀取現有資料
    existing = {}
    if os.path.exists(progress_path):
        with open(progress_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)

    # 合併新資料
    existing.update(all_progress)

    # 儲存
    with open(progress_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"\n更新進度映射表: {progress_path}")
    print(f"  總共 {len(existing)} 條 O-D 軌道")


def main():
    print("=" * 60)
    print("建立 YL/BH O-D 專屬軌道 (Phase 2.1)")
    print("=" * 60)

    # 載入資料
    tracks = load_tracks()
    stations = load_stations()

    # 檢查必要軌道
    required_tracks = ['WL-N-0', 'WL-N-1', 'YL-0', 'YL-1', 'BH-0', 'BH-1']
    missing = [t for t in required_tracks if t not in tracks]
    if missing:
        print(f"\n錯誤: 缺少軌道 {missing}")
        return

    # 收集所有 O-D 軌道的進度資料
    all_station_progress: Dict[str, Dict[str, float]] = {}

    # 建立各 O-D 軌道
    for route in OD_ROUTES:
        coords, station_progress = build_od_track(route, tracks, stations)
        if coords:
            verify_station_alignment(coords, station_progress, stations)
            save_od_track(route, coords, station_progress, stations)
            all_station_progress[route.od_track_id] = station_progress

    # 更新統一的進度映射表
    update_station_progress_file(all_station_progress)

    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
