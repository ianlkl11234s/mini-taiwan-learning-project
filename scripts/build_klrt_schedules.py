#!/usr/bin/env python3
"""
建立高雄輕軌時刻表

從 TDX StationTimeTable 和 S2STravelTime 組合完整時刻表：
- klrt_schedules.json (符合 TrackSchedule 介面)

策略：
1. 從起點站取得所有發車時間
2. 利用 S2STravelTime 計算每站到達/離開時間
3. 組合成完整的班次時刻表

環狀線特性：
- 起點和終點是同一站 (C1 籬仔內)
- Direction 0 = 順時針，Direction 1 = 逆時針
- 全程約 90 分鐘

Usage:
    python scripts/build_klrt_schedules.py
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# 路徑設定
DATA_DIR = Path(__file__).parent.parent / "data-klrt"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "data-klrt" / "schedules"

# 線路配置
LINE_CONFIG = {
    'C': {
        'name': '環狀線',
        'direction_0': {
            'origin': 'C1',
            'destination': 'C1',  # 環狀線回到起點
            'name': '順時針 (籬仔內→籬仔內)',
            # 站序將從 StationOfLine 動態載入
        },
        'direction_1': {
            'origin': 'C1',
            'destination': 'C1',  # 環狀線回到起點
            'name': '逆時針 (籬仔內→籬仔內)',
            # 站序將從 StationOfLine 動態載入（反向）
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
    with open(RAW_DIR / "klrt_station_timetable.json", 'r', encoding='utf-8') as f:
        return json.load(f)


def load_s2s_travel_time() -> List[Dict]:
    """載入站間行駛時間"""
    with open(RAW_DIR / "klrt_s2s_travel_time.json", 'r', encoding='utf-8') as f:
        return json.load(f)


def load_station_of_line() -> List[Dict]:
    """載入車站線序"""
    with open(RAW_DIR / "klrt_station_of_line.json", 'r', encoding='utf-8') as f:
        return json.load(f)


def get_station_order(line_data: List[Dict], direction: int) -> List[str]:
    """
    取得指定方向的車站順序

    環狀線特性：
    - 起點和終點都是 C1 (籬仔內)
    - Direction 0 (順時針): C1 → C2 → C3 → ... → C37 → C1
    - Direction 1 (逆時針): C1 → C37 → C36 → ... → C2 → C1
    """
    if not line_data:
        return []

    # KLRT 只有一條線
    line = line_data[0]
    stations = [s['StationID'] for s in line.get('Stations', [])]

    if direction == 0:
        # 順時針：正向順序 (C1 → C2 → ... → C37)
        return stations
    else:
        # 逆時針：從起點出發，往反方向走
        # 原順序: [C1, C2, C3, ..., C37]
        # 逆時針: [C1, C37, C36, ..., C2]
        if len(stations) <= 1:
            return stations
        origin = stations[0]  # C1
        rest = stations[1:]   # [C2, C3, ..., C37]
        return [origin] + list(reversed(rest))


def build_travel_time_map(s2s_data: List[Dict]) -> Dict[str, Dict[str, int]]:
    """
    建立站間行駛時間映射表

    TDX API 的 S2STravelTime 資料包含兩種格式：
    1. 累積時間（從某站到終點站的剩餘時間）- 數值較大
    2. 相鄰站間時間 - 數值較小（約 120-180 秒）

    策略：
    1. 當有重複的站間組合時，取最小值（相鄰站間時間）
    2. 建立雙向映射（環狀線兩個方向使用相同的站間時間）

    返回：{ 'C1->C2': { 'run': 120, 'stop': 30 } }
    """
    travel_map = {}

    def add_or_update(key: str, run_time: int, stop_time: int):
        """添加或更新映射，取較小的 run_time"""
        if key in travel_map:
            if run_time < travel_map[key]['run']:
                travel_map[key] = {'run': run_time, 'stop': stop_time}
        else:
            travel_map[key] = {'run': run_time, 'stop': stop_time}

    for item in s2s_data:
        for travel in item.get('TravelTimes', []):
            from_station = travel['FromStationID']
            to_station = travel['ToStationID']

            # 跳過相同站的項目（如 C1->C1 表示完整環線時間）
            if from_station == to_station:
                continue

            run_time = travel.get('RunTime', 120)
            stop_time = travel.get('StopTime', 30)

            # 添加正向和反向映射（環狀線兩方向站間時間相同）
            key_forward = f"{from_station}->{to_station}"
            key_reverse = f"{to_station}->{from_station}"

            add_or_update(key_forward, run_time, stop_time)
            add_or_update(key_reverse, run_time, stop_time)

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

    # 按發車時間排序
    departures.sort(key=lambda x: x['departure_time'])

    # 去重
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
    train_id: str,
    is_circular: bool = False
) -> Dict:
    """
    建立單一班次的完整時刻表

    參數：
        departure_time: 起點站發車時間 (HH:MM)
        stations: 站序列表
        travel_map: 站間行駛時間映射
        train_id: 列車編號
        is_circular: 是否為環狀線

    返回：
        {
            'departure_time': '06:00:00',
            'train_id': 'KLRT-C-0-001',
            'stations': [{ 'station_id': 'C1', 'arrival': 0, 'departure': 40 }, ...],
            'total_travel_time': 5400
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
            # 輕軌停站時間較短
            stop_time = min(stop_time, 45)

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
            run_time = travel_map.get(key, {}).get('run', 150)  # 輕軌站間約 2.5 分鐘

            # 到達時間
            arrival = current_seconds + run_time

            # 離開時間（最後一站不需離開時間）
            if i < len(stations) - 1:
                next_key = f"{station_id}->{stations[i+1]}"
                stop_time = travel_map.get(next_key, {}).get('stop', 30)
                # 輕軌一般中間站停站約 30-45 秒
                stop_time = min(stop_time, 45)
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
        'total_travel_time': total_travel_time,
        'is_circular': is_circular
    }


def main():
    print("=" * 50)
    print("高雄輕軌時刻表建立腳本")
    print("=" * 50)

    # 營運日設定
    SERVICE_TAG = '平日'

    # 確保輸出目錄存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 載入資料
    print("\n載入資料...")
    timetable_data = load_station_timetable()
    s2s_data = load_s2s_travel_time()
    line_data = load_station_of_line()

    print(f"  時刻表筆數: {len(timetable_data)}")
    print(f"  站間時間筆數: {len(s2s_data)}")
    print(f"  線路資料筆數: {len(line_data)}")
    print(f"  使用營運日: {SERVICE_TAG}")

    # 建立站間時間映射
    travel_map = build_travel_time_map(s2s_data)
    print(f"  站間時間映射: {len(travel_map)} 組")

    # 處理環狀線
    line_id = 'C'
    line_config = LINE_CONFIG[line_id]

    schedules = {}

    print(f"\n處理 {line_config['name']}...")

    for direction in [0, 1]:
        dir_config = line_config[f'direction_{direction}']
        track_id = f"KLRT-{line_id}-{direction}"

        print(f"\n  {track_id} ({dir_config['name']})...")

        # 取得站序
        stations = get_station_order(line_data, direction)
        print(f"    站序: {len(stations)} 站")

        if not stations:
            print(f"    ⚠️ 警告：找不到站序")
            continue

        # 環狀線需要加上終點站（回到起點）
        # 如果時刻表提供的是完整環線，則不需要重複
        # 根據 API 測試，Direction 0 的站序已經是 C1->C2->...->C37
        # 需要添加 C1 作為終點來形成環
        if stations[-1] != 'C1':
            stations = stations + ['C1']
            print(f"    添加終點站 C1 形成環線: {len(stations)} 站")

        # 取得起點站發車時間
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
            train_id = f"KLRT-{line_id}-{direction}-{i+1:03d}"
            schedule = build_train_schedule(
                dep['departure_time'],
                stations,
                travel_map,
                train_id,
                is_circular=True
            )
            departures.append(schedule)

        # 按發車時間排序
        departures.sort(key=lambda x: x['departure_time'])

        # 計算統計資訊
        total_minutes = departures[0]['total_travel_time'] // 60 if departures else 0

        schedules[track_id] = {
            'track_id': track_id,
            'route_id': f"KLRT-{line_id}",
            'name': dir_config['name'],
            'origin': dir_config['origin'],
            'destination': dir_config['destination'],
            'stations': stations,
            'travel_time_minutes': total_minutes,
            'dwell_time_seconds': 30,
            'service_tag': SERVICE_TAG,
            'is_weekday': SERVICE_TAG == '平日',
            'is_circular': True,
            'departure_count': len(departures),
            'departures': departures
        }

        print(f"    班次數: {len(departures)}")
        print(f"    行車時間: {total_minutes} 分鐘")
        if departures:
            print(f"    首班: {departures[0]['departure_time']}")
            print(f"    末班: {departures[-1]['departure_time']}")

    # 儲存結果
    output_path = OUTPUT_DIR / "klrt_schedules.json"
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
        print(f"  {track_id}: {schedule['departure_count']} 班 ({schedule['travel_time_minutes']} 分/趟)")
    print(f"  總計: {total_trains} 班")


if __name__ == '__main__':
    main()
