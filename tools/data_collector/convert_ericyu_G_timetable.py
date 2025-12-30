#!/usr/bin/env python3
"""
轉換 Eric Yu 的綠線時刻表格式到 Mini Taipei V3 格式

來源: https://github.com/ericyu/TaipeiMetroTimeTable (G.json)
輸出: public/data/schedules/ 下的 JSON 檔案

綠線路線分類規則:
- G-1: 全程車 (新店 G01 ↔ 松山 G19)
- G-2: 區間車 (台電大樓 G08 ↔ 松山 G19)

注意：小碧潭支線 (G03A) 沒有在 ericyu 時刻表中

方向定義:
- direction 0: 往新店（南下）
- direction 1: 往松山（北上）
"""

import json
from pathlib import Path
from typing import List, Dict, Any

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
SOURCE_FILE = SCRIPT_DIR / "source" / "ericyu_G.json"
OUTPUT_DIR = SCRIPT_DIR.parent.parent / "public" / "data" / "schedules"

# 站點順序 (新店→松山方向，即 direction=1 往松山)
STATION_ORDER = [
    "G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G09",
    "G10", "G11", "G12", "G13", "G14", "G15", "G16", "G17", "G18", "G19"
]

# 站名對照
STATION_NAMES = {
    "G01": "新店", "G02": "新店區公所", "G03": "七張", "G03A": "小碧潭",
    "G04": "大坪林", "G05": "景美", "G06": "萬隆", "G07": "公館",
    "G08": "台電大樓", "G09": "古亭", "G10": "中正紀念堂", "G11": "小南門",
    "G12": "西門", "G13": "北門", "G14": "中山", "G15": "松江南京",
    "G16": "南京復興", "G17": "台北小巨蛋", "G18": "南京三民", "G19": "松山"
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
    if station_id.startswith('G'):
        num_part = station_id[1:]
        # 處理 G03A 等特殊站號
        if num_part.endswith('A'):
            return int(num_part[:-1])
        return int(num_part)
    return 0


def classify_train(schedule: List[Dict], direction: str) -> str:
    """
    分類列車到適當的軌道

    direction: "新店" (往南) 或 "松山" (往北)

    路線定義：
    - G-1: 全程車 (新店 G01 ↔ 松山 G19)
    - G-2: 區間車 (台電大樓 G08 ↔ 松山 G19)
    """
    start_station = schedule[0]["StationCode"]
    end_station = schedule[-1]["StationCode"]
    start_num = station_num(start_station)
    end_num = station_num(end_station)

    if direction == "新店":
        # 往新店方向（南下）
        if end_station == "G01":
            # 終點新店 = 全程車
            return "G-1"
        elif end_num >= 8:  # G08 台電大樓
            # 終點台電大樓或更北 = 區間車
            return "G-2"
        else:
            # 其他視為全程車軌道
            return "G-1"
    else:
        # 往松山方向（北上）
        if start_station == "G01":
            # 從新店出發 = 全程車
            return "G-1"
        elif start_num >= 8:  # G08 台電大樓
            # 從台電大樓或更北出發 = 區間車
            return "G-2"
        else:
            # 其他視為全程車軌道
            return "G-1"


def convert_train(train: Dict, direction: str, train_idx: int, route_type: str) -> Dict:
    """轉換單一列車資料"""
    schedule = train["Schedule"]
    start_station = schedule[0]["StationCode"]
    first_dep_time = schedule[0]["DepTime"]
    first_dep_seconds = time_to_seconds(first_dep_time)

    # 決定 track_id
    if direction == "新店":
        track_suffix = "0"  # G-1-0 或 G-2-0 (往新店)
    else:
        track_suffix = "1"  # G-1-1 或 G-2-1 (往松山)

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
        avg_travel_time = sum(travel_times) // len(travel_times) if travel_times else 35
    else:
        avg_travel_time = 35

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
    print("Eric Yu 綠線時刻表轉換工具")
    print("=" * 60)

    # 讀取來源資料
    print(f"\n讀取來源: {SOURCE_FILE}")
    with open(SOURCE_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # 準備輸出資料結構
    schedules = {
        "G-1-0": [],  # 松山→新店 全程
        "G-1-1": [],  # 新店→松山 全程
        "G-2-0": [],  # 松山→台電大樓 區間
        "G-2-1": [],  # 台電大樓→松山 區間
    }

    # 統計各路線班次 (全域)
    route_counts = {"G-1": 0, "G-2": 0}

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
            dir_counts = {"G-1": 0, "G-2": 0}

            for train in trains:
                route_type = classify_train(train["Schedule"], direction)
                dir_counts[route_type] += 1
                route_counts[route_type] += 1
                train_idx = route_counts[route_type]

                converted = convert_train(train, direction, train_idx, route_type)

                # 決定 track_id
                if direction == "新店":
                    track_id = f"{route_type}-0"
                else:
                    track_id = f"{route_type}-1"

                schedules[track_id].append(converted)

            print(f"    G-1 (全程): {dir_counts['G-1']} 班")
            print(f"    G-2 (區間): {dir_counts['G-2']} 班")

    # 排序並輸出
    print(f"\n輸出目錄: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # G-1-0: 松山→新店 全程
    g1_0_deps = sort_departures(schedules["G-1-0"])
    g1_0 = create_schedule_file(
        track_id="G-1-0",
        route_id="G-1",
        name="松山 → 新店",
        origin="G19",
        destination="G01",
        stations=list(reversed(STATION_ORDER)),
        departures=g1_0_deps
    )

    # G-1-1: 新店→松山 全程
    g1_1_deps = sort_departures(schedules["G-1-1"])
    g1_1 = create_schedule_file(
        track_id="G-1-1",
        route_id="G-1",
        name="新店 → 松山",
        origin="G01",
        destination="G19",
        stations=STATION_ORDER.copy(),
        departures=g1_1_deps
    )

    # G-2 區間車站 (G08-G19)
    g2_stations_north = ["G08", "G09", "G10", "G11", "G12", "G13", "G14", "G15", "G16", "G17", "G18", "G19"]

    # G-2-0: 松山→台電大樓 區間
    g2_0_deps = sort_departures(schedules["G-2-0"])
    g2_0 = create_schedule_file(
        track_id="G-2-0",
        route_id="G-2",
        name="松山 → 台電大樓",
        origin="G19",
        destination="G08",
        stations=list(reversed(g2_stations_north)),
        departures=g2_0_deps
    )

    # G-2-1: 台電大樓→松山 區間
    g2_1_deps = sort_departures(schedules["G-2-1"])
    g2_1 = create_schedule_file(
        track_id="G-2-1",
        route_id="G-2",
        name="台電大樓 → 松山",
        origin="G08",
        destination="G19",
        stations=g2_stations_north,
        departures=g2_1_deps
    )

    # 寫入檔案
    output_files = [
        ("G-1-0.json", g1_0),
        ("G-1-1.json", g1_1),
        ("G-2-0.json", g2_0),
        ("G-2-1.json", g2_1),
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
    print(f"  G-1 (全程車): {g1_0['departure_count'] + g1_1['departure_count']} 班")
    print(f"    - G-1-0 松山→新店: {g1_0['departure_count']} 班")
    print(f"    - G-1-1 新店→松山: {g1_1['departure_count']} 班")
    print(f"  G-2 (區間車): {g2_0['departure_count'] + g2_1['departure_count']} 班")
    print(f"    - G-2-0 松山→台電大樓: {g2_0['departure_count']} 班")
    print(f"    - G-2-1 台電大樓→松山: {g2_1['departure_count']} 班")

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
