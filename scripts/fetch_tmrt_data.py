#!/usr/bin/env python3
"""
從 TDX API 下載台中捷運原始資料

下載以下資料：
- 車站資訊 (Station)
- 路線形狀 (Shape)
- 車站線序 (StationOfLine)
- 車站時刻表 (StationTimeTable)
- 站間行駛時間 (S2STravelTime)

Usage:
    python scripts/fetch_tmrt_data.py
"""

import os
import sys
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# TDX API 設定
TDX_AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TDX_API_BASE = "https://tdx.transportdata.tw/api/basic"

# 輸出目錄
OUTPUT_DIR = Path(__file__).parent.parent / "data-tmrt" / "raw"

# TMRT 系統代碼
RAIL_SYSTEM = "TMRT"


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


def fetch_tmrt_data():
    """下載台中捷運資料"""

    # 確保輸出目錄存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    client = TDXClient()

    print("\n=== 下載台中捷運 TDX 資料 ===\n")

    # 1. 車站資訊
    print("[1/5] 下載車站資訊...")
    stations = client.get(f"/v2/Rail/Metro/Station/{RAIL_SYSTEM}")
    with open(OUTPUT_DIR / "tmrt_stations.json", 'w', encoding='utf-8') as f:
        json.dump(stations, f, ensure_ascii=False, indent=2)
    print(f"      儲存 {len(stations)} 個車站")

    # 2. 路線形狀 (WKT)
    print("[2/5] 下載路線形狀...")
    shape = client.get(f"/v2/Rail/Metro/Shape/{RAIL_SYSTEM}")
    with open(OUTPUT_DIR / "tmrt_shape.json", 'w', encoding='utf-8') as f:
        json.dump(shape, f, ensure_ascii=False, indent=2)
    print(f"      儲存 {len(shape)} 條路線")

    # 3. 車站線序
    print("[3/5] 下載車站線序...")
    station_of_line = client.get(f"/v2/Rail/Metro/StationOfLine/{RAIL_SYSTEM}")
    with open(OUTPUT_DIR / "tmrt_station_of_line.json", 'w', encoding='utf-8') as f:
        json.dump(station_of_line, f, ensure_ascii=False, indent=2)
    print(f"      儲存 {len(station_of_line)} 條線路資料")

    # 4. 車站時刻表 (TMRT 可能沒有此 API)
    print("[4/5] 下載車站時刻表...")
    try:
        station_timetable = client.get(f"/v2/Rail/Metro/StationTimeTable/{RAIL_SYSTEM}")
        with open(OUTPUT_DIR / "tmrt_station_timetable.json", 'w', encoding='utf-8') as f:
            json.dump(station_timetable, f, ensure_ascii=False, indent=2)
        print(f"      儲存 {len(station_timetable)} 筆車站時刻表")
    except requests.exceptions.HTTPError as e:
        print(f"      ⚠️ 無法取得時刻表 API: {e}")
        print(f"      將使用固定班距生成時刻表")

    # 5. 站間行駛時間
    print("[5/5] 下載站間行駛時間...")
    try:
        s2s_travel_time = client.get(f"/v2/Rail/Metro/S2STravelTime/{RAIL_SYSTEM}")
        with open(OUTPUT_DIR / "tmrt_s2s_travel_time.json", 'w', encoding='utf-8') as f:
            json.dump(s2s_travel_time, f, ensure_ascii=False, indent=2)
        print(f"      儲存 {len(s2s_travel_time)} 筆站間時間")
    except requests.exceptions.HTTPError as e:
        print(f"      ⚠️ 無法取得站間時間 API: {e}")
        print(f"      將使用預設行駛時間")

    print("\n=== 下載完成 ===")
    print(f"資料儲存於: {OUTPUT_DIR}")
    print(f"  - tmrt_stations.json")
    print(f"  - tmrt_shape.json")
    print(f"  - tmrt_station_of_line.json")
    print(f"  - tmrt_station_timetable.json")
    print(f"  - tmrt_s2s_travel_time.json")

    # 顯示路線摘要
    print("\n路線摘要:")
    for line in station_of_line:
        line_id = line.get('LineID', line.get('LineNo', 'N/A'))
        line_name = line.get('LineName', {}).get('Zh_tw', 'N/A')
        stations_count = len(line.get('Stations', []))
        print(f"  {line_id} {line_name}: {stations_count} 站")


def main():
    try:
        fetch_tmrt_data()
    except Exception as e:
        print(f"\n錯誤: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
