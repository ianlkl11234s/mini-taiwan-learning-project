#!/usr/bin/env python3
"""
建立西部幹線南段 (彰化→新左營) O-D 軌道

合併 WL-S2 (彰化→石龜) + WL-S1 (石龜→新左營) 建立完整軌道

輸出：
- tracks_golden/WL-S-CH-ZY-0.geojson (彰化→新左營 顯示軌道)
- tracks_golden/WL-S-CH-ZY-1.geojson (新左營→彰化 顯示軌道)
- tracks_od/WL-CH-ZY-0.geojson (彰化→新左營 O-D 軌道)
- tracks_od/WL-ZY-CH-1.geojson (新左營→彰化 O-D 軌道)
- 更新 tracks_od/od_station_progress.json
"""

import json
import math
import os

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACKS_OFFICIAL_DIR = os.path.join(BASE_DIR, 'public/data/tra/tracks_official')
TRACKS_GOLDEN_DIR = os.path.join(BASE_DIR, 'public/data/tra/tracks_golden')
TRACKS_OD_DIR = os.path.join(BASE_DIR, 'public/data/tra/tracks_od')
STATIONS_FILE = os.path.join(BASE_DIR, 'public/data/tra/stations_snapped.geojson')

# 南段車站列表 (彰化→新左營，由北往南)
SOUTH_STATIONS = [
    ('3360', '彰化'),
    ('3370', '花壇'),
    ('3380', '大村'),
    ('3390', '員林'),
    ('3400', '永靖'),
    ('3410', '社頭'),
    ('3420', '田中'),
    ('3430', '二水'),
    ('3450', '林內'),
    ('3460', '石榴'),
    ('3470', '斗六'),
    ('3480', '斗南'),
    ('3490', '石龜'),
    ('4050', '大林'),
    ('4060', '民雄'),
    ('4080', '嘉義'),
    ('4090', '水上'),
    ('4100', '南靖'),
    ('4110', '後壁'),
    ('4120', '新營'),
    ('4130', '柳營'),
    ('4140', '林鳳營'),
    ('4150', '隆田'),
    ('4160', '拔林'),
    ('4170', '善化'),
    ('4180', '南科'),
    ('4190', '新市'),
    ('4200', '永康'),
    ('4210', '大橋'),
    ('4220', '臺南'),
    ('4250', '保安'),
    ('4260', '仁德'),
    ('4270', '中洲'),
    ('4290', '大湖'),
    ('4300', '路竹'),
    ('4310', '岡山'),
    ('4320', '橋頭'),
    ('4330', '楠梓'),
    ('4340', '新左營'),
]


def euclidean_distance(coord1, coord2):
    """計算歐幾里得距離（平面，度為單位）"""
    dx = coord2[0] - coord1[0]
    dy = coord2[1] - coord1[1]
    return math.sqrt(dx * dx + dy * dy)


def load_track(filename):
    """載入軌道檔案，返回座標列表"""
    filepath = os.path.join(TRACKS_OFFICIAL_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if data['type'] == 'FeatureCollection':
        features = data['features']
    else:
        features = [data]

    all_coords = []
    for feature in features:
        geom = feature['geometry']
        if geom['type'] == 'MultiLineString':
            for segment in geom['coordinates']:
                all_coords.extend(segment)
        else:
            all_coords.extend(geom['coordinates'])

    return all_coords


def load_stations():
    """載入車站座標"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stations = {}
    for feature in data['features']:
        props = feature['properties']
        station_id = props.get('station_id') or props.get('id')
        if station_id:
            stations[station_id] = {
                'id': station_id,
                'name': props.get('name_zh') or props.get('name'),
                'coord': feature['geometry']['coordinates']
            }

    return stations


def project_point_to_segment(point, seg_start, seg_end):
    """
    將點投影到線段上，返回 (投影點座標, 投影點在線段上的參數 t, 點到投影點的距離)
    t 在 [0, 1] 表示投影點在線段內
    """
    px, py = point[0], point[1]
    x1, y1 = seg_start[0], seg_start[1]
    x2, y2 = seg_end[0], seg_end[1]

    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return seg_start, 0, euclidean_distance(point, seg_start)

    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))  # 限制在 [0, 1]

    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    proj_point = [proj_x, proj_y]

    dist = euclidean_distance(point, proj_point)

    return proj_point, t, dist


def calculate_station_progress(coords, station_coord):
    """
    使用投影法計算車站在軌道上的 progress 值
    返回 (progress, 距離)
    """
    # 計算軌道總長度
    total_length = 0
    segment_lengths = []
    for i in range(len(coords) - 1):
        length = euclidean_distance(coords[i], coords[i + 1])
        segment_lengths.append(length)
        total_length += length

    if total_length == 0:
        return 0, float('inf')

    # 找最佳投影位置
    best_progress = 0
    best_dist = float('inf')
    cumulative_length = 0

    for i in range(len(coords) - 1):
        proj_point, t, dist = project_point_to_segment(
            station_coord, coords[i], coords[i + 1]
        )

        if dist < best_dist:
            # 計算投影點的累積距離
            proj_length = cumulative_length + t * segment_lengths[i]
            best_progress = proj_length / total_length
            best_dist = dist

        cumulative_length += segment_lengths[i]

    return best_progress, best_dist


def remove_consecutive_duplicates(coords, tolerance=1e-8):
    """移除連續重複的座標點"""
    if not coords:
        return coords

    result = [coords[0]]
    for coord in coords[1:]:
        if euclidean_distance(coord, result[-1]) > tolerance:
            result.append(coord)

    return result


def merge_tracks():
    """合併 WL-S2 和 WL-S1 軌道"""
    print("=== 載入軌道資料 ===")

    # WL-S2: 彰化→石龜 (direction 0 是由北往南)
    wl_s2_0 = load_track('WL-S2-0.geojson')
    print(f"WL-S2-0: {len(wl_s2_0)} points, {wl_s2_0[0]} -> {wl_s2_0[-1]}")

    # WL-S1: 石龜→新左營 (direction 0 是由北往南)
    wl_s1_0 = load_track('WL-S1-0.geojson')
    print(f"WL-S1-0: {len(wl_s1_0)} points, {wl_s1_0[0]} -> {wl_s1_0[-1]}")

    # 檢查接點
    # WL-S2-0 終點應該接 WL-S1-0 起點
    # 但實際上 WL-S1 是從新左營開始的，WL-S2 是從石龜開始的
    # 讓我們根據緯度判斷

    s2_start_lat = wl_s2_0[0][1]
    s2_end_lat = wl_s2_0[-1][1]
    s1_start_lat = wl_s1_0[0][1]
    s1_end_lat = wl_s1_0[-1][1]

    print(f"\nWL-S2-0: lat {s2_start_lat:.4f} -> {s2_end_lat:.4f}")
    print(f"WL-S1-0: lat {s1_start_lat:.4f} -> {s1_end_lat:.4f}")

    # WL-S2-0: 23.63 -> 24.09 (石龜→彰化，由南往北)
    # WL-S1-0: 22.64 -> 23.63 (新左營→石龜，由南往北)

    # 我們要建立彰化→新左營 (由北往南)
    # 所以需要反轉兩個軌道，然後合併

    # 彰化→新左營 (由北往南):
    # 1. 反轉 WL-S2-0 得到 彰化→石龜
    # 2. 反轉 WL-S1-0 得到 石龜→新左營
    # 3. 合併 (移除重複的石龜接點)

    wl_s2_reversed = list(reversed(wl_s2_0))  # 彰化→石龜
    wl_s1_reversed = list(reversed(wl_s1_0))  # 石龜→新左營

    print(f"\nReversed WL-S2: {wl_s2_reversed[0]} -> {wl_s2_reversed[-1]}")
    print(f"Reversed WL-S1: {wl_s1_reversed[0]} -> {wl_s1_reversed[-1]}")

    # 檢查接點距離
    junction_dist = euclidean_distance(wl_s2_reversed[-1], wl_s1_reversed[0])
    print(f"Junction distance: {junction_dist:.8f} degrees")

    # 合併座標 (移除第二段的第一個點避免重複)
    if junction_dist < 0.0001:  # 約 10 公尺
        merged_coords = wl_s2_reversed + wl_s1_reversed[1:]
    else:
        # 接點有距離，保留兩邊
        merged_coords = wl_s2_reversed + wl_s1_reversed

    # 移除連續重複點
    merged_coords = remove_consecutive_duplicates(merged_coords)

    print(f"\nMerged track: {len(merged_coords)} points")
    print(f"  Start: {merged_coords[0]} (應該接近彰化)")
    print(f"  End: {merged_coords[-1]} (應該接近新左營)")

    return merged_coords


def save_golden_track(coords, track_id, name, origin, destination, direction):
    """儲存 Golden Track"""
    feature = {
        "type": "Feature",
        "properties": {
            "track_id": track_id,
            "line_id": "WL-S",
            "direction": direction,
            "name": name,
            "origin": origin,
            "destination": destination
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coords
        }
    }

    filepath = os.path.join(TRACKS_GOLDEN_DIR, f"{track_id}.geojson")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(feature, f, ensure_ascii=False)

    print(f"Saved: {filepath}")


def save_od_track(coords, track_id, name, origin, destination, direction):
    """儲存 O-D Track"""
    feature_collection = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "name": name,
                "origin": origin,
                "destination": destination,
                "direction": direction
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }

    filepath = os.path.join(TRACKS_OD_DIR, f"{track_id}.geojson")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(feature_collection, f, ensure_ascii=False)

    print(f"Saved: {filepath}")


def calculate_all_station_progress(coords_0, coords_1, stations_data):
    """計算所有車站的 progress"""
    progress_0 = {}  # 彰化→新左營
    progress_1 = {}  # 新左營→彰化

    print("\n=== 計算 Station Progress ===")
    print("\n方向 0 (彰化→新左營):")

    for station_id, station_name in SOUTH_STATIONS:
        if station_id not in stations_data:
            print(f"  警告: 找不到車站 {station_id} ({station_name})")
            continue

        station_coord = stations_data[station_id]['coord']
        prog, dist = calculate_station_progress(coords_0, station_coord)
        progress_0[station_id] = round(prog, 6)

        # 距離轉換為公尺 (1度 ≈ 111km)
        dist_m = dist * 111000
        status = "✓" if dist_m < 200 else "⚠️"
        print(f"  {station_id} {station_name}: progress={prog:.6f}, dist={dist_m:.1f}m {status}")

    print("\n方向 1 (新左營→彰化):")
    for station_id, station_name in reversed(SOUTH_STATIONS):
        if station_id not in stations_data:
            continue

        station_coord = stations_data[station_id]['coord']
        prog, dist = calculate_station_progress(coords_1, station_coord)
        progress_1[station_id] = round(prog, 6)

        dist_m = dist * 111000
        status = "✓" if dist_m < 200 else "⚠️"
        print(f"  {station_id} {station_name}: progress={prog:.6f}, dist={dist_m:.1f}m {status}")

    return progress_0, progress_1


def update_station_progress_file(progress_0, progress_1):
    """更新 od_station_progress.json"""
    progress_file = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')

    # 載入現有資料
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            all_progress = json.load(f)
    else:
        all_progress = {}

    # 更新南段資料
    all_progress['WL-CH-ZY-0'] = progress_0
    all_progress['WL-ZY-CH-1'] = progress_1

    # 儲存
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)

    print(f"\nUpdated: {progress_file}")


def main():
    print("=" * 60)
    print("建立西部幹線南段 (彰化→新左營) O-D 軌道")
    print("=" * 60)

    # 1. 合併軌道
    coords_0 = merge_tracks()  # 彰化→新左營
    coords_1 = list(reversed(coords_0))  # 新左營→彰化

    # 2. 載入車站資料
    stations_data = load_stations()

    # 3. 儲存 Golden Track
    print("\n=== 儲存 Golden Track ===")
    save_golden_track(
        coords_0, 'WL-S-CH-ZY-0',
        '縱貫線南段 (彰化→新左營)', '彰化', '新左營', 0
    )
    save_golden_track(
        coords_1, 'WL-S-CH-ZY-1',
        '縱貫線南段 (新左營→彰化)', '新左營', '彰化', 1
    )

    # 4. 儲存 O-D Track
    print("\n=== 儲存 O-D Track ===")
    save_od_track(
        coords_0, 'WL-CH-ZY-0',
        '縱貫線南段 (彰化→新左營)', '彰化', '新左營', 0
    )
    save_od_track(
        coords_1, 'WL-ZY-CH-1',
        '縱貫線南段 (新左營→彰化)', '新左營', '彰化', 1
    )

    # 5. 計算 Station Progress
    progress_0, progress_1 = calculate_all_station_progress(
        coords_0, coords_1, stations_data
    )

    # 6. 更新 station_progress 檔案
    update_station_progress_file(progress_0, progress_1)

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
