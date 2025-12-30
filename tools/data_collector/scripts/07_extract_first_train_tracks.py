#!/usr/bin/env python3
"""
07_extract_first_train_tracks.py - 提取 BL 和 G 線首班車軌道

從主要軌道 (BL-1, G-1) 中提取首班車軌道區段

BL 線首班車:
- BL-3-0: 新埔(BL08) → 南港展覽館(BL23)
- BL-4-0: 台北車站(BL12) → 南港展覽館(BL23)
- BL-5-0: 忠孝復興(BL15) → 南港展覽館(BL23)
- BL-6-0: 市政府(BL18) → 南港展覽館(BL23)
- BL-7-0: 南港(BL22) → 南港展覽館(BL23)
- BL-8-1: 永寧(BL02) → 頂埔(BL01)
- BL-9-1: 亞東醫院(BL05) → 頂埔(BL01)
- BL-10-1: 江子翠(BL09) → 頂埔(BL01)
- BL-11-1: 台北車站(BL12) → 頂埔(BL01)
- BL-12-1: 國父紀念館(BL17) → 頂埔(BL01)
- BL-13-1: 後山埤(BL20) → 頂埔(BL01)

G 線首班車:
- G-4-0: 七張(G03) → 新店(G01)
- G-5-0: 台電大樓(G08) → 新店(G01)
- G-6-0: 西門(G12) → 新店(G01)
- G-7-0: 中山(G14) → 新店(G01)
- G-8-1: 大坪林(G04) → 松山(G19)
- G-9-1: 公館(G07) → 松山(G19)
- G-10-1: 中正紀念堂(G10) → 松山(G19)
- G-11-1: 北門(G13) → 松山(G19)
- G-12-1: 南京復興(G16) → 松山(G19)
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from shapely.geometry import LineString, Point
from shapely.ops import substring

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
PUBLIC_DIR = PROJECT_ROOT / "public" / "data"
TRACKS_DIR = PUBLIC_DIR / "tracks"

# BL 線首班車路線
BL_FIRST_TRAIN_ROUTES = {
    # === 往南港展覽館 (direction=0) ===
    ("BL08", "BL23"): ("BL-3", 0),
    ("BL12", "BL23"): ("BL-4", 0),
    ("BL15", "BL23"): ("BL-5", 0),
    ("BL18", "BL23"): ("BL-6", 0),
    ("BL22", "BL23"): ("BL-7", 0),
    # === 往頂埔 (direction=1) ===
    ("BL02", "BL01"): ("BL-8", 1),
    ("BL05", "BL01"): ("BL-9", 1),
    ("BL09", "BL01"): ("BL-10", 1),
    ("BL12", "BL01"): ("BL-11", 1),
    ("BL17", "BL01"): ("BL-12", 1),
    ("BL20", "BL01"): ("BL-13", 1),
}

# G 線首班車路線
G_FIRST_TRAIN_ROUTES = {
    # === 往新店 (direction=0) ===
    ("G03", "G01"): ("G-4", 0),
    ("G08", "G01"): ("G-5", 0),
    ("G12", "G01"): ("G-6", 0),
    ("G14", "G01"): ("G-7", 0),
    # === 往松山 (direction=1) ===
    ("G04", "G19"): ("G-8", 1),
    ("G07", "G19"): ("G-9", 1),
    ("G10", "G19"): ("G-10", 1),
    ("G13", "G19"): ("G-11", 1),
    ("G16", "G19"): ("G-12", 1),
}

# 站名對照
BL_STATION_NAMES = {
    "BL01": "頂埔", "BL02": "永寧", "BL03": "土城", "BL04": "海山",
    "BL05": "亞東醫院", "BL06": "府中", "BL07": "板橋", "BL08": "新埔",
    "BL09": "江子翠", "BL10": "龍山寺", "BL11": "西門", "BL12": "台北車站",
    "BL13": "善導寺", "BL14": "忠孝新生", "BL15": "忠孝復興", "BL16": "忠孝敦化",
    "BL17": "國父紀念館", "BL18": "市政府", "BL19": "永春", "BL20": "後山埤",
    "BL21": "昆陽", "BL22": "南港", "BL23": "南港展覽館"
}

G_STATION_NAMES = {
    "G01": "新店", "G02": "新店區公所", "G03": "七張", "G03A": "小碧潭",
    "G04": "大坪林", "G05": "景美", "G06": "萬隆", "G07": "公館",
    "G08": "台電大樓", "G09": "古亭", "G10": "中正紀念堂", "G11": "小南門",
    "G12": "西門", "G13": "北門", "G14": "中山", "G15": "松江南京",
    "G16": "南京復興", "G17": "台北小巨蛋", "G18": "南京三民", "G19": "松山"
}


def load_json(filepath: Path) -> Any:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_substring_track(base_track_coords: List, station_coords: Dict,
                            start_station: str, end_station: str) -> List:
    """
    從基礎軌道中提取子區段
    """
    line = LineString(base_track_coords)

    start_point = Point(station_coords[start_station])
    end_point = Point(station_coords[end_station])

    start_dist = line.project(start_point)
    end_dist = line.project(end_point)

    # 確保 start_dist < end_dist
    if start_dist > end_dist:
        start_dist, end_dist = end_dist, start_dist
        # 提取後反轉
        extracted = substring(line, start_dist, end_dist)
        return list(reversed(list(extracted.coords)))
    else:
        extracted = substring(line, start_dist, end_dist)
        return list(extracted.coords)


def create_track_geojson(coords: List, track_id: str, route_id: str,
                         origin: str, destination: str, line_id: str) -> Dict:
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "route_id": route_id,
                "direction": int(track_id.split('-')[-1]),
                "line_id": line_id,
                "origin": origin,
                "destination": destination
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[c[0], c[1]] for c in coords]
            }
        }]
    }


def calculate_station_progress(coords: List, station_coords: Dict,
                               station_ids: List[str]) -> Dict[str, float]:
    """計算各站在軌道上的進度"""
    line = LineString(coords)
    progress = {}

    for sid in station_ids:
        if sid in station_coords:
            point = Point(station_coords[sid])
            p = line.project(point, normalized=True)
            progress[sid] = round(p, 6)

    return progress


def get_stations_between(start: str, end: str, all_stations: List[str]) -> List[str]:
    """取得起訖站之間的站點列表"""
    try:
        start_idx = all_stations.index(start)
        end_idx = all_stations.index(end)

        if start_idx <= end_idx:
            return all_stations[start_idx:end_idx + 1]
        else:
            return list(reversed(all_stations[end_idx:start_idx + 1]))
    except ValueError:
        return [start, end]


def main():
    print("=" * 70)
    print("BL 和 G 線首班車軌道提取工具")
    print("=" * 70)

    # 載入車站資料
    print("\n載入車站資料...")
    bl_stations = load_json(PUBLIC_DIR / "blue_line_stations.geojson")
    g_stations = load_json(PUBLIC_DIR / "green_line_stations.geojson")

    # 提取車站座標
    bl_station_coords = {}
    for feature in bl_stations['features']:
        sid = feature['properties'].get('station_id', '')
        if sid:
            bl_station_coords[sid] = feature['geometry']['coordinates']

    g_station_coords = {}
    for feature in g_stations['features']:
        sid = feature['properties'].get('station_id', '')
        if sid:
            g_station_coords[sid] = feature['geometry']['coordinates']

    print(f"  BL 線: {len(bl_station_coords)} 站")
    print(f"  G 線: {len(g_station_coords)} 站")

    # 載入基礎軌道
    print("\n載入基礎軌道...")
    bl1_0 = load_json(TRACKS_DIR / "BL-1-0.geojson")
    bl1_1 = load_json(TRACKS_DIR / "BL-1-1.geojson")
    g1_0 = load_json(TRACKS_DIR / "G-1-0.geojson")
    g1_1 = load_json(TRACKS_DIR / "G-1-1.geojson")

    bl1_0_coords = bl1_0['features'][0]['geometry']['coordinates']
    bl1_1_coords = bl1_1['features'][0]['geometry']['coordinates']
    g1_0_coords = g1_0['features'][0]['geometry']['coordinates']
    g1_1_coords = g1_1['features'][0]['geometry']['coordinates']

    print(f"  BL-1-0: {len(bl1_0_coords)} 座標點")
    print(f"  BL-1-1: {len(bl1_1_coords)} 座標點")
    print(f"  G-1-0: {len(g1_0_coords)} 座標點")
    print(f"  G-1-1: {len(g1_1_coords)} 座標點")

    # BL 線站點順序
    BL_STATION_ORDER = [
        "BL01", "BL02", "BL03", "BL04", "BL05", "BL06", "BL07", "BL08", "BL09",
        "BL10", "BL11", "BL12", "BL13", "BL14", "BL15", "BL16", "BL17", "BL18",
        "BL19", "BL20", "BL21", "BL22", "BL23"
    ]

    # G 線站點順序
    G_STATION_ORDER = [
        "G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G09",
        "G10", "G11", "G12", "G13", "G14", "G15", "G16", "G17", "G18", "G19"
    ]

    # 載入現有 station_progress
    progress_file = PUBLIC_DIR / "station_progress.json"
    if progress_file.exists():
        station_progress = load_json(progress_file)
    else:
        station_progress = {}

    # === 處理 BL 線首班車 ===
    print("\n" + "=" * 40)
    print("處理 BL 線首班車軌道")
    print("=" * 40)

    for (start, end), (route_id, direction) in BL_FIRST_TRAIN_ROUTES.items():
        track_id = f"{route_id}-{direction}"
        start_name = BL_STATION_NAMES.get(start, start)
        end_name = BL_STATION_NAMES.get(end, end)

        print(f"\n  {track_id}: {start_name}({start}) → {end_name}({end})")

        # 選擇基礎軌道
        if direction == 0:
            # 往南港展覽館: 使用 BL-1-0 (也是往南港展覽館)
            base_coords = bl1_0_coords
        else:
            # 往頂埔: 使用 BL-1-1 (也是往頂埔)
            base_coords = bl1_1_coords

        # 提取子區段
        try:
            extracted_coords = extract_substring_track(base_coords, bl_station_coords, start, end)
            print(f"    提取 {len(extracted_coords)} 座標點")

            # 建立 GeoJSON
            geojson = create_track_geojson(extracted_coords, track_id, route_id, start, end, "BL")

            # 儲存
            save_json(geojson, TRACKS_DIR / f"{track_id}.geojson")
            print(f"    ✅ {track_id}.geojson")

            # 計算 station_progress
            stations_in_route = get_stations_between(start, end, BL_STATION_ORDER)
            progress = calculate_station_progress(extracted_coords, bl_station_coords, stations_in_route)
            station_progress[track_id] = progress

            # 顯示起終站進度
            origin_progress = progress.get(start, 'N/A')
            dest_progress = progress.get(end, 'N/A')
            print(f"    station_progress: {start}={origin_progress}, {end}={dest_progress}")

        except Exception as e:
            print(f"    ❌ 錯誤: {e}")

    # === 處理 G 線首班車 ===
    print("\n" + "=" * 40)
    print("處理 G 線首班車軌道")
    print("=" * 40)

    for (start, end), (route_id, direction) in G_FIRST_TRAIN_ROUTES.items():
        track_id = f"{route_id}-{direction}"
        start_name = G_STATION_NAMES.get(start, start)
        end_name = G_STATION_NAMES.get(end, end)

        print(f"\n  {track_id}: {start_name}({start}) → {end_name}({end})")

        # 選擇基礎軌道
        if direction == 0:
            # 往新店: 使用 G-1-0 (也是往新店)
            base_coords = g1_0_coords
        else:
            # 往松山: 使用 G-1-1 (也是往松山)
            base_coords = g1_1_coords

        # 提取子區段
        try:
            extracted_coords = extract_substring_track(base_coords, g_station_coords, start, end)
            print(f"    提取 {len(extracted_coords)} 座標點")

            # 建立 GeoJSON
            geojson = create_track_geojson(extracted_coords, track_id, route_id, start, end, "G")

            # 儲存
            save_json(geojson, TRACKS_DIR / f"{track_id}.geojson")
            print(f"    ✅ {track_id}.geojson")

            # 計算 station_progress
            stations_in_route = get_stations_between(start, end, G_STATION_ORDER)
            progress = calculate_station_progress(extracted_coords, g_station_coords, stations_in_route)
            station_progress[track_id] = progress

            # 顯示起終站進度
            origin_progress = progress.get(start, 'N/A')
            dest_progress = progress.get(end, 'N/A')
            print(f"    station_progress: {start}={origin_progress}, {end}={dest_progress}")

        except Exception as e:
            print(f"    ❌ 錯誤: {e}")

    # 儲存更新的 station_progress
    print("\n更新 station_progress.json...")
    save_json(station_progress, progress_file)
    print(f"  ✅ station_progress.json (共 {len(station_progress)} 軌道)")

    # 統計
    print("\n" + "=" * 70)
    print("完成！")
    print("=" * 70)

    bl_count = sum(1 for k in station_progress if k.startswith('BL-') and int(k.split('-')[1]) >= 3)
    g_count = sum(1 for k in station_progress if k.startswith('G-') and int(k.split('-')[1]) >= 4)

    print(f"\n產生的首班車軌道:")
    print(f"  BL 線: {bl_count} 條")
    print(f"  G 線: {g_count} 條")


if __name__ == "__main__":
    main()
