#!/usr/bin/env python3
"""
轉換 Eric Yu 的時刻表格式到 Mini Taipei V3 格式

來源: https://github.com/ericyu/TaipeiMetroTimeTable
輸出: public/data/schedules/ 下的 JSON 檔案

路線分類規則:
- R-1: 全程車 (象山 R02 ↔ 淡水 R28)
- R-2: 區間車 (象山/大安 R02/R05 ↔ 北投 R22)
- R-3: 新北投支線 (北投 R22 ↔ 新北投 R22A) - 不在此處理
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
SOURCE_FILE = SCRIPT_DIR / "source" / "ericyu_R.json"
OUTPUT_DIR = SCRIPT_DIR.parent.parent / "public" / "data" / "schedules"

# 站點順序 (象山→淡水方向)
STATION_ORDER = [
    "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10",
    "R11", "R12", "R13", "R14", "R15", "R16", "R17", "R18", "R19",
    "R20", "R21", "R22", "R23", "R24", "R25", "R26", "R27", "R28"
]

# 站名對照
STATION_NAMES = {
    "R02": "象山", "R03": "台北101/世貿", "R04": "信義安和", "R05": "大安",
    "R06": "大安森林公園", "R07": "東門", "R08": "中正紀念堂", "R09": "台大醫院",
    "R10": "台北車站", "R11": "中山", "R12": "雙連", "R13": "民權西路",
    "R14": "圓山", "R15": "劍潭", "R16": "士林", "R17": "芝山", "R18": "明德",
    "R19": "石牌", "R20": "唭哩岸", "R21": "奇岩", "R22": "北投",
    "R23": "復興崗", "R24": "忠義", "R25": "關渡", "R26": "竹圍",
    "R27": "紅樹林", "R28": "淡水"
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


def classify_train(schedule: List[Dict], direction: str) -> str:
    """
    分類列車為 R-1 (全程) 或 R-2 (區間)

    direction: "淡水" (北上) 或 "象山" (南下)
    """
    start_station = schedule[0]["StationCode"]
    end_station = schedule[-1]["StationCode"]

    if direction == "淡水":
        # 北上: R02/R05 → R28
        # 全程車: 從 R02 發車且到 R28
        if start_station == "R02" and end_station == "R28":
            return "R-1"
        else:
            return "R-2"
    else:
        # 南下: R28 → R02
        # 全程車: 從 R28 發車且到 R02
        if start_station == "R28" and end_station == "R02":
            return "R-1"
        else:
            return "R-2"


def convert_train(train: Dict, direction: str, train_idx: int, route_type: str) -> Dict:
    """轉換單一列車資料"""
    schedule = train["Schedule"]
    start_station = schedule[0]["StationCode"]
    first_dep_time = schedule[0]["DepTime"]
    first_dep_seconds = time_to_seconds(first_dep_time)

    # 決定 track_id
    if direction == "淡水":
        track_suffix = "0"  # R-1-0 或 R-2-0 (往淡水/北投)
    else:
        track_suffix = "1"  # R-1-1 或 R-2-1 (往象山)

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
        "origin_station": start_station,  # 新增：實際發車站
        "total_travel_time": total_travel_time,  # 新增：總行程時間
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
        avg_travel_time = sum(travel_times) // len(travel_times) if travel_times else 54
    else:
        avg_travel_time = 54

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
    print("Eric Yu 時刻表轉換工具")
    print("=" * 60)

    # 讀取來源資料
    print(f"\n讀取來源: {SOURCE_FILE}")
    with open(SOURCE_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # 準備輸出資料結構
    schedules = {
        "R-1-0": [],  # 象山→淡水 全程
        "R-1-1": [],  # 淡水→象山 全程
        "R-2-0": [],  # 象山/大安→北投 區間 (往北投方向)
        "R-2-1": [],  # 北投→象山/大安 區間 (往象山方向)
    }

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

            # 統計各路線班次
            r1_count = 0
            r2_count = 0

            for train in trains:
                route_type = classify_train(train["Schedule"], direction)

                if route_type == "R-1":
                    r1_count += 1
                    train_idx = r1_count
                else:
                    r2_count += 1
                    train_idx = r2_count

                converted = convert_train(train, direction, train_idx, route_type)

                # 決定 track_id
                if direction == "淡水":
                    track_id = f"{route_type}-0"
                else:
                    track_id = f"{route_type}-1"

                schedules[track_id].append(converted)

            print(f"    R-1 (全程): {r1_count} 班")
            print(f"    R-2 (區間): {r2_count} 班")

    # 排序並輸出
    print(f"\n輸出目錄: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # R-1-0: 象山→淡水 全程
    r1_0_deps = sort_departures(schedules["R-1-0"])
    r1_0 = create_schedule_file(
        track_id="R-1-0",
        route_id="R-1",
        name="象山 → 淡水",
        origin="R02",
        destination="R28",
        stations=STATION_ORDER.copy(),
        departures=r1_0_deps
    )

    # R-1-1: 淡水→象山 全程
    r1_1_deps = sort_departures(schedules["R-1-1"])
    r1_1 = create_schedule_file(
        track_id="R-1-1",
        route_id="R-1",
        name="淡水 → 象山",
        origin="R28",
        destination="R02",
        stations=list(reversed(STATION_ORDER)),
        departures=r1_1_deps
    )

    # R-2-0: 往北投方向的區間車 (從象山/大安出發)
    r2_0_deps = sort_departures(schedules["R-2-0"])
    r2_0 = create_schedule_file(
        track_id="R-2-0",
        route_id="R-2",
        name="象山/大安 → 北投",
        origin="R02",
        destination="R22",
        stations=STATION_ORDER[:STATION_ORDER.index("R22")+1],  # R02~R22
        departures=r2_0_deps
    )

    # R-2-1: 往象山方向的區間車 (從北投出發)
    r2_1_deps = sort_departures(schedules["R-2-1"])
    # 找出實際的終點站 (可能是 R02 或 R05)
    r2_1_stations = list(reversed(STATION_ORDER[:STATION_ORDER.index("R22")+1]))
    r2_1 = create_schedule_file(
        track_id="R-2-1",
        route_id="R-2",
        name="北投 → 象山/大安",
        origin="R22",
        destination="R02",
        stations=r2_1_stations,
        departures=r2_1_deps
    )

    # 寫入檔案
    output_files = [
        ("R-1-0.json", r1_0),
        ("R-1-1.json", r1_1),
        ("R-2-0.json", r2_0),
        ("R-2-1.json", r2_1),
    ]

    for filename, data in output_files:
        output_path = OUTPUT_DIR / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  ✅ {filename}: {data['departure_count']} 班車")

    # 統計摘要
    print("\n" + "=" * 60)
    print("轉換完成！")
    print("=" * 60)
    print(f"  R-1 (全程車): {r1_0['departure_count'] + r1_1['departure_count']} 班")
    print(f"    - R-1-0 象山→淡水: {r1_0['departure_count']} 班")
    print(f"    - R-1-1 淡水→象山: {r1_1['departure_count']} 班")
    print(f"  R-2 (區間車): {r2_0['departure_count'] + r2_1['departure_count']} 班")
    print(f"    - R-2-0 往北投: {r2_0['departure_count']} 班")
    print(f"    - R-2-1 往象山: {r2_1['departure_count']} 班")

    # 顯示首班車資訊
    print("\n首班車資訊 (06:00 發車):")
    for filename, data in output_files:
        print(f"\n  {data['name']}:")
        early_trains = [d for d in data['departures'] if d['departure_time'] < '06:15:00']
        for train in early_trains[:5]:
            origin = train.get('origin_station', data['origin'])
            print(f"    {origin} {train['departure_time'][:5]}")


if __name__ == "__main__":
    main()
