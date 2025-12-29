#!/usr/bin/env python3
"""
建立中途站出發的首班車專用軌道

從 R-1-0 和 R-1-1 軌道切割出子軌道，供首班車使用。
"""

import json
from pathlib import Path
import math

# 路徑設定
BASE_DIR = Path(__file__).parent.parent.parent
TRACKS_DIR = BASE_DIR / "public" / "data" / "tracks"
STATIONS_FILE = BASE_DIR / "public" / "data" / "red_line_stations.geojson"
PROGRESS_FILE = BASE_DIR / "public" / "data" / "station_progress.json"

# 要建立的軌道
TRACKS_TO_CREATE = [
    # (track_id, source_track, start_station, end_station, name, direction)
    # === 往淡水方向 (北上) ===
    ("R-5-0", "R-1-0", "R05", "R28", "大安 → 淡水", 0),
    ("R-6-0", "R-1-0", "R10", "R28", "雙連 → 淡水", 0),
    ("R-7-0", "R-1-0", "R15", "R28", "圓山 → 淡水", 0),
    ("R-8-0", "R-1-0", "R20", "R28", "芝山 → 淡水", 0),
    ("R-9-1", "R-1-1", "R24", "R02", "紅樹林 → 象山", 1),

    # === 往象山方向 (南下) - 從中途站出發 ===
    ("R-10-1", "R-1-1", "R05", "R02", "大安 → 象山", 1),
    ("R-11-1", "R-1-1", "R10", "R02", "雙連 → 象山", 1),
    ("R-12-1", "R-1-1", "R13", "R02", "民權西路 → 象山", 1),
    ("R-13-1", "R-1-1", "R15", "R02", "圓山 → 象山", 1),
    ("R-14-1", "R-1-1", "R19", "R02", "石牌 → 象山", 1),
    ("R-15-1", "R-1-1", "R20", "R02", "唭哩岸 → 象山", 1),
]

def load_stations():
    """載入車站資料"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stations = {}
    for feature in data['features']:
        props = feature['properties']
        station_id = props['station_id']
        coords = feature['geometry']['coordinates']
        stations[station_id] = {
            'coords': coords,
            'name': props.get('name_zh', station_id)
        }
    return stations

def load_track(track_id):
    """載入軌道資料"""
    track_file = TRACKS_DIR / f"{track_id}.geojson"
    with open(track_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['features'][0]['geometry']['coordinates']

def distance(p1, p2):
    """計算兩點距離"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def find_closest_point_index(coords, target):
    """找到軌道上最接近目標點的索引"""
    min_dist = float('inf')
    min_idx = 0
    for i, coord in enumerate(coords):
        d = distance(coord, target)
        if d < min_dist:
            min_dist = d
            min_idx = i
    return min_idx

def calculate_progress(coords, station_indices, station_ids):
    """計算各站在軌道上的進度 (0-1)"""
    # 計算總長度
    total_length = 0
    cumulative = [0]
    for i in range(len(coords) - 1):
        total_length += distance(coords[i], coords[i + 1])
        cumulative.append(total_length)

    # 計算各站進度
    progress = {}
    for station_id, idx in zip(station_ids, station_indices):
        progress[station_id] = cumulative[idx] / total_length if total_length > 0 else 0

    return progress

def find_insertion_point(coords, station_pos):
    """找到車站座標應該插入的位置

    透過計算車站到每個線段的投影距離，找到最近的線段，
    然後在該線段的終點處插入。
    """
    min_dist = float('inf')
    best_idx = 0

    for i in range(len(coords) - 1):
        p1 = coords[i]
        p2 = coords[i + 1]

        # 計算點到線段的距離
        # 使用向量投影來判斷點是否在線段範圍內
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        seg_len_sq = dx * dx + dy * dy

        if seg_len_sq == 0:
            # 線段長度為 0，直接計算點距離
            d = distance(p1, station_pos)
        else:
            # 計算投影參數 t (0 <= t <= 1 表示在線段上)
            t = max(0, min(1, ((station_pos[0] - p1[0]) * dx + (station_pos[1] - p1[1]) * dy) / seg_len_sq))

            # 投影點
            proj_x = p1[0] + t * dx
            proj_y = p1[1] + t * dy

            d = distance([proj_x, proj_y], station_pos)

            # 如果點在線段範圍內 (0 < t < 1)，這是理想的插入位置
            if 0 < t < 1 and d < min_dist:
                min_dist = d
                best_idx = i + 1  # 插入在 p2 的位置 (p1 之後)

        # 也檢查到端點的距離
        d1 = distance(p1, station_pos)
        d2 = distance(p2, station_pos)

        if d1 < min_dist:
            min_dist = d1
            best_idx = i
        if d2 < min_dist:
            min_dist = d2
            best_idx = i + 1

    return best_idx, min_dist

def insert_station_coords(coords, station_coords, stations_data):
    """在軌道中插入精確的車站座標

    確保軌道通過每個車站的精確位置，而不是只用最近的軌道點。
    車站會按照沿軌道的順序插入。
    """
    result = list(coords)

    # 跳過首尾站（已經在 create_track 中設定）
    middle_stations = station_coords[1:-1] if len(station_coords) > 2 else []

    for station_id in middle_stations:
        if station_id not in stations_data:
            continue

        station_pos = stations_data[station_id]['coords']

        # 找到最佳插入位置
        insert_idx, min_dist = find_insertion_point(result, station_pos)

        # 檢查該位置是否已經很接近車站座標
        if insert_idx < len(result) and distance(result[insert_idx], station_pos) < 0.00005:
            # 距離已經很近，直接替換
            result[insert_idx] = station_pos
        elif insert_idx > 0 and distance(result[insert_idx - 1], station_pos) < 0.00005:
            # 前一個點很近，替換前一個點
            result[insert_idx - 1] = station_pos
        else:
            # 插入新座標
            result.insert(insert_idx, station_pos)

    return result

def create_track(track_id, source_track_id, start_station, end_station, name, stations_data):
    """建立新軌道"""
    source_coords = load_track(source_track_id)

    # 找到起點和終點在軌道上的位置
    start_coords = stations_data[start_station]['coords']
    end_coords = stations_data[end_station]['coords']

    start_idx = find_closest_point_index(source_coords, start_coords)
    end_idx = find_closest_point_index(source_coords, end_coords)

    # 確保方向正確
    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx
        # 需要反轉座標
        new_coords = source_coords[start_idx:end_idx + 1][::-1]
    else:
        new_coords = source_coords[start_idx:end_idx + 1]

    # 確保起點和終點是精確的車站座標
    new_coords[0] = start_coords
    new_coords[-1] = end_coords

    print(f"  {track_id}: 從索引 {start_idx} 到 {end_idx}, 共 {len(new_coords)} 點")

    return new_coords

def get_stations_on_track(start_station, end_station, direction):
    """取得軌道上的車站列表"""
    # R 線車站順序 (象山到淡水)
    all_stations = [
        "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10",
        "R11", "R12", "R13", "R14", "R15", "R16", "R17", "R18", "R19",
        "R20", "R21", "R22", "R22A", "R23", "R24", "R25", "R26", "R27", "R28"
    ]

    start_idx = all_stations.index(start_station)
    end_idx = all_stations.index(end_station)

    if start_idx <= end_idx:
        stations = all_stations[start_idx:end_idx + 1]
    else:
        stations = all_stations[end_idx:start_idx + 1][::-1]

    # 移除 R22A（新北投支線）如果不在路徑上
    if "R22A" in stations and not (start_station == "R22A" or end_station == "R22A"):
        stations.remove("R22A")

    return stations

def main():
    print("=" * 60)
    print("建立中途站首班車專用軌道")
    print("=" * 60)
    print()

    # 載入車站資料
    stations_data = load_stations()

    # 載入現有進度
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        all_progress = json.load(f)

    # 建立各軌道
    for track_id, source_track, start_station, end_station, name, direction in TRACKS_TO_CREATE:
        print(f"\n建立 {track_id} ({name})...")

        # 取得此軌道上的車站（先取得，用於插入座標）
        track_stations = get_stations_on_track(start_station, end_station, direction)
        print(f"  車站: {track_stations[0]} ~ {track_stations[-1]} ({len(track_stations)} 站)")

        # 建立軌道並取得座標
        new_coords = create_track(track_id, source_track, start_station, end_station, name, stations_data)

        # 插入所有中間站的精確座標
        new_coords = insert_station_coords(new_coords, track_stations, stations_data)
        print(f"  插入車站座標後: {len(new_coords)} 點")

        # 重新儲存包含精確車站座標的軌道
        route_id = track_id.rsplit('-', 1)[0]
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "track_id": track_id,
                    "route_id": route_id,
                    "name": name,
                    "color": "#d90023"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": new_coords
                }
            }]
        }
        output_file = TRACKS_DIR / f"{track_id}.geojson"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)

        # 計算各站在新軌道上的索引
        station_indices = []
        for station_id in track_stations:
            if station_id in stations_data:
                idx = find_closest_point_index(new_coords, stations_data[station_id]['coords'])
                station_indices.append(idx)
            else:
                station_indices.append(0)

        # 計算進度
        progress = calculate_progress(new_coords, station_indices, track_stations)
        all_progress[track_id] = progress

        # 顯示首尾站進度
        print(f"  進度: {track_stations[0]}={progress[track_stations[0]]:.4f}, {track_stations[-1]}={progress[track_stations[-1]]:.4f}")

    # 儲存更新的進度
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已更新 {PROGRESS_FILE}")

    print("\n" + "=" * 60)
    print("軌道建立完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
