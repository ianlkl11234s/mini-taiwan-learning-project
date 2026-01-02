#!/usr/bin/env python3
"""
建立台灣高鐵時刻表

從 TDX DailyTimetable 轉換為專案格式：
- thsr_schedules.json (符合 TrackSchedule 介面)

Usage:
    python scripts/build_thsr_schedules.py
"""

import json
from pathlib import Path
from datetime import datetime

# 路徑設定
DATA_DIR = Path(__file__).parent.parent / "data-thsr"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = DATA_DIR / "schedules"


def time_to_seconds(time_str: str) -> int:
    """將 HH:MM 轉換為當日秒數"""
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    return hours * 3600 + minutes * 60


def build_thsr_schedules():
    """建立高鐵時刻表"""

    # 確保輸出目錄存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n=== 建立台灣高鐵時刻表 ===\n")

    # 1. 讀取時刻表資料
    print("[1/3] 讀取時刻表資料...")
    with open(RAW_DIR / "thsr_timetable.json", 'r', encoding='utf-8') as f:
        timetable_data = json.load(f)
    print(f"      載入 {len(timetable_data)} 班車次")

    # 2. 讀取車站線序以取得完整站序
    print("[2/3] 讀取車站線序...")
    with open(RAW_DIR / "thsr_station_of_line.json", 'r', encoding='utf-8') as f:
        line_data = json.load(f)

    all_stations = line_data[0]['Stations']
    southbound_stations = [s['StationID'] for s in all_stations]  # 南港->左營
    northbound_stations = list(reversed(southbound_stations))     # 左營->南港

    print(f"      南下站序: {len(southbound_stations)} 站")
    print(f"      北上站序: {len(northbound_stations)} 站")

    # 3. 分類車次並轉換格式
    print("[3/3] 轉換時刻表格式...")

    # 南下 (Direction 0): THSR-1-0
    # 北上 (Direction 1): THSR-1-1
    departures_0 = []  # 南下
    departures_1 = []  # 北上

    for train in timetable_data:
        info = train['DailyTrainInfo']
        stop_times = train['StopTimes']
        direction = info['Direction']
        train_no = info['TrainNo']

        if not stop_times:
            continue

        # 取得發車時間
        first_stop = stop_times[0]
        departure_time = first_stop['DepartureTime'] + ":00"  # 加上秒數
        base_seconds = time_to_seconds(first_stop['DepartureTime'])

        # 轉換各站時間為相對秒數
        stations = []
        for stop in stop_times:
            arrival_seconds = time_to_seconds(stop['ArrivalTime']) - base_seconds
            departure_seconds = time_to_seconds(stop['DepartureTime']) - base_seconds

            # 處理跨日情況
            if arrival_seconds < 0:
                arrival_seconds += 24 * 3600
            if departure_seconds < 0:
                departure_seconds += 24 * 3600

            stations.append({
                "station_id": stop['StationID'],
                "arrival": arrival_seconds,
                "departure": departure_seconds
            })

        # 計算總行駛時間
        total_travel_time = stations[-1]['arrival'] if stations else 0

        departure = {
            "departure_time": departure_time,
            "train_id": f"THSR-{train_no}",
            "stations": stations,
            "total_travel_time": total_travel_time
        }

        if direction == 0:
            departures_0.append(departure)
        else:
            departures_1.append(departure)

    # 按發車時間排序
    departures_0.sort(key=lambda d: d['departure_time'])
    departures_1.sort(key=lambda d: d['departure_time'])

    # 建立 TrackSchedule 格式
    schedules = {
        "THSR-1-0": {
            "track_id": "THSR-1-0",
            "route_id": "THSR",
            "name": "台灣高鐵 南下",
            "origin": "南港",
            "destination": "左營",
            "stations": southbound_stations,
            "travel_time_minutes": 105,  # 約 1 小時 45 分
            "dwell_time_seconds": 120,   # 停站約 2 分鐘
            "is_weekday": True,
            "departure_count": len(departures_0),
            "departures": departures_0
        },
        "THSR-1-1": {
            "track_id": "THSR-1-1",
            "route_id": "THSR",
            "name": "台灣高鐵 北上",
            "origin": "左營",
            "destination": "南港",
            "stations": northbound_stations,
            "travel_time_minutes": 105,
            "dwell_time_seconds": 120,
            "is_weekday": True,
            "departure_count": len(departures_1),
            "departures": departures_1
        }
    }

    # 寫入檔案
    output_path = OUTPUT_DIR / "thsr_schedules.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schedules, f, ensure_ascii=False, indent=2)

    print("\n=== 建立完成 ===")
    print(f"輸出檔案: {output_path}")
    print(f"\n統計:")
    print(f"  南下班次: {len(departures_0)} 班")
    print(f"  北上班次: {len(departures_1)} 班")
    print(f"  總班次:   {len(departures_0) + len(departures_1)} 班")

    # 顯示部分範例
    print("\n南下首班車:")
    if departures_0:
        d = departures_0[0]
        print(f"  {d['train_id']} - {d['departure_time']}")
        print(f"  停靠站數: {len(d['stations'])}")
        print(f"  行駛時間: {d['total_travel_time'] // 60} 分鐘")

    print("\n北上首班車:")
    if departures_1:
        d = departures_1[0]
        print(f"  {d['train_id']} - {d['departure_time']}")
        print(f"  停靠站數: {len(d['stations'])}")
        print(f"  行駛時間: {d['total_travel_time'] // 60} 分鐘")


if __name__ == '__main__':
    build_thsr_schedules()
