#!/usr/bin/env python3
"""
00_fetch_s2s_travel_time.py - 下載 TDX S2STravelTime API 資料

取得精確的站間運行時間與停站時間，用於產生更準確的時刻表。

輸出：
- raw_data/trtc_s2s_travel_time.json: 站間運行時間資料

API 端點：
- GET /v2/Rail/Metro/S2STravelTime/TRTC

資料結構：
{
  "RouteID": "R-1",
  "TravelTimes": [
    {
      "FromStationID": "R28",
      "ToStationID": "R27",
      "RunTime": 175,    // 運行秒數
      "StopTime": 0      // 停站秒數
    }
  ]
}
"""

import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
RAW_DATA_DIR = SCRIPT_DIR.parent / "raw_data"

# TDX API 設定
TDX_APP_ID = os.getenv("TDX_APP_ID")
TDX_APP_KEY = os.getenv("TDX_APP_KEY")
TDX_AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TDX_API_BASE = "https://tdx.transportdata.tw/api/basic/v2"


def get_access_token() -> str:
    """取得 TDX Access Token"""
    if not TDX_APP_ID or not TDX_APP_KEY:
        raise ValueError("請設定 TDX_APP_ID 和 TDX_APP_KEY 環境變數")

    auth_data = {
        "grant_type": "client_credentials",
        "client_id": TDX_APP_ID,
        "client_secret": TDX_APP_KEY
    }

    response = requests.post(TDX_AUTH_URL, data=auth_data)
    response.raise_for_status()

    return response.json()["access_token"]


def fetch_s2s_travel_time(access_token: str) -> list:
    """下載站間運行時間資料"""
    url = f"{TDX_API_BASE}/Rail/Metro/S2STravelTime/TRTC"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept-Encoding": "gzip"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def filter_red_line(data: list) -> list:
    """過濾出紅線資料"""
    return [item for item in data if item.get("LineID") == "R"]


def save_json(filepath: Path, data) -> None:
    """儲存 JSON 檔案"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 已儲存: {filepath}")


def analyze_travel_times(data: list) -> None:
    """分析並顯示站間時間統計"""
    print("\n" + "=" * 60)
    print("站間運行時間分析")
    print("=" * 60)

    for route in data:
        route_id = route.get("RouteID", "Unknown")
        travel_times = route.get("TravelTimes", [])

        if not travel_times:
            continue

        run_times = [t["RunTime"] for t in travel_times]
        stop_times = [t["StopTime"] for t in travel_times if t["StopTime"] > 0]

        print(f"\n【{route_id}】")
        print(f"  站數: {len(travel_times) + 1}")
        print(f"  運行時間: {min(run_times)}-{max(run_times)} 秒 (平均 {sum(run_times)/len(run_times):.0f} 秒)")
        if stop_times:
            print(f"  停站時間: {min(stop_times)}-{max(stop_times)} 秒 (平均 {sum(stop_times)/len(stop_times):.0f} 秒)")

        # 計算總行程時間
        total_run = sum(run_times)
        total_stop = sum(t["StopTime"] for t in travel_times)
        total = total_run + total_stop
        print(f"  總行程: {total} 秒 ({total/60:.1f} 分鐘)")

        # 顯示最長和最短區間
        max_segment = max(travel_times, key=lambda t: t["RunTime"])
        min_segment = min(travel_times, key=lambda t: t["RunTime"])
        print(f"  最長區間: {max_segment['FromStationID']}→{max_segment['ToStationID']} ({max_segment['RunTime']}秒)")
        print(f"  最短區間: {min_segment['FromStationID']}→{min_segment['ToStationID']} ({min_segment['RunTime']}秒)")


def main():
    """主程式"""
    print("=" * 60)
    print("00_fetch_s2s_travel_time.py - 下載站間運行時間")
    print("=" * 60)

    # 取得 Access Token
    print("\n取得 TDX Access Token...")
    try:
        access_token = get_access_token()
        print("  ✓ 認證成功")
    except Exception as e:
        print(f"  ✗ 認證失敗: {e}")
        return

    # 下載資料
    print("\n下載 S2STravelTime API 資料...")
    try:
        all_data = fetch_s2s_travel_time(access_token)
        print(f"  ✓ 取得 {len(all_data)} 筆資料")
    except Exception as e:
        print(f"  ✗ 下載失敗: {e}")
        return

    # 過濾紅線
    red_line_data = filter_red_line(all_data)
    print(f"  ✓ 紅線資料: {len(red_line_data)} 筆")

    # 儲存原始資料 (全部)
    save_json(RAW_DATA_DIR / "trtc_s2s_travel_time_all.json", all_data)

    # 儲存紅線資料
    save_json(RAW_DATA_DIR / "trtc_s2s_travel_time.json", red_line_data)

    # 分析資料
    analyze_travel_times(red_line_data)

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
