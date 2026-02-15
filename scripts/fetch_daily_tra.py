#!/usr/bin/env python3
"""
下載指定日期的台鐵時刻表並轉換為專案格式

從 TDX DailyTrainTimetable API (v3) 下載指定日期的時刻表，
匹配 O-D 軌道，轉換為與 master_schedule.json 相同格式，
輸出到 public/data/tra/schedules_real/daily/{date}.json

Usage:
    python3 scripts/fetch_daily_tra.py                    # 今天
    python3 scripts/fetch_daily_tra.py --date 2026-02-15  # 指定日期
    python3 scripts/fetch_daily_tra.py --range 3          # 未來3天
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

import requests
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 路徑設定
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "public" / "data" / "tra"
TRACKS_OD_DIR = DATA_DIR / "tracks_od"
OUTPUT_DIR = DATA_DIR / "schedules_real" / "daily"

# TDX API 設定
TDX_AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TDX_API_BASE = "https://tdx.transportdata.tw/api/basic"

# ============================================================
# Station ID 對照表：TDX 新 ID → 軌道舊 ID
# ============================================================
STATION_ID_MAPPING = {
    '3250': '3240',  # 潭子
    '3260': '3243',  # 頭家厝
    '3270': '3245',  # 松竹
    '3280': '3247',  # 太原
    '3290': '3249',  # 精武
    '3340': '3330',  # 新烏日 → 烏日
    '3350': '3330',  # 成功
}

# ============================================================
# 車種代碼對照表
# ============================================================
TDX_TRAIN_TYPE_MAPPING = {
    '普悠瑪(普悠瑪)': 'PP',
    '太魯閣(太魯閣)': 'TZ',
    '自強(3000)(EMU3000 型電車)': 'TC',
    '自強(推拉式自強號且無自行車車廂)': 'TC-PP',
    '自強(推拉式自強號且有自行車車廂)': 'TC-PP',
    '自強(DMU3100 型柴聯)': 'TC-DMU',
    '自強(商務專開列車)': 'TC',
    '莒光(有身障座位)': 'CG',
    '莒光(無身障座位)': 'CG',
    '區間快': 'CK',
    '區間': 'LC',
    '區間(專開列車)': 'LC',
    '普快(專開列車)': 'LC',
}


class TDXClient:
    """TDX API 客戶端"""

    def __init__(self):
        self.app_id = os.getenv('TDX_APP_ID')
        self.app_key = os.getenv('TDX_APP_KEY')
        if not self.app_id or not self.app_key:
            raise ValueError("TDX API 金鑰未設定。請在 .env 中設定 TDX_APP_ID 和 TDX_APP_KEY")
        self._access_token = None

    def _get_token(self) -> str:
        if self._access_token:
            return self._access_token
        response = requests.post(
            TDX_AUTH_URL,
            headers={'content-type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'client_credentials',
                'client_id': self.app_id,
                'client_secret': self.app_key
            }
        )
        response.raise_for_status()
        self._access_token = response.json()['access_token']
        return self._access_token

    def get(self, endpoint: str) -> dict:
        url = f"{TDX_API_BASE}{endpoint}"
        headers = {
            'authorization': f'Bearer {self._get_token()}',
            'Accept-Encoding': 'gzip'
        }
        response = requests.get(url, headers=headers, params={'$format': 'JSON'})
        response.raise_for_status()
        return response.json()


def normalize_station_id(station_id: str) -> str:
    """將 TDX 新 ID 轉換為軌道使用的舊 ID"""
    return STATION_ID_MAPPING.get(station_id, station_id)


def get_train_type_code(tdx_train_type: str) -> str:
    """從 TDX 車種名稱取得車種代碼"""
    return TDX_TRAIN_TYPE_MAPPING.get(tdx_train_type, 'OTHER')


def time_to_seconds(time_str: str) -> int:
    """將 HH:MM 或 HH:MM:SS 轉換為當日秒數"""
    try:
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2]) if len(parts) > 2 else 0
        return hours * 3600 + minutes * 60 + seconds
    except:
        return 0


def load_od_station_progress() -> Dict[str, Dict[str, float]]:
    """載入 O-D 軌道的車站 progress"""
    file_path = TRACKS_OD_DIR / 'od_station_progress.json'
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_track_index(od_progress: Dict) -> Dict[Tuple[str, str], List[str]]:
    """建立 (起站, 迄站) → 軌道 ID 的索引"""
    index = defaultdict(list)

    for track_id, stations in od_progress.items():
        if len(stations) < 2:
            continue

        sorted_stations = sorted(stations.items(), key=lambda x: x[1])
        origin = sorted_stations[0][0]
        destination = sorted_stations[-1][0]
        index[(origin, destination)].append(track_id)

    return dict(index)


def find_matching_track(
    origin_id: str,
    dest_id: str,
    stop_ids: List[str],
    track_index: Dict,
    od_progress: Dict
) -> Optional[str]:
    """找到最匹配的軌道 ID（以停靠站覆蓋率為主要依據）"""
    origin_normalized = normalize_station_id(origin_id)
    dest_normalized = normalize_station_id(dest_id)
    stops_normalized = [normalize_station_id(s) for s in stop_ids]
    stops_set = set(stops_normalized)

    def score_track(track_id: str) -> Tuple[float, float, int, str]:
        track_stations = od_progress[track_id]
        track_set = set(track_stations.keys())
        coverage = len(stops_set & track_set)
        coverage_ratio = coverage / len(stops_normalized) if stops_normalized else 0

        prev_prog = -1.0
        forward = 0
        backward = 0
        for sid in stops_normalized:
            if sid in track_stations:
                prog = track_stations[sid]
                if prev_prog >= 0:
                    if prog > prev_prog:
                        forward += 1
                    elif prog < prev_prog:
                        backward += 1
                prev_prog = prog
        total_pairs = forward + backward
        backward_ratio = backward / total_pairs if total_pairs > 0 else 0

        if track_id.startswith('OD-'):
            type_priority = 0
        elif track_id.startswith('SP-'):
            type_priority = 1
        elif track_id.startswith('BB-'):
            type_priority = 2
        else:
            type_priority = 3

        return (backward_ratio, -coverage_ratio, type_priority, track_id)

    # 精確匹配
    key = (origin_normalized, dest_normalized)
    if key in track_index:
        candidates = track_index[key]
        best = min(candidates, key=score_track)
        return best

    # 模糊匹配
    candidates = []
    for track_id, stations in od_progress.items():
        if origin_normalized in stations and dest_normalized in stations:
            origin_prog = stations[origin_normalized]
            dest_prog = stations[dest_normalized]
            if origin_prog < dest_prog:
                candidates.append(track_id)

    if candidates:
        best = min(candidates, key=score_track)
        return best

    return None


def convert_train(
    train: Dict,
    track_index: Dict,
    od_progress: Dict
) -> Optional[Dict]:
    """將 TDX DailyTrainTimetable 列車資料轉換為 Mini Taiwan 格式"""
    # v3 DailyTrainTimetable 用 TrainInfo（非 DailyTrainInfo）
    train_info = train.get('TrainInfo', train.get('DailyTrainInfo', {}))
    stops = train.get('StopTimes', [])

    if not stops or len(stops) < 2:
        return None

    train_no = train_info.get('TrainNo', '')
    train_type_name = train_info.get('TrainTypeName', {}).get('Zh_tw', '區間')
    train_type_code = get_train_type_code(train_type_name)

    origin_id = stops[0]['StationID']
    dest_id = stops[-1]['StationID']
    origin_name = stops[0].get('StationName', {}).get('Zh_tw', '')
    dest_name = stops[-1].get('StationName', {}).get('Zh_tw', '')

    stop_ids = [s['StationID'] for s in stops]

    # 找對應軌道
    track_id = find_matching_track(origin_id, dest_id, stop_ids, track_index, od_progress)
    if not track_id:
        return None

    # 取得首站發車時間
    departure_time = stops[0].get('DepartureTime', '00:00')
    if len(departure_time.split(':')) == 2:
        departure_time += ':00'
    first_departure = time_to_seconds(departure_time)

    # 取得軌道上的車站集合
    track_station_set = set(od_progress.get(track_id, {}).keys())

    # 轉換停靠站
    converted_stations = []
    for i, stop in enumerate(stops):
        sid = stop['StationID']
        normalized_sid = normalize_station_id(sid)

        arr_time = stop.get('ArrivalTime', departure_time)
        dep_time = stop.get('DepartureTime', arr_time)

        if len(arr_time.split(':')) == 2:
            arr_time += ':00'
        if len(dep_time.split(':')) == 2:
            dep_time += ':00'

        arrival_sec = time_to_seconds(arr_time) - first_departure
        departure_sec = time_to_seconds(dep_time) - first_departure

        # 處理跨日
        if arrival_sec < 0:
            arrival_sec += 86400
        if departure_sec < 0:
            departure_sec += 86400

        # 首站：強制 arrival = 0, departure = 0
        if i == 0:
            arrival_sec = 0
            departure_sec = 0

        # 跳過不在軌道 station_progress 中的站
        if normalized_sid not in track_station_set:
            continue

        converted_stations.append({
            'station_id': normalized_sid,
            'arrival': arrival_sec,
            'departure': departure_sec
        })

    # 去除重複站（如 3350→3330 映射後與原本的 3330 重複）
    seen_ids = set()
    deduped_stations = []
    for st in converted_stations:
        if st['station_id'] not in seen_ids:
            seen_ids.add(st['station_id'])
            deduped_stations.append(st)
    converted_stations = deduped_stations

    if len(converted_stations) < 2:
        return None

    total_time = converted_stations[-1]['arrival']

    return {
        'train_id': f"{train_type_code}-{train_no}",
        'train_no': train_no,
        'train_type': train_type_name,
        'train_type_code': train_type_code,
        'departure_time': departure_time,
        'od_track_id': track_id,
        'origin_station': origin_name,
        'destination_station': dest_name,
        'total_travel_time': total_time,
        'stations': converted_stations
    }


def fetch_and_convert(client: TDXClient, date: str, track_index: Dict, od_progress: Dict):
    """下載並轉換指定日期的台鐵時刻表"""

    print(f"\n--- {date} ---")

    # TRA 使用 v3 API
    endpoint = f"/v3/Rail/TRA/DailyTrainTimetable/TrainDate/{date}"
    print(f"  下載: {endpoint}")
    response_data = client.get(endpoint)

    # v3 回傳格式：{ "TrainTimetables": [...] }
    timetable_data = response_data.get('TrainTimetables', response_data)
    if isinstance(timetable_data, dict):
        timetable_data = timetable_data.get('TrainTimetables', [])
    print(f"  取得 {len(timetable_data)} 班次")

    # 轉換
    converted = []
    failed = []
    for train in timetable_data:
        result = convert_train(train, track_index, od_progress)
        if result:
            converted.append(result)
        else:
            train_info = train.get('TrainInfo', train.get('DailyTrainInfo', {}))
            stops = train.get('StopTimes', [])
            failed.append({
                'train_no': train_info.get('TrainNo', ''),
                'origin': stops[0].get('StationName', {}).get('Zh_tw', '') if stops else '',
                'dest': stops[-1].get('StationName', {}).get('Zh_tw', '') if stops else '',
            })

    # 組裝輸出（與 master_schedule.json 相同格式）
    output = {
        'metadata': {
            'title': f'TRA 每日時刻表 {date}',
            'date': date,
            'total_trains': len(converted),
            'failed': len(failed),
            'generated_at': datetime.now().isoformat(),
            'source': 'TDX DailyTrainTimetable v3',
        },
        'schedules': converted
    }

    # 輸出
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{date}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  成功: {len(converted)} 班")
    print(f"  失敗: {len(failed)} 班")
    if failed:
        for f_item in failed[:5]:
            print(f"    - {f_item['train_no']}: {f_item['origin']} → {f_item['dest']}")
        if len(failed) > 5:
            print(f"    ... 及其他 {len(failed) - 5} 班")
    print(f"  輸出: {output_path}")

    # 按車種統計
    type_counts = defaultdict(int)
    for t in converted:
        type_counts[t['train_type_code']] += 1
    type_str = ', '.join(f"{k}:{v}" for k, v in sorted(type_counts.items(), key=lambda x: -x[1]))
    print(f"  車種: {type_str}")

    return output['metadata']


def update_index():
    """掃描 daily/ 目錄，產生 index.json 供前端讀取可用日期"""
    if not OUTPUT_DIR.exists():
        return

    dates = sorted([
        f.stem for f in OUTPUT_DIR.glob("*.json")
        if f.stem != "index" and len(f.stem) == 10  # YYYY-MM-DD
    ])

    if not dates:
        return

    index_path = OUTPUT_DIR / "index.json"
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump({"dates": dates}, f, ensure_ascii=False)

    print(f"\n  index.json: {len(dates)} 個日期 ({dates[0]} ~ {dates[-1]})")


def main():
    parser = argparse.ArgumentParser(description='下載台鐵每日時刻表')
    parser.add_argument(
        '--date', type=str, action='append',
        help='指定日期 (YYYY-MM-DD)，可多次指定。預設為今日'
    )
    parser.add_argument(
        '--range', type=int, metavar='DAYS',
        help='下載從今天起未來 N 天的時刻表（含今天）'
    )
    args = parser.parse_args()

    # 決定日期清單
    dates = []
    if args.range:
        today = datetime.now()
        for i in range(args.range):
            dates.append((today + timedelta(days=i)).strftime('%Y-%m-%d'))
    elif args.date:
        dates = args.date
    else:
        dates = [datetime.now().strftime('%Y-%m-%d')]

    print(f"=== 下載台鐵每日時刻表 ===")
    print(f"日期: {', '.join(dates)}")

    # 載入 O-D 軌道資料（只載入一次）
    print("\n載入 O-D 軌道資料...")
    od_progress = load_od_station_progress()
    track_index = build_track_index(od_progress)
    print(f"  軌道: {len(od_progress)} 條, 索引: {len(track_index)} 組 O-D 對")

    client = TDXClient()

    results = []
    for date in dates:
        try:
            meta = fetch_and_convert(client, date, track_index, od_progress)
            results.append(meta)
        except Exception as e:
            print(f"  錯誤: {e}")

    # 產生 index.json
    update_index()

    print(f"\n=== 完成 ===")
    print(f"成功: {len(results)}/{len(dates)}")


if __name__ == '__main__':
    main()
