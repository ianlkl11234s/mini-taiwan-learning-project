#!/usr/bin/env python3
"""
04_extract_green_line_tracks.py - 提取綠線各路線軌道

從完整的綠線軌道幾何中，根據各營運路線的起迄站，
切割出對應的軌道段落。

G 線路線結構：
- G-1: 全程車 (新店 G01 ↔ 松山 G19)
- G-2: 區間車 (台電大樓 G08 ↔ 松山 G19)
- G-3: 小碧潭支線 (七張 G03 ↔ 小碧潭 G03A) - 暫不處理（無時刻表）

輸入：
- kepler_mrt_routes.geojson: 完整軌道幾何
- kepler_mrt_stations.geojson: 車站座標

輸出：
- output/tracks/G-1-0.geojson: 松山→新店
- output/tracks/G-1-1.geojson: 新店→松山
- output/tracks/G-2-0.geojson: 松山→台電大樓
- output/tracks/G-2-1.geojson: 台電大樓→松山
- output/green_line_stations.geojson: G線車站
"""

import json
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from shapely.geometry import LineString, Point, MultiLineString
from shapely.ops import linemerge

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
RAW_DATA_DIR = Path("/Users/migu/Desktop/資料庫/gen_ai_try/ichef_工作用/GIS/mini-taipei/raw_data/mrt")
OUTPUT_DIR = SCRIPT_DIR.parent / "output"
TRACKS_DIR = OUTPUT_DIR / "tracks"

# 綠線顏色
G_COLOR = "#008659"

# 顏色設定（用於視覺區分）
TRACK_COLORS = {
    "G-1-0": G_COLOR,       # 綠色 - 松山→新店
    "G-1-1": "#33a77c",     # 淺綠 - 新店→松山
    "G-2-0": "#006644",     # 深綠 - 松山→台電大樓
    "G-2-1": "#66c4a0",     # 淡綠 - 台電大樓→松山
}

# 站點順序 (新店→松山方向，即 direction=1 往松山)
# 注意：ericyu 時刻表中沒有小碧潭支線
STATION_ORDER = [
    "G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G09",
    "G10", "G11", "G12", "G13", "G14", "G15", "G16", "G17", "G18", "G19"
]

# 站名對照
STATION_NAMES = {
    "G01": "新店", "G02": "新店區公所", "G03": "七張", "G03A": "小碧潭",
    "G04": "大坪林", "G05": "景美", "G06": "萬隆", "G07": "公館",
    "G08": "台電大樓", "G09": "古亭", "G10": "中正紀念堂", "G11": "小南門",
    "G12": "西門", "G13": "北門", "G14": "中山", "G15": "松江南京",
    "G16": "南京復興", "G17": "台北小巨蛋", "G18": "南京三民", "G19": "松山"
}


def load_json(filepath: Path) -> Any:
    """載入 JSON 檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, filepath: Path) -> None:
    """儲存 JSON 檔案"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_g_line_geometry(routes_data: Dict) -> Optional[LineString]:
    """從 kepler 資料提取 G 線幾何"""
    for feature in routes_data['features']:
        props = feature['properties']
        if props.get('line_id') == 'G':
            coords = feature['geometry']['coordinates']

            # 處理嵌套陣列（多段線）
            if coords and isinstance(coords[0][0], list):
                # 這是多段線，需要合併
                lines = [LineString(segment) for segment in coords]
                merged = linemerge(lines)
                if isinstance(merged, LineString):
                    return merged
                elif isinstance(merged, MultiLineString):
                    # 如果無法完全合併，取最長的
                    return max(merged.geoms, key=lambda x: x.length)
            else:
                return LineString(coords)
    return None


def extract_g_stations(stations_data: Dict) -> List[Dict]:
    """提取 G 線車站"""
    g_stations = []
    for feature in stations_data['features']:
        props = feature['properties']
        station_id = props.get('station_id', '')
        if station_id.startswith('G') and station_id in STATION_ORDER:
            coords = feature['geometry']['coordinates']
            g_stations.append({
                'station_id': station_id,
                'name_zh': STATION_NAMES.get(station_id, ''),
                'name_en': props.get('name_en', ''),
                'coords': coords
            })

    # 按站號排序
    g_stations.sort(key=lambda x: STATION_ORDER.index(x['station_id']))
    return g_stations


def find_nearest_point_on_line(line: LineString, point: Point) -> float:
    """找到點在線上的最近位置（0-1 normalized）"""
    return line.project(point, normalized=True)


def cut_line_by_progress(line: LineString, start_progress: float, end_progress: float) -> LineString:
    """根據進度切割線段"""
    if start_progress > end_progress:
        start_progress, end_progress = end_progress, start_progress

    total_length = line.length
    start_dist = start_progress * total_length
    end_dist = end_progress * total_length

    # 收集切割後的座標點
    coords = list(line.coords)
    result_coords = []
    current_dist = 0

    for i in range(len(coords) - 1):
        p1 = Point(coords[i])
        p2 = Point(coords[i + 1])
        segment_length = p1.distance(p2)
        next_dist = current_dist + segment_length

        # 檢查起點
        if current_dist <= start_dist < next_dist:
            # 插入起點
            ratio = (start_dist - current_dist) / segment_length
            x = coords[i][0] + ratio * (coords[i + 1][0] - coords[i][0])
            y = coords[i][1] + ratio * (coords[i + 1][1] - coords[i][1])
            result_coords.append((x, y))

        # 檢查是否在範圍內
        if start_dist <= current_dist < end_dist:
            if not result_coords or result_coords[-1] != coords[i]:
                result_coords.append(coords[i])

        # 檢查終點
        if current_dist < end_dist <= next_dist:
            # 插入終點
            ratio = (end_dist - current_dist) / segment_length
            x = coords[i][0] + ratio * (coords[i + 1][0] - coords[i][0])
            y = coords[i][1] + ratio * (coords[i + 1][1] - coords[i][1])
            result_coords.append((x, y))
            break

        current_dist = next_dist

    # 確保至少有兩個點
    if len(result_coords) < 2:
        # 使用原始起終點
        start_point = line.interpolate(start_progress, normalized=True)
        end_point = line.interpolate(end_progress, normalized=True)
        result_coords = [(start_point.x, start_point.y), (end_point.x, end_point.y)]

    return LineString(result_coords)


def create_track_geojson(
    coords: List[Tuple[float, float]],
    track_id: str,
    route_id: str,
    name: str,
    origin: str,
    destination: str,
    color: str
) -> Dict:
    """建立軌道 GeoJSON"""
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "route_id": route_id,
                "line_id": "G",
                "name": name,
                "origin": origin,
                "destination": destination,
                "color": color
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[c[0], c[1]] for c in coords]
            }
        }]
    }


def create_stations_geojson(stations: List[Dict]) -> Dict:
    """建立車站 GeoJSON"""
    features = []
    for station in stations:
        features.append({
            "type": "Feature",
            "properties": {
                "station_id": station['station_id'],
                "name_zh": station['name_zh'],
                "name_en": station.get('name_en', ''),
                "line_id": "G"
            },
            "geometry": {
                "type": "Point",
                "coordinates": station['coords']
            }
        })
    return {
        "type": "FeatureCollection",
        "features": features
    }


def calculate_station_progress(
    line: LineString,
    stations: List[Dict],
    reverse: bool = False
) -> Dict[str, float]:
    """計算各站在軌道上的進度"""
    progress = {}
    for station in stations:
        point = Point(station['coords'])
        p = find_nearest_point_on_line(line, point)
        if reverse:
            p = 1.0 - p
        progress[station['station_id']] = round(p, 6)
    return progress


def main():
    print("=" * 60)
    print("G 線（松山新店線）軌道提取工具")
    print("=" * 60)

    # 載入資料
    print("\n載入資料...")
    routes_data = load_json(RAW_DATA_DIR / "kepler_mrt_routes.geojson")
    stations_data = load_json(RAW_DATA_DIR / "kepler_mrt_stations.geojson")

    # 提取 G 線幾何
    print("提取 G 線軌道幾何...")
    g_line = extract_g_line_geometry(routes_data)
    if g_line is None:
        print("錯誤：找不到 G 線資料")
        return

    print(f"  軌道座標點數: {len(g_line.coords)}")
    print(f"  軌道長度: {g_line.length:.6f} (度)")

    # 提取 G 線車站
    print("\n提取 G 線車站...")
    g_stations = extract_g_stations(stations_data)
    print(f"  車站數: {len(g_stations)}")
    for s in g_stations:
        print(f"    {s['station_id']}: {s['name_zh']}")

    # 計算各站進度
    print("\n計算各站進度...")
    station_progress = {}
    for station in g_stations:
        point = Point(station['coords'])
        progress = find_nearest_point_on_line(g_line, point)
        station_progress[station['station_id']] = progress
        print(f"  {station['station_id']}: {progress:.4f}")

    # 確定軌道方向（檢查 G01 新店和 G19 松山的位置）
    g01_progress = station_progress.get('G01', 0)
    g19_progress = station_progress.get('G19', 1)

    # 如果 G01 的進度較大，表示軌道方向需要反轉
    if g01_progress > g19_progress:
        print("\n軌道方向: 松山(G19) → 新店(G01)")
        direction_to_xindian = True  # 原始方向是往新店
    else:
        print("\n軌道方向: 新店(G01) → 松山(G19)")
        direction_to_xindian = False  # 原始方向是往松山

    # 取得關鍵站點進度
    g08_progress = station_progress.get('G08', 0.5)

    # 建立輸出目錄
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 建立各軌道
    tracks_data = {}

    # G-1-0: 松山 → 新店（全程）
    if direction_to_xindian:
        # 原始方向就是往新店
        g1_0_line = g_line
        g1_0_coords = list(g_line.coords)
    else:
        # 需要反轉
        g1_0_coords = list(reversed(g_line.coords))
        g1_0_line = LineString(g1_0_coords)

    tracks_data['G-1-0'] = create_track_geojson(
        g1_0_coords, 'G-1-0', 'G-1',
        '松山 → 新店', 'G19', 'G01', TRACK_COLORS['G-1-0']
    )

    # G-1-1: 新店 → 松山（全程）
    g1_1_coords = list(reversed(g1_0_coords))
    tracks_data['G-1-1'] = create_track_geojson(
        g1_1_coords, 'G-1-1', 'G-1',
        '新店 → 松山', 'G01', 'G19', TRACK_COLORS['G-1-1']
    )

    # 計算 G08 在 G-1-0 上的進度
    g1_0_line_obj = LineString(g1_0_coords)
    g08_point = Point([s['coords'] for s in g_stations if s['station_id'] == 'G08'][0])
    g08_on_g1_0 = find_nearest_point_on_line(g1_0_line_obj, g08_point)

    print(f"\nG08 在 G-1-0 軌道上的進度: {g08_on_g1_0:.4f}")

    # G-2-0: 松山 → 台電大樓（區間）
    # 從 G19 到 G08，是 G-1-0 的前半段（0 到 g08 進度）
    g2_0_line = cut_line_by_progress(g1_0_line_obj, 0, g08_on_g1_0)
    g2_0_coords = list(g2_0_line.coords)
    tracks_data['G-2-0'] = create_track_geojson(
        g2_0_coords, 'G-2-0', 'G-2',
        '松山 → 台電大樓', 'G19', 'G08', TRACK_COLORS['G-2-0']
    )

    # G-2-1: 台電大樓 → 松山（區間）
    g2_1_coords = list(reversed(g2_0_coords))
    tracks_data['G-2-1'] = create_track_geojson(
        g2_1_coords, 'G-2-1', 'G-2',
        '台電大樓 → 松山', 'G08', 'G19', TRACK_COLORS['G-2-1']
    )

    # 儲存軌道檔案
    print("\n儲存軌道檔案...")
    for track_id, data in tracks_data.items():
        filepath = TRACKS_DIR / f"{track_id}.geojson"
        save_json(data, filepath)
        coord_count = len(data['features'][0]['geometry']['coordinates'])
        print(f"  ✅ {track_id}.geojson ({coord_count} 座標點)")

    # 儲存車站檔案
    print("\n儲存車站檔案...")
    stations_geojson = create_stations_geojson(g_stations)
    save_json(stations_geojson, OUTPUT_DIR / "green_line_stations.geojson")
    print(f"  ✅ green_line_stations.geojson ({len(g_stations)} 車站)")

    # 計算 station_progress 並輸出
    print("\n計算 station_progress...")

    # G-1-0: 松山→新店
    g1_0_progress = calculate_station_progress(
        LineString(g1_0_coords), g_stations, reverse=False
    )

    # G-1-1: 新店→松山 (反向)
    g1_1_progress = {k: round(1.0 - v, 6) for k, v in g1_0_progress.items()}

    # G-2 區間車站 (G08-G19)
    g2_stations = [s for s in g_stations if s['station_id'] in
                   ['G08', 'G09', 'G10', 'G11', 'G12', 'G13', 'G14', 'G15', 'G16', 'G17', 'G18', 'G19']]

    # G-2-0: 松山→台電大樓
    g2_0_progress = calculate_station_progress(
        LineString(g2_0_coords), g2_stations, reverse=False
    )

    # G-2-1: 台電大樓→松山 (反向)
    g2_1_progress = {k: round(1.0 - v, 6) for k, v in g2_0_progress.items()}

    print("\n  G-1-0 (松山→新店) station_progress:")
    for sid in STATION_ORDER:
        if sid in g1_0_progress:
            print(f"    {sid}: {g1_0_progress[sid]:.6f}")

    print("\n  G-2-0 (松山→台電大樓) station_progress:")
    for sid in ['G19', 'G18', 'G17', 'G16', 'G15', 'G14', 'G13', 'G12', 'G11', 'G10', 'G09', 'G08']:
        if sid in g2_0_progress:
            print(f"    {sid}: {g2_0_progress[sid]:.6f}")

    # 輸出 station_progress JSON
    station_progress_output = {
        "G-1-0": g1_0_progress,
        "G-1-1": g1_1_progress,
        "G-2-0": g2_0_progress,
        "G-2-1": g2_1_progress
    }
    save_json(station_progress_output, OUTPUT_DIR / "g_line_station_progress.json")
    print("\n  ✅ g_line_station_progress.json")

    # 產生預覽用的合併檔
    print("\n產生預覽檔...")
    all_features = []
    for track_id, data in tracks_data.items():
        all_features.extend(data['features'])

    preview_data = {
        "type": "FeatureCollection",
        "features": all_features
    }
    save_json(preview_data, OUTPUT_DIR / "green_line_tracks_preview.geojson")
    print("  ✅ green_line_tracks_preview.geojson")

    print("\n" + "=" * 60)
    print("G 線軌道提取完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
