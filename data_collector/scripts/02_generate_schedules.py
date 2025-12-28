#!/usr/bin/env python3
"""
02_generate_schedules.py - 產生紅線模擬時刻表

基於班距 (Frequency) 資料和路線 (Routes) 資料產生模擬時刻表。
此方式與 Mini Tokyo 3D 類似，使用發車頻率來模擬實際營運。

輸入：
- raw_data/trtc_routes.json: 路線定義（包含行駛時間）
- raw_data/trtc_frequency.json: 班距資料（各時段發車間隔）
- raw_data/trtc_stations.json: 車站資料（取得車站序列）

輸出：
- output/schedules/R-1-0.json: 象山→淡水 發車時刻表
- output/schedules/R-1-1.json: 淡水→象山 發車時刻表
- output/schedules/R-2-0.json: 大安→北投 發車時刻表
- output/schedules/R-2-1.json: 北投→大安 發車時刻表
- output/schedules/R-3-0.json: 北投→新北投 發車時刻表
- output/schedules/R-3-1.json: 新北投→北投 發車時刻表

資料結構：
{
  "track_id": "R-1-0",
  "departures": [
    {
      "departure_time": "06:00:00",
      "train_id": "R-1-0-001",
      "stations": [
        { "station_id": "R02", "arrival": 0, "departure": 40 },
        { "station_id": "R03", "arrival": 120, "departure": 160 },
        ...
      ],
      "total_travel_time": 3240
    }
  ]
}
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
RAW_DATA_DIR = SCRIPT_DIR.parent / "raw_data"
OUTPUT_DIR = SCRIPT_DIR.parent / "output"
SCHEDULES_DIR = OUTPUT_DIR / "schedules"

# 停站時間設定（秒）
DWELL_TIME = 40  # 每站停靠 40 秒


@dataclass
class TrackDefinition:
    """軌道定義"""
    track_id: str
    route_id: str
    direction: int
    name: str
    origin: str
    destination: str
    stations: List[str]
    travel_time: int  # 分鐘


# 紅線軌道定義
TRACK_DEFINITIONS: Dict[str, TrackDefinition] = {
    "R-1-0": TrackDefinition(
        track_id="R-1-0",
        route_id="R-1",
        direction=0,
        name="象山 → 淡水",
        origin="R02",
        destination="R28",
        stations=[
            "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10",
            "R11", "R12", "R13", "R14", "R15", "R16", "R17", "R18", "R19",
            "R20", "R21", "R22", "R23", "R24", "R25", "R26", "R27", "R28"
        ],
        travel_time=54
    ),
    "R-1-1": TrackDefinition(
        track_id="R-1-1",
        route_id="R-1",
        direction=1,
        name="淡水 → 象山",
        origin="R28",
        destination="R02",
        stations=[
            "R28", "R27", "R26", "R25", "R24", "R23", "R22", "R21", "R20",
            "R19", "R18", "R17", "R16", "R15", "R14", "R13", "R12", "R11",
            "R10", "R09", "R08", "R07", "R06", "R05", "R04", "R03", "R02"
        ],
        travel_time=54
    ),
    "R-2-0": TrackDefinition(
        track_id="R-2-0",
        route_id="R-2",
        direction=0,
        name="大安 → 北投",
        origin="R05",
        destination="R22",
        stations=[
            "R05", "R06", "R07", "R08", "R09", "R10", "R11", "R12", "R13",
            "R14", "R15", "R16", "R17", "R18", "R19", "R20", "R21", "R22"
        ],
        travel_time=32
    ),
    "R-2-1": TrackDefinition(
        track_id="R-2-1",
        route_id="R-2",
        direction=1,
        name="北投 → 大安",
        origin="R22",
        destination="R05",
        stations=[
            "R22", "R21", "R20", "R19", "R18", "R17", "R16", "R15", "R14",
            "R13", "R12", "R11", "R10", "R09", "R08", "R07", "R06", "R05"
        ],
        travel_time=32
    ),
    "R-3-0": TrackDefinition(
        track_id="R-3-0",
        route_id="R-3",
        direction=0,
        name="北投 → 新北投",
        origin="R22",
        destination="R22A",
        stations=["R22", "R22A"],
        travel_time=4
    ),
    "R-3-1": TrackDefinition(
        track_id="R-3-1",
        route_id="R-3",
        direction=1,
        name="新北投 → 北投",
        origin="R22A",
        destination="R22",
        stations=["R22A", "R22"],
        travel_time=4
    ),
}


def load_json(filepath: Path) -> Any:
    """載入 JSON 檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filepath: Path, data: Any) -> None:
    """儲存 JSON 檔案"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 已儲存: {filepath}")


def time_to_seconds(time_str: str) -> int:
    """將時間字串轉換為當日秒數 (HH:MM 或 HH:MM:SS)"""
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2]) if len(parts) > 2 else 0
    return hours * 3600 + minutes * 60 + seconds


def seconds_to_time(seconds: int) -> str:
    """將秒數轉換為時間字串 (HH:MM:SS)"""
    # 處理跨日
    seconds = seconds % 86400
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def get_frequency_for_route(
    frequency_data: List[Dict],
    route_id: str,
    is_weekday: bool = True
) -> List[Dict]:
    """取得特定路線的班距資料

    Args:
        frequency_data: 班距資料列表
        route_id: 路線 ID (如 "R-1")
        is_weekday: 是否為平日

    Returns:
        該路線的班距資料
    """
    service_tag = "平日" if is_weekday else "假日"

    for freq in frequency_data:
        if freq.get('RouteID') == route_id:
            service_day = freq.get('ServiceDay', {})
            if service_day.get('ServiceTag') == service_tag:
                return freq.get('Headways', [])

    return []


def generate_departure_times(
    headways: List[Dict],
    operation_start: str,
    operation_end: str
) -> List[str]:
    """根據班距資料產生發車時刻列表

    Args:
        headways: 班距資料
        operation_start: 營運開始時間
        operation_end: 營運結束時間

    Returns:
        發車時刻列表
    """
    departures = []

    # 排序班距資料
    sorted_headways = sorted(headways, key=lambda h: time_to_seconds(h['StartTime']))

    # 產生整天的發車時刻
    op_start_sec = time_to_seconds(operation_start)
    op_end_sec = time_to_seconds(operation_end)

    # 處理跨日（如 24:00 = 00:00）
    if op_end_sec <= op_start_sec:
        op_end_sec += 86400

    current_time = op_start_sec

    while current_time < op_end_sec:
        # 找到當前時間適用的班距
        headway_mins = 10  # 預設 10 分鐘
        current_time_of_day = current_time % 86400

        for hw in sorted_headways:
            hw_start = time_to_seconds(hw['StartTime'])
            hw_end = time_to_seconds(hw['EndTime'])

            # 處理跨日
            if hw_end <= hw_start:
                hw_end += 86400

            if hw_start <= current_time_of_day < hw_end:
                # 使用平均班距
                min_hw = hw.get('MinHeadwayMins', 8)
                max_hw = hw.get('MaxHeadwayMins', 10)
                avg_hw = (min_hw + max_hw) / 2
                # 防止無限迴圈：班距至少 1 分鐘
                if avg_hw > 0:
                    headway_mins = avg_hw
                break

        departures.append(seconds_to_time(current_time % 86400))
        current_time += int(headway_mins * 60)

    return departures


def build_station_times(
    stations: List[str],
    total_travel_time: int,
    dwell_time: int
) -> List[Dict]:
    """建立各站時刻序列

    假設各站間行駛時間相等（簡化模型）

    Args:
        stations: 車站序列
        total_travel_time: 總行駛時間（分鐘）
        dwell_time: 停站時間（秒）

    Returns:
        各站時刻序列
    """
    num_stations = len(stations)
    if num_stations < 2:
        return [{"station_id": stations[0], "arrival": 0, "departure": 0}]

    # 總行駛時間（秒），不含停站時間
    # 總時間 = 行駛時間 + (站數-2) * 停站時間
    # （起點站不算停站，終點站也不算停站）
    total_seconds = total_travel_time * 60
    num_intermediate_stops = num_stations - 2
    pure_travel_time = total_seconds - num_intermediate_stops * dwell_time

    # 每站間的行駛時間
    num_segments = num_stations - 1
    segment_time = pure_travel_time / num_segments

    result = []
    current_time = 0

    for i, station_id in enumerate(stations):
        if i == 0:
            # 起點站：停站後發車
            result.append({
                "station_id": station_id,
                "arrival": 0,
                "departure": dwell_time
            })
            current_time = dwell_time
        elif i == num_stations - 1:
            # 終點站：只有到站時間
            arrival = current_time + int(segment_time)
            result.append({
                "station_id": station_id,
                "arrival": arrival,
                "departure": arrival  # 終點站不再發車
            })
        else:
            # 中間站：到站 + 停站
            arrival = current_time + int(segment_time)
            departure = arrival + dwell_time
            result.append({
                "station_id": station_id,
                "arrival": arrival,
                "departure": departure
            })
            current_time = departure

    return result


def generate_schedule_for_track(
    track_def: TrackDefinition,
    frequency_data: List[Dict],
    is_weekday: bool = True
) -> Dict:
    """為單一軌道產生時刻表

    Args:
        track_def: 軌道定義
        frequency_data: 班距資料
        is_weekday: 是否為平日

    Returns:
        軌道時刻表
    """
    # 取得班距資料
    headways = get_frequency_for_route(frequency_data, track_def.route_id, is_weekday)

    if not headways:
        print(f"  ⚠️ 找不到 {track_def.route_id} 的班距資料，使用預設值")
        # 使用預設班距
        headways = [{"StartTime": "06:00", "EndTime": "24:00", "MinHeadwayMins": 8, "MaxHeadwayMins": 10}]

    # 產生發車時刻
    departure_times = generate_departure_times(headways, "06:00", "24:00")

    # 建立各站時刻序列（模板）
    station_times_template = build_station_times(
        track_def.stations,
        track_def.travel_time,
        DWELL_TIME
    )

    # 產生每班車的時刻表
    departures = []
    for i, dep_time in enumerate(departure_times):
        departures.append({
            "departure_time": dep_time,
            "train_id": f"{track_def.track_id}-{i+1:03d}",
            "stations": station_times_template,
            "total_travel_time": station_times_template[-1]["arrival"]
        })

    return {
        "track_id": track_def.track_id,
        "route_id": track_def.route_id,
        "name": track_def.name,
        "origin": track_def.origin,
        "destination": track_def.destination,
        "stations": track_def.stations,
        "travel_time_minutes": track_def.travel_time,
        "dwell_time_seconds": DWELL_TIME,
        "is_weekday": is_weekday,
        "departure_count": len(departures),
        "departures": departures
    }


def main():
    """主程式"""
    print("=" * 60)
    print("02_generate_schedules.py - 產生紅線模擬時刻表")
    print("=" * 60)

    # 載入資料
    print("\n載入資料...")
    frequency_data = load_json(RAW_DATA_DIR / "trtc_frequency.json")
    print(f"  班距資料筆數: {len(frequency_data)}")

    # 過濾紅線班距資料
    red_line_freq = [f for f in frequency_data if f.get('RouteID', '').startswith('R-')]
    print(f"  紅線班距資料: {len(red_line_freq)} 筆")

    # 產生各軌道時刻表
    print(f"\n產生時刻表 (停站時間: {DWELL_TIME} 秒)...")

    for track_id, track_def in TRACK_DEFINITIONS.items():
        print(f"\n處理 {track_id}: {track_def.name}")
        print(f"  車站數: {len(track_def.stations)}")
        print(f"  行駛時間: {track_def.travel_time} 分鐘")

        # 產生平日時刻表
        schedule = generate_schedule_for_track(track_def, frequency_data, is_weekday=True)

        print(f"  產生班次: {schedule['departure_count']} 班")
        print(f"  首班車: {schedule['departures'][0]['departure_time']}")
        print(f"  末班車: {schedule['departures'][-1]['departure_time']}")

        # 儲存
        filepath = SCHEDULES_DIR / f"{track_id}.json"
        save_json(filepath, schedule)

    # 統計摘要
    print("\n" + "=" * 60)
    print("統計摘要")
    print("=" * 60)

    total_trains = 0
    for track_id in TRACK_DEFINITIONS:
        schedule = load_json(SCHEDULES_DIR / f"{track_id}.json")
        count = schedule['departure_count']
        total_trains += count
        track_def = TRACK_DEFINITIONS[track_id]
        print(f"  {track_id} ({track_def.name}): {count} 班")

    print(f"\n  總計: {total_trains} 班列車")

    # 顯示範例資料
    print("\n" + "=" * 60)
    print("範例資料 (R-1-0 第一班車)")
    print("=" * 60)

    sample = load_json(SCHEDULES_DIR / "R-1-0.json")
    first_train = sample['departures'][0]
    print(f"\n  發車時間: {first_train['departure_time']}")
    print(f"  車次編號: {first_train['train_id']}")
    print(f"  全程時間: {first_train['total_travel_time']} 秒 ({first_train['total_travel_time']/60:.1f} 分鐘)")
    print(f"\n  各站時刻:")
    for i, st in enumerate(first_train['stations'][:5]):  # 前 5 站
        print(f"    {st['station_id']}: 到站 {st['arrival']}s, 離站 {st['departure']}s")
    print("    ...")
    print(f"    {first_train['stations'][-1]['station_id']}: 到站 {first_train['stations'][-1]['arrival']}s")

    print("\n" + "=" * 60)
    print("完成！")
    print(f"輸出目錄: {SCHEDULES_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
