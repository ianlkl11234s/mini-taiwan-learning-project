#!/usr/bin/env python3
"""
建立西部幹線山線 (竹南→彰化) O-D 軌道

從備份檔案讀取 WL-M 軌道，延伸到彰化站和竹南站，建立完整軌道

輸出：
- tracks_golden/WL-M-ZN-CH-0.geojson (竹南→彰化 顯示軌道)
- tracks_golden/WL-M-CH-ZN-1.geojson (彰化→竹南 顯示軌道)
- tracks_od/WL-M-ZN-CH-0.geojson (竹南→彰化 O-D 軌道)
- tracks_od/WL-M-CH-ZN-1.geojson (彰化→竹南 O-D 軌道)
- 更新 tracks_od/od_station_progress.json
"""

import json
import math
import os

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACKS_BACKUP_FILE = os.path.join(BASE_DIR, 'public/data/tra/tracks_archive/tracks_official_backup/all_tracks_backup.geojson')
TRACKS_GOLDEN_DIR = os.path.join(BASE_DIR, 'public/data/tra/tracks_golden')
TRACKS_OD_DIR = os.path.join(BASE_DIR, 'public/data/tra/tracks_od')
STATIONS_FILE = os.path.join(BASE_DIR, 'public/data/tra/stations_snapped.geojson')

# 山線車站列表 (竹南→彰化，方向0)
MOUNTAIN_STATIONS = [
    ('1250', '竹南'),
    ('3140', '造橋'),
    ('3150', '豐富'),
    ('3160', '苗栗'),
    ('3170', '南勢'),
    ('3180', '銅鑼'),
    ('3190', '三義'),
    ('3210', '泰安'),
    ('3220', '后里'),
    ('3230', '豐原'),
    ('3232', '栗林'),
    ('3240', '潭子'),
    ('3243', '頭家厝'),
    ('3245', '松竹'),
    ('3247', '太原'),
    ('3249', '精武'),
    ('3300', '臺中'),
    ('3305', '五權'),
    ('3310', '大慶'),
    ('3320', '烏日'),
    ('3325', '新烏日'),
    ('3330', '成功'),
    ('3360', '彰化'),
]

# 車站座標 (用於投影)
STATION_COORDS = {
    '1250': [120.876823, 24.686267],  # 竹南
    '3140': [120.864056, 24.641483],  # 造橋
    '3150': [120.824091, 24.607002],  # 豐富
    '3160': [120.824577, 24.571589],  # 苗栗
    '3170': [120.823006, 24.540062],  # 南勢
    '3180': [120.786754, 24.489651],  # 銅鑼
    '3190': [120.761318, 24.414913],  # 三義
    '3210': [120.738823, 24.332726],  # 泰安
    '3220': [120.724281, 24.303483],  # 后里
    '3230': [120.720383, 24.254089],  # 豐原
    '3232': [120.710484, 24.232587],  # 栗林
    '3240': [120.705741, 24.212831],  # 潭子
    '3243': [120.699890, 24.191509],  # 頭家厝
    '3245': [120.690891, 24.171913],  # 松竹
    '3247': [120.687377, 24.163426],  # 太原
    '3249': [120.681563, 24.150742],  # 精武
    '3300': [120.685083, 24.137083],  # 臺中
    '3305': [120.666687, 24.126009],  # 五權
    '3310': [120.651603, 24.119269],  # 大慶
    '3320': [120.623657, 24.109847],  # 烏日
    '3325': [120.615906, 24.109088],  # 新烏日
    '3330': [120.597878, 24.104919],  # 成功
    '3360': [120.538402, 24.081859],  # 彰化
}


def euclidean_distance(coord1, coord2):
    """計算歐幾里得距離（平面，度為單位）"""
    dx = coord2[0] - coord1[0]
    dy = coord2[1] - coord1[1]
    return math.sqrt(dx * dx + dy * dy)


def load_wl_m_from_backup():
    """從備份檔案載入 WL-M 軌道"""
    with open(TRACKS_BACKUP_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    wl_m_0 = None
    wl_m_1 = None

    for feat in data['features']:
        track_id = feat['properties'].get('track_id')
        if track_id == 'WL-M-0':
            wl_m_0 = feat['geometry']['coordinates']
        elif track_id == 'WL-M-1':
            wl_m_1 = feat['geometry']['coordinates']

    return wl_m_0, wl_m_1


def project_point_to_segment(point, seg_start, seg_end):
    """
    將點投影到線段上，返回 (投影點座標, 投影點在線段上的參數 t, 點到投影點的距離)
    """
    px, py = point[0], point[1]
    x1, y1 = seg_start[0], seg_start[1]
    x2, y2 = seg_end[0], seg_end[1]

    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return seg_start, 0, euclidean_distance(point, seg_start)

    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))

    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    proj_point = [proj_x, proj_y]

    dist = euclidean_distance(point, proj_point)

    return proj_point, t, dist


def calculate_station_progress(coords, station_coord):
    """使用投影法計算車站在軌道上的 progress 值"""
    total_length = 0
    segment_lengths = []
    for i in range(len(coords) - 1):
        length = euclidean_distance(coords[i], coords[i + 1])
        segment_lengths.append(length)
        total_length += length

    if total_length == 0:
        return 0, float('inf')

    best_progress = 0
    best_dist = float('inf')
    cumulative_length = 0

    for i in range(len(coords) - 1):
        proj_point, t, dist = project_point_to_segment(
            station_coord, coords[i], coords[i + 1]
        )

        if dist < best_dist:
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


def extend_track_to_stations(coords):
    """延伸軌道到彰化站和竹南站"""
    print("=== 延伸軌道到車站 ===")

    changhua = STATION_COORDS['3360']  # 彰化
    zhunan = STATION_COORDS['1250']    # 竹南

    # 檢查軌道方向 (TDX WL-M-0 是從南往北: 彰化附近 → 竹南附近)
    start_lat = coords[0][1]
    end_lat = coords[-1][1]
    print(f"原始軌道: 起點緯度 {start_lat:.4f}, 終點緯度 {end_lat:.4f}")

    # 計算起終點到車站的距離
    start_to_changhua = euclidean_distance(coords[0], changhua) * 111000
    end_to_zhunan = euclidean_distance(coords[-1], zhunan) * 111000

    print(f"起點到彰化站: {start_to_changhua:.0f}m")
    print(f"終點到竹南站: {end_to_zhunan:.0f}m")

    # 延伸軌道
    extended_coords = list(coords)

    # 如果起點距離彰化站超過 100m，則延伸
    if start_to_changhua > 100:
        print(f"延伸起點到彰化站")
        extended_coords.insert(0, changhua)

    # 如果終點距離竹南站超過 100m，則延伸
    if end_to_zhunan > 100:
        print(f"延伸終點到竹南站")
        extended_coords.append(zhunan)

    return extended_coords


def build_direction_0_track(wl_m_coords):
    """
    建立方向 0 軌道 (竹南→彰化)
    TDX 的 WL-M-0 是從彰化附近到竹南附近，需要反轉
    """
    # 反轉座標，使其從竹南到彰化
    coords = list(reversed(wl_m_coords))

    # 延伸到車站
    coords = extend_track_to_stations(coords)

    # 確保方向正確 (竹南在北，彰化在南)
    if coords[0][1] < coords[-1][1]:
        # 起點緯度較小，表示起點在南邊，需要反轉
        print("警告: 軌道方向錯誤，反轉中...")
        coords = list(reversed(coords))

    return remove_consecutive_duplicates(coords)


def save_golden_track(coords, track_id, name, origin, destination, direction):
    """儲存 Golden Track"""
    feature = {
        "type": "Feature",
        "properties": {
            "track_id": track_id,
            "line_id": "WL-M",
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


def calculate_all_station_progress(coords_0, coords_1):
    """計算所有車站的 progress"""
    progress_0 = {}  # 竹南→彰化
    progress_1 = {}  # 彰化→竹南

    print("\n=== 計算 Station Progress ===")
    print("\n方向 0 (竹南→彰化):")

    max_dist = 0
    for station_id, station_name in MOUNTAIN_STATIONS:
        station_coord = STATION_COORDS[station_id]
        prog, dist = calculate_station_progress(coords_0, station_coord)
        progress_0[station_id] = round(prog, 6)

        dist_m = dist * 111000
        if dist_m > max_dist:
            max_dist = dist_m
        status = "✓" if dist_m < 300 else "⚠️" if dist_m < 1000 else "✗"
        print(f"  {station_id} {station_name:4s}: progress={prog:.6f}, dist={dist_m:6.0f}m {status}")

    print(f"\n  最大距離: {max_dist:.0f}m")

    print("\n方向 1 (彰化→竹南):")
    for station_id, station_name in reversed(MOUNTAIN_STATIONS):
        station_coord = STATION_COORDS[station_id]
        prog, dist = calculate_station_progress(coords_1, station_coord)
        progress_1[station_id] = round(prog, 6)

        dist_m = dist * 111000
        status = "✓" if dist_m < 300 else "⚠️" if dist_m < 1000 else "✗"
        print(f"  {station_id} {station_name:4s}: progress={prog:.6f}, dist={dist_m:6.0f}m {status}")

    return progress_0, progress_1


def update_station_progress_file(progress_0, progress_1):
    """更新 od_station_progress.json"""
    progress_file = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')

    # 讀取現有資料
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            all_progress = json.load(f)
    else:
        all_progress = {}

    # 更新山線資料
    all_progress['WL-M-ZN-CH-0'] = progress_0
    all_progress['WL-M-CH-ZN-1'] = progress_1

    # 寫入檔案
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)

    print(f"\nUpdated: {progress_file}")


def main():
    print("=" * 60)
    print("建立 WL-M 山線 O-D 軌道")
    print("=" * 60)

    # 1. 載入軌道
    print("\n=== 載入軌道資料 ===")
    wl_m_0, wl_m_1 = load_wl_m_from_backup()
    print(f"WL-M-0: {len(wl_m_0)} points")
    print(f"  起點: {wl_m_0[0]}")
    print(f"  終點: {wl_m_0[-1]}")

    # 2. 建立方向 0 軌道 (竹南→彰化)
    print("\n=== 建立方向 0 軌道 (竹南→彰化) ===")
    coords_0 = build_direction_0_track(wl_m_0)
    print(f"方向 0 軌道: {len(coords_0)} points")
    print(f"  起點: {coords_0[0]} (竹南)")
    print(f"  終點: {coords_0[-1]} (彰化)")

    # 3. 建立方向 1 軌道 (彰化→竹南)
    print("\n=== 建立方向 1 軌道 (彰化→竹南) ===")
    coords_1 = list(reversed(coords_0))
    print(f"方向 1 軌道: {len(coords_1)} points")
    print(f"  起點: {coords_1[0]} (彰化)")
    print(f"  終點: {coords_1[-1]} (竹南)")

    # 4. 計算 station progress
    progress_0, progress_1 = calculate_all_station_progress(coords_0, coords_1)

    # 5. 儲存 Golden Track
    print("\n=== 儲存 Golden Track ===")
    save_golden_track(coords_0, "WL-M-ZN-CH-0", "山線", "竹南", "彰化", 0)
    save_golden_track(coords_1, "WL-M-CH-ZN-1", "山線", "彰化", "竹南", 1)

    # 6. 儲存 O-D Track
    print("\n=== 儲存 O-D Track ===")
    save_od_track(coords_0, "WL-M-ZN-CH-0", "山線", "竹南", "彰化", 0)
    save_od_track(coords_1, "WL-M-CH-ZN-1", "山線", "彰化", "竹南", 1)

    # 7. 更新 station progress
    print("\n=== 更新 Station Progress ===")
    update_station_progress_file(progress_0, progress_1)

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
