#!/usr/bin/env python3
"""
轉換 Eric Yu 的綠線時刻表格式到 Mini Taipei V3 格式

來源: https://github.com/ericyu/TaipeiMetroTimeTable (G.json)
輸出: public/data/schedules/ 下的 JSON 檔案

綠線路線分類規則:
- G-1: 全程車 (新店 G01 ↔ 松山 G19)
- G-2: 區間車 (台電大樓 G08 ↔ 松山 G19)
- G-3: 小碧潭支線 (七張 G03 ↔ 小碧潭 G03A)
- G-4 ~ G-7: 首班車往新店 (從中途站出發)
- G-8 ~ G-12: 首班車往松山 (從中途站出發)

注意：小碧潭支線 (G03A) 沒有在 ericyu 時刻表中

方向定義:
- direction 0: 往新店（南下）
- direction 1: 往松山（北上）
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

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

# 首班車路線定義
# 格式: (起站, 終站): (route_id, direction)
# direction: 0=往新店, 1=往松山
FIRST_TRAIN_ROUTES = {
    # === 往新店 (direction=0) ===
    ("G03", "G01"): ("G-4", 0),   # 七張→新店
    ("G08", "G01"): ("G-5", 0),   # 台電大樓→新店
    ("G12", "G01"): ("G-6", 0),   # 西門→新店
    ("G14", "G01"): ("G-7", 0),   # 中山→新店

    # === 往松山 (direction=1) ===
    ("G04", "G19"): ("G-8", 1),   # 大坪林→松山
    ("G07", "G19"): ("G-9", 1),   # 公館→松山
    ("G10", "G19"): ("G-10", 1),  # 中正紀念堂→松山
    ("G13", "G19"): ("G-11", 1),  # 北門→松山
    ("G16", "G19"): ("G-12", 1),  # 南京復興→松山
}


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


def get_stations_between(start_station: str, end_station: str) -> List[str]:
    """取得兩站之間的站點列表（含起終站）"""
    start_idx = STATION_ORDER.index(start_station)
    end_idx = STATION_ORDER.index(end_station)

    if start_idx <= end_idx:
        # 往松山（北上）
        return STATION_ORDER[start_idx:end_idx + 1]
    else:
        # 往新店（南下）
        return list(reversed(STATION_ORDER[end_idx:start_idx + 1]))


def classify_train(schedule: List[Dict], direction: str) -> Tuple[str, Optional[Tuple[str, str]]]:
    """
    分類列車到適當的軌道

    返回: (route_id, first_train_key 或 None)
    - first_train_key: 如果是首班車，返回 (起站, 終站) 元組
    """
    start_station = schedule[0]["StationCode"]
    end_station = schedule[-1]["StationCode"]
    start_num = station_num(start_station)
    end_num = station_num(end_station)

    # 檢查是否為首班車
    first_train_key = (start_station, end_station)
    if first_train_key in FIRST_TRAIN_ROUTES:
        route_id = FIRST_TRAIN_ROUTES[first_train_key][0]
        return route_id, first_train_key

    if direction == "新店":
        # 往新店方向（南下）
        if end_station == "G01":
            # 終點新店 = 全程車
            return "G-1", None
        elif end_num >= 8:  # G08 台電大樓
            # 終點台電大樓或更北 = 區間車
            return "G-2", None
        else:
            # 其他視為全程車軌道
            return "G-1", None
    else:
        # 往松山方向（北上）
        if start_station == "G01":
            # 從新店出發 = 全程車
            return "G-1", None
        elif start_num >= 8:  # G08 台電大樓
            # 從台電大樓或更北出發 = 區間車
            return "G-2", None
        else:
            # 其他視為全程車軌道
            return "G-1", None


def convert_train(train: Dict, direction: str, train_idx: int, route_type: str,
                  first_train_key: Optional[Tuple[str, str]] = None) -> Dict:
    """轉換單一列車資料"""
    schedule = train["Schedule"]
    start_station = schedule[0]["StationCode"]
    first_dep_time = schedule[0]["DepTime"]
    first_dep_seconds = time_to_seconds(first_dep_time)

    # 決定 track_id
    if first_train_key:
        # 首班車使用預定義的 direction
        direction_num = FIRST_TRAIN_ROUTES[first_train_key][1]
        track_suffix = str(direction_num)
    else:
        if direction == "新店":
            track_suffix = "0"  # 往新店
        else:
            track_suffix = "1"  # 往松山

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
        if i > 0:
            min_travel_time = 60
            min_arrival = prev_arrival + DWELL_TIME + min_travel_time
            if arrival_seconds < min_arrival:
                arrival_seconds = min_arrival

        stations.append({
            "station_id": station_id,
            "arrival": arrival_seconds,
            "departure": arrival_seconds + DWELL_TIME
        })
        prev_arrival = arrival_seconds

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
    print("Eric Yu 綠線時刻表轉換工具 (含首班車支援)")
    print("=" * 60)

    # 讀取來源資料
    print(f"\n讀取來源: {SOURCE_FILE}")
    with open(SOURCE_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # 準備輸出資料結構
    schedules = defaultdict(list)

    # 統計各路線班次
    route_counts = defaultdict(int)
    first_train_counts = defaultdict(int)

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

            for train in trains:
                route_type, first_train_key = classify_train(train["Schedule"], direction)

                if first_train_key:
                    # 首班車
                    first_train_counts[route_type] += 1
                    train_idx = first_train_counts[route_type]
                    converted = convert_train(train, direction, train_idx, route_type, first_train_key)
                    dir_num = FIRST_TRAIN_ROUTES[first_train_key][1]
                    track_id = f"{route_type}-{dir_num}"
                else:
                    # 一般車
                    route_counts[route_type] += 1
                    train_idx = route_counts[route_type]
                    converted = convert_train(train, direction, train_idx, route_type)
                    if direction == "新店":
                        track_id = f"{route_type}-0"
                    else:
                        track_id = f"{route_type}-1"

                schedules[track_id].append(converted)

    # 排序並輸出
    print(f"\n輸出目錄: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_files = []

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
    output_files.append(("G-1-0.json", g1_0))

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
    output_files.append(("G-1-1.json", g1_1))

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
    output_files.append(("G-2-0.json", g2_0))

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
    output_files.append(("G-2-1.json", g2_1))

    # 處理首班車軌道
    for (start, end), (route_id, direction) in FIRST_TRAIN_ROUTES.items():
        track_id = f"{route_id}-{direction}"
        deps = sort_departures(schedules.get(track_id, []))

        if not deps:
            continue

        stations = get_stations_between(start, end)
        start_name = STATION_NAMES.get(start, start)
        end_name = STATION_NAMES.get(end, end)

        schedule_file = create_schedule_file(
            track_id=track_id,
            route_id=route_id,
            name=f"{start_name} → {end_name}",
            origin=start,
            destination=end,
            stations=stations,
            departures=deps
        )
        output_files.append((f"{track_id}.json", schedule_file))

    # 寫入檔案
    for filename, data_obj in output_files:
        output_path = OUTPUT_DIR / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data_obj, f, ensure_ascii=False, indent=2)
        print(f"  ✅ {filename}: {data_obj['departure_count']} 班車")

    # 統計摘要
    print("\n" + "=" * 60)
    print("轉換完成！")
    print("=" * 60)

    print("\n全程車/區間車:")
    print(f"  G-1 (全程車): {g1_0['departure_count'] + g1_1['departure_count']} 班")
    print(f"    - G-1-0 松山→新店: {g1_0['departure_count']} 班")
    print(f"    - G-1-1 新店→松山: {g1_1['departure_count']} 班")
    print(f"  G-2 (區間車): {g2_0['departure_count'] + g2_1['departure_count']} 班")
    print(f"    - G-2-0 松山→台電大樓: {g2_0['departure_count']} 班")
    print(f"    - G-2-1 台電大樓→松山: {g2_1['departure_count']} 班")

    # 首班車統計
    first_train_total = 0
    print("\n首班車:")
    for (start, end), (route_id, direction) in sorted(FIRST_TRAIN_ROUTES.items(), key=lambda x: x[1][0]):
        track_id = f"{route_id}-{direction}"
        count = len(schedules.get(track_id, []))
        if count > 0:
            first_train_total += count
            start_name = STATION_NAMES.get(start, start)
            end_name = STATION_NAMES.get(end, end)
            print(f"  {track_id} ({start_name}→{end_name}): {count} 班")

    print(f"\n總計: {g1_0['departure_count'] + g1_1['departure_count'] + g2_0['departure_count'] + g2_1['departure_count']} 班 (全程+區間) + {first_train_total} 班 (首班車)")


if __name__ == "__main__":
    main()
