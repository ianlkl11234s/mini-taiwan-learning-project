#!/usr/bin/env python3
"""
建立高雄捷運軌道 GeoJSON

從 TDX Shape 資料 (WKT) 生成校準後的軌道 GeoJSON：
- KRTC-O-0.geojson (橘線 哈瑪星→大寮)
- KRTC-O-1.geojson (橘線 大寮→哈瑪星)
- KRTC-R-0.geojson (紅線 小港→岡山)
- KRTC-R-1.geojson (紅線 岡山→小港)

Usage:
    python scripts/build_krtc_tracks.py
"""

import json
import math
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any

# 路徑設定
DATA_DIR = Path(__file__).parent.parent / "data-krtc"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "data-krtc" / "tracks"
STATIONS_FILE = Path(__file__).parent.parent / "public" / "data-krtc" / "stations" / "krtc_stations.geojson"

# 線路配置
LINES_CONFIG = {
    'O': {
        'name': '橘線',
        'color': '#f8981d',
        'direction_0': '哈瑪星 → 大寮',
        'direction_1': '大寮 → 哈瑪星',
        'start_station': 'O1',
        'end_station': 'OT1',
    },
    'R': {
        'name': '紅線',
        'color': '#e2211c',
        'direction_0': '小港 → 岡山車站',
        'direction_1': '岡山車站 → 小港',
        'start_station': 'R3',
        'end_station': 'RK1',
    }
}


def parse_wkt_multilinestring(wkt: str) -> List[List[float]]:
    """
    解析 WKT MULTILINESTRING 為座標陣列

    輸入: MULTILINESTRING((lon lat, lon lat, ...))
    輸出: [[lon, lat], [lon, lat], ...]
    """
    # 移除 MULTILINESTRING 和外層括號
    wkt = wkt.strip()

    # 提取內部座標字串
    if wkt.upper().startswith('MULTILINESTRING'):
        # 找到最內層的座標部分
        # MULTILINESTRING((coords)) -> coords
        inner_start = wkt.find('((')
        inner_end = wkt.rfind('))')
        if inner_start != -1 and inner_end != -1:
            coords_str = wkt[inner_start + 2:inner_end]
        else:
            raise ValueError(f"無法解析 MULTILINESTRING: {wkt[:100]}...")
    elif wkt.upper().startswith('LINESTRING'):
        inner_start = wkt.find('(')
        inner_end = wkt.rfind(')')
        if inner_start != -1 and inner_end != -1:
            coords_str = wkt[inner_start + 1:inner_end]
        else:
            raise ValueError(f"無法解析 LINESTRING: {wkt[:100]}...")
    else:
        raise ValueError(f"無法解析 WKT: {wkt[:100]}...")

    # 處理多個 LineString 的情況 (用 ),( 分隔)
    # 只取第一個 LineString
    if '),(' in coords_str:
        coords_str = coords_str.split('),(')[0]

    coordinates = []

    for point in coords_str.split(','):
        point = point.strip()
        # 移除可能的括號
        point = point.replace('(', '').replace(')', '')
        parts = point.split()
        if len(parts) >= 2:
            lon = float(parts[0])
            lat = float(parts[1])
            coordinates.append([lon, lat])

    return coordinates


def euclidean(p1: List[float], p2: List[float]) -> float:
    """計算 Euclidean 距離"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


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


def calibrate_track(
    track_coords: List[List[float]],
    stations: List[Dict[str, Any]],
    reverse: bool = False
) -> Tuple[List[List[float]], Dict[str, int]]:
    """
    校準軌道：插入車站座標並截斷

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
    offset = 0
    for info in insert_info:
        station_id = info['station_id']
        proj_coord = info['proj_coord']
        seg_idx = info['segment_idx'] + offset

        coords.insert(seg_idx + 1, proj_coord)
        station_indices[station_id] = seg_idx + 1
        offset += 1

    # 第三階段：截斷軌道
    first_station = ordered_stations[0]['properties']['station_id']
    last_station = ordered_stations[-1]['properties']['station_id']

    first_idx = station_indices[first_station]
    last_idx = station_indices[last_station]

    start_idx = min(first_idx, last_idx)
    end_idx = max(first_idx, last_idx)

    truncated_coords = coords[start_idx:end_idx + 1]

    # 更新車站索引
    new_indices = {}
    for station_id, old_idx in station_indices.items():
        new_idx = old_idx - start_idx
        if 0 <= new_idx < len(truncated_coords):
            new_indices[station_id] = new_idx

    return truncated_coords, new_indices


def load_stations_by_line(line_id: str) -> List[Dict[str, Any]]:
    """載入指定線路的車站資料"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stations = [
        f for f in data['features']
        if f['properties']['line_id'] == line_id
    ]

    # 按順序排序
    stations.sort(key=lambda x: x['properties']['sequence'])
    return stations


def load_shape_by_line(line_id: str) -> str:
    """載入指定線路的軌道幾何"""
    with open(RAW_DIR / "krtc_shape.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    for shape in data:
        if shape.get('LineID') == line_id:
            return shape.get('Geometry', '')

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
                "start_station": config['start_station'] if direction == 0 else config['end_station'],
                "end_station": config['end_station'] if direction == 0 else config['start_station'],
                "color": config['color']
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }


def main():
    print("=" * 50)
    print("高雄捷運軌道建立腳本")
    print("=" * 50)

    # 確保輸出目錄存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for line_id, config in LINES_CONFIG.items():
        print(f"\n處理 {config['name']} ({line_id})...")

        # 載入車站
        stations = load_stations_by_line(line_id)
        print(f"  車站數量: {len(stations)}")

        if not stations:
            print(f"  ⚠️ 警告：找不到 {line_id} 線車站")
            continue

        # 載入軌道幾何
        wkt = load_shape_by_line(line_id)
        if not wkt:
            print(f"  ⚠️ 警告：找不到 {line_id} 線軌道")
            continue

        # 解析 WKT
        original_coords = parse_wkt_multilinestring(wkt)
        print(f"  原始座標點數: {len(original_coords)}")

        # 建立 Direction 0 (正向)
        track_id_0 = f"KRTC-{line_id}-0"
        print(f"\n  建立 {track_id_0} ({config['direction_0']})...")

        coords_0, indices_0 = calibrate_track(original_coords, stations, reverse=False)
        print(f"    校準後座標點數: {len(coords_0)}")
        print(f"    車站索引: {len(indices_0)}")

        geojson_0 = create_geojson(track_id_0, coords_0, line_id, 0, config)
        output_path_0 = OUTPUT_DIR / f"{track_id_0}.geojson"
        with open(output_path_0, 'w', encoding='utf-8') as f:
            json.dump(geojson_0, f, ensure_ascii=False, indent=2)
        print(f"    ✅ 已儲存: {output_path_0.name}")

        # 建立 Direction 1 (反向)
        track_id_1 = f"KRTC-{line_id}-1"
        print(f"\n  建立 {track_id_1} ({config['direction_1']})...")

        coords_1, indices_1 = calibrate_track(original_coords, stations, reverse=True)
        print(f"    校準後座標點數: {len(coords_1)}")
        print(f"    車站索引: {len(indices_1)}")

        geojson_1 = create_geojson(track_id_1, coords_1, line_id, 1, config)
        output_path_1 = OUTPUT_DIR / f"{track_id_1}.geojson"
        with open(output_path_1, 'w', encoding='utf-8') as f:
            json.dump(geojson_1, f, ensure_ascii=False, indent=2)
        print(f"    ✅ 已儲存: {output_path_1.name}")

        # 顯示車站索引
        print(f"\n  Direction 0 車站索引:")
        for station in stations:
            sid = station['properties']['station_id']
            name = station['properties']['name_zh']
            if sid in indices_0:
                print(f"    {name} ({sid}): 索引 {indices_0[sid]}")

    print("\n" + "=" * 50)
    print("完成！")
    print("=" * 50)
    print(f"\n產出檔案位於: {OUTPUT_DIR}")
    print("\n下一步：執行 build_krtc_schedules.py 建立時刻表")


if __name__ == '__main__':
    main()
