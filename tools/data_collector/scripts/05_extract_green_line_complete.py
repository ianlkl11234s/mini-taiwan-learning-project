#!/usr/bin/env python3
"""
05_extract_green_line_complete.py - 提取完整綠線軌道（含小碧潭支線）

修復版本：正確合併所有 segment，包含：
- 主線：松山 G19 ↔ 新店 G01（完整覆蓋）
- 小碧潭支線：七張 G03 ↔ 小碧潭 G03A

Kepler 資料 Segment 分析：
- Segment 0-7: 松山端到台電大樓
- Segment 8: 小碧潭支線 (740點，高密度)
- Segment 9: 七張到景美區段
- Segment 10: 新店端 (G01, G02)

輸出：
- G-1-0/1: 全程車 (松山↔新店)
- G-2-0/1: 區間車 (松山↔台電大樓)
- G-3-0/1: 小碧潭支線 (七張↔小碧潭)
"""

import json
from pathlib import Path
from typing import List, Tuple, Dict, Any
from shapely.geometry import LineString, Point
from shapely.ops import linemerge
import math

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
RAW_DATA_DIR = Path("/Users/migu/Desktop/資料庫/gen_ai_try/ichef_工作用/GIS/mini-taipei/raw_data/mrt")
OUTPUT_DIR = SCRIPT_DIR.parent / "output"
TRACKS_DIR = OUTPUT_DIR / "tracks"

# 綠線顏色
TRACK_COLORS = {
    "G-1-0": "#008659",     # 深綠 - 松山→新店
    "G-1-1": "#33a77c",     # 淺綠 - 新店→松山
    "G-2-0": "#006644",     # 暗綠 - 松山→台電大樓
    "G-2-1": "#66c4a0",     # 淡綠 - 台電大樓→松山
    "G-3-0": "#00a86b",     # 碧綠 - 七張→小碧潭
    "G-3-1": "#7dd4b0",     # 薄綠 - 小碧潭→七張
}

# 主線站點順序 (新店→松山)
MAIN_STATION_ORDER = [
    "G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G09",
    "G10", "G11", "G12", "G13", "G14", "G15", "G16", "G17", "G18", "G19"
]

# 小碧潭支線站點
XIAOBITAN_STATIONS = ["G03", "G03A"]

# 站名對照
STATION_NAMES = {
    "G01": ("新店", "Xindian"),
    "G02": ("新店區公所", "Xindian District Office"),
    "G03": ("七張", "Qizhang"),
    "G03A": ("小碧潭", "Xiaobitan"),
    "G04": ("大坪林", "Dapinglin"),
    "G05": ("景美", "Jingmei"),
    "G06": ("萬隆", "Wanlong"),
    "G07": ("公館", "Gongguan"),
    "G08": ("台電大樓", "Taipower Building"),
    "G09": ("古亭", "Guting"),
    "G10": ("中正紀念堂", "Chiang Kai-Shek Memorial Hall"),
    "G11": ("小南門", "Xiaonanmen"),
    "G12": ("西門", "Ximen"),
    "G13": ("北門", "Beimen"),
    "G14": ("中山", "Zhongshan"),
    "G15": ("松江南京", "Songjiang Nanjing"),
    "G16": ("南京復興", "Nanjing Fuxing"),
    "G17": ("台北小巨蛋", "Taipei Arena"),
    "G18": ("南京三民", "Nanjing Sanmin"),
    "G19": ("松山", "Songshan"),
}

# 小碧潭站座標 (從官方資料)
XIAOBITAN_COORDS = [121.529776, 24.972208]


def load_json(filepath: Path) -> Any:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def distance(p1: List[float], p2: List[float]) -> float:
    """計算兩點距離"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def find_closest_segment_endpoint(segments: List[List], target: List[float], exclude_idx: int = -1) -> Tuple[int, str, float]:
    """找到最接近目標點的 segment 端點"""
    best_idx = -1
    best_end = ""
    best_dist = float('inf')

    for i, seg in enumerate(segments):
        if i == exclude_idx:
            continue

        start_dist = distance(seg[0], target)
        end_dist = distance(seg[-1], target)

        if start_dist < best_dist:
            best_dist = start_dist
            best_idx = i
            best_end = "start"

        if end_dist < best_dist:
            best_dist = end_dist
            best_idx = i
            best_end = "end"

    return best_idx, best_end, best_dist


def manual_merge_mainline(segments: List[List]) -> List[List[float]]:
    """
    手動合併主線 segments，排除小碧潭支線 (Segment 8)

    正確的連接順序（從南到北）：
    Segment 10 (新店端) → Segment 9 → Segment 1 → Segment 0 →
    Segment 7 → Segment 3 → Segment 2 → Segment 4 → Segment 5 → Segment 6 (松山端)
    """
    # 主線 segment 索引 (排除 Segment 8 小碧潭支線)
    # 根據分析，正確順序是：10, 9, 1, 0, 7, 3, 2, 4, 5, 6

    mainline_order = [10, 9, 1, 0, 7, 3, 2, 4, 5, 6]

    merged_coords = []

    for i, seg_idx in enumerate(mainline_order):
        seg = segments[seg_idx]

        if i == 0:
            # 第一段，直接加入
            merged_coords.extend(seg)
        else:
            # 檢查連接方向
            prev_end = merged_coords[-1]

            start_dist = distance(seg[0], prev_end)
            end_dist = distance(seg[-1], prev_end)

            if end_dist < start_dist:
                # 需要反轉
                seg = list(reversed(seg))

            # 跳過第一個點（避免重複）
            merged_coords.extend(seg[1:])

    return merged_coords


def extract_xiaobitan_branch(segments: List[List]) -> List[List[float]]:
    """提取小碧潭支線 (Segment 8)"""
    return segments[8]


def cut_line_by_station(coords: List[List[float]], stations: Dict, start_id: str, end_id: str) -> List[List[float]]:
    """根據起終站切割軌道"""
    line = LineString(coords)

    start_point = Point(stations[start_id])
    end_point = Point(stations[end_id])

    start_progress = line.project(start_point, normalized=True)
    end_progress = line.project(end_point, normalized=True)

    if start_progress > end_progress:
        start_progress, end_progress = end_progress, start_progress

    # 切割
    total_length = line.length
    start_dist = start_progress * total_length
    end_dist = end_progress * total_length

    result_coords = []
    current_dist = 0

    for i in range(len(coords) - 1):
        p1, p2 = coords[i], coords[i + 1]
        seg_length = distance(p1, p2)
        next_dist = current_dist + seg_length

        # 起點
        if current_dist <= start_dist < next_dist:
            ratio = (start_dist - current_dist) / seg_length if seg_length > 0 else 0
            x = p1[0] + ratio * (p2[0] - p1[0])
            y = p1[1] + ratio * (p2[1] - p1[1])
            result_coords.append([x, y])

        # 中間點
        if start_dist <= current_dist < end_dist:
            if not result_coords or result_coords[-1] != p1:
                result_coords.append(list(p1))

        # 終點
        if current_dist < end_dist <= next_dist:
            ratio = (end_dist - current_dist) / seg_length if seg_length > 0 else 0
            x = p1[0] + ratio * (p2[0] - p1[0])
            y = p1[1] + ratio * (p2[1] - p1[1])
            result_coords.append([x, y])
            break

        current_dist = next_dist

    return result_coords if len(result_coords) >= 2 else coords


def create_track_geojson(coords: List, track_id: str, route_id: str, name: str,
                          origin: str, destination: str, color: str) -> Dict:
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


def create_stations_geojson(stations: Dict, station_list: List[str]) -> Dict:
    features = []
    for sid in station_list:
        if sid in stations:
            name_zh, name_en = STATION_NAMES.get(sid, (sid, sid))
            features.append({
                "type": "Feature",
                "properties": {
                    "station_id": sid,
                    "name_zh": name_zh,
                    "name_en": name_en,
                    "line_id": "G"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": stations[sid]
                }
            })
    return {"type": "FeatureCollection", "features": features}


def calculate_station_progress(coords: List, stations: Dict, station_ids: List[str]) -> Dict[str, float]:
    """計算各站在軌道上的進度"""
    line = LineString(coords)
    progress = {}

    for sid in station_ids:
        if sid in stations:
            point = Point(stations[sid])
            p = line.project(point, normalized=True)
            progress[sid] = round(p, 6)

    return progress


def main():
    print("=" * 60)
    print("G 線（松山新店線）完整軌道提取工具 v2")
    print("=" * 60)

    # 載入資料
    print("\n載入資料...")
    routes_data = load_json(RAW_DATA_DIR / "kepler_mrt_routes.geojson")
    stations_data = load_json(RAW_DATA_DIR / "kepler_mrt_stations.geojson")

    # 提取 G 線 segments
    g_segments = None
    for feature in routes_data['features']:
        if feature['properties'].get('line_id') == 'G':
            g_segments = feature['geometry']['coordinates']
            break

    if not g_segments:
        print("錯誤：找不到 G 線資料")
        return

    print(f"  找到 {len(g_segments)} 個 segments")

    # 提取車站座標
    station_coords = {}
    for feature in stations_data['features']:
        sid = feature['properties'].get('station_id', '')
        if sid.startswith('G'):
            station_coords[sid] = feature['geometry']['coordinates']

    # 加入小碧潭站
    station_coords['G03A'] = XIAOBITAN_COORDS
    print(f"  載入 {len(station_coords)} 個車站")

    # === 合併主線 ===
    print("\n合併主線軌道...")
    mainline_coords = manual_merge_mainline(g_segments)
    print(f"  主線座標點數: {len(mainline_coords)}")

    # 檢查方向（G01 應該在軌道尾端，G19 在起點）
    line = LineString(mainline_coords)
    g01_progress = line.project(Point(station_coords['G01']), normalized=True)
    g19_progress = line.project(Point(station_coords['G19']), normalized=True)

    print(f"  G01 (新店) 進度: {g01_progress:.4f}")
    print(f"  G19 (松山) 進度: {g19_progress:.4f}")

    # 確保方向是 松山→新店 (G19 在 0，G01 在 1)
    if g01_progress < g19_progress:
        print("  → 反轉軌道方向")
        mainline_coords = list(reversed(mainline_coords))
        g01_progress, g19_progress = 1 - g01_progress, 1 - g19_progress

    # === 提取小碧潭支線 ===
    print("\n提取小碧潭支線...")
    xiaobitan_coords = extract_xiaobitan_branch(g_segments)
    print(f"  小碧潭支線座標點數: {len(xiaobitan_coords)}")

    # 檢查小碧潭支線方向 (G03 應該在起點)
    xb_line = LineString(xiaobitan_coords)
    g03_on_xb = xb_line.project(Point(station_coords['G03']), normalized=True)
    g03a_on_xb = xb_line.project(Point(station_coords['G03A']), normalized=True)

    print(f"  G03 (七張) 進度: {g03_on_xb:.4f}")
    print(f"  G03A (小碧潭) 進度: {g03a_on_xb:.4f}")

    # 確保方向是 七張→小碧潭 (G03 在 0，G03A 在 1)
    if g03_on_xb > g03a_on_xb:
        print("  → 反轉小碧潭支線方向")
        xiaobitan_coords = list(reversed(xiaobitan_coords))

    # === 建立輸出目錄 ===
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)

    # === 產生軌道檔案 ===
    print("\n產生軌道檔案...")

    tracks_data = {}

    # G-1-0: 松山 → 新店 (全程)
    g1_0_coords = mainline_coords
    tracks_data['G-1-0'] = create_track_geojson(
        g1_0_coords, 'G-1-0', 'G-1', '松山 → 新店', 'G19', 'G01', TRACK_COLORS['G-1-0']
    )

    # G-1-1: 新店 → 松山 (全程)
    g1_1_coords = list(reversed(mainline_coords))
    tracks_data['G-1-1'] = create_track_geojson(
        g1_1_coords, 'G-1-1', 'G-1', '新店 → 松山', 'G01', 'G19', TRACK_COLORS['G-1-1']
    )

    # G-2: 區間車 (松山 ↔ 台電大樓)
    g08_progress = line.project(Point(station_coords['G08']), normalized=True)
    g2_0_coords = cut_line_by_station(mainline_coords, station_coords, 'G19', 'G08')
    tracks_data['G-2-0'] = create_track_geojson(
        g2_0_coords, 'G-2-0', 'G-2', '松山 → 台電大樓', 'G19', 'G08', TRACK_COLORS['G-2-0']
    )

    g2_1_coords = list(reversed(g2_0_coords))
    tracks_data['G-2-1'] = create_track_geojson(
        g2_1_coords, 'G-2-1', 'G-2', '台電大樓 → 松山', 'G08', 'G19', TRACK_COLORS['G-2-1']
    )

    # G-3: 小碧潭支線 (七張 ↔ 小碧潭)
    g3_0_coords = xiaobitan_coords
    tracks_data['G-3-0'] = create_track_geojson(
        g3_0_coords, 'G-3-0', 'G-3', '七張 → 小碧潭', 'G03', 'G03A', TRACK_COLORS['G-3-0']
    )

    g3_1_coords = list(reversed(xiaobitan_coords))
    tracks_data['G-3-1'] = create_track_geojson(
        g3_1_coords, 'G-3-1', 'G-3', '小碧潭 → 七張', 'G03A', 'G03', TRACK_COLORS['G-3-1']
    )

    # 儲存軌道
    for track_id, data in tracks_data.items():
        filepath = TRACKS_DIR / f"{track_id}.geojson"
        save_json(data, filepath)
        coord_count = len(data['features'][0]['geometry']['coordinates'])
        print(f"  ✅ {track_id}.geojson ({coord_count} 座標點)")

    # === 產生車站檔案 ===
    print("\n產生車站檔案...")
    all_stations = MAIN_STATION_ORDER + ['G03A']
    stations_geojson = create_stations_geojson(station_coords, all_stations)
    save_json(stations_geojson, OUTPUT_DIR / "green_line_stations.geojson")
    print(f"  ✅ green_line_stations.geojson ({len(all_stations)} 車站)")

    # === 計算 station_progress ===
    print("\n計算 station_progress...")

    # G-1-0
    g1_0_progress = calculate_station_progress(g1_0_coords, station_coords, MAIN_STATION_ORDER)
    g1_1_progress = {k: round(1.0 - v, 6) for k, v in g1_0_progress.items()}

    # G-2
    g2_stations = ['G08', 'G09', 'G10', 'G11', 'G12', 'G13', 'G14', 'G15', 'G16', 'G17', 'G18', 'G19']
    g2_0_progress = calculate_station_progress(g2_0_coords, station_coords, g2_stations)
    g2_1_progress = {k: round(1.0 - v, 6) for k, v in g2_0_progress.items()}

    # G-3
    g3_0_progress = calculate_station_progress(g3_0_coords, station_coords, XIAOBITAN_STATIONS)
    g3_1_progress = {k: round(1.0 - v, 6) for k, v in g3_0_progress.items()}

    station_progress_output = {
        "G-1-0": g1_0_progress,
        "G-1-1": g1_1_progress,
        "G-2-0": g2_0_progress,
        "G-2-1": g2_1_progress,
        "G-3-0": g3_0_progress,
        "G-3-1": g3_1_progress,
    }

    save_json(station_progress_output, OUTPUT_DIR / "g_line_station_progress.json")
    print("  ✅ g_line_station_progress.json")

    # 顯示進度
    print("\n  G-1-0 station_progress:")
    for sid in MAIN_STATION_ORDER:
        if sid in g1_0_progress:
            print(f"    {sid}: {g1_0_progress[sid]:.6f}")

    print("\n  G-3-0 station_progress:")
    for sid in XIAOBITAN_STATIONS:
        if sid in g3_0_progress:
            print(f"    {sid}: {g3_0_progress[sid]:.6f}")

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
