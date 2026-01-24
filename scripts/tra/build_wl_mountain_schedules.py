#!/usr/bin/env python3
"""
Build WL-M Mountain Line Test Schedules (Zhunan <-> Changhua)

Creates test schedules for the mountain line with:
- One train per hour from 06:00 to 22:00
- Realistic station stop times based on actual travel times

Mountain Line Stations (23 stations, ~87 km):
竹南 → 造橋 → 豐富 → 苗栗 → 南勢 → 銅鑼 → 三義 → 泰安 → 后里 → 豐原 →
栗林 → 潭子 → 頭家厝 → 松竹 → 太原 → 精武 → 臺中 → 五權 → 大慶 →
烏日 → 新烏日 → 成功 → 彰化
"""

import json
import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRA_DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
SCHEDULES_OD_DIR = os.path.join(TRA_DATA_DIR, 'schedules_od')

# Mountain line stations with approximate travel times (seconds from start)
# Total journey time: approximately 85-95 minutes for local trains
# Direction 0: 竹南 → 彰化 (north to south)
STATIONS_DIR_0 = [
    {'station_id': '1250', 'name': '竹南', 'travel_offset': 0},
    {'station_id': '3140', 'name': '造橋', 'travel_offset': 360},      # 6 min
    {'station_id': '3150', 'name': '豐富', 'travel_offset': 600},      # 10 min
    {'station_id': '3160', 'name': '苗栗', 'travel_offset': 900},      # 15 min
    {'station_id': '3170', 'name': '南勢', 'travel_offset': 1140},     # 19 min
    {'station_id': '3180', 'name': '銅鑼', 'travel_offset': 1500},     # 25 min
    {'station_id': '3190', 'name': '三義', 'travel_offset': 1980},     # 33 min
    {'station_id': '3210', 'name': '泰安', 'travel_offset': 2460},     # 41 min
    {'station_id': '3220', 'name': '后里', 'travel_offset': 2760},     # 46 min
    {'station_id': '3230', 'name': '豐原', 'travel_offset': 3120},     # 52 min
    {'station_id': '3232', 'name': '栗林', 'travel_offset': 3300},     # 55 min
    {'station_id': '3240', 'name': '潭子', 'travel_offset': 3480},     # 58 min
    {'station_id': '3243', 'name': '頭家厝', 'travel_offset': 3660},   # 61 min
    {'station_id': '3245', 'name': '松竹', 'travel_offset': 3840},     # 64 min
    {'station_id': '3247', 'name': '太原', 'travel_offset': 4020},     # 67 min
    {'station_id': '3249', 'name': '精武', 'travel_offset': 4200},     # 70 min
    {'station_id': '3300', 'name': '臺中', 'travel_offset': 4380},     # 73 min
    {'station_id': '3305', 'name': '五權', 'travel_offset': 4560},     # 76 min
    {'station_id': '3310', 'name': '大慶', 'travel_offset': 4740},     # 79 min
    {'station_id': '3320', 'name': '烏日', 'travel_offset': 4920},     # 82 min
    {'station_id': '3325', 'name': '新烏日', 'travel_offset': 5100},   # 85 min
    {'station_id': '3330', 'name': '成功', 'travel_offset': 5280},     # 88 min
    {'station_id': '3360', 'name': '彰化', 'travel_offset': 5580},     # 93 min
]

# Direction 1: 彰化 → 竹南 (south to north)
STATIONS_DIR_1 = [
    {'station_id': '3360', 'name': '彰化', 'travel_offset': 0},
    {'station_id': '3330', 'name': '成功', 'travel_offset': 300},      # 5 min
    {'station_id': '3325', 'name': '新烏日', 'travel_offset': 480},    # 8 min
    {'station_id': '3320', 'name': '烏日', 'travel_offset': 660},      # 11 min
    {'station_id': '3310', 'name': '大慶', 'travel_offset': 840},      # 14 min
    {'station_id': '3305', 'name': '五權', 'travel_offset': 1020},     # 17 min
    {'station_id': '3300', 'name': '臺中', 'travel_offset': 1200},     # 20 min
    {'station_id': '3249', 'name': '精武', 'travel_offset': 1380},     # 23 min
    {'station_id': '3247', 'name': '太原', 'travel_offset': 1560},     # 26 min
    {'station_id': '3245', 'name': '松竹', 'travel_offset': 1740},     # 29 min
    {'station_id': '3243', 'name': '頭家厝', 'travel_offset': 1920},   # 32 min
    {'station_id': '3240', 'name': '潭子', 'travel_offset': 2100},     # 35 min
    {'station_id': '3232', 'name': '栗林', 'travel_offset': 2280},     # 38 min
    {'station_id': '3230', 'name': '豐原', 'travel_offset': 2460},     # 41 min
    {'station_id': '3220', 'name': '后里', 'travel_offset': 2820},     # 47 min
    {'station_id': '3210', 'name': '泰安', 'travel_offset': 3120},     # 52 min
    {'station_id': '3190', 'name': '三義', 'travel_offset': 3600},     # 60 min
    {'station_id': '3180', 'name': '銅鑼', 'travel_offset': 4080},     # 68 min
    {'station_id': '3170', 'name': '南勢', 'travel_offset': 4440},     # 74 min
    {'station_id': '3160', 'name': '苗栗', 'travel_offset': 4680},     # 78 min
    {'station_id': '3150', 'name': '豐富', 'travel_offset': 4980},     # 83 min
    {'station_id': '3140', 'name': '造橋', 'travel_offset': 5220},     # 87 min
    {'station_id': '1250', 'name': '竹南', 'travel_offset': 5580},     # 93 min
]

DWELL_TIME = 60  # 60 seconds stop at each station


def time_to_seconds(time_str):
    """Convert HH:MM:SS to seconds since midnight."""
    parts = time_str.split(':')
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])


def seconds_to_time(seconds):
    """Convert seconds since midnight to HH:MM:SS."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def create_departure(train_id, train_no, departure_time, stations_info, od_track_id, origin, destination):
    """Create a single departure entry."""
    stations = []

    for i, st in enumerate(stations_info):
        arrival = st['travel_offset']
        # Last station has no departure (train terminates)
        if i == len(stations_info) - 1:
            departure = arrival
        else:
            departure = arrival + DWELL_TIME

        stations.append({
            'station_id': st['station_id'],
            'arrival': arrival,
            'departure': departure
        })

    return {
        'train_id': train_id,
        'train_no': train_no,
        'departure_time': departure_time,
        'origin': origin,
        'destination': destination,
        'od_track_id': od_track_id,
        'stations': stations
    }


def build_schedules():
    """Build test schedules for WL-M Mountain Line."""
    os.makedirs(SCHEDULES_OD_DIR, exist_ok=True)

    # Direction 0: 竹南 → 彰化
    departures_0 = []
    train_counter = 1

    for hour in range(6, 23):  # 06:00 to 22:00
        departure_time = f"{hour:02d}:00:00"
        train_no = f"3{hour:02d}1"  # e.g., 3061, 3071, etc.
        train_id = f"WL-M-ZN-CH-0-{train_counter:03d}"

        departure = create_departure(
            train_id=train_id,
            train_no=train_no,
            departure_time=departure_time,
            stations_info=STATIONS_DIR_0,
            od_track_id='WL-M-ZN-CH-0',
            origin='竹南',
            destination='彰化'
        )
        departures_0.append(departure)
        train_counter += 1

    schedule_0 = {
        'track_id': 'WL-M-ZN-CH-0',
        'line_name': '山線',
        'origin': '竹南',
        'destination': '彰化',
        'direction': 0,
        'departures': departures_0
    }

    filepath_0 = os.path.join(SCHEDULES_OD_DIR, 'WL-M-ZN-CH-0.json')
    with open(filepath_0, 'w', encoding='utf-8') as f:
        json.dump(schedule_0, f, ensure_ascii=False, indent=2)
    print(f"Created: {filepath_0} ({len(departures_0)} departures)")

    # Direction 1: 彰化 → 竹南
    departures_1 = []
    train_counter = 1

    for hour in range(6, 23):  # 06:00 to 22:00
        departure_time = f"{hour:02d}:30:00"  # Offset by 30 minutes from direction 0
        train_no = f"3{hour:02d}2"  # e.g., 3062, 3072, etc.
        train_id = f"WL-M-CH-ZN-1-{train_counter:03d}"

        departure = create_departure(
            train_id=train_id,
            train_no=train_no,
            departure_time=departure_time,
            stations_info=STATIONS_DIR_1,
            od_track_id='WL-M-CH-ZN-1',
            origin='彰化',
            destination='竹南'
        )
        departures_1.append(departure)
        train_counter += 1

    schedule_1 = {
        'track_id': 'WL-M-CH-ZN-1',
        'line_name': '山線',
        'origin': '彰化',
        'destination': '竹南',
        'direction': 1,
        'departures': departures_1
    }

    filepath_1 = os.path.join(SCHEDULES_OD_DIR, 'WL-M-CH-ZN-1.json')
    with open(filepath_1, 'w', encoding='utf-8') as f:
        json.dump(schedule_1, f, ensure_ascii=False, indent=2)
    print(f"Created: {filepath_1} ({len(departures_1)} departures)")

    print(f"\nTotal: {len(departures_0) + len(departures_1)} departures for WL-M Mountain Line")


if __name__ == '__main__':
    print("=" * 60)
    print("Building WL-M Mountain Line Test Schedules")
    print("=" * 60)
    build_schedules()
    print("=" * 60)
    print("Done!")
    print("=" * 60)
