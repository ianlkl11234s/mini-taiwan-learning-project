#!/usr/bin/env python3
"""
建立西部幹線南段 (彰化↔新左營) 測試時刻表

根據實際距離比例計算站間時間
全程約 140 公里，區間車約需 2.5-3 小時

輸出：
- schedules_od/WL-CH-ZY-0.json (彰化→新左營)
- schedules_od/WL-ZY-CH-1.json (新左營→彰化)
"""

import json
import os

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEDULES_OD_DIR = os.path.join(BASE_DIR, 'public/data/tra/schedules_od')
TRACKS_OD_DIR = os.path.join(BASE_DIR, 'public/data/tra/tracks_od')

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


def load_station_progress():
    """載入 station progress"""
    progress_file = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')
    with open(progress_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_station_times(station_list, progress_dict, total_travel_time, dwell_time=40):
    """
    根據 progress 比例計算各站時間

    Args:
        station_list: [(station_id, station_name), ...]
        progress_dict: {station_id: progress, ...}
        total_travel_time: 全程行駛時間（秒）
        dwell_time: 停站時間（秒）

    Returns:
        [{"station_id": ..., "arrival": ..., "departure": ...}, ...]
    """
    stations = []

    for i, (station_id, station_name) in enumerate(station_list):
        progress = progress_dict.get(station_id, 0)

        # 根據 progress 計算累積行駛時間
        travel_time = int(progress * total_travel_time)

        if i == 0:
            # 起點站
            arrival = 0
            departure = dwell_time
        elif i == len(station_list) - 1:
            # 終點站
            arrival = travel_time
            departure = travel_time + dwell_time
        else:
            # 中間站
            arrival = travel_time
            departure = travel_time + dwell_time

        stations.append({
            "station_id": station_id,
            "arrival": arrival,
            "departure": departure
        })

    return stations


def generate_schedule(od_track_id, origin, destination, station_list, progress_dict,
                     total_travel_time, departure_hours):
    """生成時刻表"""
    departures = []

    for i, hour in enumerate(departure_hours):
        train_no = f"TEST{hour:02d}"
        train_id = f"{od_track_id}-{hour:02d}"

        stations = calculate_station_times(
            station_list, progress_dict, total_travel_time
        )

        departure = {
            "train_id": train_id,
            "train_no": train_no,
            "train_type": "區間",
            "departure_time": f"{hour:02d}:00:00",
            "od_track_id": od_track_id,
            "origin_station": origin,
            "destination_station": destination,
            "total_travel_time": total_travel_time,
            "stations": stations
        }

        departures.append(departure)

    return {
        "track_id": od_track_id,
        "departures": departures
    }


def main():
    print("=" * 60)
    print("建立西部幹線南段 (彰化↔新左營) 測試時刻表")
    print("=" * 60)

    # 載入 station progress
    all_progress = load_station_progress()

    progress_0 = all_progress.get('WL-CH-ZY-0', {})
    progress_1 = all_progress.get('WL-ZY-CH-1', {})

    print(f"\n彰化→新左營: {len(progress_0)} 站")
    print(f"新左營→彰化: {len(progress_1)} 站")

    # 全程約 140 公里，區間車平均時速約 50km/h，約需 2.8 小時 = 10080 秒
    # 加上停站時間 (39站 * 40秒 = 1560秒)，總計約 11640 秒
    # 簡化為 10800 秒 (3 小時)
    total_travel_time = 10800  # 3 小時

    # 發車時間 (06:00 ~ 22:00，每小時一班)
    departure_hours = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]

    # 生成彰化→新左營時刻表
    print("\n=== 生成 WL-CH-ZY-0 時刻表 ===")
    schedule_0 = generate_schedule(
        'WL-CH-ZY-0', '彰化', '新左營',
        SOUTH_STATIONS, progress_0,
        total_travel_time, departure_hours
    )

    filepath_0 = os.path.join(SCHEDULES_OD_DIR, 'WL-CH-ZY-0.json')
    with open(filepath_0, 'w', encoding='utf-8') as f:
        json.dump(schedule_0, f, ensure_ascii=False, indent=2)
    print(f"Saved: {filepath_0}")
    print(f"  {len(schedule_0['departures'])} 班次")

    # 生成新左營→彰化時刻表
    print("\n=== 生成 WL-ZY-CH-1 時刻表 ===")
    reversed_stations = list(reversed(SOUTH_STATIONS))

    schedule_1 = generate_schedule(
        'WL-ZY-CH-1', '新左營', '彰化',
        reversed_stations, progress_1,
        total_travel_time, departure_hours
    )

    filepath_1 = os.path.join(SCHEDULES_OD_DIR, 'WL-ZY-CH-1.json')
    with open(filepath_1, 'w', encoding='utf-8') as f:
        json.dump(schedule_1, f, ensure_ascii=False, indent=2)
    print(f"Saved: {filepath_1}")
    print(f"  {len(schedule_1['departures'])} 班次")

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
