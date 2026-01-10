#!/usr/bin/env python3
"""
rebuild_bh_from_gaps.py - 從手繪軌道重建 BH 北迴線

從 gaps_to_fill.geojson 擷取正確的手繪軌道段落，
合併成完整的 BH 軌道（蘇澳新 → 花蓮）。
"""

import json
import os
import math
from typing import List, Tuple, Dict, Any

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_DIR = os.path.join(DATA_DIR, 'tracks_official')
GAPS_FILE = os.path.join(DATA_DIR, 'gaps_to_fill.geojson')

# BH 北迴線車站座標（用於找到切割點）
BH_STATIONS = {
    '7130': {'name': '蘇澳新', 'lat': 24.608, 'lon': 121.827},
    '7110': {'name': '永樂', 'lat': 24.515},
    '7100': {'name': '東澳', 'lat': 24.463},
    '7090': {'name': '南澳', 'lat': 24.443},
    '7080': {'name': '武塔', 'lat': 24.387},
    '7070': {'name': '漢本', 'lat': 24.317},
    '7060': {'name': '和平', 'lat': 24.301},
    '7050': {'name': '和仁', 'lat': 24.247},
    '7040': {'name': '崇德', 'lat': 24.165},
    '7030': {'name': '新城', 'lat': 24.125},
    '7020': {'name': '景美', 'lat': 24.041},
    '7010': {'name': '北埔', 'lat': 24.002},
    '7000': {'name': '花蓮', 'lat': 23.968, 'lon': 121.601},
}

Coord = Tuple[float, float]


def euclidean_distance(coord1: Coord, coord2: Coord) -> float:
    """計算兩點間的歐幾里得距離"""
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)


def find_closest_point_index(coords: List[Coord], target_lat: float) -> int:
    """找到座標列表中最接近目標緯度的點索引"""
    min_diff = float('inf')
    min_idx = 0
    for i, coord in enumerate(coords):
        diff = abs(coord[1] - target_lat)
        if diff < min_diff:
            min_diff = diff
            min_idx = i
    return min_idx


def load_gap_segments() -> Dict[str, List[Coord]]:
    """載入 gaps_to_fill.geojson 中的手繪段落"""
    with open(GAPS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    segments = {}
    target_names = ['四城 → 和平', '和平 → 新城', '新城 → 吉安']

    for feat in data.get('features', []):
        props = feat.get('properties', {})
        name = props.get('name', '')

        if name in target_names:
            geom = feat['geometry']
            if geom['type'] == 'LineString':
                coords = [tuple(c) for c in geom['coordinates']]
            elif geom['type'] == 'MultiLineString':
                coords = [tuple(c) for line in geom['coordinates'] for c in line]
            else:
                continue

            segments[name] = coords
            print(f"載入段落: {name}, {len(coords)} 點")

    return segments


def build_bh_track(segments: Dict[str, List[Coord]]) -> List[Coord]:
    """從手繪段落建立完整的 BH 軌道"""

    # 取得三個段落
    seg_north = segments.get('四城 → 和平', [])
    seg_middle = segments.get('和平 → 新城', [])
    seg_south = segments.get('新城 → 吉安', [])

    if not seg_north:
        print("錯誤: 找不到 '四城 → 和平' 段落")
        return []
    if not seg_middle:
        print("錯誤: 找不到 '和平 → 新城' 段落")
        return []
    if not seg_south:
        print("錯誤: 找不到 '新城 → 吉安' 段落")
        return []

    # 「四城 → 和平」包含了 YL 末段 + BH 北段
    # 需要從蘇澳新站（緯度約 24.608）開始切割
    suaoxin_lat = BH_STATIONS['7130']['lat']

    # 檢查段落方向（由北往南還是由南往北）
    north_start_lat = seg_north[0][1]
    north_end_lat = seg_north[-1][1]

    print(f"\n「四城 → 和平」段落:")
    print(f"  起點緯度: {north_start_lat:.4f}")
    print(f"  終點緯度: {north_end_lat:.4f}")

    # 找到蘇澳新站位置
    suaoxin_idx = find_closest_point_index(seg_north, suaoxin_lat)
    print(f"  蘇澳新站索引: {suaoxin_idx} (緯度 {seg_north[suaoxin_idx][1]:.4f})")

    # 決定如何切割
    if north_start_lat > north_end_lat:
        # 由北往南（四城 → 和平）
        # 從蘇澳新站開始到終點（和平）
        bh_north_segment = seg_north[suaoxin_idx:]
        print(f"  BH 北段: 索引 {suaoxin_idx} 到 {len(seg_north)-1}, {len(bh_north_segment)} 點")
    else:
        # 由南往北（和平 → 四城）
        # 從起點（和平）到蘇澳新站
        bh_north_segment = seg_north[:suaoxin_idx+1]
        bh_north_segment = list(reversed(bh_north_segment))  # 反轉為由北往南
        print(f"  BH 北段 (反轉): {len(bh_north_segment)} 點")

    # 檢查中間段落方向
    middle_start_lat = seg_middle[0][1]
    middle_end_lat = seg_middle[-1][1]

    print(f"\n「和平 → 新城」段落:")
    print(f"  起點緯度: {middle_start_lat:.4f}")
    print(f"  終點緯度: {middle_end_lat:.4f}")

    if middle_start_lat < middle_end_lat:
        # 由南往北，需要反轉
        seg_middle = list(reversed(seg_middle))
        print(f"  已反轉為由北往南")

    # 檢查南段方向
    south_start_lat = seg_south[0][1]
    south_end_lat = seg_south[-1][1]

    print(f"\n「新城 → 吉安」段落:")
    print(f"  起點緯度: {south_start_lat:.4f}")
    print(f"  終點緯度: {south_end_lat:.4f}")

    if south_start_lat < south_end_lat:
        # 由南往北，需要反轉
        seg_south = list(reversed(seg_south))
        print(f"  已反轉為由北往南")

    # 合併所有段落（由北往南：蘇澳新 → 花蓮）
    combined = []

    # 加入北段
    combined.extend(bh_north_segment)
    print(f"\n合併北段後: {len(combined)} 點")

    # 加入中間段（跳過第一個點避免重複）
    if seg_middle:
        combined.extend(seg_middle[1:])
        print(f"合併中段後: {len(combined)} 點")

    # 加入南段（跳過第一個點避免重複）
    if seg_south:
        combined.extend(seg_south[1:])
        print(f"合併南段後: {len(combined)} 點")

    return combined


def verify_track(coords: List[Coord]) -> bool:
    """驗證軌道是否正確"""
    if not coords:
        print("錯誤: 軌道為空")
        return False

    lats = [c[1] for c in coords]
    lons = [c[0] for c in coords]

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    print(f"\n軌道驗證:")
    print(f"  點數: {len(coords)}")
    print(f"  緯度範圍: {min_lat:.4f} - {max_lat:.4f}")
    print(f"  經度範圍: {min_lon:.4f} - {max_lon:.4f}")
    print(f"  起點: ({coords[0][0]:.5f}, {coords[0][1]:.5f})")
    print(f"  終點: ({coords[-1][0]:.5f}, {coords[-1][1]:.5f})")

    # 檢查是否涵蓋所有 BH 車站
    print(f"\n車站涵蓋檢查:")
    all_covered = True
    for station_id, station in sorted(BH_STATIONS.items(), key=lambda x: -x[1]['lat']):
        station_lat = station['lat']
        covered = min_lat <= station_lat <= max_lat
        status = "✅" if covered else "❌"
        print(f"  {status} {station['name']} ({station_id}): 緯度 {station_lat:.3f}")
        if not covered:
            all_covered = False

    # 檢查是否沿海岸（經度主要在 121.75-121.85）
    coastal_count = sum(1 for lon in lons if 121.5 <= lon <= 121.9)
    coastal_ratio = coastal_count / len(lons)
    print(f"\n沿海岸比例: {coastal_ratio*100:.1f}%")

    if coastal_ratio < 0.8:
        print("警告: 超過 20% 的點不在海岸範圍內")

    return all_covered


def save_track(coords: List[Coord], direction: int):
    """儲存軌道檔案"""
    track_id = f"BH-{direction}"

    if direction == 0:
        # BH-0: 蘇澳新 → 花蓮（由北往南）
        track_coords = coords
        origin = '蘇澳新'
        destination = '花蓮'
    else:
        # BH-1: 花蓮 → 蘇澳新（由南往北）
        track_coords = list(reversed(coords))
        origin = '花蓮'
        destination = '蘇澳新'

    feature = {
        "type": "Feature",
        "properties": {
            "track_id": track_id,
            "route_id": "BH",
            "direction": direction,
            "line_name": "北迴線",
            "origin": origin,
            "destination": destination,
            "rebuilt_from_gaps": True
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[c[0], c[1]] for c in track_coords]
        }
    }

    geojson = {
        "type": "FeatureCollection",
        "features": [feature]
    }

    output_path = os.path.join(TRACKS_DIR, f"{track_id}.geojson")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"儲存: {output_path} ({len(track_coords)} 點)")


def update_all_tracks(coords: List[Coord]):
    """更新 all_tracks.geojson 中的 BH 軌道"""
    all_tracks_path = os.path.join(TRACKS_DIR, 'all_tracks.geojson')

    with open(all_tracks_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 更新 BH-0 和 BH-1
    for feat in data['features']:
        track_id = feat['properties'].get('track_id', '')
        if track_id == 'BH-0':
            feat['geometry']['type'] = 'LineString'
            feat['geometry']['coordinates'] = [[c[0], c[1]] for c in coords]
            feat['properties']['rebuilt_from_gaps'] = True
            feat['properties'].pop('supplemented', None)
            print(f"更新 all_tracks.geojson 中的 BH-0")
        elif track_id == 'BH-1':
            feat['geometry']['type'] = 'LineString'
            feat['geometry']['coordinates'] = [[c[0], c[1]] for c in reversed(coords)]
            feat['properties']['rebuilt_from_gaps'] = True
            feat['properties'].pop('supplemented', None)
            print(f"更新 all_tracks.geojson 中的 BH-1")

    with open(all_tracks_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"儲存: {all_tracks_path}")


def main():
    print("=" * 60)
    print("從手繪軌道重建 BH 北迴線")
    print("=" * 60)

    # Step 1: 載入手繪段落
    print("\n[Step 1] 載入手繪段落")
    segments = load_gap_segments()

    if len(segments) < 3:
        print(f"錯誤: 只找到 {len(segments)} 個段落，需要 3 個")
        return

    # Step 2: 建立完整軌道
    print("\n[Step 2] 建立完整軌道")
    coords = build_bh_track(segments)

    if not coords:
        print("錯誤: 無法建立軌道")
        return

    # Step 3: 驗證
    print("\n[Step 3] 驗證軌道")
    if not verify_track(coords):
        print("警告: 軌道驗證有問題，請檢查")

    # Step 4: 儲存
    print("\n[Step 4] 儲存軌道檔案")
    save_track(coords, 0)  # BH-0: 蘇澳新 → 花蓮
    save_track(coords, 1)  # BH-1: 花蓮 → 蘇澳新

    # Step 5: 更新 all_tracks.geojson
    print("\n[Step 5] 更新 all_tracks.geojson")
    update_all_tracks(coords)

    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
