#!/usr/bin/env python3
"""
分析 TDX 時刻表，統計所有車次的起迄站分佈
找出需要建立的 O-D 軌道清單
"""

import requests
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from dotenv import load_dotenv

# 載入 .env
load_dotenv()

# TDX API 設定
TDX_BASE_URL = "https://tdx.transportdata.tw/api/basic"
TDX_AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"

def get_access_token():
    """取得 TDX Access Token"""
    app_id = os.getenv('TDX_APP_ID')
    app_key = os.getenv('TDX_APP_KEY')

    if not app_id or not app_key:
        raise ValueError("請在 .env 中設定 TDX_APP_ID 和 TDX_APP_KEY")

    response = requests.post(
        TDX_AUTH_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": app_id,
            "client_secret": app_key
        }
    )
    return response.json()["access_token"]

def fetch_general_timetable(token):
    """取得定期時刻表"""
    url = f"{TDX_BASE_URL}/v3/Rail/TRA/GeneralTrainTimetable"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"$format": "JSON"}
    
    print("正在從 TDX 取得定期時刻表...")
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def analyze_od_distribution(timetable_data):
    """分析起迄站分佈"""
    
    trains = timetable_data.get("TrainTimetables", [])
    print(f"\n總車次數: {len(trains)}")
    
    # 統計起迄站
    od_counter = Counter()  # (起站, 迄站) 的次數
    origin_counter = Counter()  # 起站次數
    dest_counter = Counter()  # 迄站次數
    
    # 統計經過特定站的車次
    via_station_trains = defaultdict(list)  # 經過某站的車次清單
    
    # 重要節點站（可能的分岔點）
    key_stations = {
        "0920": "八堵",   # YL/KL 分岔
        "1040": "樹林",   # 常見起迄點
        "1000": "臺北",   # 主要起迄點
        "7330": "三貂嶺", # YL/PX 分岔
        "4080": "彰化",   # 山海線分岔
        "3360": "竹南",   # 山海線分岔
    }
    
    for train in trains:
        info = train.get("TrainInfo", {})
        train_no = info.get("TrainNo", "")
        
        origin_id = info.get("StartingStationID", "")
        origin_name = info.get("StartingStationName", {}).get("Zh_tw", "")
        dest_id = info.get("EndingStationID", "")
        dest_name = info.get("EndingStationName", {}).get("Zh_tw", "")
        
        if origin_id and dest_id:
            od_counter[(origin_id, origin_name, dest_id, dest_name)] += 1
            origin_counter[(origin_id, origin_name)] += 1
            dest_counter[(dest_id, dest_name)] += 1
        
        # 記錄經過的車站
        stop_times = train.get("StopTimes", [])
        for stop in stop_times:
            station_id = stop.get("StationID", "")
            if station_id in key_stations:
                via_station_trains[station_id].append(train_no)
    
    return {
        "od_counter": od_counter,
        "origin_counter": origin_counter,
        "dest_counter": dest_counter,
        "via_station_trains": via_station_trains,
        "key_stations": key_stations,
        "total_trains": len(trains)
    }

def print_report(analysis):
    """輸出分析報告"""
    
    print("\n" + "="*60)
    print("📊 TRA 車次起迄站分析報告")
    print("="*60)
    
    # Top 起站
    print("\n🚉 Top 20 起站：")
    for (station_id, name), count in analysis["origin_counter"].most_common(20):
        print(f"  {station_id} {name}: {count} 班次")
    
    # Top 迄站
    print("\n🏁 Top 20 迄站：")
    for (station_id, name), count in analysis["dest_counter"].most_common(20):
        print(f"  {station_id} {name}: {count} 班次")
    
    # Top O-D 組合
    print("\n🔀 Top 30 起迄組合 (O-D)：")
    for (o_id, o_name, d_id, d_name), count in analysis["od_counter"].most_common(30):
        print(f"  {o_name}({o_id}) → {d_name}({d_id}): {count} 班次")
    
    # 經過關鍵站的車次數
    print("\n📍 經過關鍵轉折站的車次數：")
    for station_id, name in analysis["key_stations"].items():
        train_count = len(analysis["via_station_trains"].get(station_id, []))
        print(f"  {station_id} {name}: {train_count} 班次經過")
    
    # 建議的 O-D 軌道
    print("\n" + "="*60)
    print("🛤️ 建議建立的 O-D 軌道（班次數 >= 5）：")
    print("="*60)
    
    suggested_od = []
    for (o_id, o_name, d_id, d_name), count in analysis["od_counter"].most_common():
        if count >= 5:
            suggested_od.append({
                "origin_id": o_id,
                "origin_name": o_name,
                "dest_id": d_id,
                "dest_name": d_name,
                "count": count
            })
            print(f"  {o_name} → {d_name}: {count} 班次")
    
    print(f"\n總共 {len(suggested_od)} 組 O-D 需要建立軌道")
    
    return suggested_od

def main():
    # 取得 Token
    token = get_access_token()
    
    # 取得時刻表
    timetable = fetch_general_timetable(token)
    
    if not timetable:
        print("無法取得時刻表")
        return
    
    # 分析
    analysis = analyze_od_distribution(timetable)
    
    # 輸出報告
    suggested_od = print_report(analysis)
    
    # 儲存結果
    output = {
        "generated_at": datetime.now().isoformat(),
        "total_trains": analysis["total_trains"],
        "suggested_od_tracks": suggested_od,
        "top_origins": [
            {"station_id": sid, "name": name, "count": count}
            for (sid, name), count in analysis["origin_counter"].most_common(50)
        ],
        "top_destinations": [
            {"station_id": sid, "name": name, "count": count}
            for (sid, name), count in analysis["dest_counter"].most_common(50)
        ]
    }
    
    with open("public/data/tra/od_analysis.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n✅ 分析結果已儲存到 public/data/tra/od_analysis.json")

if __name__ == "__main__":
    main()
