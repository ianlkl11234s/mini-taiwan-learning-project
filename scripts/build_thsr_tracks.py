#!/usr/bin/env python3
"""
建立台灣高鐵軌道 GeoJSON

從 TDX Shape 資料生成簡化的軌道 GeoJSON：
- THSR-1-0.geojson (南下：南港→左營)
- THSR-1-1.geojson (北上：左營→南港)

使用 Douglas-Peucker 演算法簡化座標點數

Usage:
    python scripts/build_thsr_tracks.py
"""

import json
import re
from pathlib import Path

# 路徑設定
DATA_DIR = Path(__file__).parent.parent / "data-thsr"
RAW_DIR = DATA_DIR / "raw"
TRACKS_DIR = DATA_DIR / "tracks"

# 簡化參數 (tolerance 約 10 公尺)
SIMPLIFY_TOLERANCE = 0.0001


def parse_wkt_linestring(geometry_str: str) -> list:
    """
    解析 WKT LINESTRING 格式

    輸入: "LINESTRING(121.62089 25.05456, 121.62083 25.05455, ...)"
    輸出: [[121.62089, 25.05456], [121.62083, 25.05455], ...]
    """
    # 移除 LINESTRING( 和 )
    coords_str = re.sub(r'^LINESTRING\s*\(', '', geometry_str)
    coords_str = re.sub(r'\)\s*$', '', coords_str)

    coords = []
    for pair in coords_str.split(','):
        parts = pair.strip().split()
        if len(parts) >= 2:
            lng = float(parts[0])
            lat = float(parts[1])
            coords.append([lng, lat])

    return coords


def distance_point_to_line(point, line_start, line_end):
    """計算點到線段的垂直距離"""
    x, y = point
    x1, y1 = line_start
    x2, y2 = line_end

    # 線段長度的平方
    line_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2

    if line_len_sq == 0:
        # 線段是一個點
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5

    # 計算投影比例
    t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / line_len_sq))

    # 最近點
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)

    return ((x - proj_x) ** 2 + (y - proj_y) ** 2) ** 0.5


def douglas_peucker(coords: list, tolerance: float) -> list:
    """
    Douglas-Peucker 線段簡化演算法

    Args:
        coords: 座標列表 [[lng, lat], ...]
        tolerance: 簡化容許值（經緯度單位）

    Returns:
        簡化後的座標列表
    """
    if len(coords) <= 2:
        return coords

    # 找到距離首尾連線最遠的點
    max_dist = 0
    max_idx = 0

    for i in range(1, len(coords) - 1):
        dist = distance_point_to_line(coords[i], coords[0], coords[-1])
        if dist > max_dist:
            max_dist = dist
            max_idx = i

    # 如果最大距離大於容許值，遞迴處理
    if max_dist > tolerance:
        left = douglas_peucker(coords[:max_idx + 1], tolerance)
        right = douglas_peucker(coords[max_idx:], tolerance)
        return left[:-1] + right
    else:
        return [coords[0], coords[-1]]


def build_thsr_tracks():
    """建立高鐵軌道 GeoJSON"""

    # 確保輸出目錄存在
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n=== 建立台灣高鐵軌道 GeoJSON ===\n")

    # 讀取 Shape 資料
    with open(RAW_DIR / "thsr_shape.json", 'r', encoding='utf-8') as f:
        shape_data = json.load(f)

    if not shape_data:
        print("錯誤: 無法讀取 Shape 資料")
        return

    shape = shape_data[0]  # 只有一條線路
    geometry_str = shape['Geometry']

    # 解析 WKT
    print("[1/4] 解析 WKT LINESTRING...")
    coords = parse_wkt_linestring(geometry_str)
    original_count = len(coords)
    print(f"      原始座標點數: {original_count}")

    # 簡化座標
    print(f"[2/4] 簡化座標 (tolerance={SIMPLIFY_TOLERANCE})...")
    simplified_coords = douglas_peucker(coords, SIMPLIFY_TOLERANCE)
    simplified_count = len(simplified_coords)
    reduction = (1 - simplified_count / original_count) * 100
    print(f"      簡化後座標點數: {simplified_count} (減少 {reduction:.1f}%)")

    # 建立南下軌道 (direction 0: 南港→左營)
    # 注意：TDX Shape 座標順序是從南港開始
    print("[3/4] 建立南下軌道 (THSR-1-0)...")
    track_0 = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": "THSR-1-0",
                "route_id": "THSR",
                "name": "台灣高鐵 南下",
                "direction": 0,
                "origin": "南港",
                "destination": "左營"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": simplified_coords
            }
        }]
    }

    with open(TRACKS_DIR / "THSR-1-0.geojson", 'w', encoding='utf-8') as f:
        json.dump(track_0, f, ensure_ascii=False, indent=2)

    # 建立北上軌道 (direction 1: 左營→南港)
    print("[4/4] 建立北上軌道 (THSR-1-1)...")
    reversed_coords = list(reversed(simplified_coords))

    track_1 = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": "THSR-1-1",
                "route_id": "THSR",
                "name": "台灣高鐵 北上",
                "direction": 1,
                "origin": "左營",
                "destination": "南港"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": reversed_coords
            }
        }]
    }

    with open(TRACKS_DIR / "THSR-1-1.geojson", 'w', encoding='utf-8') as f:
        json.dump(track_1, f, ensure_ascii=False, indent=2)

    print("\n=== 建立完成 ===")
    print(f"輸出檔案:")
    print(f"  - {TRACKS_DIR / 'THSR-1-0.geojson'} (南下)")
    print(f"  - {TRACKS_DIR / 'THSR-1-1.geojson'} (北上)")
    print(f"\n座標點數: {original_count} → {simplified_count} (減少 {reduction:.1f}%)")


if __name__ == '__main__':
    build_thsr_tracks()
