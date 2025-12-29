#!/usr/bin/env python3
"""
02_fetch_timetable.py - 抓取並處理紅線時刻表

從 TDX API 取得歷史時刻表資料，並轉換為軌道發車時刻表格式。

輸入：
- TDX API 歷史時刻表

輸出：
- output/schedules/R-1-0.json: 象山→淡水 發車時刻表
- output/schedules/R-1-1.json: 淡水→象山 發車時刻表
- output/schedules/R-2-0.json: 大安→北投 發車時刻表
- output/schedules/R-2-1.json: 北投→大安 發車時刻表
- output/schedules/R-3-0.json: 北投→新北投 發車時刻表
- output/schedules/R-3-1.json: 新北投→北投 發車時刻表
- output/raw/timetable_YYYY-MM-DD.json: 原始 API 回應（供除錯）

資料結構說明：
每個時刻表包含該軌道的所有發車班次，每班車包含：
- departure_time: 起點站發車時間
- train_id: 車次編號
- stations: 各站時間序列（用於動畫內插）
  - station_id: 車站代碼
  - arrival: 到站時間（秒，相對於發車時間）
  - departure: 離站時間（秒，相對於發車時間）
- total_travel_time: 全程行駛時間（秒）
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

# 加入專案目錄到路徑
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data_collector.src.tdx_auth import TDXAuth
from data_collector.src.tdx_client import TDXClient

# 路徑設定
OUTPUT_DIR = SCRIPT_DIR.parent / "output"
SCHEDULES_DIR = OUTPUT_DIR / "schedules"
RAW_DIR = OUTPUT_DIR / "raw"

# 停站時間設定（秒）
DWELL_TIME = 40  # 每站停靠 40 秒

# 路線定義
# 根據 TDX API，DestinationStationID 表示列車終點站
# 我們用此欄位來判斷列車屬於哪條軌道
TRACK_DEFINITIONS = {
    # R-1: 象山 ⇄ 淡水（全線）
    "R-1-0": {
        "route_id": "R-1",
        "direction": 0,
        "name": "象山 → 淡水",
        "origin": "R02",      # 象山
        "destination": "R28",  # 淡水
        "stations": [
            "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10",
            "R11", "R12", "R13", "R14", "R15", "R16", "R17", "R18", "R19",
            "R20", "R21", "R22", "R23", "R24", "R25", "R26", "R27", "R28"
        ]
    },
    "R-1-1": {
        "route_id": "R-1",
        "direction": 1,
        "name": "淡水 → 象山",
        "origin": "R28",
        "destination": "R02",
        "stations": [
            "R28", "R27", "R26", "R25", "R24", "R23", "R22", "R21", "R20",
            "R19", "R18", "R17", "R16", "R15", "R14", "R13", "R12", "R11",
            "R10", "R09", "R08", "R07", "R06", "R05", "R04", "R03", "R02"
        ]
    },
    # R-2: 大安 ⇄ 北投（區間車）
    "R-2-0": {
        "route_id": "R-2",
        "direction": 0,
        "name": "大安 → 北投",
        "origin": "R05",      # 大安
        "destination": "R22",  # 北投
        "stations": [
            "R05", "R06", "R07", "R08", "R09", "R10", "R11", "R12", "R13",
            "R14", "R15", "R16", "R17", "R18", "R19", "R20", "R21", "R22"
        ]
    },
    "R-2-1": {
        "route_id": "R-2",
        "direction": 1,
        "name": "北投 → 大安",
        "origin": "R22",
        "destination": "R05",
        "stations": [
            "R22", "R21", "R20", "R19", "R18", "R17", "R16", "R15", "R14",
            "R13", "R12", "R11", "R10", "R09", "R08", "R07", "R06", "R05"
        ]
    },
    # R-3: 北投 ⇄ 新北投（支線）
    "R-3-0": {
        "route_id": "R-3",
        "direction": 0,
        "name": "北投 → 新北投",
        "origin": "R22",       # 北投
        "destination": "R22A", # 新北投
        "stations": ["R22", "R22A"]
    },
    "R-3-1": {
        "route_id": "R-3",
        "direction": 1,
        "name": "新北投 → 北投",
        "origin": "R22A",
        "destination": "R22",
        "stations": ["R22A", "R22"]
    },
}


def time_to_seconds(time_str: str) -> int:
    """將時間字串轉換為當日秒數

    Args:
        time_str: 時間字串，格式為 "HH:MM" 或 "HH:MM:SS"

    Returns:
        當日秒數 (0-86399)
    """
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2]) if len(parts) > 2 else 0
    return hours * 3600 + minutes * 60 + seconds


def seconds_to_time(seconds: int) -> str:
    """將秒數轉換為時間字串

    Args:
        seconds: 當日秒數

    Returns:
        時間字串，格式為 "HH:MM:SS"
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def identify_track(
    origin_station: str,
    destination_station: str,
    direction: int
) -> Optional[str]:
    """根據起迄站和方向識別軌道 ID

    Args:
        origin_station: 列車發車站
        destination_station: 列車終點站
        direction: 行駛方向 (0=往淡水/北投方向, 1=往象山方向)

    Returns:
        軌道 ID 或 None
    """
    for track_id, track_def in TRACK_DEFINITIONS.items():
        # 檢查終點站是否匹配
        if track_def["destination"] == destination_station:
            # 檢查方向是否匹配
            if track_def["direction"] == direction:
                return track_id

    # 特殊處理：支線
    if destination_station == "R22A":
        return "R-3-0"  # 往新北投
    if origin_station == "R22A":
        return "R-3-1"  # 從新北投出發

    return None


def process_station_timetable(raw_data: List[Dict]) -> Dict[str, List[Dict]]:
    """處理站別時刻表，轉換為軌道發車時刻表

    TDX StationTimeTable 格式：
    - 每筆資料代表一個「車站」在某日的所有列車停靠時刻
    - Timetables 包含經過該站的所有列車
    - 我們需要重組為「以列車為單位」的時刻表

    Args:
        raw_data: TDX API 原始回應

    Returns:
        以軌道 ID 為 key 的發車時刻表
    """
    print("\n處理站別時刻表...")

    # 第一步：收集所有列車的各站時刻
    # trains[train_key] = { station_id: { arrival, departure, sequence } }
    trains: Dict[str, Dict[str, Dict]] = defaultdict(dict)
    train_metadata: Dict[str, Dict] = {}  # 儲存列車元資料

    for station_data in raw_data:
        station_id = station_data.get('StationID', '')

        # 只處理紅線車站
        if not station_id.startswith('R'):
            continue

        for timetable in station_data.get('Timetables', []):
            direction = timetable.get('Direction', 0)
            dest_station = timetable.get('DestinationStationID', '')

            for stop in timetable.get('StopTimes', []):
                # 建立唯一的列車識別 key
                # 使用 終點站 + 方向 + 發車序號 來識別同一班列車
                departure_time = stop.get('DepartureTime', '')
                sequence = stop.get('StopSequence', 0)

                # TDX 沒有提供列車編號，我們用發車時間+終點站來識別
                # 注意：同一時間可能有多班不同終點的車
                train_key = f"{dest_station}_{direction}_{departure_time}_{sequence}"

                # 取得時間資訊
                arrival_time = stop.get('ArrivalTime', departure_time)

                trains[train_key][station_id] = {
                    'arrival': arrival_time,
                    'departure': departure_time,
                    'sequence': sequence
                }

                # 儲存元資料
                if train_key not in train_metadata:
                    train_metadata[train_key] = {
                        'destination': dest_station,
                        'direction': direction
                    }

    print(f"  收集到 {len(trains)} 個列車記錄")

    # 第二步：重組為軌道發車時刻表
    # 這個方法不太對，因為 TDX 的 StationTimeTable 結構不是這樣
    # 讓我們換一個方式處理

    return reorganize_by_track(raw_data)


def reorganize_by_track(raw_data: List[Dict]) -> Dict[str, List[Dict]]:
    """重新組織時刻表資料為軌道格式

    策略：
    1. 找到每條軌道的起點站時刻表
    2. 從起點站出發的每班車，追蹤其沿途各站時刻
    3. 建立完整的發車時刻序列

    Args:
        raw_data: TDX API 原始回應

    Returns:
        以軌道 ID 為 key 的發車時刻表
    """
    # 建立站別時刻表索引
    # station_timetables[station_id][direction][dest] = [(time, sequence), ...]
    station_index: Dict[str, Dict] = {}

    for station_data in raw_data:
        station_id = station_data.get('StationID', '')
        if not station_id.startswith('R'):
            continue

        station_index[station_id] = {'0': {}, '1': {}}

        for timetable in station_data.get('Timetables', []):
            direction = str(timetable.get('Direction', 0))
            dest = timetable.get('DestinationStationID', '')

            stop_times = []
            for stop in timetable.get('StopTimes', []):
                stop_times.append({
                    'arrival': stop.get('ArrivalTime', ''),
                    'departure': stop.get('DepartureTime', ''),
                    'sequence': stop.get('StopSequence', 0)
                })

            station_index[station_id][direction][dest] = stop_times

    print(f"  建立 {len(station_index)} 個車站索引")

    # 為每條軌道建立發車時刻表
    result: Dict[str, List[Dict]] = {}

    for track_id, track_def in TRACK_DEFINITIONS.items():
        print(f"\n處理軌道 {track_id}: {track_def['name']}")

        origin = track_def['origin']
        destination = track_def['destination']
        direction = str(track_def['direction'])
        stations = track_def['stations']

        if origin not in station_index:
            print(f"  ⚠️ 找不到起點站 {origin} 的時刻表")
            result[track_id] = []
            continue

        # 取得起點站往該終點站的所有發車時刻
        origin_timetable = station_index[origin].get(direction, {})
        departures_from_origin = origin_timetable.get(destination, [])

        if not departures_from_origin:
            # 嘗試找相近的終點站
            print(f"  ⚠️ 起點站 {origin} 沒有往 {destination} 的班次")
            print(f"     可用終點站: {list(origin_timetable.keys())}")
            result[track_id] = []
            continue

        print(f"  找到 {len(departures_from_origin)} 班往 {destination} 的列車")

        # 建立每班車的完整時刻序列
        departures = []
        for i, origin_stop in enumerate(departures_from_origin):
            departure_time = origin_stop['departure']

            # 建立各站時刻序列
            station_times = build_station_times(
                stations=stations,
                station_index=station_index,
                direction=direction,
                destination=destination,
                origin_departure_time=departure_time,
                dwell_time=DWELL_TIME
            )

            if station_times:
                total_time = station_times[-1]['departure']

                departures.append({
                    'departure_time': departure_time,
                    'train_id': f"{track_id}-{i+1:03d}",
                    'stations': station_times,
                    'total_travel_time': total_time
                })

        result[track_id] = departures
        print(f"  ✓ 產生 {len(departures)} 班發車時刻")

    return result


def build_station_times(
    stations: List[str],
    station_index: Dict,
    direction: str,
    destination: str,
    origin_departure_time: str,
    dwell_time: int
) -> List[Dict]:
    """建立一班列車的各站時刻序列

    Args:
        stations: 車站序列
        station_index: 站別時刻表索引
        direction: 行駛方向
        destination: 終點站
        origin_departure_time: 起點站發車時間
        dwell_time: 停站時間（秒）

    Returns:
        各站時刻序列，包含到站/離站時間（相對秒數）
    """
    result = []
    origin_seconds = time_to_seconds(origin_departure_time)

    for i, station_id in enumerate(stations):
        if i == 0:
            # 起點站
            result.append({
                'station_id': station_id,
                'arrival': 0,
                'departure': dwell_time
            })
            continue

        # 找該站的時刻
        station_data = station_index.get(station_id, {})
        direction_data = station_data.get(direction, {})
        dest_times = direction_data.get(destination, [])

        # 在該站的時刻表中，找到與起點站發車時間匹配的班次
        # 這需要基於發車順序來匹配
        found_time = None
        for stop in dest_times:
            stop_arr_seconds = time_to_seconds(stop['arrival'])
            # 檢查是否是同一班車（到站時間應該在起點發車之後）
            if stop_arr_seconds > origin_seconds:
                found_time = stop
                break

        if found_time:
            arrival_seconds = time_to_seconds(found_time['arrival']) - origin_seconds
            departure_seconds = arrival_seconds + dwell_time
        else:
            # 如果找不到，使用估算（基於前一站）
            if result:
                prev_departure = result[-1]['departure']
                # 假設站間行駛時間 2-3 分鐘
                estimated_travel = 150  # 2.5 分鐘
                arrival_seconds = prev_departure + estimated_travel
                departure_seconds = arrival_seconds + dwell_time
            else:
                continue

        result.append({
            'station_id': station_id,
            'arrival': arrival_seconds,
            'departure': departure_seconds if i < len(stations) - 1 else arrival_seconds
        })

    return result


def save_json(filepath: Path, data: Any) -> None:
    """儲存 JSON 檔案"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 已儲存: {filepath}")


def main(date: str = None):
    """主程式

    Args:
        date: 查詢日期，格式為 'YYYY-MM-DD'，預設為昨天
    """
    print("=" * 60)
    print("02_fetch_timetable.py - 抓取並處理紅線時刻表")
    print("=" * 60)

    # 設定日期
    if date is None:
        # 使用昨天的日期（確保資料已經產生）
        yesterday = datetime.now() - timedelta(days=1)
        date = yesterday.strftime('%Y-%m-%d')

    print(f"\n查詢日期: {date}")
    print(f"停站時間: {DWELL_TIME} 秒")

    # 初始化 TDX 客戶端
    print("\n初始化 TDX API...")
    try:
        auth = TDXAuth()
        client = TDXClient(auth)
    except ValueError as e:
        print(f"❌ 認證失敗: {e}")
        print("\n請確保 .env 檔案已設定 TDX_APP_ID 和 TDX_APP_KEY")
        return

    # 抓取時刻表
    print("\n抓取歷史時刻表...")
    try:
        raw_data = client.get_metro_station_timetable('TRTC', date)
    except Exception as e:
        print(f"❌ API 請求失敗: {e}")
        return

    # 儲存原始資料
    raw_filepath = RAW_DIR / f"timetable_{date}.json"
    save_json(raw_filepath, raw_data)
    print(f"原始資料筆數: {len(raw_data)}")

    # 處理並轉換資料
    schedules = reorganize_by_track(raw_data)

    # 儲存各軌道時刻表
    print("\n儲存各軌道時刻表...")
    for track_id, departures in schedules.items():
        track_def = TRACK_DEFINITIONS[track_id]
        schedule_data = {
            'track_id': track_id,
            'route_id': track_def['route_id'],
            'name': track_def['name'],
            'origin': track_def['origin'],
            'destination': track_def['destination'],
            'stations': track_def['stations'],
            'date': date,
            'dwell_time': DWELL_TIME,
            'departure_count': len(departures),
            'departures': departures
        }

        filepath = SCHEDULES_DIR / f"{track_id}.json"
        save_json(filepath, schedule_data)

    # 統計摘要
    print("\n" + "=" * 60)
    print("統計摘要")
    print("=" * 60)
    total = 0
    for track_id, departures in schedules.items():
        track_def = TRACK_DEFINITIONS[track_id]
        count = len(departures)
        total += count
        print(f"  {track_id} ({track_def['name']}): {count} 班")
    print(f"\n  總計: {total} 班")

    print("\n" + "=" * 60)
    print("完成！")
    print(f"輸出目錄: {SCHEDULES_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else None
    main(date)
