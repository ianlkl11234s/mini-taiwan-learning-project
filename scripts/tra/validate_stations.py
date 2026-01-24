#!/usr/bin/env python3
"""
TRA 車站驗證工具
檢查重複車站、名稱正確性、距離過近的車站
"""

import json
import math
import sys
from pathlib import Path

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent.parent
STATIONS_FILE = PROJECT_ROOT / "public/data/tra/stations_snapped.geojson"

# 官方車站名稱對照表 (station_id -> name)
OFFICIAL_STATION_NAMES = {
    # 山線 (竹南-彰化)
    "1250": "竹南", "3140": "造橋", "3150": "豐富", "3160": "苗栗",
    "3170": "南勢", "3180": "銅鑼", "3190": "三義", "3210": "泰安",
    "3220": "后里", "3230": "豐原", "3232": "栗林", "3240": "潭子",
    "3243": "頭家厝", "3245": "松竹", "3247": "太原", "3249": "精武",
    "3300": "臺中", "3305": "五權", "3310": "大慶", "3320": "烏日",
    "3325": "新烏日", "3330": "成功", "3360": "彰化",
    # 可繼續擴充其他路線...
}

# 已知的舊編號對照 (舊 -> 新)
OLD_TO_NEW_STATION_ID = {
    "3250": "3240",  # 潭子
    "3260": "3243",  # 頭家厝
    "3270": "3245",  # 松竹
    "3280": "3247",  # 太原
    "3290": "3249",  # 精武
    "3340": "3325",  # 新烏日
    "3350": "3330",  # 成功
}


def euclidean_distance(p1, p2):
    """計算兩點間的歐幾里得距離 (度)"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def load_stations():
    """載入車站資料"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['features']


def check_duplicate_station_ids(stations):
    """檢查重複的 station_id"""
    issues = []
    id_counts = {}

    for feat in stations:
        sid = feat['properties']['station_id']
        if sid not in id_counts:
            id_counts[sid] = []
        id_counts[sid].append(feat['properties'].get('name', '?'))

    for sid, names in id_counts.items():
        if len(names) > 1:
            issues.append({
                'type': 'DUPLICATE_ID',
                'station_id': sid,
                'count': len(names),
                'names': names,
                'message': f'station_id {sid} 重複出現 {len(names)} 次: {names}'
            })

    return issues


def check_old_station_ids(stations):
    """檢查是否使用了舊編號"""
    issues = []

    for feat in stations:
        sid = feat['properties']['station_id']
        if sid in OLD_TO_NEW_STATION_ID:
            new_id = OLD_TO_NEW_STATION_ID[sid]
            issues.append({
                'type': 'OLD_STATION_ID',
                'station_id': sid,
                'new_id': new_id,
                'name': feat['properties'].get('name', '?'),
                'message': f'使用舊編號 {sid}，應使用新編號 {new_id}'
            })

    return issues


def check_station_names(stations):
    """檢查車站名稱是否正確"""
    issues = []

    for feat in stations:
        sid = feat['properties']['station_id']
        name = feat['properties'].get('name', '')

        if sid in OFFICIAL_STATION_NAMES:
            official_name = OFFICIAL_STATION_NAMES[sid]
            if name != official_name:
                issues.append({
                    'type': 'WRONG_NAME',
                    'station_id': sid,
                    'current_name': name,
                    'correct_name': official_name,
                    'message': f'{sid} 名稱錯誤: "{name}" 應為 "{official_name}"'
                })

    return issues


def check_close_stations(stations, threshold_km=0.1):
    """檢查距離過近的車站 (可能重複)"""
    issues = []
    threshold_deg = threshold_km / 111  # 約略轉換

    station_list = []
    for feat in stations:
        sid = feat['properties']['station_id']
        name = feat['properties'].get('name', '?')
        coords = feat['geometry']['coordinates']
        station_list.append((sid, name, coords))

    for i, (sid1, name1, coords1) in enumerate(station_list):
        for j, (sid2, name2, coords2) in enumerate(station_list):
            if i >= j:
                continue

            dist = euclidean_distance(coords1, coords2)
            if dist < threshold_deg and sid1 != sid2:
                dist_m = dist * 111000
                # 檢查是否同名
                if name1 == name2:
                    issues.append({
                        'type': 'DUPLICATE_STATION',
                        'station_id_1': sid1,
                        'station_id_2': sid2,
                        'name': name1,
                        'distance_m': round(dist_m, 1),
                        'message': f'同名車站 "{name1}" 有兩個 ID: {sid1} 和 {sid2} (距離 {dist_m:.0f}m)'
                    })
                else:
                    issues.append({
                        'type': 'CLOSE_STATIONS',
                        'station_id_1': sid1,
                        'station_id_2': sid2,
                        'name_1': name1,
                        'name_2': name2,
                        'distance_m': round(dist_m, 1),
                        'message': f'車站距離過近: {sid1} "{name1}" 與 {sid2} "{name2}" (距離 {dist_m:.0f}m)'
                    })

    return issues


def validate_stations(verbose=True):
    """執行所有驗證"""
    stations = load_stations()
    all_issues = []

    # 1. 檢查重複 ID
    issues = check_duplicate_station_ids(stations)
    all_issues.extend(issues)

    # 2. 檢查舊編號
    issues = check_old_station_ids(stations)
    all_issues.extend(issues)

    # 3. 檢查名稱
    issues = check_station_names(stations)
    all_issues.extend(issues)

    # 4. 檢查距離過近
    issues = check_close_stations(stations)
    all_issues.extend(issues)

    if verbose:
        print(f"=== TRA 車站驗證報告 ===")
        print(f"車站總數: {len(stations)}")
        print(f"問題總數: {len(all_issues)}")
        print()

        if all_issues:
            for issue in all_issues:
                issue_type = issue['type']
                if issue_type == 'DUPLICATE_ID':
                    print(f"❌ [重複ID] {issue['message']}")
                elif issue_type == 'OLD_STATION_ID':
                    print(f"⚠️ [舊編號] {issue['message']}")
                elif issue_type == 'WRONG_NAME':
                    print(f"⚠️ [名稱錯誤] {issue['message']}")
                elif issue_type == 'DUPLICATE_STATION':
                    print(f"❌ [重複車站] {issue['message']}")
                elif issue_type == 'CLOSE_STATIONS':
                    print(f"⚠️ [距離過近] {issue['message']}")
        else:
            print("✅ 未發現問題")

    return all_issues


if __name__ == "__main__":
    issues = validate_stations()
    sys.exit(1 if issues else 0)
