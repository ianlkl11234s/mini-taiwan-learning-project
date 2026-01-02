#!/usr/bin/env python3
"""
驗證 TMRT station_progress - 確認 interpolation 後的座標與車站座標一致
"""

import json
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "public" / "data-tmrt"


def euclidean_distance(lon1, lat1, lon2, lat2):
    dx = lon2 - lon1
    dy = lat2 - lat1
    return math.sqrt(dx * dx + dy * dy)


def calculate_total_length(coords):
    total = 0
    for i in range(len(coords) - 1):
        dx = coords[i + 1][0] - coords[i][0]
        dy = coords[i + 1][1] - coords[i][1]
        total += math.sqrt(dx * dx + dy * dy)
    return total


def interpolate_on_line_string(coords, progress):
    """
    與 TypeScript 版本相同的插值邏輯
    """
    if len(coords) == 0:
        return [0, 0]
    if len(coords) == 1:
        return coords[0]
    if progress <= 0:
        return coords[0]
    if progress >= 1:
        return coords[-1]

    total_length = calculate_total_length(coords)
    target_distance = total_length * progress

    accumulated = 0
    for i in range(len(coords) - 1):
        dx = coords[i + 1][0] - coords[i][0]
        dy = coords[i + 1][1] - coords[i][1]
        segment_length = math.sqrt(dx * dx + dy * dy)

        if accumulated + segment_length >= target_distance:
            segment_progress = (target_distance - accumulated) / segment_length if segment_length > 0 else 0
            return [
                coords[i][0] + dx * segment_progress,
                coords[i][1] + dy * segment_progress
            ]
        accumulated += segment_length

    return coords[-1]


def main():
    print("=" * 70)
    print("驗證 station_progress 插值結果")
    print("=" * 70)

    # 讀取資料
    with open(DATA_DIR / "station_progress.json") as f:
        station_progress = json.load(f)

    with open(DATA_DIR / "stations" / "tmrt_stations.geojson") as f:
        stations_data = json.load(f)

    stations = {}
    for feature in stations_data['features']:
        sid = feature['properties']['station_id']
        coords = feature['geometry']['coordinates']
        stations[sid] = {'name': feature['properties']['name_zh'], 'coords': coords}

    # 處理每個軌道
    for track_id in ['TMRT-G-0', 'TMRT-G-1']:
        with open(DATA_DIR / "tracks" / f"{track_id}.geojson") as f:
            track_data = json.load(f)

        track_coords = track_data['features'][0]['geometry']['coordinates']

        print(f"\n{track_id}")
        print("-" * 70)
        print(f"{'車站':8s} {'進度':12s} {'插值座標':30s} {'實際座標':30s} {'距離':12s}")
        print("-" * 70)

        progress_map = station_progress[track_id]

        max_error = 0
        max_error_station = None

        for sid, progress in progress_map.items():
            if sid not in stations:
                continue

            station = stations[sid]
            actual_coords = station['coords']

            # 使用進度值插值得到座標
            interp_coords = interpolate_on_line_string(track_coords, progress)

            # 計算誤差
            error = euclidean_distance(
                interp_coords[0], interp_coords[1],
                actual_coords[0], actual_coords[1]
            )

            if error > max_error:
                max_error = error
                max_error_station = sid

            status = "✓" if error < 0.00001 else "⚠️" if error < 0.0001 else "❌"

            print(f"{sid:8s} {progress:10.6f} [{interp_coords[0]:10.5f}, {interp_coords[1]:8.5f}] "
                  f"[{actual_coords[0]:10.5f}, {actual_coords[1]:8.5f}] {error:.8f} {status}")

        print(f"\n最大誤差: {max_error_station} = {max_error:.8f}")

    # 檢查時間與空間進度的對應關係
    print("\n" + "=" * 70)
    print("時間進度 vs 空間進度 分析")
    print("=" * 70)

    with open(DATA_DIR / "schedules" / "tmrt_schedules.json") as f:
        schedules = json.load(f)

    for track_id in ['TMRT-G-0']:  # 只分析一個方向
        schedule = schedules[track_id]
        first_departure = schedule['departures'][0]
        total_time = first_departure['total_travel_time']

        print(f"\n{track_id}")
        print(f"總行程時間: {total_time} 秒")
        print("-" * 70)
        print(f"{'車站':8s} {'到達秒':8s} {'時間進度':10s} {'空間進度':10s} {'差異':10s}")
        print("-" * 70)

        progress_map = station_progress[track_id]

        for station_time in first_departure['stations']:
            sid = station_time['station_id']
            arrival = station_time['arrival']
            departure = station_time['departure']

            time_progress = arrival / total_time if total_time > 0 else 0
            space_progress = progress_map.get(sid, 0)
            diff = space_progress - time_progress

            print(f"{sid:8s} {arrival:8d} {time_progress:10.4f} {space_progress:10.4f} {diff:+10.4f}")


if __name__ == '__main__':
    main()
