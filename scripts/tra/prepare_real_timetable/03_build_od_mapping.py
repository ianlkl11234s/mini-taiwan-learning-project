#!/usr/bin/env python3
"""
03_build_od_mapping.py - 建立 O-D → 基礎軌道對照表

功能：
1. 分析每班列車經過的路線區段
2. 建立 O-D 組合到基礎軌道的對應關係
3. 輸出 od_to_base_track.json

使用方式：
    python scripts/tra/prepare_real_timetable/03_build_od_mapping.py

輸入：
    public/data/tra/data/tdx_timetable_latest.json
    public/data/tra/data/station_mapping.json

產出：
    public/data/tra/data/od_to_base_track.json
"""

import json
import os
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
INPUT_DIR = os.path.join(DATA_DIR, 'data')
OUTPUT_DIR = INPUT_DIR

# ============================================================
# 路線定義：車站 ID 範圍和屬於的基礎軌道
# ============================================================

# 路線區段定義
ROUTE_SEGMENTS = {
    # 支線
    "NW": {"range": [(1191, 1199)], "name": "內灣線"},
    "LJ": {"range": [(1201, 1205)], "name": "六家線"},
    "SH": {"range": [(4271, 4275)], "name": "沙崙線"},
    "JJ": {"range": [(3430, 3436)], "name": "集集線"},
    "PX": {"range": [(7331, 7339)], "name": "平溪線"},
    "SA": {"range": [(7361, 7369)], "name": "深澳線"},
    "CZ": {"range": [(3330, 3339)], "name": "成追線"},

    # 西部幹線
    "WL-N": {"range": [(900, 1049)], "name": "西部幹線北段 (基隆-樹林)"},
    "WL-ZN-SL": {"range": [(1050, 1260)], "name": "西部幹線 (樹林-竹南)"},
    "WL-M": {"range": [(3300, 3370)], "name": "山線 (竹南-彰化)"},
    "WL-C": {"range": [(2100, 2270)], "name": "海線 (竹南-彰化)"},
    "WL-S": {"range": [(3370, 4350)], "name": "西部幹線南段 (彰化-新左營)"},

    # 東部幹線
    "YL": {"range": [(7200, 7400)], "name": "宜蘭線"},
    "BH": {"range": [(7000, 7130)], "name": "北迴線"},
    "TL": {"range": [(6000, 6999)], "name": "臺東線"},

    # 屏東、南迴
    "PT": {"range": [(5000, 5130)], "name": "屏東線"},
    "SK": {"range": [(5130, 5999)], "name": "南迴線"},
}

# 特殊車站對應 (車站 ID → 所屬路線)
STATION_TO_ROUTE = {
    # 八堵：西部幹線北段與宜蘭線交會
    "0920": ["WL-N", "YL"],
    # 竹南：西部幹線與山線/海線分岔
    "1250": ["WL-ZN-SL", "WL-M", "WL-C"],
    # 彰化：山線/海線合流與西部幹線南段
    "3360": ["WL-M", "WL-C", "WL-S"],
    # 新左營：西部幹線南段與屏東線
    "4400": ["WL-S", "PT"],
    # 枋寮：屏東線與南迴線
    "5120": ["PT", "SK"],
    # 臺東：臺東線與南迴線
    "6000": ["TL", "SK"],
    # 花蓮：臺東線與北迴線
    "7000": ["TL", "BH"],
    # 蘇澳新：宜蘭線與北迴線
    "7130": ["YL", "BH"],
    # 竹中：內灣線與六家線分岔
    "1193": ["NW", "LJ"],
    # 新竹：西部幹線與內灣線
    "1210": ["WL-ZN-SL", "NW", "LJ"],
    # 三貂嶺：宜蘭線與平溪線
    "7330": ["YL", "PX"],
    # 瑞芳：宜蘭線與深澳線
    "7360": ["YL", "SA"],
    # 二水：西部幹線南段與集集線
    "3430": ["WL-S", "JJ"],
    # 追分：海線與成追線
    "2260": ["WL-C", "CZ"],
    # 成功：山線與成追線
    "3330": ["WL-M", "CZ"],
    # 中洲：西部幹線南段與沙崙線
    "4270": ["WL-S", "SH"],
}


def get_station_route(station_id: str) -> List[str]:
    """判斷車站屬於哪些路線"""
    # 先檢查特殊對應
    if station_id in STATION_TO_ROUTE:
        return STATION_TO_ROUTE[station_id]

    # 根據車站 ID 範圍判斷
    try:
        sid = int(station_id)
    except ValueError:
        return []

    routes = []
    for route_code, route_info in ROUTE_SEGMENTS.items():
        for start, end in route_info["range"]:
            if start <= sid <= end:
                routes.append(route_code)
                break

    return routes


def analyze_train_route(stops: List[Dict]) -> Dict:
    """分析列車經過的路線"""
    if not stops:
        return {"routes": [], "origin": None, "destination": None}

    station_ids = [stop["StationID"] for stop in stops]
    station_names = [stop.get("StationName", {}).get("Zh_tw", "") for stop in stops]

    # 統計經過的路線
    route_counts = defaultdict(int)
    for sid in station_ids:
        for route in get_station_route(sid):
            route_counts[route] += 1

    # 依經過站數排序
    routes = sorted(route_counts.keys(), key=lambda r: -route_counts[r])

    return {
        "origin_id": station_ids[0],
        "origin_name": station_names[0],
        "destination_id": station_ids[-1],
        "destination_name": station_names[-1],
        "station_count": len(station_ids),
        "routes": routes,
        "route_counts": dict(route_counts),
    }


def determine_base_tracks(route_analysis: Dict) -> List[str]:
    """根據路線分析結果，決定需要的基礎軌道"""
    routes = route_analysis.get("routes", [])
    origin_id = route_analysis.get("origin_id", "")
    dest_id = route_analysis.get("destination_id", "")

    base_tracks = []

    # 根據經過的路線決定基礎軌道
    for route in routes:
        if route in ["NW", "LJ", "SH", "JJ", "PX", "SA", "CZ"]:
            # 支線：直接使用
            base_tracks.append(route)
        elif route == "WL-N":
            base_tracks.append("WL-N")
        elif route == "WL-ZN-SL":
            base_tracks.append("WL-ZN-SL")
        elif route == "WL-M":
            base_tracks.append("WL-M")
        elif route == "WL-C":
            base_tracks.append("WL-C")
        elif route == "WL-S":
            base_tracks.append("WL-S")
        elif route == "YL":
            base_tracks.append("YL")
        elif route == "BH":
            base_tracks.append("BH")
        elif route == "TL":
            base_tracks.append("TL")
        elif route == "PT":
            base_tracks.append("PT")
        elif route == "SK":
            base_tracks.append("SK")

    return list(dict.fromkeys(base_tracks))  # 去重保持順序


def load_data():
    """載入所需資料"""
    timetable_file = os.path.join(INPUT_DIR, "tdx_timetable_latest.json")
    station_file = os.path.join(INPUT_DIR, "station_mapping.json")

    if not os.path.exists(timetable_file):
        print(f"錯誤: 找不到時刻表檔案: {timetable_file}")
        return None, None

    with open(timetable_file, 'r', encoding='utf-8') as f:
        timetable_data = json.load(f)

    station_data = None
    if os.path.exists(station_file):
        with open(station_file, 'r', encoding='utf-8') as f:
            station_data = json.load(f)

    return timetable_data.get("timetables", []), station_data


def main():
    print("=" * 60)
    print("Phase 0.3: 建立 O-D → 基礎軌道對照表")
    print("=" * 60)

    # 載入資料
    print("\n[1/3] 載入資料...")
    timetables, station_data = load_data()
    if not timetables:
        return False
    print(f"  ✓ 載入 {len(timetables)} 班列車")

    # 分析每班車
    print("\n[2/3] 分析列車路線...")
    od_mapping = {}
    od_train_count = defaultdict(int)
    od_train_types = defaultdict(set)
    od_examples = defaultdict(list)

    for train in timetables:
        train_info = train.get("TrainInfo", {})
        stops = train.get("StopTimes", [])

        if not stops:
            continue

        train_no = train_info.get("TrainNo", "")
        train_type = train_info.get("TrainTypeName", {}).get("Zh_tw", "區間")

        # 分析路線
        route_analysis = analyze_train_route(stops)
        base_tracks = determine_base_tracks(route_analysis)

        origin = route_analysis["origin_name"]
        dest = route_analysis["destination_name"]
        od_key = f"{origin}-{dest}"

        # 記錄對應關係
        if od_key not in od_mapping:
            od_mapping[od_key] = {
                "origin": origin,
                "origin_id": route_analysis["origin_id"],
                "destination": dest,
                "destination_id": route_analysis["destination_id"],
                "base_tracks": base_tracks,
                "routes": route_analysis["routes"],
            }

        od_train_count[od_key] += 1
        od_train_types[od_key].add(train_type)

        # 記錄範例 (每個 O-D 最多 3 班)
        if len(od_examples[od_key]) < 3:
            od_examples[od_key].append({
                "train_no": train_no,
                "train_type": train_type,
                "station_count": route_analysis["station_count"]
            })

    # 加入統計資訊
    for od_key, mapping in od_mapping.items():
        mapping["train_count"] = od_train_count[od_key]
        mapping["train_types"] = list(od_train_types[od_key])
        mapping["examples"] = od_examples[od_key]

    print(f"  ✓ 分析完成，共 {len(od_mapping)} 個 O-D 組合")

    # 統計
    print("\n  基礎軌道使用次數:")
    track_usage = defaultdict(int)
    for mapping in od_mapping.values():
        for track in mapping["base_tracks"]:
            track_usage[track] += mapping["train_count"]

    for track, count in sorted(track_usage.items(), key=lambda x: -x[1]):
        print(f"    {track}: {count} 班次")

    # 儲存
    print("\n[3/3] 儲存對照表...")

    output_data = {
        "metadata": {
            "title": "O-D → 基礎軌道對照表",
            "total_od_pairs": len(od_mapping),
            "total_trains": sum(od_train_count.values()),
            "generated_at": __import__('datetime').datetime.now().isoformat(),
        },
        "track_usage": dict(track_usage),
        "od_mapping": od_mapping,
    }

    output_file = os.path.join(OUTPUT_DIR, "od_to_base_track.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"  ✓ 儲存完成: {output_file}")

    # 顯示 Top 10 O-D
    print("\n  Top 10 O-D 組合:")
    sorted_od = sorted(od_mapping.items(), key=lambda x: -x[1]["train_count"])
    for i, (od_key, mapping) in enumerate(sorted_od[:10], 1):
        tracks = ", ".join(mapping["base_tracks"])
        print(f"    {i}. {od_key}: {mapping['train_count']} 班 → [{tracks}]")

    print("\n" + "=" * 60)
    print("下一步: python scripts/tra/prepare_real_timetable/04_analyze_missing_od.py")
    print("=" * 60)

    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
