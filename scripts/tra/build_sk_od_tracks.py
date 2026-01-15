#!/usr/bin/env python3
"""
build_sk_od_tracks.py - 建立 SK (南迴線) O-D 專屬軌道

SK 南迴線路線：臺東 <-> 新左營
合併軌道來源：
- NH (南迴線): 臺東 ↔ 枋寮
- PT (屏東線): 枋寮 ↔ 高雄
- WL-S1 (縱貫線南段): 高雄 ↔ 新左營

車站順序 (臺東→新左營方向):
6000 臺東 → 5240 康樂 → 5230 知本 → 5220 太麻里 → 5210 金崙 → 5200 瀧溪 →
5190 大武 → 5170 枋野 → 5160 枋山 → 5140 內獅 → 5130 加祿 → 5120 枋寮 →
5110 東海 → 5100 佳冬 → 5090 林邊 → 5080 鎮安 → 5070 南州 → 5060 崁頂 →
5050 潮州 → 5040 竹田 → 5030 西勢 → 5020 麟洛 → 5010 歸來 → 5000 屏東 →
4470 六塊厝 → 4460 九曲堂 → 4450 後庄 → 4440 鳳山 → 4400 高雄 → 4340 新左營
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
# SK 南迴線車站定義
# ============================================================

STATIONS = {
    # 臺東線終點
    '6000': '臺東',

    # 南迴線 (臺東→枋寮)
    '5240': '康樂',
    '5230': '知本',
    '5220': '太麻里',
    '5210': '金崙',
    '5200': '瀧溪',
    '5190': '大武',
    '5170': '枋野',
    '5160': '枋山',
    '5140': '內獅',
    '5130': '加祿',
    '5120': '枋寮',

    # 屏東線 (枋寮→高雄)
    '5110': '東海',
    '5100': '佳冬',
    '5090': '林邊',
    '5080': '鎮安',
    '5070': '南州',
    '5060': '崁頂',
    '5050': '潮州',
    '5040': '竹田',
    '5030': '西勢',
    '5020': '麟洛',
    '5010': '歸來',
    '5000': '屏東',
    '4470': '六塊厝',
    '4460': '九曲堂',
    '4450': '後庄',
    '4440': '鳳山',
    '4400': '高雄',

    # 縱貫線 (高雄→新左營)
    '4340': '新左營',
}

# SK 南迴線車站順序 (臺東 → 新左營)
SK_STATIONS = [
    '6000',  # 臺東
    '5240',  # 康樂
    '5230',  # 知本
    '5220',  # 太麻里
    '5210',  # 金崙
    '5200',  # 瀧溪
    '5190',  # 大武
    '5170',  # 枋野
    '5160',  # 枋山
    '5140',  # 內獅
    '5130',  # 加祿
    '5120',  # 枋寮
    '5110',  # 東海
    '5100',  # 佳冬
    '5090',  # 林邊
    '5080',  # 鎮安
    '5070',  # 南州
    '5060',  # 崁頂
    '5050',  # 潮州
    '5040',  # 竹田
    '5030',  # 西勢
    '5020',  # 麟洛
    '5010',  # 歸來
    '5000',  # 屏東
    '4470',  # 六塊厝
    '4460',  # 九曲堂
    '4450',  # 後庄
    '4440',  # 鳳山
    '4400',  # 高雄
    '4340',  # 新左營
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
        'start_lng': start[0],
        'start_lat': start[1],
        'end_lng': end[0],
        'end_lat': end[1],
        'length': length,
        'points': len(segment),
        'coords': segment
    }


def find_best_connection(
    chain_end: Tuple[float, float],
    remaining: List[Dict],
    threshold: float = 0.02
) -> Tuple[int, bool]:
    """
    找出與鏈末端最接近的段落

    Returns:
        (index, reversed): 段落索引、是否需要反轉
    """
    best_idx = -1
    best_dist = float('inf')
    best_reversed = False

    for i, seg in enumerate(remaining):
        dist_to_start = euclidean_distance(chain_end, seg['start'])
        if dist_to_start < best_dist:
            best_dist = dist_to_start
            best_idx = i
            best_reversed = False

        dist_to_end = euclidean_distance(chain_end, seg['end'])
        if dist_to_end < best_dist:
            best_dist = dist_to_end
            best_idx = i
            best_reversed = True

    if best_dist > threshold:
        print(f"    Warning: nearest segment distance {best_dist:.6f} deg (~{best_dist * 111:.1f} km)")

    return best_idx, best_reversed


def reorder_multilinestring_by_geography(
    segments: List[List[List[float]]],
    target_start: Coord,
    target_end: Coord
) -> CoordList:
    """
    根據地理位置重新排序 MultiLineString 段落

    使用目標起終點來決定整體方向，然後根據經緯度排序段落

    Args:
        segments: MultiLineString 的 coordinates
        target_start: 期望的起點座標
        target_end: 期望的終點座標

    Returns:
        合併後的單一 LineString coordinates
    """
    if len(segments) <= 1:
        if segments:
            coords = [tuple(c) for c in segments[0]]
            # 檢查是否需要反轉
            if euclidean_distance(coords[0], target_start) > euclidean_distance(coords[-1], target_start):
                coords = list(reversed(coords))
            return coords
        return []

    # 分析所有段落
    analyzed = [analyze_segment(seg, i) for i, seg in enumerate(segments)]

    print(f"  Original segment analysis ({len(segments)} segments):")
    for seg in analyzed:
        print(f"    Segment {seg['index']}: "
              f"start=[{seg['start_lng']:.4f}, {seg['start_lat']:.4f}], "
              f"end=[{seg['end_lng']:.4f}, {seg['end_lat']:.4f}], "
              f"points={seg['points']}")

    # 計算整體方向 (主要是東西向還是南北向)
    lng_diff = abs(target_end[0] - target_start[0])
    lat_diff = abs(target_end[1] - target_start[1])

    if lng_diff > lat_diff:
        # 主要是東西向，用經度排序
        sort_key = 'start_lng'
        reverse_sort = target_start[0] > target_end[0]  # 如果起點經度大於終點，需要反向排序
        print(f"  Sorting by longitude (E-W route), reverse={reverse_sort}")
    else:
        # 主要是南北向，用緯度排序
        sort_key = 'start_lat'
        reverse_sort = target_start[1] > target_end[1]  # 如果起點緯度大於終點，需要反向排序
        print(f"  Sorting by latitude (N-S route), reverse={reverse_sort}")

    # 先對每個段落調整方向，確保與整體方向一致
    for seg in analyzed:
        if lng_diff > lat_diff:
            # 東西向路線：段落應該從東到西或從西到東
            if (not reverse_sort and seg['start_lng'] > seg['end_lng']) or \
               (reverse_sort and seg['start_lng'] < seg['end_lng']):
                # 段落方向相反，需要反轉
                seg['coords'] = list(reversed(seg['coords']))
                seg['start'], seg['end'] = seg['end'], seg['start']
                seg['start_lng'], seg['end_lng'] = seg['end_lng'], seg['start_lng']
                seg['start_lat'], seg['end_lat'] = seg['end_lat'], seg['start_lat']
        else:
            # 南北向路線
            if (not reverse_sort and seg['start_lat'] > seg['end_lat']) or \
               (reverse_sort and seg['start_lat'] < seg['end_lat']):
                seg['coords'] = list(reversed(seg['coords']))
                seg['start'], seg['end'] = seg['end'], seg['start']
                seg['start_lng'], seg['end_lng'] = seg['end_lng'], seg['start_lng']
                seg['start_lat'], seg['end_lat'] = seg['end_lat'], seg['start_lat']

    # 按照位置排序
    analyzed.sort(key=lambda s: s[sort_key], reverse=reverse_sort)

    print(f"  Sorted segment order:")
    for seg in analyzed:
        print(f"    Segment {seg['index']}: "
              f"start=[{seg['start_lng']:.4f}, {seg['start_lat']:.4f}], "
              f"end=[{seg['end_lng']:.4f}, {seg['end_lat']:.4f}]")

    # 合併所有段落
    merged_coords = []
    for i, seg in enumerate(analyzed):
        if i == 0:
            merged_coords.extend([list(c) for c in seg['coords']])
        else:
            prev_end = tuple(merged_coords[-1])
            curr_start = tuple(seg['coords'][0])
            gap = euclidean_distance(prev_end, curr_start)

            if gap > 0.001:  # > ~100m
                print(f"    Gap between segments: {gap:.6f} deg (~{gap * 111:.1f} km)")

            # 避免重複點
            if gap < 0.0001:
                merged_coords.extend([list(c) for c in seg['coords'][1:]])
            else:
                merged_coords.extend([list(c) for c in seg['coords']])

    print(f"  Merged {len(merged_coords)} points")
    return [tuple(c) for c in merged_coords]


def reorder_multilinestring(segments: List[List[List[float]]], target_start: Coord = None) -> CoordList:
    """
    重新排序 MultiLineString 段落，確保連續

    Args:
        segments: MultiLineString 的 coordinates
        target_start: 期望的起點座標（如果提供）

    Returns:
        合併後的單一 LineString coordinates
    """
    if len(segments) <= 1:
        return [tuple(c) for c in segments[0]] if segments else []

    # 分析所有段落
    analyzed = [analyze_segment(seg, i) for i, seg in enumerate(segments)]

    print(f"  Original segment analysis ({len(segments)} segments):")
    for seg in analyzed:
        print(f"    Segment {seg['index']}: "
              f"start=[{seg['start_lng']:.4f}, {seg['start_lat']:.4f}], "
              f"end=[{seg['end_lng']:.4f}, {seg['end_lat']:.4f}], "
              f"points={seg['points']}")

    # 如果有目標起點，找最接近的段落作為種子
    if target_start:
        best_start_dist = float('inf')
        best_start_seg = None
        best_reversed = False

        for seg in analyzed:
            dist_to_start = euclidean_distance(target_start, seg['start'])
            if dist_to_start < best_start_dist:
                best_start_dist = dist_to_start
                best_start_seg = seg
                best_reversed = False

            dist_to_end = euclidean_distance(target_start, seg['end'])
            if dist_to_end < best_start_dist:
                best_start_dist = dist_to_end
                best_start_seg = seg
                best_reversed = True

        start_seg = best_start_seg
        if best_reversed:
            ordered_coords = list(reversed([list(c) for c in start_seg['coords']]))
        else:
            ordered_coords = [list(c) for c in start_seg['coords']]

        print(f"  Seed segment: {start_seg['index']} (closest to target start, reversed={best_reversed})")
    else:
        # 找最長的段落作為種子
        start_seg = max(analyzed, key=lambda s: s['points'])
        ordered_coords = [list(c) for c in start_seg['coords']]
        print(f"  Seed segment: {start_seg['index']} (longest, {start_seg['points']} points)")

    remaining = [s for s in analyzed if s['index'] != start_seg['index']]

    while remaining:
        chain_end = tuple(ordered_coords[-1])

        best_idx, reversed_seg = find_best_connection(chain_end, remaining)

        if best_idx < 0:
            print(f"    Cannot find connecting segment! {len(remaining)} segments remaining")
            break

        next_seg = remaining.pop(best_idx)

        if reversed_seg:
            coords_to_add = list(reversed(next_seg['coords']))
        else:
            coords_to_add = list(next_seg['coords'])

        # 避免重複第一個點
        if euclidean_distance(tuple(coords_to_add[0]), chain_end) < 0.0001:
            coords_to_add = coords_to_add[1:]

        ordered_coords.extend(coords_to_add)

        print(f"    Connected segment {next_seg['index']}{'(reversed)' if reversed_seg else ''}")

    return [tuple(c) for c in ordered_coords]


def load_track(track_id: str) -> Tuple[Optional[CoordList], Optional[str]]:
    """載入軌道資料"""
    track_file = os.path.join(TRACKS_OFFICIAL_DIR, f'{track_id}.geojson')

    if not os.path.exists(track_file):
        print(f"  Track file not found: {track_file}")
        return None, None

    with open(track_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for feature in data.get('features', []):
        geom = feature.get('geometry', {})
        geom_type = geom.get('type')

        if geom_type == 'LineString':
            return [tuple(c) for c in geom['coordinates']], geom_type
        elif geom_type == 'MultiLineString':
            return geom['coordinates'], geom_type

    return None, None


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


def extract_segment_between_stations(
    coords: CoordList,
    stations: Dict[str, Station],
    start_station_id: str,
    end_station_id: str
) -> CoordList:
    """擷取兩站之間的軌道段落"""
    start_station = stations.get(start_station_id)
    end_station = stations.get(end_station_id)

    if not start_station or not end_station:
        return []

    start_idx = find_closest_point_index(coords, start_station.coordinates)
    end_idx = find_closest_point_index(coords, end_station.coordinates)

    if start_idx <= end_idx:
        return coords[start_idx:end_idx+1]
    else:
        return coords[end_idx:start_idx+1][::-1]


def build_sk_od_track(
    stations: Dict[str, Station],
    nh_coords: CoordList,
    pt_coords: CoordList,
    wl_coords: CoordList
) -> Tuple[CoordList, Dict[str, float]]:
    """
    建立 SK O-D 軌道 (臺東→新左營)

    合併順序：
    1. NH: 臺東 → 枋寮
    2. PT: 枋寮 → 高雄
    3. WL-S1: 高雄 → 新左營
    """
    print("\n" + "=" * 60)
    print("Building SK O-D Track (Taitung -> Xinzuoying)")
    print("=" * 60)

    # 關鍵車站座標
    taitung = stations.get('6000')      # 臺東
    fangliao = stations.get('5120')     # 枋寮
    kaohsiung = stations.get('4400')    # 高雄
    xinzuoying = stations.get('4340')   # 新左營

    print(f"\nKey stations:")
    print(f"  臺東 (6000): {taitung.coordinates if taitung else 'NOT FOUND'}")
    print(f"  枋寮 (5120): {fangliao.coordinates if fangliao else 'NOT FOUND'}")
    print(f"  高雄 (4400): {kaohsiung.coordinates if kaohsiung else 'NOT FOUND'}")
    print(f"  新左營 (4340): {xinzuoying.coordinates if xinzuoying else 'NOT FOUND'}")

    # 處理 NH (臺東→枋寮)
    print("\n--- Processing NH (Taitung -> Fangliao) ---")
    print(f"  NH track points: {len(nh_coords)}")
    print(f"  First point: [{nh_coords[0][0]:.4f}, {nh_coords[0][1]:.4f}]")
    print(f"  Last point: [{nh_coords[-1][0]:.4f}, {nh_coords[-1][1]:.4f}]")

    # 確保 NH 方向：臺東 → 枋寮
    taitung_dist_to_start = euclidean_distance(taitung.coordinates, nh_coords[0])
    taitung_dist_to_end = euclidean_distance(taitung.coordinates, nh_coords[-1])

    if taitung_dist_to_end < taitung_dist_to_start:
        print(f"  Reversing NH track (taitung closer to end)")
        nh_coords = list(reversed(nh_coords))

    print(f"  After adjustment - First point: [{nh_coords[0][0]:.4f}, {nh_coords[0][1]:.4f}]")
    print(f"  After adjustment - Last point: [{nh_coords[-1][0]:.4f}, {nh_coords[-1][1]:.4f}]")

    # 處理 PT (枋寮→高雄)
    print("\n--- Processing PT (Fangliao -> Kaohsiung) ---")
    print(f"  PT track points: {len(pt_coords)}")
    print(f"  First point: [{pt_coords[0][0]:.4f}, {pt_coords[0][1]:.4f}]")
    print(f"  Last point: [{pt_coords[-1][0]:.4f}, {pt_coords[-1][1]:.4f}]")

    # 確保 PT 方向：枋寮 → 高雄
    fangliao_dist_to_start = euclidean_distance(fangliao.coordinates, pt_coords[0])
    fangliao_dist_to_end = euclidean_distance(fangliao.coordinates, pt_coords[-1])

    if fangliao_dist_to_end < fangliao_dist_to_start:
        print(f"  Reversing PT track (fangliao closer to end)")
        pt_coords = list(reversed(pt_coords))

    print(f"  After adjustment - First point: [{pt_coords[0][0]:.4f}, {pt_coords[0][1]:.4f}]")
    print(f"  After adjustment - Last point: [{pt_coords[-1][0]:.4f}, {pt_coords[-1][1]:.4f}]")

    # 處理 WL-S1 (高雄→新左營)
    print("\n--- Processing WL-S1 (Kaohsiung -> Xinzuoying) ---")
    print(f"  WL-S1 track points: {len(wl_coords)}")
    print(f"  First point: [{wl_coords[0][0]:.4f}, {wl_coords[0][1]:.4f}]")
    print(f"  Last point: [{wl_coords[-1][0]:.4f}, {wl_coords[-1][1]:.4f}]")

    # 確保 WL 方向：高雄 → 新左營
    kaohsiung_dist_to_start = euclidean_distance(kaohsiung.coordinates, wl_coords[0])
    kaohsiung_dist_to_end = euclidean_distance(kaohsiung.coordinates, wl_coords[-1])

    if kaohsiung_dist_to_end < kaohsiung_dist_to_start:
        print(f"  Reversing WL-S1 track (kaohsiung closer to end)")
        wl_coords = list(reversed(wl_coords))

    # 擷取高雄到新左營段
    kaohsiung_idx = find_closest_point_index(wl_coords, kaohsiung.coordinates)
    xinzuoying_idx = find_closest_point_index(wl_coords, xinzuoying.coordinates)

    print(f"  Kaohsiung index: {kaohsiung_idx}")
    print(f"  Xinzuoying index: {xinzuoying_idx}")

    if kaohsiung_idx <= xinzuoying_idx:
        wl_segment = wl_coords[kaohsiung_idx:xinzuoying_idx+1]
    else:
        wl_segment = wl_coords[xinzuoying_idx:kaohsiung_idx+1][::-1]

    print(f"  WL segment points: {len(wl_segment)}")
    print(f"  WL segment start: [{wl_segment[0][0]:.4f}, {wl_segment[0][1]:.4f}]")
    print(f"  WL segment end: [{wl_segment[-1][0]:.4f}, {wl_segment[-1][1]:.4f}]")

    # 合併軌道
    print("\n--- Merging tracks ---")
    merged_coords = list(nh_coords)

    # 連接 NH 到 PT
    nh_end = merged_coords[-1]
    pt_start = pt_coords[0]
    gap_nh_pt = euclidean_distance(nh_end, pt_start)
    print(f"  Gap NH->PT: {gap_nh_pt:.6f} deg (~{gap_nh_pt * 111:.1f} km)")

    if gap_nh_pt < 0.0005:  # < ~50m
        merged_coords.extend(pt_coords[1:])
    else:
        merged_coords.extend(pt_coords)

    # 連接 PT 到 WL
    pt_end = merged_coords[-1]
    wl_start = wl_segment[0]
    gap_pt_wl = euclidean_distance(pt_end, wl_start)
    print(f"  Gap PT->WL: {gap_pt_wl:.6f} deg (~{gap_pt_wl * 111:.1f} km)")

    if gap_pt_wl < 0.0005:  # < ~50m
        merged_coords.extend(wl_segment[1:])
    else:
        merged_coords.extend(wl_segment)

    print(f"\n  Total merged points: {len(merged_coords)}")
    print(f"  Start: [{merged_coords[0][0]:.4f}, {merged_coords[0][1]:.4f}]")
    print(f"  End: [{merged_coords[-1][0]:.4f}, {merged_coords[-1][1]:.4f}]")

    # 計算車站進度
    print("\n--- Calculating station progress ---")
    cum_distances = calculate_cumulative_distances(merged_coords)
    total_length = cum_distances[-1]

    station_progress: Dict[str, float] = {}

    for station_id in SK_STATIONS:
        if station_id not in stations:
            print(f"  Warning: Station {station_id} not found")
            continue

        station = stations[station_id]
        idx = find_closest_point_index(merged_coords, station.coordinates)
        progress = cum_distances[idx] / total_length if total_length > 0 else 0

        # 驗證距離
        track_point = merged_coords[idx]
        error_m = haversine_distance(station.coordinates, track_point)

        station_progress[station_id] = round(progress, 6)
        status = "OK" if error_m < 200 else f"WARNING ({error_m:.0f}m)"
        print(f"  {station.name} ({station_id}): progress={progress:.4f}, error={error_m:.0f}m {status}")

    return merged_coords, station_progress


def save_od_track(
    od_track_id: str,
    coords: CoordList,
    station_progress: Dict[str, float],
    stations: Dict[str, Station],
    origin_id: str,
    dest_id: str,
    direction: int
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
            "direction": direction,
            "source_tracks": ["NH", "PT", "WL-S1"],
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

    print(f"\nSaved: {output_path}")
    print(f"  Points: {len(coords)}")


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
    print("Building SK (South Link Line) O-D Tracks")
    print("臺東 <-> 新左營")
    print("=" * 60)

    # 載入車站資料
    stations = load_stations()
    print(f"Loaded {len(stations)} stations")

    # 載入軌道資料
    print("\n--- Loading track data ---")

    # NH-1: 枋寮→臺東方向 (需要反轉成 臺東→枋寮)
    nh_raw, nh_type = load_track('NH-1')
    taitung = stations.get('6000')
    fangliao_nh = stations.get('5120')
    if nh_type == 'MultiLineString':
        # Use geography-based reorder for NH
        nh_coords = reorder_multilinestring_by_geography(
            nh_raw,
            target_start=taitung.coordinates if taitung else (121.123, 22.794),
            target_end=fangliao_nh.coordinates if fangliao_nh else (120.595, 22.368)
        )
    else:
        nh_coords = nh_raw
    print(f"  NH-1 loaded: {len(nh_coords) if nh_coords else 0} points (type: {nh_type})")

    # PT-1: 枋寮→高雄方向
    pt_raw, pt_type = load_track('PT-1')
    fangliao = stations.get('5120')
    kaohsiung = stations.get('4400')
    if pt_type == 'MultiLineString':
        # Use geography-based reorder for PT (has scattered segments)
        pt_coords = reorder_multilinestring_by_geography(
            pt_raw,
            target_start=fangliao.coordinates if fangliao else (120.595, 22.368),
            target_end=kaohsiung.coordinates if kaohsiung else (120.302, 22.639)
        )
    else:
        pt_coords = pt_raw
    print(f"  PT-1 loaded: {len(pt_coords) if pt_coords else 0} points (type: {pt_type})")

    # WL-S1-0: 彰化→高雄方向 (我們需要高雄→新左營段，所以需要取反)
    wl_raw, wl_type = load_track('WL-S1-0')
    if wl_type == 'MultiLineString':
        kaohsiung = stations.get('4400')
        wl_coords = reorder_multilinestring(wl_raw, target_start=kaohsiung.coordinates if kaohsiung else None)
    else:
        wl_coords = wl_raw if wl_raw else []
    print(f"  WL-S1-0 loaded: {len(wl_coords) if wl_coords else 0} points (type: {wl_type})")

    if not nh_coords or not pt_coords or not wl_coords:
        print("\nError: Failed to load one or more track files")
        return

    # 建立臺東→新左營軌道
    merged_coords, station_progress = build_sk_od_track(
        stations, nh_coords, pt_coords, wl_coords
    )

    if not merged_coords:
        print("Failed to build SK O-D track")
        return

    all_station_progress: Dict[str, Dict[str, float]] = {}

    # 儲存 SK-TT-ZY-0 (臺東→新左營)
    save_od_track(
        'SK-TT-ZY-0',
        merged_coords,
        station_progress,
        stations,
        '6000',  # 臺東
        '4340',  # 新左營
        0
    )
    all_station_progress['SK-TT-ZY-0'] = station_progress

    # 建立反向軌道 SK-ZY-TT-1 (新左營→臺東)
    print("\n" + "=" * 60)
    print("Building reverse track: SK-ZY-TT-1 (Xinzuoying -> Taitung)")
    print("=" * 60)

    reversed_coords = list(reversed(merged_coords))

    # 重新計算車站進度 (反向)
    cum_distances = calculate_cumulative_distances(reversed_coords)
    total_length = cum_distances[-1]

    reversed_progress: Dict[str, float] = {}
    reversed_station_order = list(reversed(SK_STATIONS))

    for station_id in reversed_station_order:
        if station_id not in stations:
            continue
        station = stations[station_id]
        idx = find_closest_point_index(reversed_coords, station.coordinates)
        progress = cum_distances[idx] / total_length if total_length > 0 else 0
        reversed_progress[station_id] = round(progress, 6)
        print(f"  {station.name} ({station_id}): progress={progress:.4f}")

    save_od_track(
        'SK-ZY-TT-1',
        reversed_coords,
        reversed_progress,
        stations,
        '4340',  # 新左營
        '6000',  # 臺東
        1
    )
    all_station_progress['SK-ZY-TT-1'] = reversed_progress

    # 更新進度映射表
    update_station_progress_file(all_station_progress)

    print("\n" + "=" * 60)
    print("Complete!")
    print("=" * 60)
    print("\nOutput files:")
    print(f"  1. {OUTPUT_DIR}/SK-TT-ZY-0.geojson (臺東→新左營)")
    print(f"  2. {OUTPUT_DIR}/SK-ZY-TT-1.geojson (新左營→臺東)")
    print("\nNext steps:")
    print("1. Create test schedule: schedules_od/SK-0.json, SK-1.json")
    print("2. Update useTraData.ts to load SK tracks")
    print("3. Update TraTrainEngine.ts for SK mapping")
    print("4. Update traInfo.ts with SK station names")
    print("5. Update TRACKS_STATUS.md")


if __name__ == '__main__':
    main()
