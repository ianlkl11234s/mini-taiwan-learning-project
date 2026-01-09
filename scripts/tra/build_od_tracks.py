#!/usr/bin/env python3
"""
build_od_tracks.py - 建立 O-D 專屬軌道

為每個獨特的起迄組合建立專屬軌道，解決軌道切換時的抖動問題。
先以 NW (內灣線) 和 LJ (六家線) 為驗證對象。
"""

import json
import os
import math
from typing import List, Tuple, Dict, Optional
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
    # 軌道段列表: [(track_id, start_station_id, end_station_id), ...]
    segments: List[Tuple[str, str, str]]


# ============================================================
# NW/LJ O-D 路由定義
# ============================================================

# 車站 ID 對照
STATIONS = {
    '1210': '新竹',
    '1190': '北新竹',
    '1191': '千甲',
    '1192': '新莊',
    '1193': '竹中',
    '1194': '六家',
    '1201': '上員',
    '1202': '榮華',
    '1203': '竹東',
    '1204': '橫山',
    '1205': '九讚頭',
    '1206': '合興',
    '1207': '富貴',
    '1208': '內灣',
    # 平溪線
    '7330': '三貂嶺',
    '7331': '大華',
    '7332': '十分',
    '7333': '望古',
    '7334': '嶺腳',
    '7335': '平溪',
    '7336': '菁桐',
    # 集集線
    '3430': '二水',
    '3431': '源泉',
    '3432': '濁水',
    '3433': '龍泉',
    '3434': '集集',
    '3435': '水里',
    '3436': '車埕',
    # 成追線
    '3350': '成功',
    '2260': '追分',
    # 沙崙線 (含縱貫線共線區段)
    '4220': '臺南',
    '4250': '保安',
    '4260': '仁德',
    '4270': '中洲',
    '4271': '長榮大學',
    '4272': '沙崙',
}

# NW 線車站順序 (從新竹方向)
NW_STATIONS = ['1210', '1190', '1191', '1192', '1193', '1201', '1202', '1203', '1204', '1205', '1206', '1207', '1208']
# 新竹 -> 北新竹 -> 千甲 -> 新莊 -> 竹中 -> 上員 -> 榮華 -> 竹東 -> 橫山 -> 九讚頭 -> 合興 -> 富貴 -> 內灣

# LJ 線車站順序 (從新竹方向，與 NW 線共線到竹中)
LJ_STATIONS = ['1210', '1190', '1191', '1192', '1193', '1194']
# 新竹 -> 北新竹 -> 千甲 -> 新莊 -> 竹中 -> 六家

# PX 線車站順序 (從三貂嶺到菁桐)
PX_STATIONS = ['7330', '7331', '7332', '7333', '7334', '7335', '7336']
# 三貂嶺 -> 大華 -> 十分 -> 望古 -> 嶺腳 -> 平溪 -> 菁桐

# JJ 線車站順序 (從二水到車埕)
JJ_STATIONS = ['3430', '3431', '3432', '3433', '3434', '3435', '3436']
# 二水 -> 源泉 -> 濁水 -> 龍泉 -> 集集 -> 水里 -> 車埕

# CZ 線車站順序 (從成功到追分)
CZ_STATIONS = ['3350', '2260']
# 成功 -> 追分

# SH 線車站順序 (從臺南到沙崙，包含縱貫線共線區段)
SH_STATIONS = ['4220', '4250', '4260', '4270', '4271', '4272']
# 臺南 -> 保安 -> 仁德 -> 中洲 -> 長榮大學 -> 沙崙

# O-D 路由定義
OD_ROUTES = [
    # NW 線 O-D
    ODRoute(
        od_track_id='NW-HC-NB',
        origin_station_id='1210',
        destination_station_id='1208',
        origin_name='新竹',
        destination_name='內灣',
        segments=[
            ('WL-N-0', '1210', '1190'),  # 新竹→北新竹 (縱貫線)
            ('NW-0', '1190', '1208'),    # 北新竹→內灣 (內灣線)
        ]
    ),
    ODRoute(
        od_track_id='NW-NB-HC',
        origin_station_id='1208',
        destination_station_id='1210',
        origin_name='內灣',
        destination_name='新竹',
        segments=[
            ('NW-1', '1208', '1190'),    # 內灣→北新竹 (內灣線)
            ('WL-N-1', '1190', '1210'),  # 北新竹→新竹 (縱貫線)
        ]
    ),
    ODRoute(
        od_track_id='NW-JJ-NB',
        origin_station_id='1193',
        destination_station_id='1208',
        origin_name='竹中',
        destination_name='內灣',
        segments=[
            ('NW-0', '1193', '1208'),    # 竹中→內灣
        ]
    ),
    ODRoute(
        od_track_id='NW-NB-JJ',
        origin_station_id='1208',
        destination_station_id='1193',
        origin_name='內灣',
        destination_name='竹中',
        segments=[
            ('NW-1', '1208', '1193'),    # 內灣→竹中
        ]
    ),
    ODRoute(
        od_track_id='NW-HC-JD',
        origin_station_id='1210',
        destination_station_id='1203',
        origin_name='新竹',
        destination_name='竹東',
        segments=[
            ('WL-N-0', '1210', '1190'),  # 新竹→北新竹
            ('NW-0', '1190', '1203'),    # 北新竹→竹東
        ]
    ),
    # LJ 線 O-D
    ODRoute(
        od_track_id='LJ-HC-LJ',
        origin_station_id='1210',
        destination_station_id='1194',
        origin_name='新竹',
        destination_name='六家',
        segments=[
            ('WL-N-0', '1210', '1190'),  # 新竹→北新竹
            ('NW-0', '1190', '1193'),    # 北新竹→竹中 (使用內灣線高精度)
            ('LJ-0', '1193', '1194'),    # 竹中→六家
        ]
    ),
    ODRoute(
        od_track_id='LJ-LJ-HC',
        origin_station_id='1194',
        destination_station_id='1210',
        origin_name='六家',
        destination_name='新竹',
        segments=[
            ('LJ-1', '1194', '1193'),    # 六家→竹中
            ('NW-1', '1193', '1190'),    # 竹中→北新竹 (使用內灣線高精度)
            ('WL-N-1', '1190', '1210'),  # 北新竹→新竹
        ]
    ),
    # PX 線 O-D (平溪線)
    ODRoute(
        od_track_id='PX-SD-JT',
        origin_station_id='7330',
        destination_station_id='7336',
        origin_name='三貂嶺',
        destination_name='菁桐',
        segments=[
            ('PX-0', '7330', '7336'),    # 三貂嶺→菁桐 (全線)
        ]
    ),
    ODRoute(
        od_track_id='PX-JT-SD',
        origin_station_id='7336',
        destination_station_id='7330',
        origin_name='菁桐',
        destination_name='三貂嶺',
        segments=[
            ('PX-1', '7336', '7330'),    # 菁桐→三貂嶺 (全線)
        ]
    ),
    # JJ 線 O-D (集集線)
    ODRoute(
        od_track_id='JJ-ES-CT',
        origin_station_id='3430',
        destination_station_id='3436',
        origin_name='二水',
        destination_name='車埕',
        segments=[
            ('JJ-0', '3430', '3436'),    # 二水→車埕 (全線)
        ]
    ),
    ODRoute(
        od_track_id='JJ-CT-ES',
        origin_station_id='3436',
        destination_station_id='3430',
        origin_name='車埕',
        destination_name='二水',
        segments=[
            ('JJ-1', '3436', '3430'),    # 車埕→二水 (全線)
        ]
    ),
    # CZ 線 O-D (成追線)
    ODRoute(
        od_track_id='CZ-CG-ZF',
        origin_station_id='3350',
        destination_station_id='2260',
        origin_name='成功',
        destination_name='追分',
        segments=[
            ('CZ-0', '3350', '2260'),    # 成功→追分 (全線)
        ]
    ),
    ODRoute(
        od_track_id='CZ-ZF-CG',
        origin_station_id='2260',
        destination_station_id='3350',
        origin_name='追分',
        destination_name='成功',
        segments=[
            ('CZ-1', '2260', '3350'),    # 追分→成功 (全線)
        ]
    ),
    # SH 線 O-D (沙崙線)
    # SH-0 實際方向是沙崙→中洲 (座標分析確認)
    # SH-1 實際方向是中洲→沙崙
    # WL-S1-0 是北上 (高雄→彰化)，WL-S1-1 是南下 (彰化→高雄)
    ODRoute(
        od_track_id='SH-TN-SL',
        origin_station_id='4220',
        destination_station_id='4272',
        origin_name='臺南',
        destination_name='沙崙',
        segments=[
            ('WL-S1-1', '4220', '4270'),  # 臺南→中洲 (縱貫線南下)
            ('SH-1', '4270', '4272'),     # 中洲→沙崙 (沙崙線)
        ]
    ),
    ODRoute(
        od_track_id='SH-SL-TN',
        origin_station_id='4272',
        destination_station_id='4220',
        origin_name='沙崙',
        destination_name='臺南',
        segments=[
            ('SH-0', '4272', '4270'),     # 沙崙→中洲 (沙崙線)
            ('WL-S1-0', '4270', '4220'),  # 中洲→臺南 (縱貫線北上)
        ]
    ),
]


def haversine_distance(coord1: Coord, coord2: Coord) -> float:
    """計算兩點間的 Haversine 距離 (公尺)"""
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    R = 6371000  # 地球半徑 (公尺)

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def euclidean_distance(coord1: Coord, coord2: Coord) -> float:
    """計算兩點間的歐幾里得距離"""
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)


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
        d = math.sqrt(dx * dx + dy * dy)  # 歐幾里得距離（度）
        distances.append(distances[-1] + d)
    return distances


def extract_segment(
    coords: CoordList,
    start_coord: Coord,
    end_coord: Coord,
    start_station_name: str,
    end_station_name: str
) -> CoordList:
    """從軌道座標中提取指定段落"""
    start_idx = find_closest_point_index(coords, start_coord)
    end_idx = find_closest_point_index(coords, end_coord)

    print(f"    提取段落: {start_station_name}(idx={start_idx}) → {end_station_name}(idx={end_idx})")

    if start_idx <= end_idx:
        segment = coords[start_idx:end_idx+1]
    else:
        segment = coords[end_idx:start_idx+1][::-1]

    # 確保起終點座標準確
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
                    # 避免重複點
                    if tuple(segment[0]) != coords[-1]:
                        coords.append(tuple(segment[0]))
                coords.extend([tuple(c) for c in segment[1:]] if coords else [tuple(c) for c in segment])
        else:
            print(f"警告: 未知幾何類型 {geom['type']} for {track_id}")
            continue

        tracks[track_id] = coords
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

    # 修正集集線車站座標 - 從軌道推算的近似座標
    # 由於原始 stations_snapped.geojson 中部分車站座標錯誤，這裡手動修正
    jj_station_corrections = {
        '3430': (120.62169, 23.81130),   # 二水 - 軌道起點附近
        '3431': (120.64211, 23.79852),   # 源泉 - 保持原值
        '3432': (120.65500, 23.80016),   # 濁水 - 軌道中段
        '3433': (120.66550, 23.80690),   # 龍泉 - 軌道中段
        '3434': (120.68000, 23.81900),   # 集集 - 軌道中段
        '3435': (120.69200, 23.82800),   # 水里 - 軌道中段
        '3436': (120.70141, 23.83409),   # 車埕 - 軌道終點
    }
    for station_id, coords in jj_station_corrections.items():
        if station_id in stations:
            stations[station_id] = Station(
                station_id=station_id,
                name=stations[station_id].name,
                coordinates=coords
            )
            print(f"修正 {stations[station_id].name} ({station_id}) 座標: {coords}")

    return stations


def build_od_track(
    route: ODRoute,
    tracks: Dict[str, CoordList],
    stations: Dict[str, Station]
) -> Tuple[CoordList, Dict[str, float]]:
    """建立單一 O-D 專屬軌道"""
    print(f"\n建立 O-D 軌道: {route.od_track_id} ({route.origin_name} → {route.destination_name})")

    combined_coords: CoordList = []
    station_positions: Dict[str, int] = {}  # station_id -> 在合併座標中的索引

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

        # 記錄車站位置
        if seg_idx == 0:
            station_positions[start_station_id] = 0
        else:
            station_positions[start_station_id] = len(combined_coords) - 1

        # 合併座標
        if combined_coords:
            # 跳過第一個點（與上一段的終點重複）
            combined_coords.extend(segment[1:])
        else:
            combined_coords.extend(segment)

        station_positions[end_station_id] = len(combined_coords) - 1

    print(f"  合併後座標點數: {len(combined_coords)}")

    # 計算各站進度值
    cum_distances = calculate_cumulative_distances(combined_coords)
    total_length = cum_distances[-1]

    station_progress: Dict[str, float] = {}
    for station_id, idx in station_positions.items():
        progress = cum_distances[idx] / total_length if total_length > 0 else 0
        station_progress[station_id] = round(progress, 6)
        station_name = stations[station_id].name if station_id in stations else station_id
        print(f"    {station_name} ({station_id}): 進度 {progress:.4f}")

    # 補充中間車站
    # 根據 O-D 軌道，找出所有應該經過的車站
    all_station_ids = get_intermediate_stations(route, stations)
    for station_id in all_station_ids:
        if station_id in station_progress:
            continue
        if station_id not in stations:
            continue

        station = stations[station_id]
        # 找到最接近的點
        idx = find_closest_point_index(combined_coords, station.coordinates)
        progress = cum_distances[idx] / total_length if total_length > 0 else 0
        station_progress[station_id] = round(progress, 6)
        print(f"    {station.name} ({station_id}): 進度 {progress:.4f} (補充)")

    return combined_coords, station_progress


def get_intermediate_stations(route: ODRoute, stations: Dict[str, Station]) -> List[str]:
    """取得路由經過的所有車站 ID"""
    # 根據路由類型決定車站列表
    if route.od_track_id.startswith('NW-'):
        # 內灣線
        origin_idx = NW_STATIONS.index(route.origin_station_id) if route.origin_station_id in NW_STATIONS else -1
        dest_idx = NW_STATIONS.index(route.destination_station_id) if route.destination_station_id in NW_STATIONS else -1

        if origin_idx >= 0 and dest_idx >= 0:
            if origin_idx <= dest_idx:
                return NW_STATIONS[origin_idx:dest_idx+1]
            else:
                return NW_STATIONS[dest_idx:origin_idx+1][::-1]

    elif route.od_track_id.startswith('LJ-'):
        # 六家線
        origin_idx = LJ_STATIONS.index(route.origin_station_id) if route.origin_station_id in LJ_STATIONS else -1
        dest_idx = LJ_STATIONS.index(route.destination_station_id) if route.destination_station_id in LJ_STATIONS else -1

        if origin_idx >= 0 and dest_idx >= 0:
            if origin_idx <= dest_idx:
                return LJ_STATIONS[origin_idx:dest_idx+1]
            else:
                return LJ_STATIONS[dest_idx:origin_idx+1][::-1]

    elif route.od_track_id.startswith('PX-'):
        # 平溪線
        origin_idx = PX_STATIONS.index(route.origin_station_id) if route.origin_station_id in PX_STATIONS else -1
        dest_idx = PX_STATIONS.index(route.destination_station_id) if route.destination_station_id in PX_STATIONS else -1

        if origin_idx >= 0 and dest_idx >= 0:
            if origin_idx <= dest_idx:
                return PX_STATIONS[origin_idx:dest_idx+1]
            else:
                return PX_STATIONS[dest_idx:origin_idx+1][::-1]

    elif route.od_track_id.startswith('JJ-'):
        # 集集線
        origin_idx = JJ_STATIONS.index(route.origin_station_id) if route.origin_station_id in JJ_STATIONS else -1
        dest_idx = JJ_STATIONS.index(route.destination_station_id) if route.destination_station_id in JJ_STATIONS else -1

        if origin_idx >= 0 and dest_idx >= 0:
            if origin_idx <= dest_idx:
                return JJ_STATIONS[origin_idx:dest_idx+1]
            else:
                return JJ_STATIONS[dest_idx:origin_idx+1][::-1]

    elif route.od_track_id.startswith('CZ-'):
        # 成追線
        origin_idx = CZ_STATIONS.index(route.origin_station_id) if route.origin_station_id in CZ_STATIONS else -1
        dest_idx = CZ_STATIONS.index(route.destination_station_id) if route.destination_station_id in CZ_STATIONS else -1

        if origin_idx >= 0 and dest_idx >= 0:
            if origin_idx <= dest_idx:
                return CZ_STATIONS[origin_idx:dest_idx+1]
            else:
                return CZ_STATIONS[dest_idx:origin_idx+1][::-1]

    elif route.od_track_id.startswith('SH-'):
        # 沙崙線
        origin_idx = SH_STATIONS.index(route.origin_station_id) if route.origin_station_id in SH_STATIONS else -1
        dest_idx = SH_STATIONS.index(route.destination_station_id) if route.destination_station_id in SH_STATIONS else -1

        if origin_idx >= 0 and dest_idx >= 0:
            if origin_idx <= dest_idx:
                return SH_STATIONS[origin_idx:dest_idx+1]
            else:
                return SH_STATIONS[dest_idx:origin_idx+1][::-1]

    return [route.origin_station_id, route.destination_station_id]


def save_od_track(
    route: ODRoute,
    coords: CoordList,
    station_progress: Dict[str, float],
    stations: Dict[str, Station]
):
    """儲存 O-D 軌道到 GeoJSON"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 建立 GeoJSON
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


def main():
    print("=" * 60)
    print("建立 O-D 專屬軌道")
    print("=" * 60)

    # 載入資料
    tracks = load_tracks()
    stations = load_stations()

    # 收集所有 O-D 軌道的進度資料
    all_station_progress: Dict[str, Dict[str, float]] = {}

    # 建立各 O-D 軌道
    for route in OD_ROUTES:
        coords, station_progress = build_od_track(route, tracks, stations)
        if coords:
            save_od_track(route, coords, station_progress, stations)
            all_station_progress[route.od_track_id] = station_progress

    # 儲存統一的進度映射表
    progress_path = os.path.join(OUTPUT_DIR, 'od_station_progress.json')
    with open(progress_path, 'w', encoding='utf-8') as f:
        json.dump(all_station_progress, f, ensure_ascii=False, indent=2)
    print(f"\n儲存進度映射表: {progress_path}")

    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
