#!/usr/bin/env python3
"""
generate_yl_bh_schedules.py - 生成 YL (宜蘭線) 和 BH (北迴線) 時刻表

支援兩種模式:
1. TDX API: 使用真實時刻表（需要 TDX_APP_ID 和 TDX_APP_KEY）
2. 模擬: 根據典型 TRA 運行模式生成模擬時刻表

Usage:
    python generate_yl_bh_schedules.py [--mode tdx|simulate]
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
OUTPUT_DIR = os.path.join(DATA_DIR, 'schedules_od')

# 車站定義
STATIONS = {
    # 西部幹線北段
    '1000': '臺北', '0990': '松山', '0980': '南港', '0970': '汐科',
    '0960': '汐止', '0950': '五堵', '0940': '百福', '0930': '七堵', '0920': '八堵',
    # YL 宜蘭線
    '7390': '暖暖', '7380': '四腳亭', '7360': '瑞芳', '7350': '猴硐',
    '7330': '三貂嶺', '7320': '牡丹', '7310': '雙溪', '7300': '貢寮',
    '7290': '福隆', '7280': '石城', '7270': '大里', '7260': '大溪',
    '7250': '龜山', '7240': '外澳', '7230': '頭城', '7220': '頂埔',
    '7210': '礁溪', '7200': '四城', '7190': '宜蘭', '7180': '二結',
    '7170': '中里', '7160': '羅東', '7150': '冬山', '7140': '新馬',
    '7130': '蘇澳新', '7120': '蘇澳',
    # BH 北迴線
    '7110': '永樂', '7100': '東澳', '7090': '南澳', '7080': '武塔',
    '7070': '漢本', '7060': '和平', '7050': '和仁', '7040': '崇德',
    '7030': '新城', '7020': '景美', '7010': '北埔', '7000': '花蓮',
}

# O-D 路由對應的車站序列
OD_ROUTES_STATIONS = {
    # 臺北→花蓮 (約 2.5 小時)
    'YL-TP-HL': [
        '1000', '0990', '0980', '0970', '0960', '0950', '0940', '0930', '0920',  # WL-N
        '7390', '7380', '7360', '7350', '7330', '7320', '7310', '7300', '7290',  # YL 前段
        '7280', '7270', '7260', '7250', '7240', '7230', '7220', '7210', '7200', '7190',  # YL 中段
        '7180', '7170', '7160', '7150', '7140', '7130',  # YL 後段
        '7110', '7100', '7090', '7080', '7070', '7060', '7050', '7040', '7030', '7020', '7010', '7000',  # BH
    ],
    # 臺北→宜蘭 (約 1.5 小時)
    'YL-TP-YL': [
        '1000', '0990', '0980', '0970', '0960', '0950', '0940', '0930', '0920',
        '7390', '7380', '7360', '7350', '7330', '7320', '7310', '7300', '7290',
        '7280', '7270', '7260', '7250', '7240', '7230', '7220', '7210', '7200', '7190',
    ],
    # 臺北→蘇澳 (約 2 小時)
    'YL-TP-SA': [
        '1000', '0990', '0980', '0970', '0960', '0950', '0940', '0930', '0920',
        '7390', '7380', '7360', '7350', '7330', '7320', '7310', '7300', '7290',
        '7280', '7270', '7260', '7250', '7240', '7230', '7220', '7210', '7200', '7190',
        '7180', '7170', '7160', '7150', '7140', '7130', '7120',
    ],
    # 蘇澳新→花蓮 (BH 單線，約 1 小時)
    'BH-SX-HL': [
        '7130', '7110', '7100', '7090', '7080', '7070', '7060', '7050', '7040', '7030', '7020', '7010', '7000',
    ],
}

# 反向路由
OD_ROUTES_STATIONS['YL-HL-TP'] = list(reversed(OD_ROUTES_STATIONS['YL-TP-HL']))
OD_ROUTES_STATIONS['YL-YL-TP'] = list(reversed(OD_ROUTES_STATIONS['YL-TP-YL']))
OD_ROUTES_STATIONS['YL-SA-TP'] = list(reversed(OD_ROUTES_STATIONS['YL-TP-SA']))
OD_ROUTES_STATIONS['BH-HL-SX'] = list(reversed(OD_ROUTES_STATIONS['BH-SX-HL']))

# 列車類型定義（影響停站和行駛時間）
TRAIN_TYPES = {
    '自強': {'stop_time': 30, 'speed_factor': 1.0, 'skip_minor_stations': True},
    '莒光': {'stop_time': 40, 'speed_factor': 0.85, 'skip_minor_stations': True},
    '區間': {'stop_time': 40, 'speed_factor': 0.7, 'skip_minor_stations': False},
    '區間快': {'stop_time': 35, 'speed_factor': 0.8, 'skip_minor_stations': True},
}

# 主要車站（自強號停靠）
MAJOR_STATIONS = {
    '1000', '0990', '0980',  # 臺北、松山、南港
    '7360',  # 瑞芳
    '7210',  # 礁溪
    '7190',  # 宜蘭
    '7160',  # 羅東
    '7130',  # 蘇澳新
    '7060',  # 和平
    '7030',  # 新城
    '7000',  # 花蓮
}

# 站間平均行駛時間（秒）
DEFAULT_SEGMENT_TIME = 180  # 3 分鐘
SEGMENT_TIMES = {
    # 長區間
    ('7330', '7320'): 300,  # 三貂嶺→牡丹
    ('7300', '7290'): 280,  # 貢寮→福隆
    ('7080', '7070'): 600,  # 武塔→漢本（北迴線長區間）
    ('7070', '7060'): 300,  # 漢本→和平
    ('7060', '7050'): 360,  # 和平→和仁
    ('7050', '7040'): 360,  # 和仁→崇德
}


def get_segment_time(from_station: str, to_station: str, train_type: str) -> int:
    """取得站間行駛時間"""
    base_time = SEGMENT_TIMES.get((from_station, to_station),
                 SEGMENT_TIMES.get((to_station, from_station), DEFAULT_SEGMENT_TIME))
    speed_factor = TRAIN_TYPES[train_type]['speed_factor']
    return int(base_time / speed_factor)


def should_stop(station_id: str, train_type: str) -> bool:
    """判斷列車是否在此站停靠"""
    if not TRAIN_TYPES[train_type]['skip_minor_stations']:
        return True
    return station_id in MAJOR_STATIONS


def generate_train_schedule(
    od_track_id: str,
    train_no: str,
    train_type: str,
    departure_time: str,
) -> Dict[str, Any]:
    """生成單一列車時刻表"""
    stations_list = OD_ROUTES_STATIONS[od_track_id]
    stop_time = TRAIN_TYPES[train_type]['stop_time']

    # 先找出所有停靠站的索引
    stop_indices = [i for i, sid in enumerate(stations_list) if should_stop(sid, train_type)]

    stations = []
    current_time = 0  # 從出發站開始計算（秒）

    for idx, stop_idx in enumerate(stop_indices):
        station_id = stations_list[stop_idx]

        arrival = current_time
        departure = current_time + stop_time

        stations.append({
            'station_id': station_id,
            'station_name': STATIONS.get(station_id, station_id),
            'arrival': arrival,
            'departure': departure,
        })

        # 計算到下一個停靠站的時間（累加所有區段，包含跳過的站）
        if idx < len(stop_indices) - 1:
            next_stop_idx = stop_indices[idx + 1]
            segment_time = 0
            for j in range(stop_idx, next_stop_idx):
                segment_time += get_segment_time(stations_list[j], stations_list[j + 1], train_type)
            current_time = departure + segment_time

    # 最後一站不需要停留
    if stations:
        stations[-1]['departure'] = stations[-1]['arrival']

    origin_station = stations[0]['station_id'] if stations else ''
    destination_station = stations[-1]['station_id'] if stations else ''
    total_travel_time = stations[-1]['arrival'] if stations else 0

    return {
        'departure_time': departure_time,
        'train_id': f"{od_track_id.split('-')[0]}-{train_no}",
        'train_no': train_no,
        'train_type': train_type,
        'origin_station': origin_station,
        'destination_station': destination_station,
        'od_track_id': od_track_id,
        'stations': stations,
        'total_travel_time': total_travel_time,
    }


def generate_schedule_for_track(track_id: str, direction: int) -> Dict[str, Any]:
    """生成軌道時刻表"""
    # 根據 track_id 和 direction 選擇 O-D 路由
    if track_id == 'YL':
        if direction == 0:
            # YL-0: 臺北方向（南下），混合各種目的地
            od_routes = ['YL-TP-HL', 'YL-TP-YL', 'YL-TP-SA']
        else:
            # YL-1: 花蓮方向（北上），混合各種起點
            od_routes = ['YL-HL-TP', 'YL-YL-TP', 'YL-SA-TP']
    elif track_id == 'BH':
        if direction == 0:
            od_routes = ['BH-SX-HL']  # 蘇澳新→花蓮
        else:
            od_routes = ['BH-HL-SX']  # 花蓮→蘇澳新
    else:
        return None

    departures = []

    # 生成整天的班次 (06:00 - 22:00)
    # YL 約每 30 分鐘一班，BH 約每 60 分鐘一班
    interval_minutes = 30 if track_id == 'YL' else 60
    train_counter = 1000

    current_time = datetime.strptime('06:00', '%H:%M')
    end_time = datetime.strptime('22:00', '%H:%M')

    train_types_cycle = ['自強', '區間', '區間快', '區間'] if track_id == 'YL' else ['自強', '區間']

    while current_time <= end_time:
        train_type = train_types_cycle[train_counter % len(train_types_cycle)]
        od_route = od_routes[train_counter % len(od_routes)]

        departure_str = current_time.strftime('%H:%M:%S')
        train_no = str(train_counter)

        schedule = generate_train_schedule(od_route, train_no, train_type, departure_str)
        departures.append(schedule)

        train_counter += 2  # 車次號遞增
        current_time += timedelta(minutes=interval_minutes)

    return {
        'track_id': f'{track_id}-{direction}',
        'route_id': track_id,
        'name': f'{track_id} 線時刻表',
        'departure_count': len(departures),
        'departures': departures,
    }


def save_schedule(schedule: Dict[str, Any]):
    """儲存時刻表"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{schedule['track_id']}.json")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

    print(f"儲存: {output_path} ({schedule['departure_count']} 班次)")


def main():
    print("=" * 60)
    print("生成 YL/BH 時刻表 (模擬模式)")
    print("=" * 60)

    for track_id in ['YL', 'BH']:
        for direction in [0, 1]:
            print(f"\n生成 {track_id}-{direction}...")
            schedule = generate_schedule_for_track(track_id, direction)
            if schedule:
                save_schedule(schedule)

    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
