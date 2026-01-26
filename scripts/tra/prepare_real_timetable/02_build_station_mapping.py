#!/usr/bin/env python3
"""
02_build_station_mapping.py - 建立車站 ID ↔ 名稱對照表

功能：
1. 從 TDX 時刻表提取所有車站資訊
2. 建立 station_id → station_name 對照表
3. 統計各車站的列車經過次數

使用方式：
    python scripts/tra/prepare_real_timetable/02_build_station_mapping.py

輸入：
    public/data/tra/data/tdx_timetable_latest.json

產出：
    public/data/tra/data/station_mapping.json
"""

import json
import os
from typing import Dict, List, Set
from collections import defaultdict

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
INPUT_DIR = os.path.join(DATA_DIR, 'data')
OUTPUT_DIR = INPUT_DIR


def load_timetable() -> List[Dict]:
    """載入 TDX 時刻表"""
    input_file = os.path.join(INPUT_DIR, "tdx_timetable_latest.json")

    if not os.path.exists(input_file):
        print(f"錯誤: 找不到時刻表檔案: {input_file}")
        print("請先執行 01_fetch_tdx_timetable.py")
        return []

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get("timetables", [])


def extract_stations(timetables: List[Dict]) -> Dict[str, Dict]:
    """從時刻表提取所有車站"""
    stations = {}
    station_train_count = defaultdict(int)
    station_as_origin = defaultdict(int)
    station_as_dest = defaultdict(int)

    for train in timetables:
        stops = train.get("StopTimes", [])

        for i, stop in enumerate(stops):
            station_id = stop.get("StationID", "")
            station_name = stop.get("StationName", {}).get("Zh_tw", "")

            if station_id and station_name:
                if station_id not in stations:
                    stations[station_id] = {
                        "id": station_id,
                        "name": station_name,
                        "name_en": stop.get("StationName", {}).get("En", ""),
                    }

                station_train_count[station_id] += 1

                # 統計作為起站/迄站次數
                if i == 0:
                    station_as_origin[station_id] += 1
                if i == len(stops) - 1:
                    station_as_dest[station_id] += 1

    # 加入統計資訊
    for station_id, info in stations.items():
        info["train_count"] = station_train_count[station_id]
        info["as_origin"] = station_as_origin[station_id]
        info["as_dest"] = station_as_dest[station_id]

    return stations


def categorize_stations(stations: Dict[str, Dict]) -> Dict[str, List[str]]:
    """根據 station_id 範圍分類車站"""
    categories = {
        "western_north": [],      # 0900-1190: 基隆-新竹
        "western_central": [],    # 1200-1350: 竹南-苗栗附近
        "mountain_line": [],      # 3300-3400: 山線
        "coast_line": [],         # 2100-2260: 海線
        "western_south": [],      # 3400-4400: 彰化-高雄
        "pingtung_line": [],      # 5000-5200: 屏東線
        "south_link": [],         # 5200-6000: 南迴線
        "yilan_line": [],         # 7200-7400: 宜蘭線
        "beihui_line": [],        # 7000-7200: 北迴線
        "taitung_line": [],       # 6000-7000: 臺東線
        "neiwan_liujia": [],      # 1190-1205: 內灣線、六家線
        "shalun": [],             # 4260-4280: 沙崙線
        "jiji": [],               # 3420-3440: 集集線
        "pingxi": [],             # 7340-7360: 平溪線
        "shenao": [],             # 7360-7370: 深澳線
        "other": [],              # 其他
    }

    for station_id, info in stations.items():
        try:
            sid = int(station_id)
        except ValueError:
            categories["other"].append(station_id)
            continue

        if 900 <= sid < 1200:
            categories["western_north"].append(station_id)
        elif 1200 <= sid < 1360:
            categories["western_central"].append(station_id)
        elif 2100 <= sid < 2270:
            categories["coast_line"].append(station_id)
        elif 3300 <= sid < 3400:
            categories["mountain_line"].append(station_id)
        elif 3400 <= sid < 4400:
            categories["western_south"].append(station_id)
        elif 4260 <= sid < 4280:
            categories["shalun"].append(station_id)
        elif 5000 <= sid < 5200:
            categories["pingtung_line"].append(station_id)
        elif 5200 <= sid < 6000:
            categories["south_link"].append(station_id)
        elif 6000 <= sid < 7000:
            categories["taitung_line"].append(station_id)
        elif 7000 <= sid < 7200:
            categories["beihui_line"].append(station_id)
        elif 7200 <= sid < 7400:
            categories["yilan_line"].append(station_id)
        elif 7340 <= sid < 7360:
            categories["pingxi"].append(station_id)
        elif 1190 <= sid < 1210:
            categories["neiwan_liujia"].append(station_id)
        elif 3420 <= sid < 3440:
            categories["jiji"].append(station_id)
        else:
            categories["other"].append(station_id)

    # 排序各類別
    for cat in categories:
        categories[cat].sort(key=lambda x: int(x) if x.isdigit() else 0)

    return categories


def main():
    print("=" * 60)
    print("Phase 0.2: 建立車站對照表")
    print("=" * 60)

    # 載入時刻表
    print("\n[1/3] 載入時刻表...")
    timetables = load_timetable()
    if not timetables:
        return False
    print(f"  ✓ 載入 {len(timetables)} 班列車")

    # 提取車站
    print("\n[2/3] 提取車站資訊...")
    stations = extract_stations(timetables)
    print(f"  ✓ 發現 {len(stations)} 個車站")

    # 分類車站
    categories = categorize_stations(stations)
    print("\n  各線車站數:")
    category_names = {
        "western_north": "西部幹線北段 (基隆-新竹)",
        "western_central": "西部幹線中段 (竹南-苗栗)",
        "mountain_line": "山線",
        "coast_line": "海線",
        "western_south": "西部幹線南段 (彰化-高雄)",
        "pingtung_line": "屏東線",
        "south_link": "南迴線",
        "yilan_line": "宜蘭線",
        "beihui_line": "北迴線",
        "taitung_line": "臺東線",
        "neiwan_liujia": "內灣/六家線",
        "shalun": "沙崙線",
        "jiji": "集集線",
        "pingxi": "平溪線",
        "shenao": "深澳線",
        "other": "其他",
    }
    for cat, station_ids in categories.items():
        if station_ids:
            print(f"    {category_names.get(cat, cat)}: {len(station_ids)} 站")

    # 統計熱門車站
    print("\n  Top 10 繁忙車站 (列車經過次數):")
    sorted_stations = sorted(stations.values(), key=lambda x: -x["train_count"])
    for i, s in enumerate(sorted_stations[:10], 1):
        print(f"    {i}. {s['name']} ({s['id']}): {s['train_count']} 次")

    print("\n  Top 10 起站:")
    sorted_by_origin = sorted(stations.values(), key=lambda x: -x["as_origin"])
    for i, s in enumerate(sorted_by_origin[:10], 1):
        print(f"    {i}. {s['name']}: {s['as_origin']} 班")

    print("\n  Top 10 迄站:")
    sorted_by_dest = sorted(stations.values(), key=lambda x: -x["as_dest"])
    for i, s in enumerate(sorted_by_dest[:10], 1):
        print(f"    {i}. {s['name']}: {s['as_dest']} 班")

    # 建立輸出資料
    print("\n[3/3] 儲存車站對照表...")

    # 簡單的 id → name 對照
    id_to_name = {sid: info["name"] for sid, info in stations.items()}
    name_to_id = {info["name"]: sid for sid, info in stations.items()}

    output_data = {
        "metadata": {
            "title": "TRA 車站對照表",
            "total_stations": len(stations),
            "generated_at": __import__('datetime').datetime.now().isoformat(),
        },
        "id_to_name": id_to_name,
        "name_to_id": name_to_id,
        "stations": stations,
        "categories": categories,
    }

    output_file = os.path.join(OUTPUT_DIR, "station_mapping.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"  ✓ 儲存完成: {output_file}")

    print("\n" + "=" * 60)
    print("下一步: python scripts/tra/prepare_real_timetable/03_build_od_mapping.py")
    print("=" * 60)

    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
