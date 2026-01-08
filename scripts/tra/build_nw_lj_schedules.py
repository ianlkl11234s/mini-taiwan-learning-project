#!/usr/bin/env python3
"""
build_nw_lj_schedules.py - 建立 NW/LJ 線時刻表

從 TDX API 下載或使用模擬資料建立內灣線和六家線的時刻表。
每班車根據起迄站對應到正確的 O-D 軌道。
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
OUTPUT_DIR = os.path.join(DATA_DIR, 'schedules_od')

# 車站資料
NW_STATIONS = {
    '1210': {'name': '新竹', 'name_en': 'Hsinchu'},
    '1190': {'name': '北新竹', 'name_en': 'North Hsinchu'},
    '1191': {'name': '千甲', 'name_en': 'Qianjia'},
    '1192': {'name': '新莊', 'name_en': 'Xinzhuang'},
    '1193': {'name': '竹中', 'name_en': 'Zhuzhong'},
    '1201': {'name': '上員', 'name_en': 'Shangyuan'},
    '1202': {'name': '榮華', 'name_en': 'Ronghua'},
    '1203': {'name': '竹東', 'name_en': 'Zhudong'},
    '1204': {'name': '橫山', 'name_en': 'Hengshan'},
    '1205': {'name': '九讚頭', 'name_en': 'Jiuzantou'},
    '1206': {'name': '合興', 'name_en': 'Hexing'},
    '1207': {'name': '富貴', 'name_en': 'Fugui'},
    '1208': {'name': '內灣', 'name_en': 'Neiwan'},
}

LJ_STATIONS = {
    '1210': {'name': '新竹', 'name_en': 'Hsinchu'},
    '1190': {'name': '北新竹', 'name_en': 'North Hsinchu'},
    '1191': {'name': '千甲', 'name_en': 'Qianjia'},
    '1192': {'name': '新莊', 'name_en': 'Xinzhuang'},
    '1193': {'name': '竹中', 'name_en': 'Zhuzhong'},
    '1194': {'name': '六家', 'name_en': 'Liujia'},
}

# 車站序列
NW_STATION_ORDER = ['1210', '1190', '1191', '1192', '1193', '1201', '1202', '1203', '1204', '1205', '1206', '1207', '1208']
LJ_STATION_ORDER = ['1210', '1190', '1191', '1192', '1193', '1194']
# 新竹 → 北新竹 → 千甲 → 新莊 → 竹中 → 六家

# O-D 軌道對應
OD_TRACK_MAP = {
    # NW 線
    ('1210', '1208'): 'NW-HC-NB',  # 新竹→內灣
    ('1208', '1210'): 'NW-NB-HC',  # 內灣→新竹
    ('1193', '1208'): 'NW-JJ-NB',  # 竹中→內灣
    ('1208', '1193'): 'NW-NB-JJ',  # 內灣→竹中
    ('1210', '1203'): 'NW-HC-JD',  # 新竹→竹東
    # LJ 線
    ('1210', '1194'): 'LJ-HC-LJ',  # 新竹→六家
    ('1194', '1210'): 'LJ-LJ-HC',  # 六家→新竹
}


def get_station_sequence(origin_id: str, destination_id: str, line: str) -> List[str]:
    """取得起迄站之間的車站序列"""
    if line == 'NW':
        stations = NW_STATION_ORDER
    else:
        stations = LJ_STATION_ORDER

    try:
        origin_idx = stations.index(origin_id)
        dest_idx = stations.index(destination_id)

        if origin_idx <= dest_idx:
            return stations[origin_idx:dest_idx+1]
        else:
            return stations[dest_idx:origin_idx+1][::-1]
    except ValueError:
        return [origin_id, destination_id]


def generate_station_times(
    station_ids: List[str],
    start_time: int,
    avg_travel_time: int = 180,  # 平均站間行車時間 (秒)
    dwell_time: int = 30  # 停站時間 (秒)
) -> List[Dict]:
    """生成各站時刻"""
    stations = []
    current_time = start_time

    for i, sid in enumerate(station_ids):
        station_info = NW_STATIONS.get(sid) or LJ_STATIONS.get(sid) or {'name': sid}

        if i == 0:
            # 起站
            stations.append({
                'station_id': sid,
                'station_name': station_info['name'],
                'arrival': 0,
                'departure': 0
            })
        elif i == len(station_ids) - 1:
            # 終站
            arrival = current_time
            stations.append({
                'station_id': sid,
                'station_name': station_info['name'],
                'arrival': arrival,
                'departure': arrival
            })
        else:
            # 中間站
            arrival = current_time
            departure = arrival + dwell_time
            stations.append({
                'station_id': sid,
                'station_name': station_info['name'],
                'arrival': arrival,
                'departure': departure
            })
            current_time = departure

        if i < len(station_ids) - 1:
            current_time += avg_travel_time

    return stations


def generate_nw_schedules() -> List[Dict]:
    """生成內灣線時刻表"""
    departures = []

    # 新竹→內灣 (7 班)
    hc_nb_times = ['06:02', '08:35', '10:12', '12:45', '15:22', '17:55', '19:32']
    for i, time_str in enumerate(hc_nb_times):
        h, m = map(int, time_str.split(':'))
        station_ids = get_station_sequence('1210', '1208', 'NW')
        stations = generate_station_times(station_ids, 0, avg_travel_time=240, dwell_time=30)

        departures.append({
            'departure_time': f'{time_str}:00',
            'train_id': f'NW-{1100 + i}',
            'train_no': str(1100 + i),
            'train_type': '區間',
            'origin_station': '1210',
            'destination_station': '1208',
            'od_track_id': 'NW-HC-NB',
            'stations': stations,
            'total_travel_time': stations[-1]['arrival']
        })

    # 內灣→新竹 (8 班)
    nb_hc_times = ['07:15', '09:48', '11:25', '14:02', '16:35', '18:12', '19:48', '21:25']
    for i, time_str in enumerate(nb_hc_times):
        station_ids = get_station_sequence('1208', '1210', 'NW')
        stations = generate_station_times(station_ids, 0, avg_travel_time=240, dwell_time=30)

        departures.append({
            'departure_time': f'{time_str}:00',
            'train_id': f'NW-{1200 + i}',
            'train_no': str(1200 + i),
            'train_type': '區間',
            'origin_station': '1208',
            'destination_station': '1210',
            'od_track_id': 'NW-NB-HC',
            'stations': stations,
            'total_travel_time': stations[-1]['arrival']
        })

    # 竹中→內灣 (11 班)
    jj_nb_times = ['05:30', '07:00', '08:30', '10:00', '11:30', '13:00', '14:30', '16:00', '17:30', '19:00', '20:30']
    for i, time_str in enumerate(jj_nb_times):
        station_ids = get_station_sequence('1193', '1208', 'NW')
        stations = generate_station_times(station_ids, 0, avg_travel_time=240, dwell_time=30)

        departures.append({
            'departure_time': f'{time_str}:00',
            'train_id': f'NW-{1300 + i}',
            'train_no': str(1300 + i),
            'train_type': '區間',
            'origin_station': '1193',
            'destination_station': '1208',
            'od_track_id': 'NW-JJ-NB',
            'stations': stations,
            'total_travel_time': stations[-1]['arrival']
        })

    # 內灣→竹中 (11 班)
    nb_jj_times = ['06:15', '07:45', '09:15', '10:45', '12:15', '13:45', '15:15', '16:45', '18:15', '19:45', '21:15']
    for i, time_str in enumerate(nb_jj_times):
        station_ids = get_station_sequence('1208', '1193', 'NW')
        stations = generate_station_times(station_ids, 0, avg_travel_time=240, dwell_time=30)

        departures.append({
            'departure_time': f'{time_str}:00',
            'train_id': f'NW-{1400 + i}',
            'train_no': str(1400 + i),
            'train_type': '區間',
            'origin_station': '1208',
            'destination_station': '1193',
            'od_track_id': 'NW-NB-JJ',
            'stations': stations,
            'total_travel_time': stations[-1]['arrival']
        })

    # 新竹→竹東 (1 班)
    departures.append({
        'departure_time': '22:30:00',
        'train_id': 'NW-1500',
        'train_no': '1500',
        'train_type': '區間',
        'origin_station': '1210',
        'destination_station': '1203',
        'od_track_id': 'NW-HC-JD',
        'stations': generate_station_times(
            get_station_sequence('1210', '1203', 'NW'),
            0, avg_travel_time=240, dwell_time=30
        ),
        'total_travel_time': 0
    })
    departures[-1]['total_travel_time'] = departures[-1]['stations'][-1]['arrival']

    return departures


def generate_lj_schedules() -> List[Dict]:
    """生成六家線時刻表"""
    departures = []

    # 新竹→六家 (35 班, 約每 30 分鐘)
    for i in range(35):
        hour = 6 + (i * 30) // 60
        minute = (i * 30) % 60
        if hour > 22:
            break

        time_str = f'{hour:02d}:{minute:02d}'
        station_ids = get_station_sequence('1210', '1194', 'LJ')
        # 實際行車時間約 19 分鐘 (1140 秒)
        # 5 段行車 × 200 秒 + 4 個中間站 × 35 秒停靠 = 1140 秒
        stations = generate_station_times(station_ids, 0, avg_travel_time=200, dwell_time=35)

        departures.append({
            'departure_time': f'{time_str}:00',
            'train_id': f'LJ-{2100 + i}',
            'train_no': str(2100 + i),
            'train_type': '區間',
            'origin_station': '1210',
            'destination_station': '1194',
            'od_track_id': 'LJ-HC-LJ',
            'stations': stations,
            'total_travel_time': stations[-1]['arrival']
        })

    # 六家→新竹 (35 班, 約每 30 分鐘, 錯開 15 分鐘)
    for i in range(35):
        hour = 6 + ((i * 30) + 15) // 60
        minute = ((i * 30) + 15) % 60
        if hour > 22:
            break

        time_str = f'{hour:02d}:{minute:02d}'
        station_ids = get_station_sequence('1194', '1210', 'LJ')
        # 實際行車時間約 19 分鐘 (1140 秒)
        stations = generate_station_times(station_ids, 0, avg_travel_time=200, dwell_time=35)

        departures.append({
            'departure_time': f'{time_str}:00',
            'train_id': f'LJ-{2200 + i}',
            'train_no': str(2200 + i),
            'train_type': '區間',
            'origin_station': '1194',
            'destination_station': '1210',
            'od_track_id': 'LJ-LJ-HC',
            'stations': stations,
            'total_travel_time': stations[-1]['arrival']
        })

    return departures


def save_schedule(line_id: str, departures: List[Dict], direction: int):
    """儲存時刻表"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 依方向分類
    if direction == 0:
        # 往終點方向
        if line_id == 'NW':
            filtered = [d for d in departures if d['od_track_id'] in ['NW-HC-NB', 'NW-JJ-NB', 'NW-HC-JD']]
        else:
            filtered = [d for d in departures if d['od_track_id'] == 'LJ-HC-LJ']
    else:
        # 往起點方向
        if line_id == 'NW':
            filtered = [d for d in departures if d['od_track_id'] in ['NW-NB-HC', 'NW-NB-JJ']]
        else:
            filtered = [d for d in departures if d['od_track_id'] == 'LJ-LJ-HC']

    # 按出發時間排序
    filtered.sort(key=lambda x: x['departure_time'])

    schedule = {
        'track_id': f'{line_id}-{direction}',
        'route_id': line_id,
        'name': f'{line_id} 線時刻表',
        'departure_count': len(filtered),
        'departures': filtered
    }

    output_path = os.path.join(OUTPUT_DIR, f'{line_id}-{direction}.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

    print(f'儲存: {output_path} ({len(filtered)} 班)')


def main():
    print("=" * 60)
    print("建立 NW/LJ 時刻表")
    print("=" * 60)

    # 生成時刻表
    nw_departures = generate_nw_schedules()
    lj_departures = generate_lj_schedules()

    print(f"\nNW 線: {len(nw_departures)} 班")
    print(f"LJ 線: {len(lj_departures)} 班")

    # 儲存
    save_schedule('NW', nw_departures, 0)
    save_schedule('NW', nw_departures, 1)
    save_schedule('LJ', lj_departures, 0)
    save_schedule('LJ', lj_departures, 1)

    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
