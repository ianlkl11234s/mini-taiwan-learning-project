#!/usr/bin/env python3
"""
修正軌道上車站處的折角問題

策略：
1. 找到車站前後一定距離內的軌道點
2. 計算這兩點之間的直線
3. 將車站投影到直線上
4. 用直線段取代原本的折線段
"""

import json
import math
from pathlib import Path
from typing import NamedTuple
import shutil
from datetime import datetime


class FixResult(NamedTuple):
    station_id: str
    name: str
    original_angle: float
    new_angle: float
    original_coord: tuple[float, float]
    new_coord: tuple[float, float]
    distance_moved: float  # 公尺


def calculate_bearing(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """計算從點1到點2的方位角（度）"""
    dx = lon2 - lon1
    dy = lat2 - lat1
    angle = math.degrees(math.atan2(dx, dy))
    return (angle + 360) % 360


def angle_difference(bearing1: float, bearing2: float) -> float:
    """計算兩個方位角之間的最小差異（0-180度）"""
    diff = abs(bearing2 - bearing1)
    if diff > 180:
        diff = 360 - diff
    return diff


def euclidean_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """計算歐式距離（座標單位）"""
    dx = lon2 - lon1
    dy = lat2 - lat1
    return math.sqrt(dx * dx + dy * dy)


def haversine_distance_meters(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """計算兩點之間的距離（公尺）"""
    R = 6371000
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def find_coord_index(track_coords: list, station_coord: tuple, tolerance: float = 0.00001) -> int:
    """找到車站座標在軌道中的索引（精確匹配）"""
    for i, coord in enumerate(track_coords):
        if abs(coord[0] - station_coord[0]) < tolerance and abs(coord[1] - station_coord[1]) < tolerance:
            return i
    return -1


def find_nearest_coord_index(track_coords: list, station_coord: tuple, max_distance: float = 0.0005) -> int:
    """找到最接近車站座標的軌道點索引（距離匹配）

    Args:
        track_coords: 軌道座標列表
        station_coord: 車站座標
        max_distance: 最大搜尋距離（座標單位，約 50 公尺）

    Returns:
        最近點的索引，若超過最大距離則返回 -1
    """
    min_dist = float('inf')
    nearest_idx = -1

    for i, coord in enumerate(track_coords):
        dist = euclidean_distance(coord[0], coord[1], station_coord[0], station_coord[1])
        if dist < min_dist:
            min_dist = dist
            nearest_idx = i

    if min_dist <= max_distance:
        return nearest_idx
    return -1


def project_point_to_line(px: float, py: float,
                          ax: float, ay: float,
                          bx: float, by: float) -> tuple[float, float]:
    """
    將點 P 投影到線段 AB 上

    Returns:
        投影點座標 (x, y)
    """
    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy

    if length_sq == 0:
        return ax, ay

    # 計算投影參數 t
    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    t = max(0, min(1, t))  # 限制在 [0, 1] 範圍內

    # 計算投影點
    proj_x = ax + t * dx
    proj_y = ay + t * dy

    return proj_x, proj_y


def find_search_range(track_coords: list, station_idx: int, search_distance_meters: float = 100) -> tuple[int, int]:
    """
    找到車站前後一定距離內的軌道點索引

    Args:
        track_coords: 軌道座標列表
        station_idx: 車站在軌道中的索引
        search_distance_meters: 搜尋距離（公尺）

    Returns:
        (start_idx, end_idx) 前後點的索引
    """
    station_coord = track_coords[station_idx]

    # 往前搜尋
    start_idx = station_idx
    accumulated_dist = 0
    for i in range(station_idx - 1, -1, -1):
        dist = haversine_distance_meters(
            track_coords[i][0], track_coords[i][1],
            track_coords[i + 1][0], track_coords[i + 1][1]
        )
        accumulated_dist += dist
        if accumulated_dist >= search_distance_meters:
            start_idx = i
            break
    else:
        start_idx = max(0, station_idx - 1)

    # 往後搜尋
    end_idx = station_idx
    accumulated_dist = 0
    for i in range(station_idx + 1, len(track_coords)):
        dist = haversine_distance_meters(
            track_coords[i - 1][0], track_coords[i - 1][1],
            track_coords[i][0], track_coords[i][1]
        )
        accumulated_dist += dist
        if accumulated_dist >= search_distance_meters:
            end_idx = i
            break
    else:
        end_idx = min(len(track_coords) - 1, station_idx + 1)

    return start_idx, end_idx


def calculate_angle_at_index(track_coords: list, idx: int) -> float:
    """計算軌道在指定索引處的角度變化"""
    if idx <= 0 or idx >= len(track_coords) - 1:
        return 0

    prev_coord = track_coords[idx - 1]
    curr_coord = track_coords[idx]
    next_coord = track_coords[idx + 1]

    bearing_before = calculate_bearing(
        prev_coord[0], prev_coord[1],
        curr_coord[0], curr_coord[1]
    )
    bearing_after = calculate_bearing(
        curr_coord[0], curr_coord[1],
        next_coord[0], next_coord[1]
    )

    return angle_difference(bearing_before, bearing_after)


def fix_station_angle(
    track_coords: list,
    station_idx: int,
    search_distance_meters: float = 100,
    max_move_meters: float = 30
) -> tuple[list, tuple[float, float], float]:
    """
    修正單一車站的折角問題

    Args:
        track_coords: 軌道座標列表（會被修改）
        station_idx: 車站在軌道中的索引
        search_distance_meters: 搜尋直線端點的距離
        max_move_meters: 允許車站移動的最大距離

    Returns:
        (修改後的軌道座標, 新車站座標, 移動距離)
    """
    original_coord = track_coords[station_idx]

    # 找到前後的軌道點
    start_idx, end_idx = find_search_range(track_coords, station_idx, search_distance_meters)

    # 確保至少有前後各一個點
    if start_idx >= station_idx:
        start_idx = max(0, station_idx - 1)
    if end_idx <= station_idx:
        end_idx = min(len(track_coords) - 1, station_idx + 1)

    start_coord = track_coords[start_idx]
    end_coord = track_coords[end_idx]

    # 將車站投影到直線上
    new_lon, new_lat = project_point_to_line(
        original_coord[0], original_coord[1],
        start_coord[0], start_coord[1],
        end_coord[0], end_coord[1]
    )

    # 計算移動距離
    move_distance = haversine_distance_meters(
        original_coord[0], original_coord[1],
        new_lon, new_lat
    )

    # 如果移動距離超過限制，則不修正
    if move_distance > max_move_meters:
        return track_coords, tuple(original_coord), 0

    # 更新軌道座標
    new_coords = track_coords.copy()

    # 刪除 start_idx+1 到 end_idx-1 之間的所有點（包括原車站點）
    # 然後插入新的車站點
    del new_coords[start_idx + 1:end_idx]
    new_coords.insert(start_idx + 1, [new_lon, new_lat])

    return new_coords, (new_lon, new_lat), move_distance


def fix_track_angles(
    track_file: Path,
    stations_file: Path,
    output_track_file: Path,
    output_stations_file: Path,
    angle_threshold: float = 10.0,
    search_distance: float = 100,
    max_move: float = 30
) -> list[FixResult]:
    """
    修正軌道上所有問題車站的折角

    Args:
        track_file: 輸入軌道 GeoJSON
        stations_file: 輸入車站 GeoJSON
        output_track_file: 輸出軌道 GeoJSON
        output_stations_file: 輸出車站 GeoJSON
        angle_threshold: 角度閾值
        search_distance: 搜尋距離（公尺）
        max_move: 最大移動距離（公尺）

    Returns:
        修正結果列表
    """
    # 讀取資料
    with open(track_file, 'r', encoding='utf-8') as f:
        track_data = json.load(f)

    with open(stations_file, 'r', encoding='utf-8') as f:
        stations_data = json.load(f)

    track_coords = track_data['features'][0]['geometry']['coordinates']

    # 建立車站資訊
    stations = {}
    for feature in stations_data['features']:
        sid = feature['properties']['station_id']
        coords = feature['geometry']['coordinates']
        name = feature['properties']['name_zh']
        stations[sid] = {
            'name': name,
            'coords': tuple(coords),
            'feature': feature
        }

    results = []

    # 找出所有需要修正的車站（使用最近點搜尋，而非精確匹配）
    stations_to_fix = []
    for sid, sdata in stations.items():
        # 先嘗試精確匹配
        idx = find_coord_index(track_coords, sdata['coords'])
        # 若找不到，嘗試最近點搜尋
        if idx == -1:
            idx = find_nearest_coord_index(track_coords, sdata['coords'])

        if idx == -1 or idx == 0 or idx >= len(track_coords) - 1:
            continue

        angle = calculate_angle_at_index(track_coords, idx)
        if angle >= angle_threshold:
            stations_to_fix.append((idx, sid, sdata, angle))

    # 按索引從後往前排序
    stations_to_fix.sort(key=lambda x: x[0], reverse=True)

    # 逐一修正
    for idx, sid, sdata, original_angle in stations_to_fix:
        # 重新找索引（使用最近點搜尋）
        current_idx = find_coord_index(track_coords, sdata['coords'])
        if current_idx == -1:
            current_idx = find_nearest_coord_index(track_coords, sdata['coords'])
        if current_idx == -1:
            continue

        track_coords, new_coord, move_dist = fix_station_angle(
            track_coords,
            current_idx,
            search_distance,
            max_move
        )

        if move_dist > 0:
            # 更新車站座標
            for feature in stations_data['features']:
                if feature['properties']['station_id'] == sid:
                    feature['geometry']['coordinates'] = list(new_coord)
                    break

            # 重新計算新角度
            new_idx = find_coord_index(track_coords, new_coord)
            new_angle = calculate_angle_at_index(track_coords, new_idx) if new_idx != -1 else 0

            results.append(FixResult(
                station_id=sid,
                name=sdata['name'],
                original_angle=original_angle,
                new_angle=new_angle,
                original_coord=sdata['coords'],
                new_coord=new_coord,
                distance_moved=move_dist
            ))

            # 更新 sdata 以供後續使用
            sdata['coords'] = new_coord

    # 更新軌道資料
    track_data['features'][0]['geometry']['coordinates'] = track_coords

    # 儲存結果
    with open(output_track_file, 'w', encoding='utf-8') as f:
        json.dump(track_data, f, indent=2, ensure_ascii=False)

    with open(output_stations_file, 'w', encoding='utf-8') as f:
        json.dump(stations_data, f, indent=2, ensure_ascii=False)

    return results


def main():
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "public" / "data" / "klrt"
    BACKUP_DIR = PROJECT_ROOT / "scripts" / "backup_klrt"

    print("=" * 70)
    print("高雄輕軌軌道折角修正")
    print("=" * 70)

    # 建立備份目錄
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    stations_file = DATA_DIR / "stations" / "klrt_stations.geojson"

    # 備份原始檔案
    print(f"\n📁 備份原始檔案到 {BACKUP_DIR}")
    shutil.copy(stations_file, BACKUP_DIR / f"klrt_stations_{timestamp}.geojson")

    all_results = []

    for track_id in ['KLRT-C-0', 'KLRT-C-1']:
        track_file = DATA_DIR / "tracks" / f"{track_id}.geojson"

        # 備份軌道檔案
        shutil.copy(track_file, BACKUP_DIR / f"{track_id}_{timestamp}.geojson")

        print(f"\n🔧 修正軌道: {track_id}")
        print("-" * 70)

        # 重新讀取最新的車站資料（因為可能被上一個軌道修改過）
        results = fix_track_angles(
            track_file=track_file,
            stations_file=stations_file,
            output_track_file=track_file,  # 覆蓋原檔案
            output_stations_file=stations_file,  # 覆蓋原檔案
            angle_threshold=10.0,
            search_distance=100,
            max_move=30
        )

        if results:
            print(f"\n{'站號':8s} {'站名':12s} {'原角度':8s} {'新角度':8s} {'移動':10s}")
            print("-" * 70)

            for r in results:
                status = "✅" if r.new_angle < 10 else "⚠️"
                print(f"{r.station_id:8s} {r.name:12s} {r.original_angle:6.1f}° {r.new_angle:6.1f}° "
                      f"{r.distance_moved:8.1f}m {status}")

            all_results.extend(results)
        else:
            print("  沒有需要修正的車站")

    print("\n" + "=" * 70)
    print("修正摘要")
    print("=" * 70)
    print(f"共修正 {len(all_results)} 個車站")

    if all_results:
        fixed_count = sum(1 for r in all_results if r.new_angle < 10)
        still_bad = sum(1 for r in all_results if r.new_angle >= 10)
        avg_improvement = sum(r.original_angle - r.new_angle for r in all_results) / len(all_results)

        print(f"  - 成功修正（<10°）: {fixed_count} 站")
        print(f"  - 仍需注意（>=10°）: {still_bad} 站")
        print(f"  - 平均角度改善: {avg_improvement:.1f}°")

    print(f"\n✅ 已覆蓋原始檔案")
    print(f"📁 備份已儲存至: {BACKUP_DIR}")


if __name__ == '__main__':
    main()
