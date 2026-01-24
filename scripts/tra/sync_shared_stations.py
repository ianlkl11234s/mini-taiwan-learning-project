#!/usr/bin/env python3
"""
TRA 共用車站同步工具
確保跨路線共用車站使用相同的座標和 station_id
"""

import json
import sys
from pathlib import Path

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent.parent
STATIONS_FILE = PROJECT_ROOT / "public/data/tra/stations_snapped.geojson"
PROGRESS_FILE = PROJECT_ROOT / "public/data/tra/tracks_od/od_station_progress.json"
TRACKS_OD_DIR = PROJECT_ROOT / "public/data/tra/tracks_od"

# 共用車站定義: {station_id: [使用此車站的軌道 ID 列表]}
SHARED_STATIONS = {
    # 成功站 - 山線與成追線共用
    "3330": [
        "WL-M-ZN-CH-0", "WL-M-CH-ZN-1",  # 山線
        "CZ-CG-ZF", "CZ-ZF-CG",           # 成追線
    ],
    # 八堵 - 多條路線共用
    "0920": [
        "YL-BD-SA-0", "YL-SA-BD-1",      # 宜蘭線
        "WL-SL-BD-0", "WL-BD-SL-1",      # 西部幹線
        "KL-BD-KL-0", "KL-KL-BD-1",      # 基隆線
    ],
    # 可繼續擴充...
}

# 舊編號到新編號的對照
OLD_TO_NEW_ID = {
    "3350": "3330",  # 成功站
}


def load_stations():
    """載入車站資料"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_progress():
    """載入進度值資料"""
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_progress(data):
    """儲存進度值資料"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_station_coord(stations_data, station_id):
    """取得車站座標"""
    for feat in stations_data['features']:
        if feat['properties']['station_id'] == station_id:
            return feat['geometry']['coordinates']
    return None


def check_shared_stations(verbose=True):
    """檢查共用車站的一致性"""
    stations_data = load_stations()
    progress_data = load_progress()
    issues = []

    if verbose:
        print("=== 共用車站一致性檢查 ===")
        print()

    for station_id, track_ids in SHARED_STATIONS.items():
        coord = get_station_coord(stations_data, station_id)
        station_name = None
        for feat in stations_data['features']:
            if feat['properties']['station_id'] == station_id:
                station_name = feat['properties'].get('name', '?')
                break

        if verbose:
            print(f"📍 {station_id} {station_name}")

        for track_id in track_ids:
            if track_id not in progress_data:
                if verbose:
                    print(f"   ⚠️ {track_id}: 軌道不存在於進度值檔案")
                issues.append({
                    'type': 'MISSING_TRACK',
                    'station_id': station_id,
                    'track_id': track_id
                })
                continue

            # 檢查是否使用正確的 station_id
            track_progress = progress_data[track_id]

            if station_id in track_progress:
                if verbose:
                    print(f"   ✅ {track_id}: 使用 {station_id}")
            else:
                # 檢查是否使用了舊編號
                old_id_used = None
                for old_id, new_id in OLD_TO_NEW_ID.items():
                    if new_id == station_id and old_id in track_progress:
                        old_id_used = old_id
                        break

                if old_id_used:
                    if verbose:
                        print(f"   ❌ {track_id}: 使用舊編號 {old_id_used}，應改為 {station_id}")
                    issues.append({
                        'type': 'OLD_ID_USED',
                        'station_id': station_id,
                        'old_id': old_id_used,
                        'track_id': track_id
                    })
                else:
                    if verbose:
                        print(f"   ⚠️ {track_id}: 未包含此車站")
                    issues.append({
                        'type': 'STATION_NOT_IN_TRACK',
                        'station_id': station_id,
                        'track_id': track_id
                    })

        if verbose:
            print()

    return issues


def sync_station_id(old_id, new_id, dry_run=True):
    """
    將進度值檔案中的舊 station_id 替換為新 station_id

    Args:
        old_id: 舊的 station_id
        new_id: 新的 station_id
        dry_run: 如果為 True，只顯示結果不實際修改
    """
    progress_data = load_progress()
    changes = []

    for track_id, stations in progress_data.items():
        if old_id in stations:
            progress_value = stations[old_id]
            changes.append({
                'track_id': track_id,
                'old_id': old_id,
                'new_id': new_id,
                'progress': progress_value
            })

            if not dry_run:
                del stations[old_id]
                stations[new_id] = progress_value

    if changes:
        print(f"=== 替換 station_id: {old_id} → {new_id} ===")
        for change in changes:
            print(f"   {change['track_id']}: {change['old_id']} → {change['new_id']}")

        if not dry_run:
            save_progress(progress_data)
            print(f"\n✅ 已更新 {len(changes)} 處")
        else:
            print(f"\n💡 使用 --apply 參數來實際修改")
    else:
        print(f"未找到使用 {old_id} 的軌道")

    return changes


def sync_all_shared_stations(dry_run=True):
    """同步所有共用車站"""
    all_changes = []

    for old_id, new_id in OLD_TO_NEW_ID.items():
        changes = sync_station_id(old_id, new_id, dry_run)
        all_changes.extend(changes)

    return all_changes


def main():
    """主程式"""
    import argparse
    parser = argparse.ArgumentParser(description='TRA 共用車站同步工具')
    parser.add_argument('--check', action='store_true', help='檢查共用車站一致性')
    parser.add_argument('--sync', action='store_true', help='同步所有舊編號到新編號')
    parser.add_argument('--apply', action='store_true', help='實際修改檔案')
    args = parser.parse_args()

    if args.check:
        issues = check_shared_stations()
        if issues:
            print(f"發現 {len(issues)} 個問題")
            sys.exit(1)
    elif args.sync:
        sync_all_shared_stations(dry_run=not args.apply)
    else:
        # 預設執行檢查
        check_shared_stations()


if __name__ == "__main__":
    main()
