#!/usr/bin/env python3
"""
06_extract_orange_line_tracks.py - 提取中和新蘆線 (O線) 軌道

O 線是 Y 形結構：
- 共用段: O01 南勢角 ↔ O12 大橋頭 (12 站)
- 新莊支線: O12 大橋頭 ↔ O21 迴龍 (10 站, O13-O21)
- 蘆洲支線: O12 大橋頭 ↔ O54 蘆洲 (5 站, O50-O54)

Kepler Segments 分析:
- 共用段: Segments 6→5→4→3→2→1→0→7 (從南到北)
- 新莊線: Segments 8→9→10→12 (從 O12 到 O21)
- 蘆洲線: Segment 11 (從 O12 到 O54)

輸出:
- O-1-0/1: 新莊線全程 (迴龍↔南勢角, 21 站)
- O-2-0/1: 蘆洲線全程 (蘆洲↔南勢角, 17 站)
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from shapely.geometry import LineString, Point
from shapely.ops import substring
import math

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
RAW_DATA_DIR = Path("/Users/migu/Desktop/資料庫/gen_ai_try/ichef_工作用/GIS/mini-taipei/raw_data/mrt")
OUTPUT_DIR = SCRIPT_DIR.parent / "output"
TRACKS_DIR = OUTPUT_DIR / "tracks"
PUBLIC_DIR = PROJECT_ROOT / "public" / "data"

# O 線顏色
TRACK_COLORS = {
    "O-1-0": "#f8b61c",     # 橘黃 - 迴龍→南勢角
    "O-1-1": "#fac94c",     # 淺橘 - 南勢角→迴龍
    "O-2-0": "#e5a010",     # 深橘 - 蘆洲→南勢角
    "O-2-1": "#ffd966",     # 淡橘 - 南勢角→蘆洲
}

# 新莊線站點順序 (O01-O21)
XINZHUANG_STATIONS = [
    "O01", "O02", "O03", "O04", "O05", "O06", "O07", "O08", "O09",
    "O10", "O11", "O12", "O13", "O14", "O15", "O16", "O17", "O18",
    "O19", "O20", "O21"
]

# 蘆洲線站點順序 (O01-O12 + O50-O54)
LUZHOU_STATIONS = [
    "O01", "O02", "O03", "O04", "O05", "O06", "O07", "O08", "O09",
    "O10", "O11", "O12", "O50", "O51", "O52", "O53", "O54"
]

# 共用段站點 (O01-O12)
SHARED_STATIONS = [
    "O01", "O02", "O03", "O04", "O05", "O06", "O07", "O08", "O09",
    "O10", "O11", "O12"
]

# 站名對照
STATION_NAMES = {
    "O01": ("南勢角", "Nanshijiao"),
    "O02": ("景安", "Jingan"),
    "O03": ("永安市場", "Yongan Market"),
    "O04": ("頂溪", "Dingxi"),
    "O05": ("古亭", "Guting"),
    "O06": ("東門", "Dongmen"),
    "O07": ("忠孝新生", "Zhongxiao Xinsheng"),
    "O08": ("松江南京", "Songjiang Nanjing"),
    "O09": ("行天宮", "Xingtian Temple"),
    "O10": ("中山國小", "Zhongshan Elementary School"),
    "O11": ("民權西路", "Minquan W. Rd."),
    "O12": ("大橋頭", "Daqiaotou"),
    "O13": ("台北橋", "Taipei Bridge"),
    "O14": ("菜寮", "Cailiao"),
    "O15": ("三重", "Sanchong"),
    "O16": ("先嗇宮", "Xianse Temple"),
    "O17": ("頭前庄", "Touqianzhuang"),
    "O18": ("新莊", "Xinzhuang"),
    "O19": ("輔大", "Fu Jen University"),
    "O20": ("丹鳳", "Danfeng"),
    "O21": ("迴龍", "Huilong"),
    "O50": ("三重國小", "Sanchong Elementary School"),
    "O51": ("三和國中", "Sanhe Junior High School"),
    "O52": ("徐匯中學", "St. Ignatius High School"),
    "O53": ("三民高中", "Sanmin Senior High School"),
    "O54": ("蘆洲", "Luzhou"),
}


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


def merge_segments(segments: List[List], order: List[int], reverse_flags: List[bool] = None) -> List[List[float]]:
    """
    按指定順序合併 segments

    Args:
        segments: 所有 segments
        order: segment 索引順序
        reverse_flags: 是否需要反轉各 segment (可選)
    """
    merged_coords = []

    for i, seg_idx in enumerate(order):
        seg = list(segments[seg_idx])

        # 如果指定了反轉標記，按標記處理
        if reverse_flags and reverse_flags[i]:
            seg = list(reversed(seg))

        if i == 0:
            merged_coords.extend(seg)
        else:
            # 檢查連接方向
            prev_end = merged_coords[-1]
            start_dist = distance(seg[0], prev_end)
            end_dist = distance(seg[-1], prev_end)

            if end_dist < start_dist:
                seg = list(reversed(seg))

            # 跳過第一個點避免重複
            merged_coords.extend(seg[1:])

    return merged_coords


def create_track_geojson(coords: List, track_id: str, route_id: str, name: str,
                         origin: str, destination: str, color: str) -> Dict:
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "route_id": route_id,
                "line_id": "O",
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
                    "line_id": "O"
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


def trim_track_to_stations(coords: List, stations: Dict, start_station: str, end_station: str) -> List:
    """
    裁剪軌道至起訖站位置

    Args:
        coords: 原始軌道座標
        stations: 車站座標字典
        start_station: 起點站 ID
        end_station: 終點站 ID

    Returns:
        裁剪後的座標列表
    """
    line = LineString(coords)

    # 計算起訖站在軌道上的投影位置
    start_point = Point(stations[start_station])
    end_point = Point(stations[end_station])

    start_dist = line.project(start_point)
    end_dist = line.project(end_point)

    # 確保 start_dist < end_dist
    if start_dist > end_dist:
        start_dist, end_dist = end_dist, start_dist

    # 使用 substring 裁剪軌道
    trimmed_line = substring(line, start_dist, end_dist)

    # 轉換為座標列表
    return list(trimmed_line.coords)


def main():
    print("=" * 70)
    print("O 線（中和新蘆線）軌道提取工具")
    print("=" * 70)

    # 載入資料
    print("\n載入資料...")
    routes_data = load_json(RAW_DATA_DIR / "kepler_mrt_routes.geojson")
    stations_data = load_json(RAW_DATA_DIR / "kepler_mrt_stations.geojson")

    # 提取 O 線 segments
    o_segments = None
    for feature in routes_data['features']:
        if feature['properties'].get('line_id') == 'O':
            o_segments = feature['geometry']['coordinates']
            break

    if not o_segments:
        print("錯誤：找不到 O 線資料")
        return

    print(f"  找到 {len(o_segments)} 個 segments")

    # 提取車站座標
    station_coords = {}
    for feature in stations_data['features']:
        sid = feature['properties'].get('station_id', '')
        if sid.startswith('O'):
            station_coords[sid] = feature['geometry']['coordinates']

    print(f"  載入 {len(station_coords)} 個車站")

    # 分析 segments 結構
    print("\n分析 segments 結構...")
    for i, seg in enumerate(o_segments):
        lats = [c[1] for c in seg]
        lngs = [c[0] for c in seg]
        print(f"  Segment {i:2d}: lat {min(lats):.4f}~{max(lats):.4f}, "
              f"lng {min(lngs):.4f}~{max(lngs):.4f}, 點數 {len(seg):4d}")

    # === 合併共用段 (O01→O12) ===
    print("\n合併共用段 (O01→O12)...")
    # 根據分析：從南到北是 6→5→4→3→2→1→0→7
    shared_order = [6, 5, 4, 3, 2, 1, 0, 7]
    shared_coords = merge_segments(o_segments, shared_order)
    print(f"  共用段座標點數: {len(shared_coords)}")

    # 檢查方向 (O01 應在起點，O12 在終點)
    shared_line = LineString(shared_coords)
    o01_progress = shared_line.project(Point(station_coords['O01']), normalized=True)
    o12_progress = shared_line.project(Point(station_coords['O12']), normalized=True)

    print(f"  O01 進度: {o01_progress:.4f}, O12 進度: {o12_progress:.4f}")

    if o01_progress > o12_progress:
        print("  → 反轉共用段方向")
        shared_coords = list(reversed(shared_coords))

    # === 合併新莊支線 (O12→O21) ===
    print("\n合併新莊支線 (O12→O21)...")
    # Segments 8, 9, 10, 12
    xinzhuang_branch_order = [8, 9, 10, 12]
    xinzhuang_branch_coords = merge_segments(o_segments, xinzhuang_branch_order)
    print(f"  新莊支線座標點數: {len(xinzhuang_branch_coords)}")

    # 檢查方向 (應該從 O12 接近的一端開始)
    xz_line = LineString(xinzhuang_branch_coords)
    o12_on_xz = xz_line.project(Point(station_coords['O12']), normalized=True)
    o21_on_xz = xz_line.project(Point(station_coords['O21']), normalized=True)

    print(f"  O12 進度: {o12_on_xz:.4f}, O21 進度: {o21_on_xz:.4f}")

    if o12_on_xz > o21_on_xz:
        print("  → 反轉新莊支線方向")
        xinzhuang_branch_coords = list(reversed(xinzhuang_branch_coords))

    # === 提取蘆洲支線 (O12→O54) ===
    print("\n提取蘆洲支線 (O12→O54)...")
    # Segment 11
    luzhou_branch_coords = list(o_segments[11])
    print(f"  蘆洲支線座標點數: {len(luzhou_branch_coords)}")

    # 檢查方向
    lz_line = LineString(luzhou_branch_coords)
    o12_on_lz = lz_line.project(Point(station_coords['O12']), normalized=True)
    o54_on_lz = lz_line.project(Point(station_coords['O54']), normalized=True)

    print(f"  O12 進度: {o12_on_lz:.4f}, O54 進度: {o54_on_lz:.4f}")

    if o12_on_lz > o54_on_lz:
        print("  → 反轉蘆洲支線方向")
        luzhou_branch_coords = list(reversed(luzhou_branch_coords))

    # === 連接共用段與支線 ===
    print("\n連接軌道...")

    # 找到共用段終點與支線起點的連接
    shared_end = shared_coords[-1]
    xz_start = xinzhuang_branch_coords[0]
    lz_start = luzhou_branch_coords[0]

    print(f"  共用段終點: ({shared_end[0]:.4f}, {shared_end[1]:.4f})")
    print(f"  新莊支線起點: ({xz_start[0]:.4f}, {xz_start[1]:.4f})")
    print(f"  蘆洲支線起點: ({lz_start[0]:.4f}, {lz_start[1]:.4f})")

    # 計算連接距離
    xz_gap = distance(shared_end, xz_start) * 111  # 轉換為 km
    lz_gap = distance(shared_end, lz_start) * 111

    print(f"  新莊支線間隙: {xz_gap:.2f} km")
    print(f"  蘆洲支線間隙: {lz_gap:.2f} km")

    # O-1: 新莊線全程 (O01→O21)
    # 共用段 + 新莊支線
    o1_coords_raw = shared_coords + xinzhuang_branch_coords[1:]  # 跳過支線第一點避免重複

    # O-2: 蘆洲線全程 (O01→O54)
    # 共用段 + 蘆洲支線
    o2_coords_raw = shared_coords + luzhou_branch_coords[1:]  # 跳過支線第一點避免重複

    print(f"\n  O-1 (新莊線) 原始座標點數: {len(o1_coords_raw)}")
    print(f"  O-2 (蘆洲線) 原始座標點數: {len(o2_coords_raw)}")

    # === 裁剪軌道至終點站 ===
    print("\n裁剪軌道至終點站...")

    # 裁剪 O-1 (O01↔O21)
    o1_coords = trim_track_to_stations(o1_coords_raw, station_coords, 'O01', 'O21')
    print(f"  O-1 裁剪後座標點數: {len(o1_coords)}")

    # 裁剪 O-2 (O01↔O54)
    o2_coords = trim_track_to_stations(o2_coords_raw, station_coords, 'O01', 'O54')
    print(f"  O-2 裁剪後座標點數: {len(o2_coords)}")

    # === 驗證軌道 ===
    print("\n驗證軌道...")

    o1_line = LineString(o1_coords)
    o2_line = LineString(o2_coords)

    # O-1 驗證
    o01_on_o1 = o1_line.project(Point(station_coords['O01']), normalized=True)
    o21_on_o1 = o1_line.project(Point(station_coords['O21']), normalized=True)
    print(f"  O-1: O01={o01_on_o1:.4f}, O21={o21_on_o1:.4f}")

    # O-2 驗證
    o01_on_o2 = o2_line.project(Point(station_coords['O01']), normalized=True)
    o54_on_o2 = o2_line.project(Point(station_coords['O54']), normalized=True)
    print(f"  O-2: O01={o01_on_o2:.4f}, O54={o54_on_o2:.4f}")

    # === 建立輸出目錄 ===
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)

    # === 產生軌道檔案 ===
    print("\n產生軌道檔案...")

    tracks_data = {}

    # O-1-0: 迴龍 → 南勢角 (反向，從北到南)
    o1_0_coords = list(reversed(o1_coords))
    tracks_data['O-1-0'] = create_track_geojson(
        o1_0_coords, 'O-1-0', 'O-1', '迴龍 → 南勢角', 'O21', 'O01', TRACK_COLORS['O-1-0']
    )

    # O-1-1: 南勢角 → 迴龍
    o1_1_coords = o1_coords
    tracks_data['O-1-1'] = create_track_geojson(
        o1_1_coords, 'O-1-1', 'O-1', '南勢角 → 迴龍', 'O01', 'O21', TRACK_COLORS['O-1-1']
    )

    # O-2-0: 蘆洲 → 南勢角 (反向)
    o2_0_coords = list(reversed(o2_coords))
    tracks_data['O-2-0'] = create_track_geojson(
        o2_0_coords, 'O-2-0', 'O-2', '蘆洲 → 南勢角', 'O54', 'O01', TRACK_COLORS['O-2-0']
    )

    # O-2-1: 南勢角 → 蘆洲
    o2_1_coords = o2_coords
    tracks_data['O-2-1'] = create_track_geojson(
        o2_1_coords, 'O-2-1', 'O-2', '南勢角 → 蘆洲', 'O01', 'O54', TRACK_COLORS['O-2-1']
    )

    # 儲存軌道
    for track_id, data in tracks_data.items():
        filepath = TRACKS_DIR / f"{track_id}.geojson"
        save_json(data, filepath)
        coord_count = len(data['features'][0]['geometry']['coordinates'])
        print(f"  ✅ {track_id}.geojson ({coord_count} 座標點)")

    # === 產生車站檔案 ===
    print("\n產生車站檔案...")
    all_stations = list(set(XINZHUANG_STATIONS + LUZHOU_STATIONS))
    all_stations.sort(key=lambda x: (0, int(x[1:])) if int(x[1:]) < 50 else (1, int(x[1:])))

    stations_geojson = create_stations_geojson(station_coords, all_stations)
    save_json(stations_geojson, OUTPUT_DIR / "orange_line_stations.geojson")
    print(f"  ✅ orange_line_stations.geojson ({len(all_stations)} 車站)")

    # === 計算 station_progress ===
    print("\n計算 station_progress...")

    # O-1-0: 迴龍→南勢角 (O21 在起點 0, O01 在終點 1)
    o1_0_progress = calculate_station_progress(o1_0_coords, station_coords, list(reversed(XINZHUANG_STATIONS)))

    # O-1-1: 南勢角→迴龍 (O01 在起點 0, O21 在終點 1)
    o1_1_progress = calculate_station_progress(o1_1_coords, station_coords, XINZHUANG_STATIONS)

    # O-2-0: 蘆洲→南勢角 (O54 在起點 0, O01 在終點 1)
    o2_0_progress = calculate_station_progress(o2_0_coords, station_coords, list(reversed(LUZHOU_STATIONS)))

    # O-2-1: 南勢角→蘆洲 (O01 在起點 0, O54 在終點 1)
    o2_1_progress = calculate_station_progress(o2_1_coords, station_coords, LUZHOU_STATIONS)

    station_progress_output = {
        "O-1-0": o1_0_progress,
        "O-1-1": o1_1_progress,
        "O-2-0": o2_0_progress,
        "O-2-1": o2_1_progress,
    }

    save_json(station_progress_output, OUTPUT_DIR / "o_line_station_progress.json")
    print("  ✅ o_line_station_progress.json")

    # 顯示進度
    print("\n  O-1-0 (迴龍→南勢角) station_progress:")
    for sid in list(reversed(XINZHUANG_STATIONS))[:5]:
        if sid in o1_0_progress:
            print(f"    {sid}: {o1_0_progress[sid]:.6f}")
    print("    ...")
    for sid in list(reversed(XINZHUANG_STATIONS))[-3:]:
        if sid in o1_0_progress:
            print(f"    {sid}: {o1_0_progress[sid]:.6f}")

    print("\n  O-2-0 (蘆洲→南勢角) station_progress:")
    for sid in list(reversed(LUZHOU_STATIONS))[:5]:
        if sid in o2_0_progress:
            print(f"    {sid}: {o2_0_progress[sid]:.6f}")
    print("    ...")
    for sid in list(reversed(LUZHOU_STATIONS))[-3:]:
        if sid in o2_0_progress:
            print(f"    {sid}: {o2_0_progress[sid]:.6f}")

    # === 複製到 public 目錄 ===
    print("\n複製到 public 目錄...")

    # 複製軌道
    public_tracks_dir = PUBLIC_DIR / "tracks"
    public_tracks_dir.mkdir(parents=True, exist_ok=True)

    for track_id in tracks_data.keys():
        src = TRACKS_DIR / f"{track_id}.geojson"
        dst = public_tracks_dir / f"{track_id}.geojson"
        save_json(load_json(src), dst)
        print(f"  ✅ {track_id}.geojson → public/data/tracks/")

    # 複製車站
    src_stations = OUTPUT_DIR / "orange_line_stations.geojson"
    dst_stations = PUBLIC_DIR / "orange_line_stations.geojson"
    save_json(load_json(src_stations), dst_stations)
    print(f"  ✅ orange_line_stations.geojson → public/data/")

    # 更新 station_progress.json
    print("\n更新 station_progress.json...")
    progress_file = PUBLIC_DIR / "station_progress.json"
    if progress_file.exists():
        existing_progress = load_json(progress_file)
    else:
        existing_progress = {}

    existing_progress.update(station_progress_output)
    save_json(existing_progress, progress_file)
    print(f"  ✅ station_progress.json 已更新")

    print("\n" + "=" * 70)
    print("O 線軌道提取完成！")
    print("=" * 70)
    print(f"""
產生的檔案:
- public/data/tracks/O-1-0.geojson (迴龍→南勢角)
- public/data/tracks/O-1-1.geojson (南勢角→迴龍)
- public/data/tracks/O-2-0.geojson (蘆洲→南勢角)
- public/data/tracks/O-2-1.geojson (南勢角→蘆洲)
- public/data/orange_line_stations.geojson
- public/data/station_progress.json (已更新)

下一步:
1. 執行時刻表轉換腳本
2. 更新 useData.ts 和 App.tsx
""")


if __name__ == "__main__":
    main()
