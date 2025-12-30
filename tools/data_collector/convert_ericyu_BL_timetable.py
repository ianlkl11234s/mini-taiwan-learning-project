#!/usr/bin/env python3
"""
轉換 Eric Yu 的藍線時刻表格式到 Mini Taipei V3 格式

來源: https://github.com/ericyu/TaipeiMetroTimeTable (BL.json)
輸出: public/data/schedules/ 下的 JSON 檔案

藍線路線分類規則:
- BL-1: 全程車 (頂埔 BL01 ↔ 南港展覽館 BL23)
- BL-2: 區間車 (亞東醫院 BL05 ↔ 南港展覽館 BL23)

藍線特點:
- 無支線（與紅線的新北投支線不同）
- 區間車從 BL05 亞東醫院開始，不從 BL01 頂埔
- 少量首班車從中途站出發

方向定義:
- direction 0: 往東（往南港展覽館方向）
- direction 1: 往西（往頂埔方向）
"""

import json
from pathlib import Path
from typing import List, Dict, Any

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
SOURCE_FILE = SCRIPT_DIR / "source" / "ericyu_BL.json"
OUTPUT_DIR = SCRIPT_DIR.parent.parent / "public" / "data" / "schedules"

# 站點順序 (頂埔→南港展覽館方向，即 direction=0 往東)
STATION_ORDER = [
    "BL01", "BL02", "BL03", "BL04", "BL05", "BL06", "BL07", "BL08", "BL09",
    "BL10", "BL11", "BL12", "BL13", "BL14", "BL15", "BL16", "BL17", "BL18",
    "BL19", "BL20", "BL21", "BL22", "BL23"
]

# 站名對照
STATION_NAMES = {
    "BL01": "頂埔", "BL02": "永寧", "BL03": "土城", "BL04": "海山",
    "BL05": "亞東醫院", "BL06": "府中", "BL07": "板橋", "BL08": "新埔",
    "BL09": "江子翠", "BL10": "龍山寺", "BL11": "西門", "BL12": "台北車站",
    "BL13": "善導寺", "BL14": "忠孝新生", "BL15": "忠孝復興", "BL16": "忠孝敦化",
    "BL17": "國父紀念館", "BL18": "市政府", "BL19": "永春", "BL20": "後山埤",
    "BL21": "昆陽", "BL22": "南港", "BL23": "南港展覽館"
}

# 停站時間 (秒)
DWELL_TIME = 40


def time_to_seconds(time_str: str) -> int:
    """將 HH:MM 轉換為當日秒數"""
    h, m = map(int, time_str.split(':'))
    return h * 3600 + m * 60


def seconds_to_time(seconds: int) -> str:
    """將秒數轉換為 HH:MM:SS"""
    h = (seconds // 3600) % 24
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def station_num(station_id: str) -> int:
    """取得站號數字"""
    return int(station_id[2:]) if station_id.startswith('BL') else 0


def classify_train(schedule: List[Dict], direction: str) -> str:
    """
    分類列車到適當的軌道

    direction: "南港展覽館" (往東) 或 "頂埔" (往西)

    路線定義：
    - BL-1: 全程車 (頂埔 BL01 ↔ 南港展覽館 BL23)
    - BL-2: 區間車 (亞東醫院 BL05 ↔ 南港展覽館 BL23)
    """
    start_station = schedule[0]["StationCode"]
    end_station = schedule[-1]["StationCode"]
    start_num = station_num(start_station)
    end_num = station_num(end_station)

    if direction == "南港展覽館":
        # 往東方向 (往南港展覽館)
        if start_station == "BL01":
            # 從頂埔出發 = 全程車
            return "BL-1"
        elif start_num >= 5:
            # 從亞東醫院或之後出發 = 區間車
            return "BL-2"
        else:
            # 其他 (BL02-BL04 出發) = 視為全程車軌道
            return "BL-1"
    else:
        # 往西方向 (往頂埔)
        if start_station == "BL23":
            # 從南港展覽館出發
            if end_station == "BL01":
                # 終點頂埔 = 全程車
                return "BL-1"
            elif end_num >= 5:
                # 終點亞東醫院或之後 = 區間車
                return "BL-2"
            else:
                return "BL-1"
        elif end_station == "BL01":
            # 終點頂埔 = 全程車
            return "BL-1"
        elif end_num >= 5:
            # 終點在亞東醫院區域 = 區間車
            return "BL-2"
        else:
            return "BL-1"


def convert_train(train: Dict, direction: str, train_idx: int, route_type: str) -> Dict:
    """轉換單一列車資料"""
    schedule = train["Schedule"]
    start_station = schedule[0]["StationCode"]
    first_dep_time = schedule[0]["DepTime"]
    first_dep_seconds = time_to_seconds(first_dep_time)

    # 決定 track_id
    if direction == "南港展覽館":
        track_suffix = "0"  # BL-1-0 或 BL-2-0 (往東)
    else:
        track_suffix = "1"  # BL-1-1 或 BL-2-1 (往西)

    track_id = f"{route_type}-{track_suffix}"
    train_id = f"{track_id}-{train_idx:03d}"

    # 轉換各站時刻
    stations = []
    prev_arrival = 0

    for i, stop in enumerate(schedule):
        station_id = stop["StationCode"]
        dep_time_seconds = time_to_seconds(stop["DepTime"])

        # 計算相對於首站的秒數
        arrival_seconds = dep_time_seconds - first_dep_seconds

        # 處理跨日情況 (例如 23:50 → 00:10)
        if arrival_seconds < 0:
            arrival_seconds += 24 * 3600

        # 修正：確保站間至少有合理的行駛時間 (最小 60 秒)
        # Eric Yu 資料只有分鐘精度，可能導致相鄰站時間相同
        if i > 0:
            min_travel_time = 60  # 最小行駛時間 60 秒
            min_arrival = prev_arrival + DWELL_TIME + min_travel_time
            if arrival_seconds < min_arrival:
                arrival_seconds = min_arrival

        stations.append({
            "station_id": station_id,
            "arrival": arrival_seconds,
            "departure": arrival_seconds + DWELL_TIME
        })
        prev_arrival = arrival_seconds

    # 計算總行程時間 (最後一站的 departure)
    total_travel_time = stations[-1]["departure"] if stations else 0

    return {
        "departure_time": seconds_to_time(first_dep_seconds),
        "train_id": train_id,
        "origin_station": start_station,
        "total_travel_time": total_travel_time,
        "stations": stations
    }


def create_schedule_file(
    track_id: str,
    route_id: str,
    name: str,
    origin: str,
    destination: str,
    stations: List[str],
    departures: List[Dict],
    is_weekday: bool = True
) -> Dict:
    """建立完整的時刻表檔案結構"""

    # 計算平均行車時間
    if departures:
        travel_times = []
        for dep in departures:
            if dep["stations"]:
                last_arrival = dep["stations"][-1]["arrival"]
                travel_times.append(last_arrival // 60)
        avg_travel_time = sum(travel_times) // len(travel_times) if travel_times else 47
    else:
        avg_travel_time = 47

    return {
        "track_id": track_id,
        "route_id": route_id,
        "name": name,
        "origin": origin,
        "destination": destination,
        "stations": stations,
        "travel_time_minutes": avg_travel_time,
        "dwell_time_seconds": DWELL_TIME,
        "is_weekday": is_weekday,
        "departure_count": len(departures),
        "departures": departures
    }


def sort_departures(departures: List[Dict]) -> List[Dict]:
    """按發車時間排序，處理跨日情況"""
    def time_key(dep):
        time_str = dep["departure_time"]
        h, m, s = map(int, time_str.split(':'))
        # 凌晨 00:00-04:59 視為前一天的延續
        if h < 5:
            h += 24
        return h * 3600 + m * 60 + s

    return sorted(departures, key=time_key)


def main():
    print("=" * 60)
    print("Eric Yu 藍線時刻表轉換工具")
    print("=" * 60)

    # 讀取來源資料
    print(f"\n讀取來源: {SOURCE_FILE}")
    with open(SOURCE_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # 準備輸出資料結構
    schedules = {
        "BL-1-0": [],  # 頂埔→南港展覽館 全程
        "BL-1-1": [],  # 南港展覽館→頂埔 全程
        "BL-2-0": [],  # 亞東醫院→南港展覽館 區間
        "BL-2-1": [],  # 南港展覽館→亞東醫院 區間
    }

    # 統計各路線班次 (全域)
    route_counts = {"BL-1": 0, "BL-2": 0}

    # 處理各方向資料
    for direction_data in data:
        direction = direction_data["Direction"]
        print(f"\n處理方向: {direction}")

        for timetable in direction_data["Timetables"]:
            days = timetable["Days"]

            # 只處理平日 (1,2,3,4,5)
            if days != "1,2,3,4,5":
                print(f"  跳過 Days={days}")
                continue

            print(f"  處理 Days={days}, 共 {len(timetable['Trains'])} 班車")

            trains = timetable["Trains"]

            # 統計各路線班次 (此方向)
            dir_counts = {"BL-1": 0, "BL-2": 0}

            for train in trains:
                route_type = classify_train(train["Schedule"], direction)
                dir_counts[route_type] += 1
                route_counts[route_type] += 1
                train_idx = route_counts[route_type]

                converted = convert_train(train, direction, train_idx, route_type)

                # 決定 track_id
                if direction == "南港展覽館":
                    track_id = f"{route_type}-0"
                else:
                    track_id = f"{route_type}-1"

                schedules[track_id].append(converted)

            print(f"    BL-1 (全程): {dir_counts['BL-1']} 班")
            print(f"    BL-2 (區間): {dir_counts['BL-2']} 班")

    # 排序並輸出
    print(f"\n輸出目錄: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # BL-1-0: 頂埔→南港展覽館 全程
    bl1_0_deps = sort_departures(schedules["BL-1-0"])
    bl1_0 = create_schedule_file(
        track_id="BL-1-0",
        route_id="BL-1",
        name="頂埔 → 南港展覽館",
        origin="BL01",
        destination="BL23",
        stations=STATION_ORDER.copy(),
        departures=bl1_0_deps
    )

    # BL-1-1: 南港展覽館→頂埔 全程
    bl1_1_deps = sort_departures(schedules["BL-1-1"])
    bl1_1 = create_schedule_file(
        track_id="BL-1-1",
        route_id="BL-1",
        name="南港展覽館 → 頂埔",
        origin="BL23",
        destination="BL01",
        stations=list(reversed(STATION_ORDER)),
        departures=bl1_1_deps
    )

    # BL-2-0: 亞東醫院→南港展覽館 區間
    bl2_stations_east = STATION_ORDER[STATION_ORDER.index("BL05"):]  # BL05~BL23
    bl2_0_deps = sort_departures(schedules["BL-2-0"])
    bl2_0 = create_schedule_file(
        track_id="BL-2-0",
        route_id="BL-2",
        name="亞東醫院 → 南港展覽館",
        origin="BL05",
        destination="BL23",
        stations=bl2_stations_east,
        departures=bl2_0_deps
    )

    # BL-2-1: 南港展覽館→亞東醫院 區間
    bl2_1_deps = sort_departures(schedules["BL-2-1"])
    bl2_1 = create_schedule_file(
        track_id="BL-2-1",
        route_id="BL-2",
        name="南港展覽館 → 亞東醫院",
        origin="BL23",
        destination="BL05",
        stations=list(reversed(bl2_stations_east)),
        departures=bl2_1_deps
    )

    # 寫入檔案
    output_files = [
        ("BL-1-0.json", bl1_0),
        ("BL-1-1.json", bl1_1),
        ("BL-2-0.json", bl2_0),
        ("BL-2-1.json", bl2_1),
    ]

    for filename, data_obj in output_files:
        output_path = OUTPUT_DIR / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data_obj, f, ensure_ascii=False, indent=2)
        print(f"  ✅ {filename}: {data_obj['departure_count']} 班車")

    # 統計摘要
    print("\n" + "=" * 60)
    print("轉換完成！")
    print("=" * 60)
    print(f"  BL-1 (全程車): {bl1_0['departure_count'] + bl1_1['departure_count']} 班")
    print(f"    - BL-1-0 頂埔→南港展覽館: {bl1_0['departure_count']} 班")
    print(f"    - BL-1-1 南港展覽館→頂埔: {bl1_1['departure_count']} 班")
    print(f"  BL-2 (區間車): {bl2_0['departure_count'] + bl2_1['departure_count']} 班")
    print(f"    - BL-2-0 亞東醫院→南港展覽館: {bl2_0['departure_count']} 班")
    print(f"    - BL-2-1 南港展覽館→亞東醫院: {bl2_1['departure_count']} 班")

    # 顯示首班車資訊
    print("\n首班車資訊:")
    for filename, data_obj in output_files:
        early_trains = [d for d in data_obj['departures'] if d['departure_time'] < '06:15:00']
        if early_trains:
            print(f"\n  {data_obj['name']}:")
            for train in early_trains[:3]:
                origin = train.get('origin_station', data_obj['origin'])
                origin_name = STATION_NAMES.get(origin, origin)
                print(f"    {origin_name}({origin}) {train['departure_time'][:5]}")


if __name__ == "__main__":
    main()
