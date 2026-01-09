#!/usr/bin/env python3
"""
supplement_bh_track.py - 補充 BH (北迴線) 缺失的北段軌道

BH 軌道目前只覆蓋和平到花蓮段，缺少蘇澳新到和平段（約 40km）。
此腳本使用車站座標作為 waypoints 來生成缺失段落。
"""

import json
import os
import math
from typing import List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_DIR = os.path.join(DATA_DIR, 'tracks_official')

Coord = Tuple[float, float]


# BH 北迴線車站座標 (蘇澳新 → 花蓮) - 從 stations_snapped.geojson 取得
BH_STATION_COORDS = [
    ('7130', '蘇澳新', (121.827762, 24.608827)),
    ('7110', '永樂', (121.844433, 24.568498)),
    ('7100', '東澳', (121.83049, 24.518178)),
    ('7090', '南澳', (121.800974, 24.463082)),
    ('7080', '武塔', (121.775811, 24.448763)),
    ('7070', '漢本', (121.768674, 24.335321)),
    ('7060', '和平', (121.754794, 24.297902)),
    ('7050', '和仁', (121.712634, 24.241667)),
    ('7040', '崇德', (121.65577, 24.171914)),
    ('7030', '新城', (121.64044, 24.127783)),
    ('7020', '景美', (121.610646, 24.090522)),
    ('7010', '北埔', (121.601373, 24.032515)),
    ('7000', '花蓮', (121.601044, 23.993131)),
]


def interpolate_segment(start: Coord, end: Coord, num_points: int = 20) -> List[Coord]:
    """在兩點之間線性插值生成中間點"""
    points = []
    for i in range(num_points + 1):
        t = i / num_points
        lng = start[0] + t * (end[0] - start[0])
        lat = start[1] + t * (end[1] - start[1])
        points.append((lng, lat))
    return points


def haversine_distance(coord1: Coord, coord2: Coord) -> float:
    """計算兩點間的 Haversine 距離 (公尺)"""
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def load_existing_bh_track(direction: int) -> List[Coord]:
    """載入現有 BH 軌道"""
    track_file = os.path.join(TRACKS_DIR, f'BH-{direction}.geojson')
    with open(track_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    feature = data['features'][0]
    geom = feature['geometry']

    coords = []
    if geom['type'] == 'LineString':
        coords = [tuple(c) for c in geom['coordinates']]
    elif geom['type'] == 'MultiLineString':
        for segment in geom['coordinates']:
            if coords:
                # 跳過重複的接合點
                if tuple(segment[0]) != coords[-1]:
                    coords.append(tuple(segment[0]))
                coords.extend([tuple(c) for c in segment[1:]])
            else:
                coords.extend([tuple(c) for c in segment])

    return coords


def find_closest_point_index(coords: List[Coord], target: Coord) -> int:
    """找到座標列表中最接近目標的點索引"""
    min_dist = float('inf')
    min_idx = 0
    for i, coord in enumerate(coords):
        dist = (coord[0] - target[0])**2 + (coord[1] - target[1])**2
        if dist < min_dist:
            min_dist = dist
            min_idx = i
    return min_idx


def generate_supplemented_track(direction: int) -> List[Coord]:
    """生成補充後的完整軌道"""
    # 載入現有軌道（從 BH-0 備份載入，因為已被覆蓋）
    # 現有軌道方向: 和平(北) → 花蓮(南)
    backup_file = os.path.join(TRACKS_DIR, 'BH-0.geojson.bak')
    original_file = os.path.join(TRACKS_DIR, 'BH-0.geojson')
    source_file = backup_file if os.path.exists(backup_file) else original_file

    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    feature = data['features'][0]
    geom = feature['geometry']
    existing_coords = []
    if geom['type'] == 'LineString':
        existing_coords = [tuple(c) for c in geom['coordinates']]
    elif geom['type'] == 'MultiLineString':
        for segment in geom['coordinates']:
            if existing_coords:
                if tuple(segment[0]) != existing_coords[-1]:
                    existing_coords.append(tuple(segment[0]))
                existing_coords.extend([tuple(c) for c in segment[1:]])
            else:
                existing_coords.extend([tuple(c) for c in segment])

    print(f"載入原始軌道: {len(existing_coords)} 點")
    print(f"  起點: {existing_coords[0]}")
    print(f"  終點: {existing_coords[-1]}")

    # 原始軌道是 和平(24.30) → 花蓮(23.97)
    # 方向 0: 蘇澳新 → 花蓮: 補充(蘇澳新→和平) + 原軌道(和平→花蓮)
    # 方向 1: 花蓮 → 蘇澳新: 原軌道反向(花蓮→和平) + 補充(和平→蘇澳新)

    if direction == 0:
        # 蘇澳新 → 花蓮
        supplemented = []
        for i in range(6):  # 蘇澳新(0) → 和平(6) (不含和平)
            start = BH_STATION_COORDS[i][2]
            end = BH_STATION_COORDS[i + 1][2]
            dist = haversine_distance(start, end)
            num_points = max(10, int(dist / 500))
            segment = interpolate_segment(start, end, num_points)
            if supplemented:
                supplemented.extend(segment[1:])
            else:
                supplemented.extend(segment)
            print(f"  補充段落: {BH_STATION_COORDS[i][1]} → {BH_STATION_COORDS[i+1][1]}: {len(segment)} 點")

        # 合併: 補充 + 原軌道
        final_coords = supplemented + existing_coords[1:]  # 跳過原軌道第一點避免重複
        print(f"  合併: 補充({len(supplemented)}) + 原軌道({len(existing_coords)})")

    else:  # direction == 1: 花蓮 → 蘇澳新
        # 反向原軌道
        reversed_existing = list(reversed(existing_coords))

        # 補充和平到蘇澳新
        supplemented = []
        for i in range(6, 0, -1):  # 和平(6) → 蘇澳新(0)
            start = BH_STATION_COORDS[i][2]
            end = BH_STATION_COORDS[i - 1][2]
            dist = haversine_distance(start, end)
            num_points = max(10, int(dist / 500))
            segment = interpolate_segment(start, end, num_points)
            if supplemented:
                supplemented.extend(segment[1:])
            else:
                supplemented.extend(segment)
            print(f"  補充段落: {BH_STATION_COORDS[i][1]} → {BH_STATION_COORDS[i-1][1]}: {len(segment)} 點")

        # 合併: 反向原軌道 + 補充
        final_coords = reversed_existing + supplemented[1:]  # 跳過補充第一點避免重複
        print(f"  合併: 反向原軌道({len(reversed_existing)}) + 補充({len(supplemented)})")

    return final_coords


def save_supplemented_track(coords: List[Coord], direction: int):
    """儲存補充後的軌道"""
    feature = {
        "type": "Feature",
        "properties": {
            "track_id": f"BH-{direction}",
            "route_id": "BH",
            "direction": direction,
            "line_name": "北迴線",
            "supplemented": True
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[c[0], c[1]] for c in coords]
        }
    }

    geojson = {
        "type": "FeatureCollection",
        "features": [feature]
    }

    # 備份原始檔案
    original_file = os.path.join(TRACKS_DIR, f'BH-{direction}.geojson')
    backup_file = os.path.join(TRACKS_DIR, f'BH-{direction}.geojson.bak')
    if os.path.exists(original_file) and not os.path.exists(backup_file):
        import shutil
        shutil.copy2(original_file, backup_file)
        print(f"備份: {backup_file}")

    # 儲存新檔案
    with open(original_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    print(f"儲存: {original_file} ({len(coords)} 點)")


def update_all_tracks():
    """更新 all_tracks.geojson"""
    all_tracks_file = os.path.join(TRACKS_DIR, 'all_tracks.geojson')

    with open(all_tracks_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 讀取新的 BH 軌道
    for direction in [0, 1]:
        track_file = os.path.join(TRACKS_DIR, f'BH-{direction}.geojson')
        with open(track_file, 'r', encoding='utf-8') as f:
            bh_data = json.load(f)

        # 找到並替換對應的 feature
        for i, feature in enumerate(data['features']):
            if feature['properties']['track_id'] == f'BH-{direction}':
                data['features'][i] = bh_data['features'][0]
                print(f"更新 all_tracks.geojson 中的 BH-{direction}")
                break

    with open(all_tracks_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"儲存: {all_tracks_file}")


def main():
    print("=" * 60)
    print("補充 BH 北迴線軌道資料")
    print("=" * 60)

    for direction in [0, 1]:
        print(f"\n處理 BH-{direction}...")
        coords = generate_supplemented_track(direction)
        save_supplemented_track(coords, direction)

    print("\n更新 all_tracks.geojson...")
    update_all_tracks()

    print("\n" + "=" * 60)
    print("完成！請重新執行 build_yl_bh_od_tracks.py")
    print("=" * 60)


if __name__ == '__main__':
    main()
