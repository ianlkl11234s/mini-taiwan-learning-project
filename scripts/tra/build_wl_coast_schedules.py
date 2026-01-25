#!/usr/bin/env python3
"""
Build WL-C Coastal Line Test Schedules (Zhunan <-> Changhua)

Creates test schedules for the coastal line with:
- One train per hour from 06:00 to 22:00
- Realistic station stop times based on actual travel times

Coastal Line Stations (18 stations, ~91 km):
彰化 → 追分 → 大肚 → 龍井 → 沙鹿 → 清水 → 臺中港 → 大甲 → 日南 →
苑裡 → 通霄 → 新埔 → 白沙屯 → 龍港 → 後龍 → 大山 → 談文 → 竹南
"""

import json
import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRA_DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
SCHEDULES_OD_DIR = os.path.join(TRA_DATA_DIR, 'schedules_od')

# Coastal line stations with approximate travel times (seconds from start)
# Total journey time: approximately 80-90 minutes for local trains
# Direction 0: 彰化 → 竹南 (south to north)
STATIONS_DIR_0 = [
    {'station_id': '3360', 'name': '彰化', 'travel_offset': 0},
    {'station_id': '2260', 'name': '追分', 'travel_offset': 360},      # 6 min
    {'station_id': '2250', 'name': '大肚', 'travel_offset': 660},      # 11 min
    {'station_id': '2240', 'name': '龍井', 'travel_offset': 960},      # 16 min
    {'station_id': '2230', 'name': '沙鹿', 'travel_offset': 1260},     # 21 min
    {'station_id': '2220', 'name': '清水', 'travel_offset': 1500},     # 25 min
    {'station_id': '2210', 'name': '臺中港', 'travel_offset': 1800},   # 30 min
    {'station_id': '2200', 'name': '大甲', 'travel_offset': 2160},     # 36 min
    {'station_id': '2190', 'name': '日南', 'travel_offset': 2460},     # 41 min
    {'station_id': '2180', 'name': '苑裡', 'travel_offset': 2880},     # 48 min
    {'station_id': '2170', 'name': '通霄', 'travel_offset': 3240},     # 54 min
    {'station_id': '2160', 'name': '新埔', 'travel_offset': 3540},     # 59 min
    {'station_id': '2150', 'name': '白沙屯', 'travel_offset': 3780},   # 63 min
    {'station_id': '2140', 'name': '龍港', 'travel_offset': 4260},     # 71 min
    {'station_id': '2130', 'name': '後龍', 'travel_offset': 4500},     # 75 min
    {'station_id': '2120', 'name': '大山', 'travel_offset': 4740},     # 79 min
    {'station_id': '2110', 'name': '談文', 'travel_offset': 5100},     # 85 min
    {'station_id': '1250', 'name': '竹南', 'travel_offset': 5400},     # 90 min
]

# Direction 1: 竹南 → 彰化 (north to south)
STATIONS_DIR_1 = [
    {'station_id': '1250', 'name': '竹南', 'travel_offset': 0},
    {'station_id': '2110', 'name': '談文', 'travel_offset': 300},      # 5 min
    {'station_id': '2120', 'name': '大山', 'travel_offset': 660},      # 11 min
    {'station_id': '2130', 'name': '後龍', 'travel_offset': 900},      # 15 min
    {'station_id': '2140', 'name': '龍港', 'travel_offset': 1140},     # 19 min
    {'station_id': '2150', 'name': '白沙屯', 'travel_offset': 1620},   # 27 min
    {'station_id': '2160', 'name': '新埔', 'travel_offset': 1860},     # 31 min
    {'station_id': '2170', 'name': '通霄', 'travel_offset': 2160},     # 36 min
    {'station_id': '2180', 'name': '苑裡', 'travel_offset': 2520},     # 42 min
    {'station_id': '2190', 'name': '日南', 'travel_offset': 2940},     # 49 min
    {'station_id': '2200', 'name': '大甲', 'travel_offset': 3240},     # 54 min
    {'station_id': '2210', 'name': '臺中港', 'travel_offset': 3600},   # 60 min
    {'station_id': '2220', 'name': '清水', 'travel_offset': 3900},     # 65 min
    {'station_id': '2230', 'name': '沙鹿', 'travel_offset': 4140},     # 69 min
    {'station_id': '2240', 'name': '龍井', 'travel_offset': 4440},     # 74 min
    {'station_id': '2250', 'name': '大肚', 'travel_offset': 4740},     # 79 min
    {'station_id': '2260', 'name': '追分', 'travel_offset': 5040},     # 84 min
    {'station_id': '3360', 'name': '彰化', 'travel_offset': 5400},     # 90 min
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
        'train_type': '區間',
        'departure_time': departure_time,
        'od_track_id': od_track_id,
        'origin_station': origin,
        'destination_station': destination,
        'total_travel_time': stations[-1]['arrival'],
        'stations': stations
    }


def create_schedule(direction=0):
    """Create schedule for one direction."""
    if direction == 0:
        track_id = "WL-CH-ZN-0"
        od_track_id = "WL-CH-ZN-0"
        origin = "彰化"
        destination = "竹南"
        stations_info = STATIONS_DIR_0
    else:
        track_id = "WL-ZN-CH-1"
        od_track_id = "WL-ZN-CH-1"
        origin = "竹南"
        destination = "彰化"
        stations_info = STATIONS_DIR_1

    departures = []

    # Create one train per hour from 06:00 to 22:00
    for hour in range(6, 23):
        train_no = f"WLC{hour:02d}"
        train_id = f"{track_id}-{hour:02d}"
        departure_time = f"{hour:02d}:00:00"

        departure = create_departure(
            train_id=train_id,
            train_no=train_no,
            departure_time=departure_time,
            stations_info=stations_info,
            od_track_id=od_track_id,
            origin=origin,
            destination=destination
        )
        departures.append(departure)

    return {
        'track_id': track_id,
        'departures': departures
    }


def main():
    print("=== Building WL-C Coastal Line Schedules ===\n")

    # Create schedules
    schedule_0 = create_schedule(direction=0)
    schedule_1 = create_schedule(direction=1)

    # Save schedules
    schedule_0_path = os.path.join(SCHEDULES_OD_DIR, 'WL-CH-ZN-0.json')
    schedule_1_path = os.path.join(SCHEDULES_OD_DIR, 'WL-ZN-CH-1.json')

    with open(schedule_0_path, 'w', encoding='utf-8') as f:
        json.dump(schedule_0, f, indent=2, ensure_ascii=False)
    print(f"Created: {schedule_0_path}")
    print(f"  - {len(schedule_0['departures'])} trains")
    print(f"  - Route: 彰化 → 竹南")
    print(f"  - Travel time: {STATIONS_DIR_0[-1]['travel_offset'] // 60} minutes")

    with open(schedule_1_path, 'w', encoding='utf-8') as f:
        json.dump(schedule_1, f, indent=2, ensure_ascii=False)
    print(f"\nCreated: {schedule_1_path}")
    print(f"  - {len(schedule_1['departures'])} trains")
    print(f"  - Route: 竹南 → 彰化")
    print(f"  - Travel time: {STATIONS_DIR_1[-1]['travel_offset'] // 60} minutes")

    print("\n=== Summary ===")
    print(f"Total trains: {len(schedule_0['departures']) + len(schedule_1['departures'])}")
    print(f"Operating hours: 06:00 - 22:00")
    print(f"Frequency: Every hour")
    print(f"Stations: 18 stations")


if __name__ == '__main__':
    main()
