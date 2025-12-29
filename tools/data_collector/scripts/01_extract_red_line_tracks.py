#!/usr/bin/env python3
"""
01_extract_red_line_tracks.py - 提取紅線各路線軌道

從完整的紅線軌道幾何中，根據各營運路線的起迄站，
切割出對應的軌道段落。

原始資料分析結果：
- 線段 0: 新北投支線 (37點, 約1.14km)
- 線段 1-10: 主線各段

輸入：
- kepler_mrt_routes.geojson: 完整軌道幾何
- trtc_stations.json: 車站座標
- trtc_routes.json: 路線定義

輸出：
- output/tracks/R-1-0.geojson: 象山→淡水
- output/tracks/R-1-1.geojson: 淡水→象山
- output/tracks/R-2-0.geojson: 大安→北投
- output/tracks/R-2-1.geojson: 北投→大安
- output/tracks/R-3-0.geojson: 北投→新北投
- output/tracks/R-3-1.geojson: 新北投→北投
- output/all_tracks_preview.geojson: 所有軌道合併預覽
"""

import json
import math
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from shapely.geometry import LineString, Point, MultiLineString
from shapely.ops import linemerge

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
RAW_DATA_DIR = Path("/Users/migu/Desktop/資料庫/gen_ai_try/ichef_工作用/GIS/mini-taipei/raw_data/mrt")
OUTPUT_DIR = SCRIPT_DIR.parent / "output" / "tracks"

# 顏色設定（用於視覺區分）
TRACK_COLORS = {
    "R-1-0": "#d90023",  # 紅色 - 象山→淡水
    "R-1-1": "#ff6b6b",  # 淺紅 - 淡水→象山
    "R-2-0": "#e63946",  # 暗紅 - 大安→北投
    "R-2-1": "#f4a261",  # 橙色 - 北投→大安
    "R-3-0": "#2a9d8f",  # 青色 - 北投→新北投（支線）
    "R-3-1": "#264653",  # 深青 - 新北投→北投（支線）
}


def load_json(filepath: Path) -> Any:
    """載入 JSON 檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_geojson(filepath: Path, data: Dict) -> None:
    """儲存 GeoJSON 檔案"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 已儲存: {filepath}")


def get_station_coords(stations: List[Dict], station_id: str) -> Optional[Tuple[float, float]]:
    """取得車站座標"""
    for s in stations:
        if s.get('StationID') == station_id:
            pos = s.get('StationPosition', {})
            return (pos.get('PositionLon'), pos.get('PositionLat'))
    return None


def merge_line_segments(segments: List[List[List[float]]]) -> LineString:
    """
    將多個線段合併成單一連續的 LineString
    處理線段順序和方向問題
    """
    if not segments:
        return LineString()

    lines = [LineString(coords) for coords in segments]
    merged = linemerge(lines)

    if isinstance(merged, LineString):
        return merged
    elif isinstance(merged, MultiLineString):
        # 手動連接
        all_coords = []
        remaining = list(merged.geoms)

        if remaining:
            current = remaining.pop(0)
            all_coords.extend(list(current.coords))

            while remaining:
                current_end = Point(all_coords[-1])
                best_idx = None
                best_dist = float('inf')
                reverse = False

                for i, line in enumerate(remaining):
                    start_dist = current_end.distance(Point(line.coords[0]))
                    end_dist = current_end.distance(Point(line.coords[-1]))

                    if start_dist < best_dist:
                        best_dist = start_dist
                        best_idx = i
                        reverse = False
                    if end_dist < best_dist:
                        best_dist = end_dist
                        best_idx = i
                        reverse = True

                if best_idx is not None:
                    next_line = remaining.pop(best_idx)
                    coords = list(next_line.coords)
                    if reverse:
                        coords = coords[::-1]
                    all_coords.extend(coords[1:])
                else:
                    break

        return LineString(all_coords)

    return LineString()


def find_station_position_on_line(
    line: LineString,
    station_coord: Tuple[float, float]
) -> float:
    """找到車站在軌道上的投影位置（0-1 之間的比例）"""
    station_point = Point(station_coord)
    position = line.project(station_point, normalized=True)
    return position


def extract_track_segment(
    line: LineString,
    start_position: float,
    end_position: float
) -> List[Tuple[float, float]]:
    """從軌道中提取指定範圍的線段"""

    # 確保 start < end
    if start_position > end_position:
        start_position, end_position = end_position, start_position
        need_reverse = True
    else:
        need_reverse = False

    total_length = line.length
    start_dist = start_position * total_length
    end_dist = end_position * total_length

    coords = list(line.coords)
    result_coords = []
    accumulated_dist = 0

    # 加入起點（內插）
    start_point = line.interpolate(start_dist)
    result_coords.append((start_point.x, start_point.y))

    # 收集範圍內的原始座標點
    for i in range(len(coords)):
        if i > 0:
            prev = Point(coords[i-1])
            curr = Point(coords[i])
            segment_dist = prev.distance(curr)
            accumulated_dist += segment_dist

        point_dist = line.project(Point(coords[i]))
        if start_dist < point_dist < end_dist:
            result_coords.append(coords[i])

    # 加入終點（內插）
    end_point = line.interpolate(end_dist)
    result_coords.append((end_point.x, end_point.y))

    if need_reverse:
        result_coords = result_coords[::-1]

    return result_coords


def create_track_geojson(
    track_id: str,
    coords: List[Tuple[float, float]],
    properties: Dict
) -> Dict:
    """建立軌道 GeoJSON"""
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "color": TRACK_COLORS.get(track_id, "#000000"),
                **properties
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[c[0], c[1]] for c in coords]
            }
        }]
    }


def process_red_line():
    """處理紅線軌道"""
    print("=" * 60)
    print("01_extract_red_line_tracks.py - 提取紅線各路線軌道")
    print("=" * 60)

    # 載入資料
    print("\n載入資料...")
    kepler_geojson = load_json(RAW_DATA_DIR / "kepler_mrt_routes.geojson")
    stations = load_json(RAW_DATA_DIR / "trtc_stations.json")

    # 找到紅線的完整軌道幾何
    red_line_segments = None
    for feat in kepler_geojson.get('features', []):
        if feat.get('properties', {}).get('line_id') == 'R':
            red_line_segments = feat.get('geometry', {}).get('coordinates', [])
            break

    if not red_line_segments:
        print("錯誤: 找不到紅線軌道幾何")
        return

    print(f"  原始線段數: {len(red_line_segments)}")

    # 分離主線和支線
    # 根據分析：線段 0 是新北投支線，其餘是主線
    branch_segment = red_line_segments[0]  # 線段 0 = 支線
    main_segments = red_line_segments[1:]  # 線段 1-10 = 主線

    print(f"  支線座標點數: {len(branch_segment)}")
    print(f"  主線線段數: {len(main_segments)}")

    # 建立支線 LineString
    branch_line = LineString(branch_segment)
    print(f"  支線長度: {branch_line.length * 111:.2f} km (估算)")

    # 合併主線
    main_line = merge_line_segments(main_segments)
    print(f"  主線合併後座標點: {len(list(main_line.coords))}")

    # 取得各站座標
    print("\n取得車站座標...")
    station_coords = {}
    for s in stations:
        sid = s.get('StationID', '')
        if sid.startswith('R'):
            pos = s.get('StationPosition', {})
            station_coords[sid] = (pos.get('PositionLon'), pos.get('PositionLat'))

    # 定義要提取的軌道
    track_definitions = [
        {
            "track_id": "R-1-0",
            "route_id": "R-1",
            "direction": 0,
            "start_station": "R02",  # 象山
            "end_station": "R28",    # 淡水
            "name": "象山 → 淡水",
            "line": main_line,
            "travel_time": 54
        },
        {
            "track_id": "R-1-1",
            "route_id": "R-1",
            "direction": 1,
            "start_station": "R28",  # 淡水
            "end_station": "R02",    # 象山
            "name": "淡水 → 象山",
            "line": main_line,
            "travel_time": 54
        },
        {
            "track_id": "R-2-0",
            "route_id": "R-2",
            "direction": 0,
            "start_station": "R05",  # 大安
            "end_station": "R22",    # 北投
            "name": "大安 → 北投",
            "line": main_line,
            "travel_time": 32
        },
        {
            "track_id": "R-2-1",
            "route_id": "R-2",
            "direction": 1,
            "start_station": "R22",  # 北投
            "end_station": "R05",    # 大安
            "name": "北投 → 大安",
            "line": main_line,
            "travel_time": 32
        },
        {
            "track_id": "R-3-0",
            "route_id": "R-3",
            "direction": 0,
            "start_station": "R22",  # 北投
            "end_station": "R22A",   # 新北投
            "name": "北投 → 新北投",
            "line": branch_line,     # 使用支線！
            "travel_time": 4
        },
        {
            "track_id": "R-3-1",
            "route_id": "R-3",
            "direction": 1,
            "start_station": "R22A", # 新北投
            "end_station": "R22",    # 北投
            "name": "新北投 → 北投",
            "line": branch_line,     # 使用支線！
            "travel_time": 4
        },
    ]

    # 處理每個軌道
    print("\n提取各路線軌道...")
    all_tracks_features = []

    for track_def in track_definitions:
        track_id = track_def["track_id"]
        line = track_def["line"]
        print(f"\n處理 {track_id}: {track_def['name']}")

        start_coord = station_coords.get(track_def["start_station"])
        end_coord = station_coords.get(track_def["end_station"])

        if not start_coord or not end_coord:
            print(f"  ✗ 找不到車站座標")
            continue

        print(f"  起站 {track_def['start_station']}: {start_coord}")
        print(f"  迄站 {track_def['end_station']}: {end_coord}")

        # 找到起迄站在軌道上的位置
        start_pos = find_station_position_on_line(line, start_coord)
        end_pos = find_station_position_on_line(line, end_coord)

        print(f"  起站位置: {start_pos:.4f}")
        print(f"  迄站位置: {end_pos:.4f}")

        # 支線特殊處理：直接使用整條支線
        if track_id.startswith("R-3"):
            track_coords = list(line.coords)
            # R-3-0: 北投→新北投，需要反轉（因為原始是新北投→北投）
            if track_def["direction"] == 0:
                track_coords = track_coords[::-1]
        else:
            # 主線：提取段落
            track_coords = extract_track_segment(line, start_pos, end_pos)

        print(f"  提取座標點數: {len(track_coords)}")

        # 建立 GeoJSON
        properties = {
            "route_id": track_def["route_id"],
            "direction": track_def["direction"],
            "name": track_def["name"],
            "start_station": track_def["start_station"],
            "end_station": track_def["end_station"],
            "travel_time": track_def["travel_time"],
            "line_id": "R"
        }

        track_geojson = create_track_geojson(track_id, track_coords, properties)

        # 儲存個別檔案
        save_geojson(OUTPUT_DIR / f"{track_id}.geojson", track_geojson)

        # 加入預覽集合
        all_tracks_features.append(track_geojson["features"][0])

    # 儲存合併預覽檔案
    print("\n產生合併預覽檔案...")
    preview_geojson = {
        "type": "FeatureCollection",
        "features": all_tracks_features
    }
    save_geojson(SCRIPT_DIR.parent / "output" / "all_tracks_preview.geojson", preview_geojson)

    # 產生車站 GeoJSON 供對照
    print("\n產生車站標記檔案...")
    station_features = []
    for s in stations:
        sid = s.get('StationID', '')
        if sid.startswith('R'):
            pos = s.get('StationPosition', {})
            station_features.append({
                "type": "Feature",
                "properties": {
                    "station_id": sid,
                    "name_zh": s.get('StationName', {}).get('Zh_tw', ''),
                    "name_en": s.get('StationName', {}).get('En', '')
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [pos.get('PositionLon'), pos.get('PositionLat')]
                }
            })

    stations_geojson = {
        "type": "FeatureCollection",
        "features": station_features
    }
    save_geojson(SCRIPT_DIR.parent / "output" / "red_line_stations.geojson", stations_geojson)

    print("\n" + "=" * 60)
    print("完成！")
    print(f"輸出目錄: {OUTPUT_DIR}")
    print("\n請使用 geojson.io 或 kepler.gl 開啟以下檔案驗證軌道正確性：")
    print(f"  - {SCRIPT_DIR.parent / 'output' / 'all_tracks_preview.geojson'}")
    print(f"  - {SCRIPT_DIR.parent / 'output' / 'red_line_stations.geojson'}")
    print("=" * 60)


if __name__ == "__main__":
    process_red_line()
