#!/usr/bin/env python3
"""
build_wl_north_schedules.py
建立西部幹線北段 (WL-N) 竹南→樹林 測試時刻表

輸出檔案：
- schedules_od/WL-ZN-SL-0.json (竹南→樹林)
- schedules_od/WL-SL-ZN-1.json (樹林→竹南)
"""

import json
import os
from typing import List, Tuple

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRA_DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')

# 竹南→樹林主線車站 (22站)
# 順序：由南往北（方向 0: 竹南→樹林）
WL_N_STATIONS_0 = [
    ('1250', '竹南'),
    ('1240', '崎頂'),
    ('1230', '香山'),
    ('1220', '三姓橋'),
    ('1210', '新竹'),
    ('1190', '北新竹'),
    ('1180', '竹北'),
    ('1170', '新豐'),
    ('1160', '湖口'),
    ('1150', '北湖'),
    ('1140', '新富'),
    ('1130', '富岡'),
    ('1120', '楊梅'),
    ('1110', '埔心'),
    ('1100', '中壢'),
    ('1090', '內壢'),
    ('1080', '桃園'),
    ('1075', '鳳鳴'),
    ('1070', '鶯歌'),
    ('1060', '山佳'),
    ('1050', '南樹林'),
    ('1040', '樹林'),
]

# 反向 (方向 1: 樹林→竹南)
WL_N_STATIONS_1 = list(reversed(WL_N_STATIONS_0))

# 時刻表參數
DWELL_TIME = 30  # 停站時間 (秒)
INTER_STATION_TIME = 150  # 站間行車時間 (秒，約 2.5 分鐘)
TOTAL_TRAVEL_TIME = (len(WL_N_STATIONS_0) - 1) * INTER_STATION_TIME + len(WL_N_STATIONS_0) * DWELL_TIME


def generate_schedule(direction: int, stations: List[Tuple[str, str]],
                     od_track_id: str, origin: str, destination: str) -> dict:
    """生成時刻表"""

    schedule = {
        "track_id": od_track_id,
        "departures": []
    }

    # 每小時一班，06:00 ~ 22:00
    for hour in range(6, 23):
        train_id = f"{od_track_id}-{hour:02d}"
        train_no = f"TEST{hour:02d}"
        departure_time = f"{hour:02d}:00:00"

        # 計算每站時間 (相對秒數)
        stations_data = []
        current_time = 0

        for i, (station_id, station_name) in enumerate(stations):
            if i == 0:
                # 起點站
                arrival = 0
                departure = DWELL_TIME
            elif i == len(stations) - 1:
                # 終點站
                arrival = current_time + INTER_STATION_TIME
                departure = arrival + DWELL_TIME
            else:
                # 中間站
                arrival = current_time + INTER_STATION_TIME
                departure = arrival + DWELL_TIME

            stations_data.append({
                "station_id": station_id,
                "arrival": arrival,
                "departure": departure
            })

            current_time = departure

        departure_entry = {
            "train_id": train_id,
            "train_no": train_no,
            "train_type": "區間",
            "departure_time": departure_time,
            "od_track_id": od_track_id,
            "origin_station": origin,
            "destination_station": destination,
            "total_travel_time": current_time,
            "stations": stations_data
        }

        schedule["departures"].append(departure_entry)

    return schedule


def save_json(data: dict, filepath: str):
    """儲存 JSON 檔案"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'已儲存: {filepath}')


def main():
    print('=== 建立 WL-N 西部幹線北段測試時刻表 ===\n')

    # 方向 0: 竹南→樹林
    print('建立 WL-ZN-SL-0 時刻表 (竹南→樹林)...')
    schedule_0 = generate_schedule(
        direction=0,
        stations=WL_N_STATIONS_0,
        od_track_id='WL-ZN-SL-0',
        origin='竹南',
        destination='樹林'
    )
    save_json(schedule_0, os.path.join(TRA_DATA_DIR, 'schedules_od', 'WL-ZN-SL-0.json'))
    print(f'  班次數: {len(schedule_0["departures"])}')
    print(f'  總行車時間: {TOTAL_TRAVEL_TIME // 60} 分鐘')

    # 方向 1: 樹林→竹南
    print('\n建立 WL-SL-ZN-1 時刻表 (樹林→竹南)...')
    schedule_1 = generate_schedule(
        direction=1,
        stations=WL_N_STATIONS_1,
        od_track_id='WL-SL-ZN-1',
        origin='樹林',
        destination='竹南'
    )
    save_json(schedule_1, os.path.join(TRA_DATA_DIR, 'schedules_od', 'WL-SL-ZN-1.json'))
    print(f'  班次數: {len(schedule_1["departures"])}')
    print(f'  總行車時間: {TOTAL_TRAVEL_TIME // 60} 分鐘')

    print('\n=== 完成 ===')
    print(f'總班次: {len(schedule_0["departures"]) + len(schedule_1["departures"])} 班')


if __name__ == '__main__':
    main()
