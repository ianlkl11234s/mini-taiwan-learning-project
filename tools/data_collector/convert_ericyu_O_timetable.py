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
- O-1: 新莊線全程 (迴龍 O21 ↔ 南勢角 O01)
- O-2: 蘆洲線全程 (蘆洲 O54 ↔ 南勢角 O01)
- O-3 ~ O-12: 首班車往南勢角 (從中途站出發)
- O-13 ~ O-18: 首班車往迴龍 (從中途站出發)
- O-19 ~ O-23: 首班車往蘆洲 (從中途站出發)
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict

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

# 共用段站點 (O01→O12)
SHARED_STATIONS = [
    "O01", "O02", "O03", "O04", "O05", "O06", "O07", "O08", "O09",
    "O10", "O11", "O12"
]

# 站名對照
STATION_NAMES = {
    "O01": "南勢角", "O02": "景安", "O03": "永安市場", "O04": "頂溪",
    "O05": "古亭", "O06": "東門", "O07": "忠孝新生", "O08": "松江南京",
    "O09": "行天宮", "O10": "中山國小", "O11": "民權西路", "O12": "大橋頭",
    "O13": "台北橋", "O14": "菜寮", "O15": "三重", "O16": "先嗇宮",
    "O17": "頭前庄", "O18": "新莊", "O19": "輔大", "O20": "丹鳳", "O21": "迴龍",
    "O50": "三重國小", "O51": "三和國中", "O52": "徐匯中學", "O53": "三民高中", "O54": "蘆洲"
}

# 首班車路線定義
# 格式: (起站, 終站): (route_id, direction, 使用的站點列表類型)
# direction: 0=往南勢角, 1=往迴龍/蘆洲
FIRST_TRAIN_ROUTES = {
    # === 往南勢角 (direction=0) ===
    # 新莊線支線的首班車
    ("O19", "O01"): ("O-3", 0, "xinzhuang"),
    ("O17", "O01"): ("O-4", 0, "xinzhuang"),
    ("O16", "O01"): ("O-5", 0, "xinzhuang"),
    # 共用段的首班車 (可能來自新莊或蘆洲支線)
    ("O12", "O01"): ("O-6", 0, "shared"),
    ("O11", "O01"): ("O-7", 0, "shared"),
    ("O10", "O01"): ("O-8", 0, "shared"),
    ("O07", "O01"): ("O-9", 0, "shared"),
    ("O05", "O01"): ("O-10", 0, "shared"),
    ("O03", "O01"): ("O-11", 0, "shared"),
    # 蘆洲支線的首班車
    ("O51", "O01"): ("O-12", 0, "luzhou"),

    # === 往迴龍 (direction=1) ===
    ("O02", "O21"): ("O-13", 1, "xinzhuang"),
    ("O05", "O21"): ("O-14", 1, "xinzhuang"),
    ("O09", "O21"): ("O-15", 1, "xinzhuang"),
    ("O14", "O21"): ("O-16", 1, "xinzhuang"),
    ("O18", "O21"): ("O-17", 1, "xinzhuang"),
    ("O20", "O21"): ("O-18", 1, "xinzhuang"),

    # === 往蘆洲 (direction=1) ===
    ("O03", "O54"): ("O-19", 1, "luzhou"),
    ("O05", "O54"): ("O-20", 1, "luzhou"),
    ("O07", "O54"): ("O-21", 1, "luzhou"),
    ("O11", "O54"): ("O-22", 1, "luzhou"),
    ("O52", "O54"): ("O-23", 1, "luzhou"),
}


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


def seconds_to_time(seconds: int) -> str:
    """將秒數轉換為 HH:MM:SS"""
    h = (seconds // 3600) % 24
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def get_stations_between(start: str, end: str, line_type: str) -> List[str]:
    """
    取得兩站之間的站點列表

    line_type: "xinzhuang", "luzhou", "shared"
    """
    if line_type == "xinzhuang":
        base_stations = XINZHUANG_STATIONS
    elif line_type == "luzhou":
        base_stations = LUZHOU_STATIONS
    else:  # shared
        base_stations = SHARED_STATIONS

    # 找到起終站在列表中的位置
    try:
        start_idx = base_stations.index(start)
        end_idx = base_stations.index(end)
    except ValueError:
        # 如果找不到，嘗試反向
        base_stations = list(reversed(base_stations))
        try:
            start_idx = base_stations.index(start)
            end_idx = base_stations.index(end)
        except ValueError:
            return []

    if start_idx <= end_idx:
        return base_stations[start_idx:end_idx + 1]
    else:
        return base_stations[end_idx:start_idx + 1][::-1]


def classify_train(schedule: List[Dict]) -> Tuple[Optional[str], Optional[int], Optional[List[str]]]:
    """
    分類列車到適當的路線

    Returns:
        (route_id, direction, stations_list)
        - route_id: 路線 ID (O-1, O-2, O-3, ...)
        - direction: 0 (往南勢角) 或 1 (往迴龍/蘆洲)
        - stations_list: 該班次經過的站點順序
    """
    if not schedule:
        return None, None, None

    first_station = schedule[0]['StationCode']
    last_station = schedule[-1]['StationCode']

    # 全程車模式
    if first_station == 'O21' and last_station == 'O01':
        return "O-1", 0, XINZHUANG_STATIONS.copy()
    elif first_station == 'O01' and last_station == 'O21':
        return "O-1", 1, list(reversed(XINZHUANG_STATIONS))
    elif first_station == 'O54' and last_station == 'O01':
        return "O-2", 0, LUZHOU_STATIONS.copy()
    elif first_station == 'O01' and last_station == 'O54':
        return "O-2", 1, list(reversed(LUZHOU_STATIONS))

    # 首班車模式
    key = (first_station, last_station)
    if key in FIRST_TRAIN_ROUTES:
        route_id, direction, line_type = FIRST_TRAIN_ROUTES[key]
        stations = get_stations_between(first_station, last_station, line_type)
        if stations:
            return route_id, direction, stations

    # 未知模式，記錄但不處理
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
            # 處理跨日
            if arrival_sec < 0:
                arrival_sec += 24 * 3600
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

    origin_station = schedule[0]['StationCode']

    return {
        "departure_time": first_dep,
        "train_id": f"{track_id}-{train_num:03d}",
        "origin_station": origin_station,
        "stations": stations_data,
        "total_travel_time": total_travel_time
    }


def sort_departures(departures: List[Dict]) -> List[Dict]:
    """按發車時間排序，處理跨日情況"""
    def time_key(dep):
        time_str = dep["departure_time"]
        parts = time_str.split(':')
        h = int(parts[0])
        m = int(parts[1])
        s = int(parts[2]) if len(parts) > 2 else 0
        # 凌晨 00:00-04:59 視為前一天的延續
        if h < 5:
            h += 24
        return h * 3600 + m * 60 + s

    return sorted(departures, key=time_key)


def create_schedule_file(
    track_id: str,
    route_id: str,
    name: str,
    origin: str,
    destination: str,
    stations: List[str],
    departures: List[Dict]
) -> Dict:
    """建立完整的時刻表檔案結構"""
    return {
        "track_id": track_id,
        "route_id": route_id,
        "name": name,
        "origin": origin,
        "destination": destination,
        "stations": stations,
        "dwell_time_seconds": DWELL_TIME,
        "departure_count": len(departures),
        "departures": departures
    }


def main():
    print("=" * 70)
    print("O 線（中和新蘆線）時刻表轉換工具 - 含首班車")
    print("=" * 70)

    # 載入 ericyu 資料
    source_file = SOURCE_DIR / "ericyu_O.json"
    if not source_file.exists():
        print(f"錯誤：找不到 {source_file}")
        return

    ericyu_data = load_json(source_file)
    print(f"\n載入 ericyu_O.json")

    # 收集平日班次 (Days="1,2,3,4,5")
    all_trains = []
    for direction_data in ericyu_data:
        for timetable in direction_data.get('Timetables', []):
            days = timetable.get('Days', '')
            if '1,2,3,4,5' in days:
                for train in timetable.get('Trains', []):
                    all_trains.append(train)
                print(f"  使用 {direction_data.get('Direction', '')} 方向平日時刻表: {len(timetable.get('Trains', []))} 班次")

    print(f"  平日總班次數: {len(all_trains)}")

    # 分類班次
    classified = defaultdict(list)
    unclassified = []

    for train in all_trains:
        schedule = train.get('Schedule', [])
        route_id, direction, stations_list = classify_train(schedule)

        if route_id:
            track_id = f"{route_id}-{direction}"
            classified[track_id].append({
                'train': train,
                'stations_list': stations_list
            })
        else:
            if schedule:
                first = schedule[0]['StationCode']
                last = schedule[-1]['StationCode']
                unclassified.append(f"{first}→{last}")

    print(f"\n分類結果:")

    # 先顯示全程車
    print("\n  全程車:")
    for track_id in ["O-1-0", "O-1-1", "O-2-0", "O-2-1"]:
        if track_id in classified:
            print(f"    {track_id}: {len(classified[track_id])} 班次")

    # 再顯示首班車
    first_train_tracks = [k for k in classified.keys() if k not in ["O-1-0", "O-1-1", "O-2-0", "O-2-1"]]
    if first_train_tracks:
        print("\n  首班車:")
        for track_id in sorted(first_train_tracks):
            count = len(classified[track_id])
            # 取得起終站
            if classified[track_id]:
                sample = classified[track_id][0]
                first = sample['stations_list'][0]
                last = sample['stations_list'][-1]
                first_name = STATION_NAMES.get(first, first)
                last_name = STATION_NAMES.get(last, last)
                print(f"    {track_id}: {count} 班次 ({first_name}→{last_name})")

    if unclassified:
        print(f"\n  未分類 (已忽略): {len(unclassified)} 班次")
        from collections import Counter
        for pattern, count in Counter(unclassified).most_common(5):
            print(f"    {pattern}: {count}")

    # 建立輸出目錄
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n產生時刻表...")

    # 準備所有輸出
    output_files = []
    route_counts = {}

    for track_id, train_list in sorted(classified.items()):
        route_id = track_id.rsplit('-', 1)[0]
        direction = int(track_id.split('-')[-1])

        # 取得站點順序 (從第一班車取得)
        stations = train_list[0]['stations_list']

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
        departures = sort_departures(departures)

        # 重新編號
        for i, dep in enumerate(departures, 1):
            dep['train_id'] = f"{track_id}-{i:03d}"

        # 建立路線名稱
        origin = stations[0]
        destination = stations[-1]
        origin_name = STATION_NAMES.get(origin, origin)
        dest_name = STATION_NAMES.get(destination, destination)
        name = f"{origin_name} → {dest_name}"

        schedule_data = create_schedule_file(
            track_id=track_id,
            route_id=route_id,
            name=name,
            origin=origin,
            destination=destination,
            stations=stations,
            departures=departures
        )

        # 儲存
        output_file = OUTPUT_DIR / f"{track_id}.json"
        save_json(schedule_data, output_file)

        public_file = PUBLIC_DIR / f"{track_id}.json"
        save_json(schedule_data, public_file)

        output_files.append((track_id, schedule_data))
        route_counts[track_id] = len(departures)

        # 顯示進度
        is_first_train = route_id not in ["O-1", "O-2"]
        marker = "🚃" if is_first_train else "✅"
        print(f"  {marker} {track_id}.json ({len(departures)} 班次, {len(stations)} 站) - {name}")

    # 統計
    print("\n" + "=" * 70)
    print("轉換完成！")
    print("=" * 70)

    full_count = sum(route_counts.get(t, 0) for t in ["O-1-0", "O-1-1", "O-2-0", "O-2-1"])
    first_train_count = sum(v for k, v in route_counts.items() if k not in ["O-1-0", "O-1-1", "O-2-0", "O-2-1"])

    print(f"""
統計:
  全程車:
    - O-1-0 (迴龍→南勢角): {route_counts.get('O-1-0', 0)} 班次
    - O-1-1 (南勢角→迴龍): {route_counts.get('O-1-1', 0)} 班次
    - O-2-0 (蘆洲→南勢角): {route_counts.get('O-2-0', 0)} 班次
    - O-2-1 (南勢角→蘆洲): {route_counts.get('O-2-1', 0)} 班次
    小計: {full_count} 班次

  首班車: {first_train_count} 班次 (分布在 {len(route_counts) - 4} 個獨立軌道)

  總計: {full_count + first_train_count} 班次
""")

    # 顯示首班車資訊
    print("首班車資訊 (06:15 前發車):")
    for track_id, data in output_files:
        if track_id in ["O-1-0", "O-1-1", "O-2-0", "O-2-1"]:
            continue
        early_trains = [d for d in data['departures'] if d['departure_time'] < '06:15:00']
        if early_trains:
            print(f"\n  {data['name']}:")
            for train in early_trains[:3]:
                origin = train.get('origin_station', data['origin'])
                origin_name = STATION_NAMES.get(origin, origin)
                print(f"    {origin_name} {train['departure_time'][:5]}")


if __name__ == "__main__":
    main()
