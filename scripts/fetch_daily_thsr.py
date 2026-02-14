#!/usr/bin/env python3
"""
下載指定日期的高鐵時刻表並轉換為專案格式

從 TDX DailyTimetable API 下載指定日期的時刻表，
轉換為與 thsr_schedules.json 相同格式，
輸出到 public/data/thsr/schedules/daily/{date}.json

Usage:
    python3 scripts/fetch_daily_thsr.py                    # 今天
    python3 scripts/fetch_daily_thsr.py --date 2026-02-14  # 指定日期
    python3 scripts/fetch_daily_thsr.py --date 2026-02-15 --date 2026-02-16  # 多天
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 路徑設定
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "public" / "data" / "thsr" / "schedules" / "daily"

# TDX API 設定
TDX_AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TDX_API_BASE = "https://tdx.transportdata.tw/api/basic"

# 高鐵車站線序（南港→左營）
SOUTHBOUND_STATIONS = [
    "0990", "1000", "1010", "1020", "1030",
    "1035", "1040", "1043", "1047", "1050", "1060", "1070"
]
NORTHBOUND_STATIONS = list(reversed(SOUTHBOUND_STATIONS))


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


def time_to_seconds(time_str: str) -> int:
    """將 HH:MM 或 HH:MM:SS 轉換為當日秒數"""
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2]) if len(parts) > 2 else 0
    return hours * 3600 + minutes * 60 + seconds


def convert_daily_timetable(timetable_data: list, date: str) -> dict:
    """將 TDX DailyTimetable 轉換為專案格式"""

    departures_0 = []  # 南下
    departures_1 = []  # 北上
    skipped = []

    for train in timetable_data:
        info = train.get('DailyTrainInfo', {})
        stop_times = train.get('StopTimes', [])
        direction = info.get('Direction')
        train_no = info.get('TrainNo', '')

        if not stop_times:
            skipped.append({'train_no': train_no, 'reason': '無停靠站資料'})
            continue

        # 取得發車時間
        first_stop = stop_times[0]
        departure_time = first_stop['DepartureTime']
        if len(departure_time) == 5:  # "HH:MM" → "HH:MM:00"
            departure_time += ":00"
        base_seconds = time_to_seconds(first_stop['DepartureTime'])

        # 轉換各站時間為相對秒數
        stations = []
        for stop in stop_times:
            arrival_seconds = time_to_seconds(stop['ArrivalTime']) - base_seconds
            departure_seconds = time_to_seconds(stop['DepartureTime']) - base_seconds

            # 處理跨日
            if arrival_seconds < 0:
                arrival_seconds += 86400
            if departure_seconds < 0:
                departure_seconds += 86400

            stations.append({
                "station_id": stop['StationID'],
                "arrival": arrival_seconds,
                "departure": departure_seconds
            })

        total_travel_time = stations[-1]['arrival'] if stations else 0

        departure = {
            "departure_time": departure_time,
            "train_id": f"THSR-{train_no}",
            "stations": stations,
            "total_travel_time": total_travel_time
        }

        if direction == 0:
            departures_0.append(departure)
        elif direction == 1:
            departures_1.append(departure)
        else:
            skipped.append({'train_no': train_no, 'reason': f'未知方向 {direction}'})

    # 按發車時間排序
    departures_0.sort(key=lambda d: d['departure_time'])
    departures_1.sort(key=lambda d: d['departure_time'])

    schedules = {
        "THSR-1-0": {
            "track_id": "THSR-1-0",
            "route_id": "THSR",
            "name": "台灣高鐵 南下",
            "origin": "南港",
            "destination": "左營",
            "stations": SOUTHBOUND_STATIONS,
            "travel_time_minutes": 105,
            "dwell_time_seconds": 120,
            "is_weekday": True,  # 保持相容，實際由日期決定
            "departure_count": len(departures_0),
            "departures": departures_0
        },
        "THSR-1-1": {
            "track_id": "THSR-1-1",
            "route_id": "THSR",
            "name": "台灣高鐵 北上",
            "origin": "左營",
            "destination": "南港",
            "stations": NORTHBOUND_STATIONS,
            "travel_time_minutes": 105,
            "dwell_time_seconds": 120,
            "is_weekday": True,
            "departure_count": len(departures_1),
            "departures": departures_1
        },
        "_metadata": {
            "date": date,
            "total_trains": len(departures_0) + len(departures_1),
            "southbound": len(departures_0),
            "northbound": len(departures_1),
            "skipped": len(skipped),
            "generated_at": datetime.now().isoformat(),
            "source": "TDX DailyTimetable"
        }
    }

    return schedules, skipped


def fetch_and_convert(client: TDXClient, date: str):
    """下載並轉換指定日期的時刻表"""

    print(f"\n--- {date} ---")

    # 下載
    endpoint = f"/v2/Rail/THSR/DailyTimetable/TrainDate/{date}"
    print(f"  下載: {endpoint}")
    timetable_data = client.get(endpoint)
    print(f"  取得 {len(timetable_data)} 班次")

    # 轉換
    schedules, skipped = convert_daily_timetable(timetable_data, date)
    meta = schedules['_metadata']

    # 輸出
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{date}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schedules, f, ensure_ascii=False, indent=2)

    print(f"  南下: {meta['southbound']} 班")
    print(f"  北上: {meta['northbound']} 班")
    print(f"  總計: {meta['total_trains']} 班")

    if skipped:
        print(f"  跳過: {meta['skipped']} 班")
        for s in skipped:
            print(f"    - {s['train_no']}: {s['reason']}")

    print(f"  輸出: {output_path}")
    return meta


def main():
    parser = argparse.ArgumentParser(description='下載高鐵每日時刻表')
    parser.add_argument(
        '--date', type=str, action='append',
        help='指定日期 (YYYY-MM-DD)，可多次指定。預設為今日'
    )
    parser.add_argument(
        '--range', type=int, metavar='DAYS',
        help='下載從今天起未來 N 天的時刻表（含今天）。TDX 不提供過去的每日時刻表。'
    )
    args = parser.parse_args()

    # 決定日期清單（TDX 只提供今天及未來的 DailyTimetable）
    dates = []
    if args.range:
        today = datetime.now()
        for i in range(args.range):
            dates.append((today + timedelta(days=i)).strftime('%Y-%m-%d'))
    elif args.date:
        dates = args.date
    else:
        dates = [datetime.now().strftime('%Y-%m-%d')]

    print(f"=== 下載高鐵每日時刻表 ===")
    print(f"日期: {', '.join(dates)}")

    client = TDXClient()

    results = []
    for date in dates:
        try:
            meta = fetch_and_convert(client, date)
            results.append(meta)
        except Exception as e:
            print(f"  錯誤: {e}")

    # 產生 index.json（掃描 daily/ 目錄所有已下載的日期）
    update_index()

    print(f"\n=== 完成 ===")
    print(f"成功: {len(results)}/{len(dates)}")


def update_index():
    """掃描 daily/ 目錄，產生 index.json 供前端讀取可用日期"""
    if not OUTPUT_DIR.exists():
        return

    dates = sorted([
        f.stem for f in OUTPUT_DIR.glob("*.json")
        if f.stem != "index" and len(f.stem) == 10  # YYYY-MM-DD
    ])

    index_path = OUTPUT_DIR / "index.json"
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump({"dates": dates}, f, ensure_ascii=False)

    print(f"\n  index.json: {len(dates)} 個日期 ({dates[0]} ~ {dates[-1]})")


if __name__ == '__main__':
    main()
