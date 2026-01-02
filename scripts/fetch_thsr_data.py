#!/usr/bin/env python3
"""
從 TDX API 下載台灣高鐵原始資料

下載以下資料：
- 車站資訊 (Station)
- 路線形狀 (Shape)
- 車站線序 (StationOfLine)
- 每日時刻表 (DailyTimetable)

Usage:
    python scripts/fetch_thsr_data.py
    python scripts/fetch_thsr_data.py --date 2026-01-02
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# TDX API 設定
TDX_AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TDX_API_BASE = "https://tdx.transportdata.tw/api/basic"

# 輸出目錄
OUTPUT_DIR = Path(__file__).parent.parent / "data-thsr" / "raw"


class TDXClient:
    """TDX API 客戶端"""

    def __init__(self):
        self.app_id = os.getenv('TDX_APP_ID')
        self.app_key = os.getenv('TDX_APP_KEY')

        if not self.app_id or not self.app_key:
            raise ValueError(
                "TDX API 金鑰未設定。請在 .env 檔案中設定 TDX_APP_ID 和 TDX_APP_KEY"
            )

        self._access_token = None

    def _get_token(self) -> str:
        """取得 Access Token"""
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

    def get(self, endpoint: str, params: dict = None) -> dict:
        """發送 GET 請求"""
        url = f"{TDX_API_BASE}{endpoint}"
        headers = {
            'authorization': f'Bearer {self._get_token()}',
            'Accept-Encoding': 'gzip'
        }

        request_params = {'$format': 'JSON'}
        if params:
            request_params.update(params)

        print(f"  下載: {endpoint}")
        response = requests.get(url, headers=headers, params=request_params)
        response.raise_for_status()

        return response.json()


def fetch_thsr_data(date: str = None):
    """下載高鐵資料"""

    # 確保輸出目錄存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    client = TDXClient()

    print("\n=== 下載台灣高鐵 TDX 資料 ===\n")

    # 1. 車站資訊
    print("[1/4] 下載車站資訊...")
    stations = client.get("/v2/Rail/THSR/Station")
    with open(OUTPUT_DIR / "thsr_stations.json", 'w', encoding='utf-8') as f:
        json.dump(stations, f, ensure_ascii=False, indent=2)
    print(f"      儲存 {len(stations)} 個車站")

    # 2. 路線形狀
    print("[2/4] 下載路線形狀...")
    shape = client.get("/v2/Rail/THSR/Shape")
    with open(OUTPUT_DIR / "thsr_shape.json", 'w', encoding='utf-8') as f:
        json.dump(shape, f, ensure_ascii=False, indent=2)
    print(f"      儲存 {len(shape)} 條路線")

    # 3. 車站線序
    print("[3/4] 下載車站線序...")
    station_of_line = client.get("/v2/Rail/THSR/StationOfLine")
    with open(OUTPUT_DIR / "thsr_station_of_line.json", 'w', encoding='utf-8') as f:
        json.dump(station_of_line, f, ensure_ascii=False, indent=2)
    print(f"      儲存 {len(station_of_line)} 條線路資料")

    # 4. 每日時刻表
    print("[4/4] 下載每日時刻表...")
    if date:
        endpoint = f"/v2/Rail/THSR/DailyTimetable/TrainDate/{date}"
    else:
        endpoint = "/v2/Rail/THSR/DailyTimetable/Today"

    timetable = client.get(endpoint)

    # 決定檔名
    if date:
        filename = f"thsr_timetable_{date}.json"
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"thsr_timetable_{today}.json"

    with open(OUTPUT_DIR / filename, 'w', encoding='utf-8') as f:
        json.dump(timetable, f, ensure_ascii=False, indent=2)
    print(f"      儲存 {len(timetable)} 班次")

    # 同時儲存一份通用名稱的檔案
    with open(OUTPUT_DIR / "thsr_timetable.json", 'w', encoding='utf-8') as f:
        json.dump(timetable, f, ensure_ascii=False, indent=2)

    print("\n=== 下載完成 ===")
    print(f"資料儲存於: {OUTPUT_DIR}")
    print(f"  - thsr_stations.json")
    print(f"  - thsr_shape.json")
    print(f"  - thsr_station_of_line.json")
    print(f"  - {filename}")
    print(f"  - thsr_timetable.json (通用)")


def main():
    parser = argparse.ArgumentParser(description='下載台灣高鐵 TDX 資料')
    parser.add_argument(
        '--date',
        type=str,
        help='指定日期 (格式: YYYY-MM-DD)，預設為今日'
    )

    args = parser.parse_args()

    try:
        fetch_thsr_data(args.date)
    except Exception as e:
        print(f"\n錯誤: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
