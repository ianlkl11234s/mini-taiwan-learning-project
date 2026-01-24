#!/usr/bin/env python3
"""
build_wl_north_od_tracks.py
建立西部幹線北段 (WL-N) 竹南→樹林 O-D 專屬軌道

工作內容：
1. 從 tracks_official/WL-N-0.geojson 提取軌道
2. 處理 MultiLineString，合併為連續 LineString
3. 擷取竹南→樹林區間
4. 計算車站 station_progress
5. 輸出 O-D 軌道和 Golden Track

輸出檔案：
- tracks_od/WL-ZN-SL-0.geojson (竹南→樹林)
- tracks_od/WL-SL-ZN-1.geojson (樹林→竹南)
- tracks_golden/WL-N-ZN-SL-0.geojson
- tracks_golden/WL-N-ZN-SL-1.geojson
"""

import json
import math
import os
from typing import List, Tuple, Dict

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRA_DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')

# 竹南→樹林主線車站 (排除支線)
# 順序：由南往北（竹南方向 0 → 樹林）
WL_N_STATIONS = [
    ('1250', '竹南'),
    ('1240', '崎頂'),
    ('1230', '香山'),
    ('1220', '三姓橋'),
    ('1210', '新竹'),
    ('1190', '北新竹'),
    ('1180', '竹北'),
    ('1170', '新豐'),
    ('1160', '湖口'),
    ('1150', '北湖'),
    ('1140', '新富'),
    ('1130', '富岡'),
    ('1120', '楊梅'),
    ('1110', '埔心'),
    ('1100', '中壢'),
    ('1090', '內壢'),
    ('1080', '桃園'),
    ('1075', '鳳鳴'),
    ('1070', '鶯歌'),
    ('1060', '山佳'),
    ('1050', '南樹林'),
    ('1040', '樹林'),
]


def euclidean_distance(coord1: List[float], coord2: List[float]) -> float:
    """計算歐幾里得距離（平面，度為單位）"""
    dx = coord2[0] - coord1[0]
    dy = coord2[1] - coord1[1]
    return math.sqrt(dx * dx + dy * dy)


def load_geojson(filepath: str) -> dict:
    """載入 GeoJSON 檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_geojson(data: dict, filepath: str):
    """儲存 GeoJSON 檔案"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'已儲存: {filepath}')


def load_stations() -> Dict[str, Tuple[float, float, str]]:
    """載入車站資料，回傳 {station_id: (lng, lat, name)}"""
    stations_path = os.path.join(TRA_DATA_DIR, 'stations_snapped.geojson')
    data = load_geojson(stations_path)

    stations = {}
    for feat in data['features']:
        props = feat['properties']
        sid = props.get('station_id', '')
        name = props.get('name_zh', props.get('name', 'Unknown'))
        coords = feat['geometry']['coordinates']
        stations[sid] = (coords[0], coords[1], name)

    return stations


def extract_track_from_multilinestring(geom: dict, start_coord: List[float], end_coord: List[float]) -> List[List[float]]:
    """從 MultiLineString 中提取指定區間的軌道座標"""

    if geom['type'] == 'LineString':
        return geom['coordinates']

    # 合併所有 segment
    all_coords = []
    for segment in geom['coordinates']:
        if not all_coords:
            all_coords.extend(segment)
        else:
            # 檢查是否連續
            last_pt = all_coords[-1]
            first_pt = segment[0]
            gap = euclidean_distance(last_pt, first_pt)

            if gap < 0.001:  # 約 111m 以內視為連續
                all_coords.extend(segment[1:])  # 跳過第一個重複點
            else:
                print(f'警告: 軌道有 {gap * 111:.1f}km 缺口')
                all_coords.extend(segment)

    # 找到最接近起點和終點的座標索引
    min_start_dist = float('inf')
    min_end_dist = float('inf')
    start_idx = 0
    end_idx = len(all_coords) - 1

    for i, coord in enumerate(all_coords):
        dist_to_start = euclidean_distance(coord, start_coord)
        dist_to_end = euclidean_distance(coord, end_coord)

        if dist_to_start < min_start_dist:
            min_start_dist = dist_to_start
            start_idx = i

        if dist_to_end < min_end_dist:
            min_end_dist = dist_to_end
            end_idx = i

    print(f'起點最近距離: {min_start_dist * 111:.3f}km (索引 {start_idx})')
    print(f'終點最近距離: {min_end_dist * 111:.3f}km (索引 {end_idx})')

    # 確保起點在終點之前
    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx

    # 擷取區間
    extracted = all_coords[start_idx:end_idx + 1]

    return extracted


def extend_track_to_station(coords: List[List[float]], station_coord: List[float], at_start: bool) -> List[List[float]]:
    """延伸軌道到車站座標"""
    if at_start:
        dist = euclidean_distance(coords[0], station_coord)
        if dist > 0.00001:  # > 1m
            print(f'  延伸起點: {dist * 111 * 1000:.1f}m')
            return [station_coord] + coords
    else:
        dist = euclidean_distance(coords[-1], station_coord)
        if dist > 0.00001:  # > 1m
            print(f'  延伸終點: {dist * 111 * 1000:.1f}m')
            return coords + [station_coord]
    return coords


def project_point_to_segment(p: List[float], a: List[float], b: List[float]) -> Tuple[List[float], float, float]:
    """將點 p 投影到線段 ab 上"""
    ax, ay = a[0], a[1]
    bx, by = b[0], b[1]
    px, py = p[0], p[1]

    dx = bx - ax
    dy = by - ay
    len_sq = dx * dx + dy * dy

    if len_sq == 0:
        return list(a), euclidean_distance(p, a), 0

    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / len_sq))
    proj = [ax + t * dx, ay + t * dy]
    dist = euclidean_distance(p, proj)

    return proj, dist, t


def calculate_station_progress(coords: List[List[float]], stations: Dict[str, Tuple[float, float, str]],
                                station_order: List[Tuple[str, str]]) -> Dict[str, float]:
    """計算每個車站在軌道上的進度值 (0.0 ~ 1.0)"""

    # 計算軌道總長度
    total_length = 0.0
    segment_lengths = []
    for i in range(len(coords) - 1):
        seg_len = euclidean_distance(coords[i], coords[i + 1])
        segment_lengths.append(seg_len)
        total_length += seg_len

    print(f'軌道總長度: {total_length * 111:.2f}km ({len(coords)} 座標點)')

    progress_dict = {}

    for station_id, station_name in station_order:
        if station_id not in stations:
            print(f'警告: 找不到車站 {station_id} ({station_name})')
            continue

        station_coord = [stations[station_id][0], stations[station_id][1]]

        # 找到最佳投影位置
        best_dist = float('inf')
        best_progress = 0.0
        cumulative_length = 0.0

        for i in range(len(coords) - 1):
            proj, dist, t = project_point_to_segment(station_coord, coords[i], coords[i + 1])

            if dist < best_dist:
                best_dist = dist
                # 計算進度值
                best_progress = (cumulative_length + t * segment_lengths[i]) / total_length

            cumulative_length += segment_lengths[i]

        progress_dict[station_id] = round(best_progress, 6)
        dist_m = best_dist * 111 * 1000
        status = '✅' if dist_m < 50 else '⚠️' if dist_m < 200 else '❌'
        print(f'  {status} {station_id} {station_name}: progress={best_progress:.6f}, 距離={dist_m:.1f}m')

    return progress_dict


def create_od_track_geojson(coords: List[List[float]], track_id: str, name: str,
                            origin: str, destination: str, direction: int) -> dict:
    """建立 O-D 軌道 GeoJSON"""
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "name": name,
                "origin": origin,
                "destination": destination,
                "direction": direction
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }


def create_golden_track_geojson(coords: List[List[float]], track_id: str, line_id: str,
                                 name: str, origin: str, destination: str, direction: int) -> dict:
    """建立 Golden Track GeoJSON"""
    return {
        "type": "Feature",
        "properties": {
            "track_id": track_id,
            "line_id": line_id,
            "direction": direction,
            "name": name,
            "origin": origin,
            "destination": destination
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coords
        }
    }


def main():
    print('=== 建立 WL-N 西部幹線北段 O-D 軌道 (竹南→樹林) ===\n')

    # 載入車站資料
    stations = load_stations()
    print(f'載入 {len(stations)} 個車站\n')

    # 確認必要車站存在
    missing_stations = []
    for sid, sname in WL_N_STATIONS:
        if sid not in stations:
            missing_stations.append(f'{sid} ({sname})')

    if missing_stations:
        print(f'⚠️ 缺少車站: {", ".join(missing_stations)}')
        # 繼續執行，稍後處理

    # 取得起終點座標
    zhunan_coord = list(stations.get('1250', (120.8768, 24.6863, '竹南'))[:2])
    shulin_coord = list(stations.get('1040', (121.4244, 24.9912, '樹林'))[:2])

    print(f'竹南 (1250): {zhunan_coord}')
    print(f'樹林 (1040): {shulin_coord}\n')

    # 載入 WL-N-0 軌道
    wl_n_path = os.path.join(TRA_DATA_DIR, 'tracks_official', 'WL-N-0.geojson')
    wl_n_data = load_geojson(wl_n_path)

    if wl_n_data['type'] == 'FeatureCollection':
        geom = wl_n_data['features'][0]['geometry']
    else:
        geom = wl_n_data['geometry']

    print(f'原始軌道類型: {geom["type"]}\n')

    # 提取竹南→樹林區間
    print('=== 提取竹南→樹林區間 ===')
    coords_0 = extract_track_from_multilinestring(geom, zhunan_coord, shulin_coord)
    print(f'擷取座標: {len(coords_0)} 點\n')

    # 確認方向（竹南在南，樹林在北）
    first_lat = coords_0[0][1]
    last_lat = coords_0[-1][1]

    # 方向 0: 竹南 (南) → 樹林 (北)，緯度應該遞增
    if first_lat > last_lat:
        print('調整方向：反轉座標 (改為由南往北)')
        coords_0 = list(reversed(coords_0))

    # 延伸軌道到車站
    print('\n=== 延伸軌道到車站 ===')
    coords_0 = extend_track_to_station(coords_0, zhunan_coord, at_start=True)
    coords_0 = extend_track_to_station(coords_0, shulin_coord, at_start=False)
    print(f'最終座標: {len(coords_0)} 點\n')

    # 建立反向軌道
    coords_1 = list(reversed(coords_0))

    # 計算 station_progress
    print('=== 計算 Station Progress (方向 0: 竹南→樹林) ===')
    progress_0 = calculate_station_progress(coords_0, stations, WL_N_STATIONS)

    print('\n=== 計算 Station Progress (方向 1: 樹林→竹南) ===')
    reversed_stations = list(reversed(WL_N_STATIONS))
    progress_1 = calculate_station_progress(coords_1, stations, reversed_stations)

    # 儲存 O-D 軌道
    print('\n=== 儲存 O-D 軌道 ===')

    od_0 = create_od_track_geojson(
        coords_0, 'WL-ZN-SL-0', '西部幹線北段 (竹南→樹林)',
        '竹南', '樹林', 0
    )
    save_geojson(od_0, os.path.join(TRA_DATA_DIR, 'tracks_od', 'WL-ZN-SL-0.geojson'))

    od_1 = create_od_track_geojson(
        coords_1, 'WL-SL-ZN-1', '西部幹線北段 (樹林→竹南)',
        '樹林', '竹南', 1
    )
    save_geojson(od_1, os.path.join(TRA_DATA_DIR, 'tracks_od', 'WL-SL-ZN-1.geojson'))

    # 儲存 Golden Track
    print('\n=== 儲存 Golden Track ===')

    golden_0 = create_golden_track_geojson(
        coords_0, 'WL-N-ZN-SL-0', 'WL-N',
        '西部幹線北段 (竹南→樹林)', '竹南', '樹林', 0
    )
    save_geojson(golden_0, os.path.join(TRA_DATA_DIR, 'tracks_golden', 'WL-N-ZN-SL-0.geojson'))

    golden_1 = create_golden_track_geojson(
        coords_1, 'WL-N-ZN-SL-1', 'WL-N',
        '西部幹線北段 (樹林→竹南)', '樹林', '竹南', 1
    )
    save_geojson(golden_1, os.path.join(TRA_DATA_DIR, 'tracks_golden', 'WL-N-ZN-SL-1.geojson'))

    # 更新 station_progress.json
    print('\n=== 更新 station_progress.json ===')
    progress_path = os.path.join(TRA_DATA_DIR, 'tracks_od', 'od_station_progress.json')

    if os.path.exists(progress_path):
        with open(progress_path, 'r', encoding='utf-8') as f:
            all_progress = json.load(f)
    else:
        all_progress = {}

    all_progress['WL-ZN-SL-0'] = progress_0
    all_progress['WL-SL-ZN-1'] = progress_1

    with open(progress_path, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)
    print(f'已更新: {progress_path}')

    # 驗證摘要
    print('\n=== 建構完成摘要 ===')
    print(f'軌道: {len(coords_0)} 座標點')
    print(f'車站: {len(progress_0)} 站')
    print(f'起點: 竹南 (1250) progress=0.0')
    print(f'終點: 樹林 (1040) progress=1.0')

    # 驗證進度值順序
    prev_progress = -1
    order_ok = True
    for sid, sname in WL_N_STATIONS:
        if sid in progress_0:
            if progress_0[sid] < prev_progress:
                print(f'⚠️ 進度值順序錯誤: {sid} ({sname})')
                order_ok = False
            prev_progress = progress_0[sid]

    if order_ok:
        print('✅ 進度值順序正確')

    print('\n完成！')


if __name__ == '__main__':
    main()
