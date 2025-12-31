#!/usr/bin/env python3
"""
修正 station_progress.json - 確保列車停站時精確對齊車站位置

問題：原本的 station_progress 計算有誤差，導致列車停站時
     與車站位置偏離 20-40 米。

解決：找到車站在軌道上的精確投影位置，計算正確的進度值。
"""

import json
import os
from typing import List, Tuple, Dict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "public/data/station_progress.json")
TRACK_DIR = os.path.join(PROJECT_ROOT, "public/data/tracks")
SCHEDULE_DIR = os.path.join(PROJECT_ROOT, "public/data/schedules")

# 所有車站 GeoJSON 檔案
STATION_FILES = [
    "red_line_stations.geojson",
    "blue_line_stations.geojson",
    "green_line_stations.geojson",
    "orange_line_stations.geojson",
    "brown_line_stations.geojson",
    "ankeng_lrt_stations.geojson",
    "danhai_lrt_stations.geojson",
    "tymc_stations.geojson",
    "ntmc_stations.geojson",
]


def dist(c1: List[float], c2: List[float]) -> float:
    """計算兩點距離"""
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** 0.5


def point_to_segment_projection(
    point: List[float], seg_start: List[float], seg_end: List[float]
) -> Tuple[List[float], float]:
    """
    計算點到線段的投影點和參數 t (0-1)
    t=0 表示在 seg_start，t=1 表示在 seg_end
    """
    dx = seg_end[0] - seg_start[0]
    dy = seg_end[1] - seg_start[1]

    if dx == 0 and dy == 0:
        return seg_start, 0.0

    t = ((point[0] - seg_start[0]) * dx + (point[1] - seg_start[1]) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))  # 限制在 [0, 1]

    proj = [seg_start[0] + t * dx, seg_start[1] + t * dy]
    return proj, t


def find_station_on_track(
    station_coord: List[float], track_coords: List[List[float]]
) -> Tuple[float, List[float], float]:
    """
    找到車站在軌道上的精確位置

    Returns:
        progress: 在軌道上的進度 (0-1)
        projection: 投影點座標
        distance: 車站到投影點的距離
    """
    # 計算軌道總長度
    total_length = sum(
        dist(track_coords[i], track_coords[i + 1])
        for i in range(len(track_coords) - 1)
    )

    if total_length == 0:
        return 0.0, track_coords[0], dist(station_coord, track_coords[0])

    # 找最近的線段和投影點
    best_progress = 0.0
    best_projection = track_coords[0]
    best_distance = float('inf')

    accumulated = 0.0

    for i in range(len(track_coords) - 1):
        seg_start = track_coords[i]
        seg_end = track_coords[i + 1]
        seg_length = dist(seg_start, seg_end)

        # 計算投影
        proj, t = point_to_segment_projection(station_coord, seg_start, seg_end)
        proj_dist = dist(station_coord, proj)

        if proj_dist < best_distance:
            best_distance = proj_dist
            best_projection = proj
            best_progress = (accumulated + t * seg_length) / total_length

        accumulated += seg_length

    return best_progress, best_projection, best_distance


def load_all_stations() -> Dict[str, List[float]]:
    """載入所有車站座標"""
    stations = {}
    data_dir = os.path.join(PROJECT_ROOT, "public/data")

    for filename in STATION_FILES:
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for feature in data['features']:
            station_id = feature['properties']['station_id']
            coord = feature['geometry']['coordinates']
            stations[station_id] = coord

    return stations


def load_track(track_id: str) -> List[List[float]]:
    """載入軌道座標"""
    filepath = os.path.join(TRACK_DIR, f"{track_id}.geojson")
    if not os.path.exists(filepath):
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data['features'][0]['geometry']['coordinates']


def load_schedule(track_id: str) -> Dict:
    """載入時刻表"""
    filepath = os.path.join(SCHEDULE_DIR, f"{track_id}.json")
    if not os.path.exists(filepath):
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    print("🔧 修正 station_progress.json - 車站對齊")
    print("=" * 60)

    # 載入所有車站座標
    all_stations = load_all_stations()
    print(f"📍 載入 {len(all_stations)} 個車站座標")

    # 載入現有 progress
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        old_progress = json.load(f)

    print(f"📊 處理 {len(old_progress)} 條軌道")
    print()

    new_progress = {}
    total_fixed = 0
    max_error_before = 0
    max_error_after = 0

    for track_id in old_progress.keys():
        track_coords = load_track(track_id)
        if not track_coords:
            new_progress[track_id] = old_progress[track_id]
            continue

        schedule = load_schedule(track_id)
        if not schedule:
            new_progress[track_id] = old_progress[track_id]
            continue

        # 取得此軌道的車站順序
        station_ids = schedule.get('stations', [])
        if not station_ids:
            new_progress[track_id] = old_progress[track_id]
            continue

        # 計算每個車站的精確進度
        track_progress = {}

        for station_id in station_ids:
            if station_id not in all_stations:
                # 使用舊值
                if station_id in old_progress[track_id]:
                    track_progress[station_id] = old_progress[track_id][station_id]
                continue

            station_coord = all_stations[station_id]
            progress, projection, distance = find_station_on_track(station_coord, track_coords)

            # 記錄誤差
            error_m = distance * 111000
            max_error_after = max(max_error_after, error_m)

            # 計算舊進度的誤差
            old_prog = old_progress[track_id].get(station_id, 0)
            old_total_length = sum(
                dist(track_coords[i], track_coords[i + 1])
                for i in range(len(track_coords) - 1)
            )
            old_target = old_total_length * old_prog
            old_acc = 0
            old_pos = track_coords[0]
            for i in range(len(track_coords) - 1):
                seg_len = dist(track_coords[i], track_coords[i + 1])
                if old_acc + seg_len >= old_target:
                    t = (old_target - old_acc) / seg_len if seg_len > 0 else 0
                    old_pos = [
                        track_coords[i][0] + (track_coords[i + 1][0] - track_coords[i][0]) * t,
                        track_coords[i][1] + (track_coords[i + 1][1] - track_coords[i][1]) * t,
                    ]
                    break
                old_acc += seg_len
            old_error = dist(old_pos, station_coord) * 111000
            max_error_before = max(max_error_before, old_error)

            if abs(progress - old_prog) > 0.001:
                total_fixed += 1

            track_progress[station_id] = progress

        new_progress[track_id] = track_progress

    print(f"✅ 修正 {total_fixed} 個車站進度值")
    print(f"📉 修正前最大誤差: {max_error_before:.1f} 米")
    print(f"📈 修正後最大誤差: {max_error_after:.1f} 米")
    print()

    # 驗證 G-1-0
    print("=== 驗證 G-1-0 綠線 ===")
    track_coords = load_track('G-1-0')
    total_length = sum(
        dist(track_coords[i], track_coords[i + 1])
        for i in range(len(track_coords) - 1)
    )

    print(f"{'車站':<6} {'新進度':<12} {'計算位置':<28} {'車站位置':<28} {'誤差(米)':<10}")
    print("-" * 95)

    for sid in ['G07', 'G08', 'G09', 'G10']:
        if sid not in new_progress.get('G-1-0', {}):
            continue

        prog = new_progress['G-1-0'][sid]
        station_coord = all_stations.get(sid, [0, 0])

        # 計算位置
        target = total_length * prog
        acc = 0
        pos = track_coords[0]
        for i in range(len(track_coords) - 1):
            seg_len = dist(track_coords[i], track_coords[i + 1])
            if acc + seg_len >= target:
                t = (target - acc) / seg_len if seg_len > 0 else 0
                pos = [
                    track_coords[i][0] + (track_coords[i + 1][0] - track_coords[i][0]) * t,
                    track_coords[i][1] + (track_coords[i + 1][1] - track_coords[i][1]) * t,
                ]
                break
            acc += seg_len

        error = dist(pos, station_coord) * 111000
        print(f"{sid:<6} {prog:<12.6f} [{pos[0]:.5f}, {pos[1]:.5f}]  [{station_coord[0]:.5f}, {station_coord[1]:.5f}]  {error:.1f}m")

    # 寫入
    print()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_progress, f, indent=2, ensure_ascii=False)
    print(f"💾 已更新: {PROGRESS_FILE}")

    print()
    print("🎉 完成！請重新載入頁面驗證")


if __name__ == "__main__":
    main()
