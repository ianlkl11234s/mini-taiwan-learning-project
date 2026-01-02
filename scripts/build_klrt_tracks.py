#!/usr/bin/env python3
"""
建立高雄輕軌軌道 GeoJSON

從 TDX Shape 資料 (WKT) 生成校準後的軌道 GeoJSON：
- KLRT-C-0.geojson (環狀線 順時針 籬仔內→籬仔內)
- KLRT-C-1.geojson (環狀線 逆時針 籬仔內→籬仔內)

特性：
- 環狀線：起點和終點是同一站 (C1 籬仔內)
- TDX 只提供一條軌道，Direction 1 需要反轉座標

Usage:
    python scripts/build_klrt_tracks.py
"""

import json
import math
from pathlib import Path
from typing import List, Tuple, Dict, Any

# 路徑設定
DATA_DIR = Path(__file__).parent.parent / "data-klrt"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "data-klrt" / "tracks"
STATIONS_FILE = Path(__file__).parent.parent / "public" / "data-klrt" / "stations" / "klrt_stations.geojson"

# 線路配置
LINE_CONFIG = {
    'C': {
        'name': '環狀線',
        'color': '#99cc00',  # 輕軌綠色
        'direction_0': '順時針 (籬仔內→籬仔內)',
        'direction_1': '逆時針 (籬仔內→籬仔內)',
        'start_station': 'C1',
        'end_station': 'C1',  # 環狀線起終點相同
        'is_circular': True
    }
}


def parse_single_linestring(coords_str: str) -> List[List[float]]:
    """
    解析單一 LineString 座標字串

    輸入: "lon lat, lon lat, ..."
    輸出: [[lon, lat], [lon, lat], ...]
    """
    coordinates = []
    coords_str = coords_str.strip().replace('(', '').replace(')', '')

    for point in coords_str.split(','):
        point = point.strip()
        parts = point.split()
        if len(parts) >= 2:
            lon = float(parts[0])
            lat = float(parts[1])
            coordinates.append([lon, lat])

    return coordinates


def parse_wkt_to_segments(wkt: str) -> List[List[List[float]]]:
    """
    解析 WKT MULTILINESTRING 或 LINESTRING 為多個線段

    輸入: MULTILINESTRING((lon lat, lon lat, ...),(lon lat, ...)) 或 LINESTRING(lon lat, lon lat, ...)
    輸出: [[[lon, lat], ...], [[lon, lat], ...], ...]  (每個子陣列是一個線段)
    """
    wkt = wkt.strip()
    segments = []

    if wkt.upper().startswith('MULTILINESTRING'):
        inner_start = wkt.find('((')
        inner_end = wkt.rfind('))')
        if inner_start != -1 and inner_end != -1:
            coords_str = wkt[inner_start + 2:inner_end]
        else:
            raise ValueError(f"無法解析 MULTILINESTRING: {wkt[:100]}...")

        # 分割各線段
        for segment_str in coords_str.split('),('):
            segment = parse_single_linestring(segment_str)
            if segment:
                segments.append(segment)

    elif wkt.upper().startswith('LINESTRING'):
        inner_start = wkt.find('(')
        inner_end = wkt.rfind(')')
        if inner_start != -1 and inner_end != -1:
            coords_str = wkt[inner_start + 1:inner_end]
            segment = parse_single_linestring(coords_str)
            if segment:
                segments.append(segment)
        else:
            raise ValueError(f"無法解析 LINESTRING: {wkt[:100]}...")
    else:
        raise ValueError(f"無法解析 WKT: {wkt[:100]}...")

    return segments


def euclidean(p1: List[float], p2: List[float]) -> float:
    """計算 Euclidean 距離"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def connect_segments(segments: List[List[List[float]]], tolerance: float = 0.001) -> List[List[float]]:
    """
    將多個不連續的線段按空間順序連接成一條連續的線

    使用貪婪演算法：從任意一個端點開始，不斷找到最近的下一個線段端點來連接
    """
    if not segments:
        return []

    if len(segments) == 1:
        return segments[0]

    # 複製線段，避免修改原始資料
    remaining = [seg[:] for seg in segments]

    # 從第一個線段開始
    result = remaining.pop(0)

    while remaining:
        # 取得當前路徑的起點和終點
        path_start = result[0]
        path_end = result[-1]

        best_match = None
        best_dist = float('inf')
        best_idx = -1
        best_reverse = False
        best_at_start = False

        # 嘗試找到最接近的線段端點
        for i, seg in enumerate(remaining):
            seg_start = seg[0]
            seg_end = seg[-1]

            # 情況 1: 線段起點接到路徑終點
            dist = euclidean(path_end, seg_start)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
                best_reverse = False
                best_at_start = False

            # 情況 2: 線段終點接到路徑終點 (需要反轉線段)
            dist = euclidean(path_end, seg_end)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
                best_reverse = True
                best_at_start = False

            # 情況 3: 線段終點接到路徑起點 (接在前面)
            dist = euclidean(path_start, seg_end)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
                best_reverse = False
                best_at_start = True

            # 情況 4: 線段起點接到路徑起點 (接在前面，需要反轉線段)
            dist = euclidean(path_start, seg_start)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
                best_reverse = True
                best_at_start = True

        if best_idx == -1:
            print(f"  ⚠️ 警告: 無法找到匹配的線段，剩餘 {len(remaining)} 個線段未連接")
            break

        # 取出最佳匹配的線段
        best_seg = remaining.pop(best_idx)

        # 根據需要反轉
        if best_reverse:
            best_seg = list(reversed(best_seg))

        # 連接到路徑
        if best_at_start:
            # 接到路徑前面，避免重複端點
            if euclidean(best_seg[-1], result[0]) < tolerance:
                result = best_seg[:-1] + result
            else:
                result = best_seg + result
        else:
            # 接到路徑後面，避免重複端點
            if euclidean(result[-1], best_seg[0]) < tolerance:
                result = result + best_seg[1:]
            else:
                result = result + best_seg

    return result


def parse_wkt_multilinestring(wkt: str) -> List[List[float]]:
    """
    解析 WKT MULTILINESTRING 為座標陣列

    輸入: MULTILINESTRING((lon lat, lon lat, ...),(lon lat, ...))
    輸出: [[lon, lat], [lon, lat], ...] (按空間順序連接所有線段)
    """
    segments = parse_wkt_to_segments(wkt)
    print(f"  解析到 {len(segments)} 個線段")

    # 連接所有線段
    connected = connect_segments(segments)
    print(f"  連接後總點數: {len(connected)}")

    return connected


def point_to_segment_distance(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float
) -> Tuple[float, float, float, float]:
    """
    計算點到線段的最短距離和投影點

    返回：(距離, 投影點x, 投影點y, 參數t)
    """
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return euclidean([px, py], [x1, y1]), x1, y1, 0.0

    # 投影參數 t (限制在 [0, 1])
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    proj_x = x1 + t * dx
    proj_y = y1 + t * dy

    dist = euclidean([px, py], [proj_x, proj_y])
    return dist, proj_x, proj_y, t


def find_best_segment(
    station_coord: List[float],
    track_coords: List[List[float]]
) -> Tuple[int, float, List[float]]:
    """
    找到車站應該插入的最佳線段位置

    返回：(線段起點索引, 距離, 投影點座標)
    """
    min_dist = float('inf')
    best_idx = 0
    best_proj = station_coord

    for i in range(len(track_coords) - 1):
        dist, proj_x, proj_y, _ = point_to_segment_distance(
            station_coord[0], station_coord[1],
            track_coords[i][0], track_coords[i][1],
            track_coords[i + 1][0], track_coords[i + 1][1]
        )
        if dist < min_dist:
            min_dist = dist
            best_idx = i
            best_proj = [proj_x, proj_y]

    return best_idx, min_dist, best_proj


def calibrate_circular_track(
    track_coords: List[List[float]],
    stations: List[Dict[str, Any]],
    reverse: bool = False
) -> Tuple[List[List[float]], Dict[str, int]]:
    """
    校準環狀軌道：插入車站座標

    參數：
        track_coords: 原始軌道座標
        stations: 車站資料列表（已按順序排序）
        reverse: 是否反轉軌道方向

    返回：
        (校準後的座標, 車站在座標中的索引)
    """
    # 複製座標
    coords = [c[:] for c in track_coords]

    # 根據需要反轉
    if reverse:
        coords = list(reversed(coords))
        ordered_stations = list(reversed(stations))
    else:
        ordered_stations = stations

    # 記錄每個車站插入後的索引
    station_indices: Dict[str, int] = {}

    # 第一階段：找到所有車站的最佳插入位置
    insert_info = []
    for station in ordered_stations:
        station_id = station['properties']['station_id']
        station_coord = station['geometry']['coordinates']

        seg_idx, dist, proj_coord = find_best_segment(station_coord, coords)

        insert_info.append({
            'station_id': station_id,
            'station_coord': station_coord,
            'proj_coord': proj_coord,
            'segment_idx': seg_idx,
            'distance': dist
        })

    # 按線段索引排序
    insert_info.sort(key=lambda x: x['segment_idx'])

    # 第二階段：依序插入
    # 使用車站實際座標，確保軌道「經過」車站標記點
    offset = 0
    for info in insert_info:
        station_id = info['station_id']
        station_coord = info['station_coord']
        seg_idx = info['segment_idx'] + offset

        coords.insert(seg_idx + 1, station_coord)
        station_indices[station_id] = seg_idx + 1
        offset += 1

    # 環狀線：不需要截斷，保持完整環狀
    # 但需要確保起點和終點正確對應
    return coords, station_indices


def load_stations() -> List[Dict[str, Any]]:
    """載入輕軌車站資料"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stations = data['features']

    # 按順序排序
    stations.sort(key=lambda x: x['properties']['sequence'])
    return stations


def load_shape() -> str:
    """載入輕軌軌道幾何"""
    with open(RAW_DIR / "klrt_shape.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    # KLRT 只有一條軌道
    if data:
        return data[0].get('Geometry', '')

    return ''


def create_geojson(
    track_id: str,
    coords: List[List[float]],
    line_id: str,
    direction: int,
    config: Dict
) -> Dict:
    """建立軌道 GeoJSON"""
    direction_name = config[f'direction_{direction}']

    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "line_id": line_id,
                "direction": direction,
                "name": direction_name,
                "start_station": config['start_station'],
                "end_station": config['end_station'],
                "color": config['color'],
                "is_circular": config.get('is_circular', False)
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }


def main():
    print("=" * 50)
    print("高雄輕軌軌道建立腳本")
    print("=" * 50)

    # 確保輸出目錄存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    line_id = 'C'
    config = LINE_CONFIG[line_id]

    print(f"\n處理 {config['name']} ({line_id})...")

    # 載入車站
    stations = load_stations()
    print(f"  車站數量: {len(stations)}")

    if not stations:
        print(f"  ⚠️ 警告：找不到 {line_id} 線車站")
        return

    # 載入軌道幾何
    wkt = load_shape()
    if not wkt:
        print(f"  ⚠️ 警告：找不到 {line_id} 線軌道")
        return

    # 解析 WKT
    original_coords = parse_wkt_multilinestring(wkt)
    print(f"  原始座標點數: {len(original_coords)}")

    # 建立 Direction 0 (順時針)
    track_id_0 = f"KLRT-{line_id}-0"
    print(f"\n  建立 {track_id_0} ({config['direction_0']})...")

    coords_0, indices_0 = calibrate_circular_track(original_coords, stations, reverse=False)
    print(f"    校準後座標點數: {len(coords_0)}")
    print(f"    車站索引: {len(indices_0)}")

    geojson_0 = create_geojson(track_id_0, coords_0, line_id, 0, config)
    output_path_0 = OUTPUT_DIR / f"{track_id_0}.geojson"
    with open(output_path_0, 'w', encoding='utf-8') as f:
        json.dump(geojson_0, f, ensure_ascii=False, indent=2)
    print(f"    ✅ 已儲存: {output_path_0.name}")

    # 建立 Direction 1 (逆時針)
    # 直接反轉已校準的 coords_0
    track_id_1 = f"KLRT-{line_id}-1"
    print(f"\n  建立 {track_id_1} ({config['direction_1']})...")

    coords_1 = list(reversed(coords_0))
    # 反轉車站索引
    indices_1 = {}
    total_coords = len(coords_1)
    for station_id, idx in indices_0.items():
        indices_1[station_id] = total_coords - 1 - idx

    print(f"    校準後座標點數: {len(coords_1)}")
    print(f"    車站索引: {len(indices_1)}")

    geojson_1 = create_geojson(track_id_1, coords_1, line_id, 1, config)
    output_path_1 = OUTPUT_DIR / f"{track_id_1}.geojson"
    with open(output_path_1, 'w', encoding='utf-8') as f:
        json.dump(geojson_1, f, ensure_ascii=False, indent=2)
    print(f"    ✅ 已儲存: {output_path_1.name}")

    # 顯示車站索引
    print(f"\n  Direction 0 車站索引 (順時針):")
    for station in stations[:10]:  # 只顯示前 10 站
        sid = station['properties']['station_id']
        name = station['properties']['name_zh']
        if sid in indices_0:
            print(f"    {name} ({sid}): 索引 {indices_0[sid]}")
    print(f"    ... (共 {len(indices_0)} 站)")

    print("\n" + "=" * 50)
    print("完成！")
    print("=" * 50)
    print(f"\n產出檔案位於: {OUTPUT_DIR}")
    print(f"  - {track_id_0}.geojson (順時針)")
    print(f"  - {track_id_1}.geojson (逆時針)")
    print("\n下一步：執行 build_klrt_schedules.py 建立時刻表")


if __name__ == '__main__':
    main()
