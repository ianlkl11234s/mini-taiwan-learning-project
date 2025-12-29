#!/usr/bin/env python3
"""
轉換 Eric Yu 的時刻表格式到 Mini Taipei V3 格式

來源: https://github.com/ericyu/TaipeiMetroTimeTable
輸出: public/data/schedules/ 下的 JSON 檔案

路線分類規則:
- R-1: 全程車 (象山 R02 ↔ 淡水 R28)
- R-2: 區間車 (象山/大安 R02/R05 ↔ 北投 R22)
- R-3: 新北投支線 (北投 R22 ↔ 新北投 R22A) - 不在此處理
- R-4: 北段區間車 (北投 R22 ↔ 淡水 R28)
- R-5: 首班車專用 (大安 R05 → 淡水 R28)
- R-6: 首班車專用 (雙連 R10 → 淡水 R28)
- R-7: 首班車專用 (圓山 R15 → 淡水 R28)
- R-8: 首班車專用 (芝山 R20 → 淡水 R28)
- R-9: 首班車專用 (紅樹林 R24 → 象山 R02)
- R-10: 首班車專用 (大安 R05 → 象山 R02)
- R-11: 首班車專用 (雙連 R10 → 象山 R02)
- R-12: 首班車專用 (民權西路 R13 → 象山 R02)
- R-13: 首班車專用 (圓山 R15 → 象山 R02)
- R-14: 首班車專用 (石牌 R19 → 象山 R02)
- R-15: 首班車專用 (唭哩岸 R20 → 象山 R02)
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
    分類列車到適當的軌道

    direction: "淡水" (北上) 或 "象山" (南下)

    路線定義：
    - R-1: 全程車 (象山 R02 ↔ 淡水 R28)
    - R-2: 南段區間車 (象山/大安 R02/R05 ↔ 北投 R22)
    - R-4: 北段區間車 (北投 R22 ↔ 淡水 R28)
    - R-5: 首班車專用 (大安 R05 → 淡水 R28)
    - R-6: 首班車專用 (雙連 R10 → 淡水 R28)
    - R-7: 首班車專用 (圓山 R15 → 淡水 R28)
    - R-8: 首班車專用 (芝山 R20 → 淡水 R28)
    - R-9: 首班車專用 (紅樹林 R24 → 象山 R02)
    """
    start_station = schedule[0]["StationCode"]
    end_station = schedule[-1]["StationCode"]

    # 取得站號數字
    def station_num(s):
        return int(s[1:]) if s.startswith('R') and s[1:].isdigit() else 0

    start_num = station_num(start_station)
    end_num = station_num(end_station)

    if direction == "淡水":
        # 北上方向 (往淡水)

        # 首班車專用軌道 (從中途站出發到淡水)
        if start_station == "R05" and end_station == "R28":
            return "R-5"
        elif start_station == "R10" and end_station == "R28":
            return "R-6"
        elif start_station == "R15" and end_station == "R28":
            return "R-7"
        elif start_station == "R20" and end_station == "R28":
            return "R-8"

        # 標準軌道
        if start_station == "R02" and end_station == "R28":
            # 全程車：從象山到淡水
            return "R-1"
        elif end_station == "R22" or end_num <= 22:
            # 終點在北投或以南：南段區間車
            return "R-2"
        elif end_station == "R28" and start_num >= 22:
            # 終點淡水，起點在北投或以北：北段區間車
            return "R-4"
        elif end_station == "R28":
            # 終點淡水，起點在北投以南：使用全程車軌道
            return "R-1"
        else:
            return "R-2"
    else:
        # 南下方向 (往象山)

        # 首班車專用軌道 (從中途站出發到象山)
        if end_station == "R02":
            if start_station == "R24":
                return "R-9"
            elif start_station == "R05":
                return "R-10"
            elif start_station == "R10":
                return "R-11"
            elif start_station == "R13":
                return "R-12"
            elif start_station == "R15":
                return "R-13"
            elif start_station == "R19":
                return "R-14"
            elif start_station == "R20":
                return "R-15"

        # 標準軌道
        if start_station == "R28" and end_station == "R02":
            # 全程車：從淡水到象山
            return "R-1"
        elif start_station == "R22" or start_num <= 22:
            # 起點在北投或以南：南段區間車
            return "R-2"
        elif start_num > 22 and end_num <= 22:
            # 起點在北投以北，終點在北投以南：使用全程車軌道
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
        "R-4-0": [],  # 北投→淡水 北段區間 (往淡水方向)
        "R-4-1": [],  # 淡水→北投 北段區間 (往北投方向)
        # === 往淡水方向首班車專用 ===
        "R-5-0": [],  # 大安→淡水 (首班車專用)
        "R-6-0": [],  # 雙連→淡水 (首班車專用)
        "R-7-0": [],  # 圓山→淡水 (首班車專用)
        "R-8-0": [],  # 芝山→淡水 (首班車專用)
        # === 往象山方向首班車專用 ===
        "R-9-1": [],  # 紅樹林→象山 (首班車專用)
        "R-10-1": [],  # 大安→象山 (首班車專用)
        "R-11-1": [],  # 雙連→象山 (首班車專用)
        "R-12-1": [],  # 民權西路→象山 (首班車專用)
        "R-13-1": [],  # 圓山→象山 (首班車專用)
        "R-14-1": [],  # 石牌→象山 (首班車專用)
        "R-15-1": [],  # 唭哩岸→象山 (首班車專用)
    }

    # 統計各路線班次 (全域)
    route_counts = {
        "R-1": 0, "R-2": 0, "R-4": 0,
        "R-5": 0, "R-6": 0, "R-7": 0, "R-8": 0,  # 北上首班車
        "R-9": 0, "R-10": 0, "R-11": 0, "R-12": 0, "R-13": 0, "R-14": 0, "R-15": 0  # 南下首班車
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

            # 統計各路線班次 (此方向)
            dir_counts = {
                "R-1": 0, "R-2": 0, "R-4": 0,
                "R-5": 0, "R-6": 0, "R-7": 0, "R-8": 0,  # 北上首班車
                "R-9": 0, "R-10": 0, "R-11": 0, "R-12": 0, "R-13": 0, "R-14": 0, "R-15": 0  # 南下首班車
            }

            for train in trains:
                route_type = classify_train(train["Schedule"], direction)
                dir_counts[route_type] += 1
                route_counts[route_type] += 1
                train_idx = route_counts[route_type]

                converted = convert_train(train, direction, train_idx, route_type)

                # 決定 track_id
                if route_type in ["R-9", "R-10", "R-11", "R-12", "R-13", "R-14", "R-15"]:
                    # R-9 到 R-15 都是南下方向專用
                    track_id = f"{route_type}-1"
                elif direction == "淡水":
                    track_id = f"{route_type}-0"
                else:
                    track_id = f"{route_type}-1"

                schedules[track_id].append(converted)

            print(f"    R-1 (全程): {dir_counts['R-1']} 班")
            print(f"    R-2 (南段區間): {dir_counts['R-2']} 班")
            print(f"    R-4 (北段區間): {dir_counts['R-4']} 班")
            # 北上首班車 (往淡水)
            north_count = sum(dir_counts[f'R-{i}'] for i in range(5, 9))
            if north_count > 0:
                north_details = ", ".join([f"R-{i}:{dir_counts[f'R-{i}']}" for i in range(5, 9) if dir_counts[f'R-{i}'] > 0])
                print(f"    首班車專用(北上): {north_count} 班 ({north_details})")
            # 南下首班車 (往象山)
            south_count = sum(dir_counts[f'R-{i}'] for i in range(9, 16))
            if south_count > 0:
                south_details = ", ".join([f"R-{i}:{dir_counts[f'R-{i}']}" for i in range(9, 16) if dir_counts[f'R-{i}'] > 0])
                print(f"    首班車專用(南下): {south_count} 班 ({south_details})")

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

    # R-4 北段區間 (北投 R22 ↔ 淡水 R28)
    r4_stations = STATION_ORDER[STATION_ORDER.index("R22"):]  # R22~R28

    # R-4-0: 往淡水方向的北段區間車
    r4_0_deps = sort_departures(schedules["R-4-0"])
    r4_0 = create_schedule_file(
        track_id="R-4-0",
        route_id="R-4",
        name="北投 → 淡水",
        origin="R22",
        destination="R28",
        stations=r4_stations,
        departures=r4_0_deps
    )

    # R-4-1: 往北投方向的北段區間車 (通常很少或沒有)
    r4_1_deps = sort_departures(schedules["R-4-1"])
    r4_1 = create_schedule_file(
        track_id="R-4-1",
        route_id="R-4",
        name="淡水 → 北投",
        origin="R28",
        destination="R22",
        stations=list(reversed(r4_stations)),
        departures=r4_1_deps
    )

    # === 首班車專用軌道 ===

    # R-5-0: 大安→淡水
    r5_0_deps = sort_departures(schedules["R-5-0"])
    r5_0_stations = STATION_ORDER[STATION_ORDER.index("R05"):]  # R05~R28
    r5_0 = create_schedule_file(
        track_id="R-5-0",
        route_id="R-5",
        name="大安 → 淡水",
        origin="R05",
        destination="R28",
        stations=r5_0_stations,
        departures=r5_0_deps
    )

    # R-6-0: 雙連→淡水
    r6_0_deps = sort_departures(schedules["R-6-0"])
    r6_0_stations = STATION_ORDER[STATION_ORDER.index("R10"):]  # R10~R28
    r6_0 = create_schedule_file(
        track_id="R-6-0",
        route_id="R-6",
        name="雙連 → 淡水",
        origin="R10",
        destination="R28",
        stations=r6_0_stations,
        departures=r6_0_deps
    )

    # R-7-0: 圓山→淡水
    r7_0_deps = sort_departures(schedules["R-7-0"])
    r7_0_stations = STATION_ORDER[STATION_ORDER.index("R15"):]  # R15~R28
    r7_0 = create_schedule_file(
        track_id="R-7-0",
        route_id="R-7",
        name="圓山 → 淡水",
        origin="R15",
        destination="R28",
        stations=r7_0_stations,
        departures=r7_0_deps
    )

    # R-8-0: 芝山→淡水
    r8_0_deps = sort_departures(schedules["R-8-0"])
    r8_0_stations = STATION_ORDER[STATION_ORDER.index("R20"):]  # R20~R28
    r8_0 = create_schedule_file(
        track_id="R-8-0",
        route_id="R-8",
        name="芝山 → 淡水",
        origin="R20",
        destination="R28",
        stations=r8_0_stations,
        departures=r8_0_deps
    )

    # R-9-1: 紅樹林→象山
    r9_1_deps = sort_departures(schedules["R-9-1"])
    r9_1_stations = list(reversed(STATION_ORDER[:STATION_ORDER.index("R24")+1]))  # R24~R02 (reversed)
    r9_1 = create_schedule_file(
        track_id="R-9-1",
        route_id="R-9",
        name="紅樹林 → 象山",
        origin="R24",
        destination="R02",
        stations=r9_1_stations,
        departures=r9_1_deps
    )

    # R-10-1: 大安→象山
    r10_1_deps = sort_departures(schedules["R-10-1"])
    r10_1_stations = list(reversed(STATION_ORDER[:STATION_ORDER.index("R05")+1]))  # R05~R02 (reversed)
    r10_1 = create_schedule_file(
        track_id="R-10-1",
        route_id="R-10",
        name="大安 → 象山",
        origin="R05",
        destination="R02",
        stations=r10_1_stations,
        departures=r10_1_deps
    )

    # R-11-1: 雙連→象山
    r11_1_deps = sort_departures(schedules["R-11-1"])
    r11_1_stations = list(reversed(STATION_ORDER[:STATION_ORDER.index("R10")+1]))  # R10~R02 (reversed)
    r11_1 = create_schedule_file(
        track_id="R-11-1",
        route_id="R-11",
        name="雙連 → 象山",
        origin="R10",
        destination="R02",
        stations=r11_1_stations,
        departures=r11_1_deps
    )

    # R-12-1: 民權西路→象山
    r12_1_deps = sort_departures(schedules["R-12-1"])
    r12_1_stations = list(reversed(STATION_ORDER[:STATION_ORDER.index("R13")+1]))  # R13~R02 (reversed)
    r12_1 = create_schedule_file(
        track_id="R-12-1",
        route_id="R-12",
        name="民權西路 → 象山",
        origin="R13",
        destination="R02",
        stations=r12_1_stations,
        departures=r12_1_deps
    )

    # R-13-1: 圓山→象山
    r13_1_deps = sort_departures(schedules["R-13-1"])
    r13_1_stations = list(reversed(STATION_ORDER[:STATION_ORDER.index("R15")+1]))  # R15~R02 (reversed)
    r13_1 = create_schedule_file(
        track_id="R-13-1",
        route_id="R-13",
        name="圓山 → 象山",
        origin="R15",
        destination="R02",
        stations=r13_1_stations,
        departures=r13_1_deps
    )

    # R-14-1: 石牌→象山
    r14_1_deps = sort_departures(schedules["R-14-1"])
    r14_1_stations = list(reversed(STATION_ORDER[:STATION_ORDER.index("R19")+1]))  # R19~R02 (reversed)
    r14_1 = create_schedule_file(
        track_id="R-14-1",
        route_id="R-14",
        name="石牌 → 象山",
        origin="R19",
        destination="R02",
        stations=r14_1_stations,
        departures=r14_1_deps
    )

    # R-15-1: 唭哩岸→象山
    r15_1_deps = sort_departures(schedules["R-15-1"])
    r15_1_stations = list(reversed(STATION_ORDER[:STATION_ORDER.index("R20")+1]))  # R20~R02 (reversed)
    r15_1 = create_schedule_file(
        track_id="R-15-1",
        route_id="R-15",
        name="唭哩岸 → 象山",
        origin="R20",
        destination="R02",
        stations=r15_1_stations,
        departures=r15_1_deps
    )

    # 寫入檔案
    output_files = [
        ("R-1-0.json", r1_0),
        ("R-1-1.json", r1_1),
        ("R-2-0.json", r2_0),
        ("R-2-1.json", r2_1),
        ("R-4-0.json", r4_0),
        ("R-4-1.json", r4_1),
        # 北上首班車專用軌道
        ("R-5-0.json", r5_0),
        ("R-6-0.json", r6_0),
        ("R-7-0.json", r7_0),
        ("R-8-0.json", r8_0),
        # 南下首班車專用軌道
        ("R-9-1.json", r9_1),
        ("R-10-1.json", r10_1),
        ("R-11-1.json", r11_1),
        ("R-12-1.json", r12_1),
        ("R-13-1.json", r13_1),
        ("R-14-1.json", r14_1),
        ("R-15-1.json", r15_1),
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
    print(f"  R-4 (北段區間): {r4_0['departure_count'] + r4_1['departure_count']} 班")
    print(f"  首班車專用軌道 (北上):")
    print(f"    - R-5-0 大安→淡水: {r5_0['departure_count']} 班")
    print(f"    - R-6-0 雙連→淡水: {r6_0['departure_count']} 班")
    print(f"    - R-7-0 圓山→淡水: {r7_0['departure_count']} 班")
    print(f"    - R-8-0 芝山→淡水: {r8_0['departure_count']} 班")
    print(f"  首班車專用軌道 (南下):")
    print(f"    - R-9-1 紅樹林→象山: {r9_1['departure_count']} 班")
    print(f"    - R-10-1 大安→象山: {r10_1['departure_count']} 班")
    print(f"    - R-11-1 雙連→象山: {r11_1['departure_count']} 班")
    print(f"    - R-12-1 民權西路→象山: {r12_1['departure_count']} 班")
    print(f"    - R-13-1 圓山→象山: {r13_1['departure_count']} 班")
    print(f"    - R-14-1 石牌→象山: {r14_1['departure_count']} 班")
    print(f"    - R-15-1 唭哩岸→象山: {r15_1['departure_count']} 班")

    # 顯示首班車資訊
    print("\n首班車資訊:")
    for filename, data in output_files:
        early_trains = [d for d in data['departures'] if d['departure_time'] < '06:15:00']
        if early_trains:
            print(f"\n  {data['name']}:")
            for train in early_trains[:3]:
                origin = train.get('origin_station', data['origin'])
                print(f"    {origin} {train['departure_time'][:5]}")


if __name__ == "__main__":
    main()
