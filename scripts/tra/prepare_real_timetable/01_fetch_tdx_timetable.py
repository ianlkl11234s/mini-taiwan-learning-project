#!/usr/bin/env python3
"""
01_fetch_tdx_timetable.py - 下載 TDX 台鐵時刻表

功能：
1. 從 TDX API 取得最新 GeneralTrainTimetable（定期時刻表）
2. 儲存原始資料到 data/ 目錄

使用方式：
    source venv/bin/activate
    python scripts/tra/prepare_real_timetable/01_fetch_tdx_timetable.py

環境變數：
    TDX_APP_ID: TDX 應用程式 ID
    TDX_APP_KEY: TDX 應用程式金鑰

產出：
    public/data/tra/data/tdx_timetable_YYYYMMDD.json
"""

import json
import os
import requests
from datetime import datetime
from typing import Optional, List, Dict

# 載入 .env 環境變數
try:
    from dotenv import load_dotenv
    # 路徑設定
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except ImportError:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    print("提示: 安裝 python-dotenv 可自動載入 .env 檔案")
    print("  pip install python-dotenv")
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
OUTPUT_DIR = os.path.join(DATA_DIR, 'data')

# TDX API 設定
TDX_AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
# 使用 GeneralTrainTimetable (定期時刻表)，不會受當日變動影響
TDX_TIMETABLE_URL = "https://tdx.transportdata.tw/api/basic/v3/Rail/TRA/GeneralTrainTimetable"


def get_tdx_token() -> Optional[str]:
    """從 TDX 取得 access token"""
    app_id = os.environ.get('TDX_APP_ID')
    app_key = os.environ.get('TDX_APP_KEY')

    if not app_id or not app_key:
        print("錯誤: 請設定 TDX_APP_ID 和 TDX_APP_KEY 環境變數")
        print("  export TDX_APP_ID=your_app_id")
        print("  export TDX_APP_KEY=your_app_key")
        return None

    try:
        response = requests.post(
            TDX_AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": app_id,
                "client_secret": app_key,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"取得 TDX token 失敗: {e}")
        return None


def fetch_general_timetable(token: str) -> Optional[List[Dict]]:
    """從 TDX 取得定期時刻表"""
    try:
        print("  請求 TDX GeneralTrainTimetable...")
        response = requests.get(
            TDX_TIMETABLE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept-Encoding": "gzip, deflate"
            },
            params={
                "$format": "JSON"
            }
        )
        response.raise_for_status()
        data = response.json()

        # GeneralTrainTimetable 的回應結構
        timetables = data.get("TrainTimetables", [])
        return timetables
    except Exception as e:
        print(f"取得時刻表失敗: {e}")
        return None


def analyze_timetable(timetables: List[Dict]) -> Dict:
    """分析時刻表內容"""
    train_types = {}
    od_pairs = {}

    for train in timetables:
        train_info = train.get("TrainInfo", {})
        stops = train.get("StopTimes", [])

        # 統計車種
        train_type = train_info.get("TrainTypeName", {}).get("Zh_tw", "未知")
        train_types[train_type] = train_types.get(train_type, 0) + 1

        # 統計 O-D
        if stops:
            origin = stops[0].get("StationName", {}).get("Zh_tw", "未知")
            dest = stops[-1].get("StationName", {}).get("Zh_tw", "未知")
            od_key = f"{origin} → {dest}"
            od_pairs[od_key] = od_pairs.get(od_key, 0) + 1

    return {
        "total_trains": len(timetables),
        "train_types": train_types,
        "od_pair_count": len(od_pairs),
        "top_10_od": sorted(od_pairs.items(), key=lambda x: -x[1])[:10]
    }


def main():
    print("=" * 60)
    print("Phase 0.1: 下載 TDX 台鐵時刻表")
    print("=" * 60)

    # 確保輸出目錄存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 取得 token
    print("\n[1/3] 取得 TDX token...")
    token = get_tdx_token()
    if not token:
        return False
    print("  ✓ Token 取得成功")

    # 下載時刻表
    print("\n[2/3] 下載定期時刻表...")
    timetables = fetch_general_timetable(token)
    if not timetables:
        return False
    print(f"  ✓ 取得 {len(timetables)} 班列車")

    # 分析內容
    print("\n[3/3] 分析時刻表內容...")
    analysis = analyze_timetable(timetables)

    print(f"  總班次: {analysis['total_trains']}")
    print(f"  O-D 組合數: {analysis['od_pair_count']}")
    print("\n  車種分佈:")
    for train_type, count in sorted(analysis['train_types'].items(), key=lambda x: -x[1]):
        print(f"    {train_type}: {count} 班")
    print("\n  Top 10 O-D:")
    for od, count in analysis['top_10_od']:
        print(f"    {od}: {count} 班")

    # 儲存檔案
    today = datetime.now().strftime("%Y%m%d")
    output_file = os.path.join(OUTPUT_DIR, f"tdx_timetable_{today}.json")

    output_data = {
        "metadata": {
            "title": "TDX 台鐵定期時刻表",
            "source": "TDX API v3/Rail/TRA/GeneralTrainTimetable",
            "downloaded_at": datetime.now().isoformat(),
            "total_trains": len(timetables),
            "analysis": analysis
        },
        "timetables": timetables
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 儲存完成: {output_file}")
    print(f"  檔案大小: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")

    # 建立 latest 連結
    latest_file = os.path.join(OUTPUT_DIR, "tdx_timetable_latest.json")
    if os.path.exists(latest_file):
        os.remove(latest_file)
    # 使用複製而非符號連結，避免跨平台問題
    import shutil
    shutil.copy(output_file, latest_file)
    print(f"  ✓ 建立 latest 複本: {latest_file}")

    print("\n" + "=" * 60)
    print("下一步: python scripts/tra/prepare_real_timetable/02_build_station_mapping.py")
    print("=" * 60)

    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
