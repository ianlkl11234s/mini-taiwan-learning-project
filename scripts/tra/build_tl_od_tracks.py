#!/usr/bin/env python3
"""
build_tl_od_tracks.py - 建立 TL (臺東線) O-D 專屬軌道

臺東線車站順序（花蓮→臺東方向）:
7000 花蓮 → 6250 吉安 → ... → 6000 臺東

資料來源：
- tracks_official/TD-0.geojson (TDX 使用 TD 代碼)
- stations_snapped.geojson
"""

import json
import os
import math
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OFFICIAL_DIR = os.path.join(DATA_DIR, 'tracks_official')
TRACKS_GOLDEN_DIR = os.path.join(DATA_DIR, 'tracks_golden')
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


# ============================================================
# TL 臺東線車站定義
# ============================================================

STATIONS = {
    # TL 臺東線 (花蓮 → 臺東)
    '7000': '花蓮',
    '6250': '吉安',
    '6240': '志學',
    '6230': '平和',
    '6220': '壽豐',
    '6210': '豐田',
    '6200': '林榮新光',
    '6190': '南平',
    '6180': '鳳林',
    '6170': '萬榮',
    '6160': '光復',
    '6150': '大富',
    '6140': '富源',
    '6130': '瑞穗',
    '6120': '三民',
    '6110': '玉里',
    '6100': '東里',
    '6090': '東竹',
    '6080': '富里',
    '6070': '池上',
    '6060': '海端',
    '6050': '關山',
    '6040': '瑞和',
    '6030': '瑞源',
    '6020': '鹿野',
    '6010': '山里',
    '6000': '臺東',
}

# TL 臺東線車站順序 (花蓮 → 臺東)
TL_STATIONS = [
    '7000',  # 花蓮
    '6250',  # 吉安
    '6240',  # 志學
    '6230',  # 平和
    '6220',  # 壽豐
    '6210',  # 豐田
    '6200',  # 林榮新光
    '6190',  # 南平
    '6180',  # 鳳林
    '6170',  # 萬榮
    '6160',  # 光復
    '6150',  # 大富
    '6140',  # 富源
    '6130',  # 瑞穗
    '6120',  # 三民
    '6110',  # 玉里
    '6100',  # 東里
    '6090',  # 東竹
    '6080',  # 富里
    '6070',  # 池上
    '6060',  # 海端
    '6050',  # 關山
    '6040',  # 瑞和
    '6030',  # 瑞源
    '6020',  # 鹿野
    '6010',  # 山里
    '6000',  # 臺東
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


def analyze_segment(segment: List[List[float]], idx: int) -> Dict[str, Any]:
    """分析單一段落的起點、終點和長度"""
    start = tuple(segment[0])
    end = tuple(segment[-1])
    length = 0
    for i in range(len(segment) - 1):
        length += euclidean_distance(tuple(segment[i]), tuple(segment[i+1]))

    return {
        'index': idx,
        'start': start,
        'end': end,
        'start_lat': start[1],
        'end_lat': end[1],
        'length': length,
        'points': len(segment),
        'coords': segment
    }


def find_best_bidirectional_connection(
    chain_start: Tuple[float, float],
    chain_end: Tuple[float, float],
    remaining: List[Dict],
    threshold: float = 0.02
) -> Tuple[int, bool, str]:
    """
    找出與鏈的任一端最接近的段落

    Returns:
        (index, reversed, position): 段落索引、是否需要反轉、連接位置 ('start' or 'end')
    """
    best_idx = -1
    best_dist = float('inf')
    best_reversed = False
    best_position = 'end'

    for i, seg in enumerate(remaining):
        # 檢查連接到鏈的末端
        dist_end_to_start = euclidean_distance(chain_end, seg['start'])
        if dist_end_to_start < best_dist:
            best_dist = dist_end_to_start
            best_idx = i
            best_reversed = False
            best_position = 'end'

        dist_end_to_end = euclidean_distance(chain_end, seg['end'])
        if dist_end_to_end < best_dist:
            best_dist = dist_end_to_end
            best_idx = i
            best_reversed = True
            best_position = 'end'

        # 檢查連接到鏈的起始端
        dist_start_to_end = euclidean_distance(chain_start, seg['end'])
        if dist_start_to_end < best_dist:
            best_dist = dist_start_to_end
            best_idx = i
            best_reversed = False
            best_position = 'start'

        dist_start_to_start = euclidean_distance(chain_start, seg['start'])
        if dist_start_to_start < best_dist:
            best_dist = dist_start_to_start
            best_idx = i
            best_reversed = True
            best_position = 'start'

    if best_dist > threshold:
        print(f"  Warning: nearest segment distance {best_dist:.6f} deg (~{best_dist * 111:.1f} km)")

    return best_idx, best_reversed, best_position


def reorder_segments(segments: List[List[List[float]]], direction: int) -> CoordList:
    """
    重新排序 MultiLineString 段落，確保連續

    Args:
        segments: MultiLineString 的 coordinates
        direction: 0=南下(花蓮→臺東), 1=北上(臺東→花蓮)

    Returns:
        合併後的單一 LineString coordinates
    """
    if len(segments) <= 1:
        return [tuple(c) for c in segments[0]] if segments else []

    # 分析所有段落
    analyzed = [analyze_segment(seg, i) for i, seg in enumerate(segments)]

    print(f"\n  Original segment analysis:")
    for seg in analyzed:
        print(f"    Segment {seg['index']}: "
              f"start_lat={seg['start_lat']:.4f}, "
              f"end_lat={seg['end_lat']:.4f}, "
              f"points={seg['points']}")

    # 找最長的段落作為種子
    start_seg = max(analyzed, key=lambda s: s['points'])
    print(f"\n  Seed segment: {start_seg['index']} (longest, {start_seg['points']} points)")

    # 建立排序後的座標鏈
    ordered_coords = [list(c) for c in start_seg['coords']]
    remaining = [s for s in analyzed if s['index'] != start_seg['index']]

    while remaining:
        chain_start = tuple(ordered_coords[0])
        chain_end = tuple(ordered_coords[-1])

        best_idx, reversed_seg, position = find_best_bidirectional_connection(
            chain_start, chain_end, remaining
        )

        if best_idx < 0:
            print(f"  Cannot find connecting segment! {len(remaining)} segments remaining")
            break

        next_seg = remaining.pop(best_idx)

        if reversed_seg:
            coords_to_add = list(reversed(next_seg['coords']))
        else:
            coords_to_add = list(next_seg['coords'])

        if position == 'end':
            if euclidean_distance(tuple(coords_to_add[0]), chain_end) < 0.0001:
                coords_to_add = coords_to_add[1:]
            ordered_coords.extend(coords_to_add)
        else:
            if euclidean_distance(tuple(coords_to_add[-1]), chain_start) < 0.0001:
                coords_to_add = coords_to_add[:-1]
            ordered_coords = coords_to_add + ordered_coords

        print(f"  Connected segment {next_seg['index']} -> {position}{'(reversed)' if reversed_seg else ''}")

    # 根據方向決定是否需要反轉
    start_lat = ordered_coords[0][1]
    end_lat = ordered_coords[-1][1]

    if direction == 0:
        # 南下：應該從北到南（緯度遞減）
        if start_lat < end_lat:
            print(f"\n  Reversing track to match direction 0 (southbound)")
            ordered_coords = list(reversed(ordered_coords))
    else:
        # 北上：應該從南到北（緯度遞增）
        if start_lat > end_lat:
            print(f"\n  Reversing track to match direction 1 (northbound)")
            ordered_coords = list(reversed(ordered_coords))

    return [tuple(c) for c in ordered_coords]


def calculate_cumulative_distances(coords: CoordList) -> List[float]:
    """計算累積距離 - 使用歐幾里得距離以匹配 TypeScript 引擎"""
    distances = [0.0]
    for i in range(1, len(coords)):
        dx = coords[i][0] - coords[i-1][0]
        dy = coords[i][1] - coords[i-1][1]
        d = math.sqrt(dx * dx + dy * dy)
        distances.append(distances[-1] + d)
    return distances


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


def load_td_track(direction: int) -> Optional[CoordList]:
    """載入並處理 TD 軌道資料"""
    track_file = os.path.join(TRACKS_OFFICIAL_DIR, f'TD-{direction}.geojson')

    if not os.path.exists(track_file):
        print(f"Track file not found: {track_file}")
        return None

    with open(track_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for feature in data.get('features', []):
        geom = feature.get('geometry', {})

        if geom.get('type') == 'LineString':
            return [tuple(c) for c in geom['coordinates']]
        elif geom.get('type') == 'MultiLineString':
            print(f"Processing MultiLineString with {len(geom['coordinates'])} segments")
            return reorder_segments(geom['coordinates'], direction)

    return None


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

    return stations


def build_od_track(
    od_track_id: str,
    origin_id: str,
    dest_id: str,
    coords: CoordList,
    stations: Dict[str, Station],
    station_order: List[str]
) -> Tuple[CoordList, Dict[str, float]]:
    """建立單一 O-D 專屬軌道"""
    print(f"\nBuilding O-D track: {od_track_id}")

    origin = stations.get(origin_id)
    dest = stations.get(dest_id)

    if not origin or not dest:
        print(f"  Error: Station not found ({origin_id} or {dest_id})")
        return [], {}

    print(f"  {origin.name} ({origin_id}) -> {dest.name} ({dest_id})")

    # 找到起終點在軌道上的位置
    origin_idx = find_closest_point_index(coords, origin.coordinates)
    dest_idx = find_closest_point_index(coords, dest.coordinates)

    print(f"  Origin index: {origin_idx}, Destination index: {dest_idx}")

    # 擷取軌道段落
    if origin_idx <= dest_idx:
        segment_coords = coords[origin_idx:dest_idx+1]
    else:
        segment_coords = coords[dest_idx:origin_idx+1][::-1]

    # 確保起終點座標準確
    segment_coords = list(segment_coords)
    segment_coords[0] = origin.coordinates
    segment_coords[-1] = dest.coordinates

    print(f"  Segment points: {len(segment_coords)}")

    # 計算各站進度值
    cum_distances = calculate_cumulative_distances(segment_coords)
    total_length = cum_distances[-1]

    station_progress: Dict[str, float] = {}

    # 篩選在此 O-D 範圍內的車站
    try:
        origin_order_idx = station_order.index(origin_id)
        dest_order_idx = station_order.index(dest_id)
    except ValueError:
        print(f"  Error: Station not in order list")
        return segment_coords, station_progress

    if origin_order_idx <= dest_order_idx:
        route_stations = station_order[origin_order_idx:dest_order_idx+1]
    else:
        route_stations = station_order[dest_order_idx:origin_order_idx+1][::-1]

    # 計算每站的進度
    for station_id in route_stations:
        if station_id not in stations:
            continue
        station = stations[station_id]
        idx = find_closest_point_index(segment_coords, station.coordinates)
        progress = cum_distances[idx] / total_length if total_length > 0 else 0
        station_progress[station_id] = round(progress, 6)

    # 印出所有車站進度（按進度排序）
    sorted_progress = sorted(station_progress.items(), key=lambda x: x[1])
    print(f"\n  Station progress:")
    for station_id, progress in sorted_progress:
        station_name = stations[station_id].name if station_id in stations else station_id
        print(f"    {station_name} ({station_id}): {progress:.4f}")

    return segment_coords, station_progress


def verify_station_alignment(
    coords: CoordList,
    station_progress: Dict[str, float],
    stations: Dict[str, Station]
):
    """驗證車站進度值的準確性"""
    print("\n  Verifying station alignment:")
    cum_distances = calculate_cumulative_distances(coords)
    total_length = cum_distances[-1]

    errors = []
    for station_id, progress in station_progress.items():
        if station_id not in stations:
            continue

        station = stations[station_id]
        target_distance = progress * total_length

        # 找到對應的座標點
        calc_coord = coords[-1]
        for i in range(len(cum_distances) - 1):
            if cum_distances[i] <= target_distance <= cum_distances[i + 1]:
                t = (target_distance - cum_distances[i]) / (cum_distances[i + 1] - cum_distances[i]) if cum_distances[i + 1] != cum_distances[i] else 0
                calc_lng = coords[i][0] + t * (coords[i + 1][0] - coords[i][0])
                calc_lat = coords[i][1] + t * (coords[i + 1][1] - coords[i][1])
                calc_coord = (calc_lng, calc_lat)
                break

        error_m = haversine_distance(station.coordinates, calc_coord)
        errors.append((station.name, station_id, error_m))

        if error_m > 100:
            print(f"    Warning: {station.name} ({station_id}): error {error_m:.1f}m (> 100m)")

    if errors:
        avg_error = sum(e[2] for e in errors) / len(errors)
        max_error = max(e[2] for e in errors)
        print(f"  Average error: {avg_error:.1f}m, Max error: {max_error:.1f}m")


def save_golden_track(coords: CoordList, direction: int):
    """儲存 Golden Track"""
    os.makedirs(TRACKS_GOLDEN_DIR, exist_ok=True)

    feature = {
        "type": "Feature",
        "properties": {
            "track_id": f"TL-{direction}",
            "line_id": "TL",
            "direction": direction,
            "name": f"臺東線 ({'花蓮→臺東' if direction == 0 else '臺東→花蓮'})",
            "origin": "花蓮" if direction == 0 else "臺東",
            "destination": "臺東" if direction == 0 else "花蓮",
            "source": "TD"
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

    output_path = os.path.join(TRACKS_GOLDEN_DIR, f"TL-{direction}.geojson")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"Saved Golden Track: {output_path}")


def save_od_track(
    od_track_id: str,
    coords: CoordList,
    station_progress: Dict[str, float],
    stations: Dict[str, Station],
    origin_id: str,
    dest_id: str
):
    """儲存 O-D 軌道到 GeoJSON"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    origin = stations.get(origin_id)
    dest = stations.get(dest_id)

    feature = {
        "type": "Feature",
        "properties": {
            "track_id": od_track_id,
            "origin": origin.name if origin else origin_id,
            "destination": dest.name if dest else dest_id,
            "origin_station_id": origin_id,
            "destination_station_id": dest_id,
            "source_tracks": ["TL"],
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

    output_path = os.path.join(OUTPUT_DIR, f"{od_track_id}.geojson")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"  Saved: {output_path}")


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

    print(f"\nUpdated station progress file: {progress_path}")
    print(f"  Total {len(existing)} O-D tracks")


def main():
    print("=" * 60)
    print("Building TL (Taitung Line) O-D Tracks")
    print("=" * 60)

    # 載入車站資料
    stations = load_stations()
    print(f"Loaded {len(stations)} stations")

    # 載入並處理 TD 軌道
    print("\n" + "-" * 60)
    print("Processing TD-0 (southbound: Hualien -> Taitung)")
    print("-" * 60)
    coords_0 = load_td_track(0)

    if not coords_0:
        print("Failed to load TD-0 track")
        return

    print(f"Loaded {len(coords_0)} points")

    # 檢查軌道連續性
    print("\nChecking track continuity:")
    jumps = []
    for i in range(len(coords_0) - 1):
        dist = euclidean_distance(coords_0[i], coords_0[i+1])
        if dist > 0.005:  # > ~500m
            jumps.append((i, dist))

    if jumps:
        print(f"  Found {len(jumps)} jumps > 500m")
        for idx, dist in jumps[:5]:
            print(f"    Index {idx}: {dist*111:.1f} km")
    else:
        print("  Track is continuous")

    # 驗證起終點
    print(f"\nTrack endpoints:")
    hualien = stations.get('7000')
    taitung = stations.get('6000')

    if hualien:
        start_dist = haversine_distance(coords_0[0], hualien.coordinates)
        print(f"  Start to Hualien: {start_dist:.0f}m")

    if taitung:
        end_dist = haversine_distance(coords_0[-1], taitung.coordinates)
        print(f"  End to Taitung: {end_dist:.0f}m")

    # 儲存 Golden Track
    print("\n" + "-" * 60)
    print("Saving Golden Tracks")
    print("-" * 60)
    save_golden_track(coords_0, 0)

    # 反向軌道
    coords_1 = list(reversed(coords_0))
    save_golden_track(coords_1, 1)

    # 建立 O-D 軌道
    print("\n" + "-" * 60)
    print("Building O-D Tracks")
    print("-" * 60)

    all_station_progress: Dict[str, Dict[str, float]] = {}

    # TL-HL-TT: 花蓮 → 臺東
    od_coords, od_progress = build_od_track(
        'TL-HL-TT',
        '7000',  # 花蓮
        '6000',  # 臺東
        coords_0,
        stations,
        TL_STATIONS
    )
    if od_coords:
        verify_station_alignment(od_coords, od_progress, stations)
        save_od_track('TL-HL-TT', od_coords, od_progress, stations, '7000', '6000')
        all_station_progress['TL-HL-TT'] = od_progress

    # TL-TT-HL: 臺東 → 花蓮
    od_coords, od_progress = build_od_track(
        'TL-TT-HL',
        '6000',  # 臺東
        '7000',  # 花蓮
        coords_1,
        stations,
        list(reversed(TL_STATIONS))
    )
    if od_coords:
        verify_station_alignment(od_coords, od_progress, stations)
        save_od_track('TL-TT-HL', od_coords, od_progress, stations, '6000', '7000')
        all_station_progress['TL-TT-HL'] = od_progress

    # 更新進度映射表
    update_station_progress_file(all_station_progress)

    print("\n" + "=" * 60)
    print("Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Create test schedule: schedules_od/TL-0.json, TL-1.json")
    print("2. Update useTraData.ts to load TL tracks")
    print("3. Update TraTrainEngine.ts for TL mapping")
    print("4. Update TRACKS_STATUS.md")


if __name__ == '__main__':
    main()
