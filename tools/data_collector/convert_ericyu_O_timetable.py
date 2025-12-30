#!/usr/bin/env python3
"""
convert_ericyu_O_timetable.py - 轉換 O 線 (中和新蘆線) 時刻表

ericyu 格式:
[
  {
    "Direction": "逆行",
    "Timetables": [
      {
        "Days": "1,2,3,4,5",
        "Trains": [
          {
            "Dst": "南勢角",
            "Schedule": [
              {"DepTime": "06:00", "StationCode": "O21"},
              ...
            ]
          }
        ]
      }
    ]
  }
]

Mini Taipei 格式:
{
  "track_id": "O-1-0",
  "route_id": "O-1",
  "stations": ["O21", "O20", ..., "O01"],
  "departures": [
    {
      "departure_time": "06:00:00",
      "train_id": "O-1-0-001",
      "stations": [
        {"station_id": "O21", "arrival": 0, "departure": 30},
        ...
      ],
      "total_travel_time": 2880
    }
  ]
}

O 線路線分類:
- O-1: 新莊線 (迴龍 O21 ↔ 南勢角 O01)
- O-2: 蘆洲線 (蘆洲 O54 ↔ 南勢角 O01)
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime, timedelta

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
SOURCE_DIR = SCRIPT_DIR / "source"
OUTPUT_DIR = SCRIPT_DIR / "output" / "schedules"
PUBLIC_DIR = SCRIPT_DIR.parent.parent / "public" / "data" / "schedules"

# 站點停靠時間 (秒)
DWELL_TIME = 30

# 新莊線站點 (O21→O01)
XINZHUANG_STATIONS = [
    "O21", "O20", "O19", "O18", "O17", "O16", "O15", "O14", "O13",
    "O12", "O11", "O10", "O09", "O08", "O07", "O06", "O05", "O04",
    "O03", "O02", "O01"
]

# 蘆洲線站點 (O54→O01)
LUZHOU_STATIONS = [
    "O54", "O53", "O52", "O51", "O50",
    "O12", "O11", "O10", "O09", "O08", "O07", "O06", "O05", "O04",
    "O03", "O02", "O01"
]


def load_json(filepath: Path) -> Any:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def time_to_seconds(time_str: str) -> int:
    """將 HH:MM 或 HH:MM:SS 轉換為從 00:00 起的秒數"""
    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    seconds = int(parts[2]) if len(parts) > 2 else 0
    return hours * 3600 + minutes * 60 + seconds


def classify_train(schedule: List[Dict]) -> tuple:
    """
    分類列車（只保留全程車，過濾首班車/區間車）

    Returns:
        (route_id, direction, stations_list)
        - route_id: "O-1" (新莊線) 或 "O-2" (蘆洲線)
        - direction: 0 (往南勢角) 或 1 (往迴龍/蘆洲)
        - stations_list: 標準站點順序
        - 如果不是全程車，返回 (None, None, None)
    """
    if not schedule:
        return None, None, None

    first_station = schedule[0]['StationCode']
    last_station = schedule[-1]['StationCode']

    # 只保留全程車（從終點站發車到終點站）
    # 有效的全程車模式：
    # - O21 → O01 (新莊線往南勢角)
    # - O01 → O21 (新莊線往迴龍)
    # - O54 → O01 (蘆洲線往南勢角)
    # - O01 → O54 (蘆洲線往蘆洲)

    if first_station == 'O21' and last_station == 'O01':
        # 新莊線往南勢角
        return "O-1", 0, XINZHUANG_STATIONS
    elif first_station == 'O01' and last_station == 'O21':
        # 新莊線往迴龍
        return "O-1", 1, list(reversed(XINZHUANG_STATIONS))
    elif first_station == 'O54' and last_station == 'O01':
        # 蘆洲線往南勢角
        return "O-2", 0, LUZHOU_STATIONS
    elif first_station == 'O01' and last_station == 'O54':
        # 蘆洲線往蘆洲
        return "O-2", 1, list(reversed(LUZHOU_STATIONS))
    else:
        # 首班車或區間車，忽略
        return None, None, None


def convert_train(train: Dict, route_id: str, direction: int, stations_list: List[str], train_num: int) -> Dict:
    """轉換單班列車"""
    schedule = train['Schedule']
    track_id = f"{route_id}-{direction}"

    # 建立時間對照表
    time_map = {}
    for stop in schedule:
        station_code = stop['StationCode']
        dep_time = stop['DepTime']
        time_map[station_code] = time_to_seconds(dep_time)

    # 計算各站到達時間
    base_time = time_to_seconds(schedule[0]['DepTime'])
    stations_data = []

    for station_id in stations_list:
        if station_id in time_map:
            arrival_sec = time_map[station_id] - base_time
            stations_data.append({
                "station_id": station_id,
                "arrival": arrival_sec,
                "departure": arrival_sec + DWELL_TIME
            })

    # 修正最後一站的 departure (不需要停靠時間)
    if stations_data:
        stations_data[-1]["departure"] = stations_data[-1]["arrival"]

    total_travel_time = stations_data[-1]["arrival"] if stations_data else 0

    # 格式化發車時間
    first_dep = schedule[0]['DepTime']
    if len(first_dep.split(':')) == 2:
        first_dep += ":00"

    return {
        "departure_time": first_dep,
        "train_id": f"{track_id}-{train_num:03d}",
        "stations": stations_data,
        "total_travel_time": total_travel_time
    }


def main():
    print("=" * 70)
    print("O 線（中和新蘆線）時刻表轉換工具")
    print("=" * 70)

    # 載入 ericyu 資料
    source_file = SOURCE_DIR / "ericyu_O.json"
    if not source_file.exists():
        print(f"錯誤：找不到 {source_file}")
        return

    ericyu_data = load_json(source_file)
    print(f"\n載入 ericyu_O.json")

    # 收集平日班次 (Days="1,2,3,4,5")
    # 注意：原始資料包含平日和假日時刻表，我們只使用平日的
    all_trains = []
    for direction_data in ericyu_data:
        for timetable in direction_data.get('Timetables', []):
            days = timetable.get('Days', '')
            # 只取平日時刻表
            if '1,2,3,4,5' in days:
                for train in timetable.get('Trains', []):
                    all_trains.append(train)
                print(f"  使用 {direction_data.get('Direction', '')} 方向平日時刻表: {len(timetable.get('Trains', []))} 班次")

    print(f"  平日總班次數: {len(all_trains)}")

    # 分類班次
    classified = defaultdict(list)

    for train in all_trains:
        schedule = train.get('Schedule', [])
        route_id, direction, stations_list = classify_train(schedule)

        if route_id:
            track_id = f"{route_id}-{direction}"
            classified[track_id].append({
                'train': train,
                'stations_list': stations_list
            })

    print(f"\n分類結果:")
    for track_id, trains in sorted(classified.items()):
        print(f"  {track_id}: {len(trains)} 班次")

    # 轉換各軌道的時刻表
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n產生時刻表...")

    for track_id, train_list in classified.items():
        route_id = track_id.rsplit('-', 1)[0]
        direction = int(track_id.split('-')[-1])

        # 取得站點順序
        if route_id == "O-1":
            if direction == 0:
                stations = XINZHUANG_STATIONS
            else:
                stations = list(reversed(XINZHUANG_STATIONS))
        else:  # O-2
            if direction == 0:
                stations = LUZHOU_STATIONS
            else:
                stations = list(reversed(LUZHOU_STATIONS))

        # 轉換班次
        departures = []
        for i, item in enumerate(train_list, 1):
            converted = convert_train(
                item['train'],
                route_id,
                direction,
                item['stations_list'],
                i
            )
            departures.append(converted)

        # 按發車時間排序
        departures.sort(key=lambda x: time_to_seconds(x['departure_time']))

        # 重新編號
        for i, dep in enumerate(departures, 1):
            dep['train_id'] = f"{track_id}-{i:03d}"

        schedule_data = {
            "track_id": track_id,
            "route_id": route_id,
            "stations": stations,
            "departures": departures,
            "departure_count": len(departures)
        }

        # 儲存
        output_file = OUTPUT_DIR / f"{track_id}.json"
        save_json(schedule_data, output_file)

        public_file = PUBLIC_DIR / f"{track_id}.json"
        save_json(schedule_data, public_file)

        print(f"  ✅ {track_id}.json ({len(departures)} 班次, {len(stations)} 站)")

    # 統計
    print("\n" + "=" * 70)
    print("轉換完成！")
    print("=" * 70)

    total_departures = sum(len(trains) for trains in classified.values())
    print(f"""
統計:
- O-1-0 (迴龍→南勢角): {len(classified.get('O-1-0', []))} 班次
- O-1-1 (南勢角→迴龍): {len(classified.get('O-1-1', []))} 班次
- O-2-0 (蘆洲→南勢角): {len(classified.get('O-2-0', []))} 班次
- O-2-1 (南勢角→蘆洲): {len(classified.get('O-2-1', []))} 班次
- 總計: {total_departures} 班次

輸出檔案:
- public/data/schedules/O-1-0.json
- public/data/schedules/O-1-1.json
- public/data/schedules/O-2-0.json
- public/data/schedules/O-2-1.json
""")


if __name__ == "__main__":
    main()
