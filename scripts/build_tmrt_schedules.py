#!/usr/bin/env python3
"""
建立台中捷運時刻表

由於 TDX 無提供 TMRT StationTimeTable API，
使用 S2STravelTime 和固定班距生成合成時刻表。

台中捷運綠線營運資訊：
- 營運時間：06:00 - 24:00
- 尖峰班距：約 5 分鐘
- 離峰班距：約 8 分鐘
- 全程行駛時間：約 32 分鐘

Usage:
    python scripts/build_tmrt_schedules.py
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# 路徑設定
DATA_DIR = Path(__file__).parent.parent / "data-tmrt"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "data-tmrt" / "schedules"

# 線路配置
LINES_CONFIG = {
    'G': {
        'name': '綠線',
        'direction_0': {
            'origin': 'G0',
            'destination': 'G17',
            'name': '北屯總站 → 高鐵台中站',
            'stations': ['G0', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G8a', 'G9', 'G10', 'G10a', 'G11', 'G12', 'G13', 'G14', 'G15', 'G16', 'G17']
        },
        'direction_1': {
            'origin': 'G17',
            'destination': 'G0',
            'name': '高鐵台中站 → 北屯總站',
            'stations': ['G17', 'G16', 'G15', 'G14', 'G13', 'G12', 'G11', 'G10a', 'G10', 'G9', 'G8a', 'G8', 'G7', 'G6', 'G5', 'G4', 'G3', 'G0']
        }
    }
}

# 營運時間設定
OPERATION_START = 6 * 3600  # 06:00
OPERATION_END = 24 * 3600   # 24:00
PEAK_HEADWAY = 5 * 60       # 尖峰班距 5 分鐘
OFFPEAK_HEADWAY = 8 * 60    # 離峰班距 8 分鐘
DEFAULT_DWELL_TIME = 30     # 預設停站時間 30 秒


def time_to_seconds(time_str: str) -> int:
    """將 HH:MM 轉換為當日秒數"""
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    return hours * 3600 + minutes * 60


def seconds_to_time(seconds: int) -> str:
    """將秒數轉換為 HH:MM:SS"""
    hours = (seconds // 3600) % 24
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def load_s2s_travel_time() -> List[Dict]:
    """載入站間行駛時間"""
    with open(RAW_DIR / "tmrt_s2s_travel_time.json", 'r', encoding='utf-8') as f:
        return json.load(f)


def build_travel_time_map(s2s_data: List[Dict]) -> Dict[str, Dict[str, int]]:
    """
    建立站間行駛時間映射表

    返回：{ 'G0->G3': { 'run': 124, 'stop': 30 } }
    """
    travel_map = {}

    for item in s2s_data:
        for travel in item.get('TravelTimes', []):
            from_station = travel['FromStationID']
            to_station = travel['ToStationID']
            key = f"{from_station}->{to_station}"
            # TMRT 的 StopTime 是 0，使用預設值
            stop_time = travel.get('StopTime', 0)
            if stop_time == 0:
                stop_time = DEFAULT_DWELL_TIME
            travel_map[key] = {
                'run': travel.get('RunTime', 90),
                'stop': stop_time
            }

    return travel_map


def get_headway(current_seconds: int) -> int:
    """
    根據時間決定班距
    尖峰時段：07:00-09:00, 17:00-19:00
    """
    hour = current_seconds // 3600
    if (7 <= hour < 9) or (17 <= hour < 19):
        return PEAK_HEADWAY
    return OFFPEAK_HEADWAY


def generate_departures(start_time: int, end_time: int) -> List[int]:
    """
    生成發車時間列表
    """
    departures = []
    current_time = start_time

    while current_time < end_time:
        departures.append(current_time)
        headway = get_headway(current_time)
        current_time += headway

    return departures


def build_train_schedule(
    departure_seconds: int,
    stations: List[str],
    travel_map: Dict[str, Dict[str, int]],
    train_id: str
) -> Dict:
    """
    建立單一班次的完整時刻表
    """
    current_seconds = 0
    station_times = []

    for i, station_id in enumerate(stations):
        if i == 0:
            # 起點站
            next_key = f"{station_id}->{stations[i+1]}" if i + 1 < len(stations) else None
            stop_time = travel_map.get(next_key, {}).get('stop', DEFAULT_DWELL_TIME) if next_key else DEFAULT_DWELL_TIME
            stop_time = min(stop_time, 45)  # 限制起點站停留時間

            station_times.append({
                'station_id': station_id,
                'arrival': 0,
                'departure': stop_time
            })
            current_seconds = stop_time
        else:
            # 計算行駛時間
            prev_station = stations[i - 1]
            key = f"{prev_station}->{station_id}"
            run_time = travel_map.get(key, {}).get('run', 90)

            arrival = current_seconds + run_time

            if i < len(stations) - 1:
                next_key = f"{station_id}->{stations[i+1]}"
                stop_time = travel_map.get(next_key, {}).get('stop', DEFAULT_DWELL_TIME)
                stop_time = min(stop_time, DEFAULT_DWELL_TIME)
                departure = arrival + stop_time
            else:
                departure = arrival

            station_times.append({
                'station_id': station_id,
                'arrival': arrival,
                'departure': departure
            })
            current_seconds = departure

    total_travel_time = station_times[-1]['arrival'] if station_times else 0

    return {
        'departure_time': seconds_to_time(departure_seconds),
        'train_id': train_id,
        'stations': station_times,
        'total_travel_time': total_travel_time
    }


def main():
    print("=" * 50)
    print("台中捷運時刻表建立腳本")
    print("=" * 50)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 載入資料
    print("\n載入資料...")
    s2s_data = load_s2s_travel_time()
    print(f"  站間時間筆數: {len(s2s_data)}")

    # 建立站間時間映射
    travel_map = build_travel_time_map(s2s_data)
    print(f"  站間時間映射: {len(travel_map)} 組")

    # 處理每條線路
    schedules = {}

    for line_id, line_config in LINES_CONFIG.items():
        print(f"\n處理 {line_config['name']}...")

        for direction in [0, 1]:
            dir_config = line_config[f'direction_{direction}']
            track_id = f"TMRT-{line_id}-{direction}"

            print(f"\n  {track_id} ({dir_config['name']})...")

            # 生成發車時間
            departure_times = generate_departures(OPERATION_START, OPERATION_END)
            print(f"    發車班次: {len(departure_times)}")

            # 建立每班車的時刻表
            departures = []
            for i, dep_time in enumerate(departure_times):
                train_id = f"TMRT-{line_id}-{direction}-{i+1:03d}"
                schedule = build_train_schedule(
                    dep_time,
                    dir_config['stations'],
                    travel_map,
                    train_id
                )
                departures.append(schedule)

            # 按發車時間排序
            departures.sort(key=lambda x: x['departure_time'])

            # 計算統計資訊
            total_minutes = departures[0]['total_travel_time'] // 60 if departures else 0

            schedules[track_id] = {
                'track_id': track_id,
                'route_id': f"TMRT-{line_id}",
                'name': dir_config['name'],
                'origin': dir_config['origin'],
                'destination': dir_config['destination'],
                'stations': dir_config['stations'],
                'travel_time_minutes': total_minutes,
                'dwell_time_seconds': DEFAULT_DWELL_TIME,
                'service_tag': '平日',
                'is_weekday': True,
                'departure_count': len(departures),
                'departures': departures
            }

            print(f"    班次數: {len(departures)}")
            print(f"    行車時間: {total_minutes} 分鐘")
            if departures:
                print(f"    首班: {departures[0]['departure_time']}")
                print(f"    末班: {departures[-1]['departure_time']}")

    # 儲存結果
    output_path = OUTPUT_DIR / "tmrt_schedules.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schedules, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print("完成！")
    print("=" * 50)
    print(f"\n產出檔案: {output_path}")

    # 統計摘要
    total_trains = sum(s['departure_count'] for s in schedules.values())
    print(f"\n統計:")
    for track_id, schedule in schedules.items():
        print(f"  {track_id}: {schedule['departure_count']} 班")
    print(f"  總計: {total_trains} 班")


if __name__ == '__main__':
    main()
