#!/usr/bin/env python3
"""
建立高雄捷運時刻表

從 TDX StationTimeTable 和 S2STravelTime 組合完整時刻表：
- krtc_schedules.json (符合 TrackSchedule 介面)

策略：
1. 從起點站取得所有發車時間
2. 利用 S2STravelTime 計算每站到達/離開時間
3. 組合成完整的班次時刻表

Usage:
    python scripts/build_krtc_schedules.py
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# 路徑設定
DATA_DIR = Path(__file__).parent.parent / "data-krtc"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "data-krtc" / "schedules"

# 線路配置
LINES_CONFIG = {
    'O': {
        'name': '橘線',
        'direction_0': {
            'origin': 'O1',
            'destination': 'OT1',
            'name': '哈瑪星 → 大寮',
            'stations': ['O1', 'O2', 'O4', 'O5', 'O6', 'O7', 'O8', 'O9', 'O10', 'O11', 'O12', 'O13', 'O14', 'OT1']
        },
        'direction_1': {
            'origin': 'OT1',
            'destination': 'O1',
            'name': '大寮 → 哈瑪星',
            'stations': ['OT1', 'O14', 'O13', 'O12', 'O11', 'O10', 'O9', 'O8', 'O7', 'O6', 'O5', 'O4', 'O2', 'O1']
        }
    },
    'R': {
        'name': '紅線',
        'direction_0': {
            'origin': 'R3',
            'destination': 'RK1',
            'name': '小港 → 岡山車站',
            'stations': ['R3', 'R4', 'R4A', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17', 'R18', 'R19', 'R20', 'R21', 'R22', 'R22A', 'R23', 'R24', 'RK1']
        },
        'direction_1': {
            'origin': 'RK1',
            'destination': 'R3',
            'name': '岡山車站 → 小港',
            'stations': ['RK1', 'R24', 'R23', 'R22A', 'R22', 'R21', 'R20', 'R19', 'R18', 'R17', 'R16', 'R15', 'R14', 'R13', 'R12', 'R11', 'R10', 'R9', 'R8', 'R7', 'R6', 'R5', 'R4A', 'R4', 'R3']
        }
    }
}


def time_to_seconds(time_str: str) -> int:
    """將 HH:MM 轉換為當日秒數"""
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    return hours * 3600 + minutes * 60


def seconds_to_time(seconds: int) -> str:
    """將秒數轉換為 HH:MM:SS"""
    hours = (seconds // 3600) % 24
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def load_station_timetable() -> List[Dict]:
    """載入車站時刻表"""
    with open(RAW_DIR / "krtc_station_timetable.json", 'r', encoding='utf-8') as f:
        return json.load(f)


def load_s2s_travel_time() -> List[Dict]:
    """載入站間行駛時間"""
    with open(RAW_DIR / "krtc_s2s_travel_time.json", 'r', encoding='utf-8') as f:
        return json.load(f)


def build_travel_time_map(s2s_data: List[Dict]) -> Dict[str, Dict[str, int]]:
    """
    建立站間行駛時間映射表

    返回：{ 'O1->O2': { 'run': 120, 'stop': 300 } }
    """
    travel_map = {}

    for item in s2s_data:
        for travel in item.get('TravelTimes', []):
            from_station = travel['FromStationID']
            to_station = travel['ToStationID']
            key = f"{from_station}->{to_station}"
            travel_map[key] = {
                'run': travel.get('RunTime', 120),
                'stop': travel.get('StopTime', 30)
            }

    return travel_map


def get_origin_departures(
    timetable_data: List[Dict],
    line_id: str,
    direction: int,
    origin_station: str,
    service_tag: str = '平日'
) -> List[Dict]:
    """
    取得起點站的所有發車時間

    參數：
        service_tag: 營運日類型，可選值：
            - '平日': 週一~四 (預設)
            - '假日前一天': 週五
            - '假日': 週六
            - '周日': 週日

    返回：[{ 'sequence': 1, 'departure_time': '06:00' }, ...]
    """
    departures = []

    for entry in timetable_data:
        # 檢查線路、方向、站點
        if (entry.get('LineID') != line_id or
            entry.get('Direction') != direction or
            entry.get('StationID') != origin_station):
            continue

        # 只取指定營運日的資料
        entry_service_tag = entry.get('ServiceDay', {}).get('ServiceTag', '')
        if entry_service_tag != service_tag:
            continue

        for timetable in entry.get('Timetables', []):
            departures.append({
                'sequence': timetable['Sequence'],
                'departure_time': timetable['DepartureTime']
            })

    # 按發車時間排序（不再用序號，直接用時間）
    departures.sort(key=lambda x: x['departure_time'])

    # 去重（同一營運日應該不會有重複，但保險起見）
    seen = set()
    unique_departures = []
    for d in departures:
        if d['departure_time'] not in seen:
            seen.add(d['departure_time'])
            unique_departures.append(d)

    return unique_departures


def build_train_schedule(
    departure_time: str,
    stations: List[str],
    travel_map: Dict[str, Dict[str, int]],
    train_id: str
) -> Dict:
    """
    建立單一班次的完整時刻表

    參數：
        departure_time: 起點站發車時間 (HH:MM)
        stations: 站序列表
        travel_map: 站間行駛時間映射
        train_id: 列車編號

    返回：
        {
            'departure_time': '06:00:00',
            'train_id': 'KRTC-O-0-001',
            'stations': [{ 'station_id': 'O1', 'arrival': 0, 'departure': 40 }, ...],
            'total_travel_time': 2400
        }
    """
    base_seconds = time_to_seconds(departure_time)
    current_seconds = 0

    station_times = []

    for i, station_id in enumerate(stations):
        if i == 0:
            # 起點站：到達時間=0，離開時間=初始停站時間
            key = f"{station_id}->{stations[i+1]}" if i + 1 < len(stations) else None
            stop_time = travel_map.get(key, {}).get('stop', 40) if key else 40
            # 起點站通常停站較長（300秒），但我們用較短時間讓視覺效果更好
            stop_time = min(stop_time, 60)

            station_times.append({
                'station_id': station_id,
                'arrival': 0,
                'departure': stop_time
            })
            current_seconds = stop_time
        else:
            # 計算行駛時間
            prev_station = stations[i - 1]
            key = f"{prev_station}->{station_id}"
            run_time = travel_map.get(key, {}).get('run', 120)

            # 到達時間
            arrival = current_seconds + run_time

            # 離開時間（最後一站不需離開時間）
            if i < len(stations) - 1:
                next_key = f"{station_id}->{stations[i+1]}"
                stop_time = travel_map.get(next_key, {}).get('stop', 30)
                # 一般中間站停站約20-40秒
                stop_time = min(stop_time, 40)
                departure = arrival + stop_time
            else:
                departure = arrival

            station_times.append({
                'station_id': station_id,
                'arrival': arrival,
                'departure': departure
            })
            current_seconds = departure

    total_travel_time = station_times[-1]['arrival'] if station_times else 0

    return {
        'departure_time': departure_time + ':00',
        'train_id': train_id,
        'stations': station_times,
        'total_travel_time': total_travel_time
    }


def main():
    print("=" * 50)
    print("高雄捷運時刻表建立腳本")
    print("=" * 50)

    # 營運日設定
    # 可選: '平日' (週一~四), '假日前一天' (週五), '假日' (週六), '周日'
    SERVICE_TAG = '平日'

    # 確保輸出目錄存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 載入資料
    print("\n載入資料...")
    timetable_data = load_station_timetable()
    s2s_data = load_s2s_travel_time()

    print(f"  時刻表筆數: {len(timetable_data)}")
    print(f"  站間時間筆數: {len(s2s_data)}")
    print(f"  使用營運日: {SERVICE_TAG}")

    # 建立站間時間映射
    travel_map = build_travel_time_map(s2s_data)
    print(f"  站間時間映射: {len(travel_map)} 組")

    # 處理每條線路
    schedules = {}

    for line_id, line_config in LINES_CONFIG.items():
        print(f"\n處理 {line_config['name']}...")

        for direction in [0, 1]:
            dir_config = line_config[f'direction_{direction}']
            track_id = f"KRTC-{line_id}-{direction}"

            print(f"\n  {track_id} ({dir_config['name']})...")

            # 取得起點站發車時間（只取指定營運日）
            origin_departures = get_origin_departures(
                timetable_data, line_id, direction, dir_config['origin'],
                service_tag=SERVICE_TAG
            )
            print(f"    發車班次: {len(origin_departures)}")

            if not origin_departures:
                print(f"    ⚠️ 警告：找不到發車時間")
                continue

            # 建立每班車的時刻表
            departures = []
            for i, dep in enumerate(origin_departures):
                train_id = f"KRTC-{line_id}-{direction}-{i+1:03d}"
                schedule = build_train_schedule(
                    dep['departure_time'],
                    dir_config['stations'],
                    travel_map,
                    train_id
                )
                departures.append(schedule)

            # 按發車時間排序
            departures.sort(key=lambda x: x['departure_time'])

            # 計算統計資訊
            total_minutes = departures[0]['total_travel_time'] // 60 if departures else 0

            schedules[track_id] = {
                'track_id': track_id,
                'route_id': f"KRTC-{line_id}",
                'name': dir_config['name'],
                'origin': dir_config['origin'],
                'destination': dir_config['destination'],
                'stations': dir_config['stations'],
                'travel_time_minutes': total_minutes,
                'dwell_time_seconds': 30,
                'service_tag': SERVICE_TAG,
                'is_weekday': SERVICE_TAG == '平日',
                'departure_count': len(departures),
                'departures': departures
            }

            print(f"    班次數: {len(departures)}")
            print(f"    行車時間: {total_minutes} 分鐘")
            if departures:
                print(f"    首班: {departures[0]['departure_time']}")
                print(f"    末班: {departures[-1]['departure_time']}")

    # 儲存結果
    output_path = OUTPUT_DIR / "krtc_schedules.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schedules, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print("完成！")
    print("=" * 50)
    print(f"\n產出檔案: {output_path}")

    # 統計摘要
    total_trains = sum(s['departure_count'] for s in schedules.values())
    print(f"\n統計:")
    for track_id, schedule in schedules.items():
        print(f"  {track_id}: {schedule['departure_count']} 班")
    print(f"  總計: {total_trains} 班")


if __name__ == '__main__':
    main()
