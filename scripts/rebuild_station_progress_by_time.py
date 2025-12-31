#!/usr/bin/env python3
"""
重建 station_progress.json - 使用時間進度取代距離進度

問題：原本的 station_progress 是基於軌道幾何距離計算的，
導致動畫中列車到站時間與實際時刻表不符。

解決：從時刻表中的 station arrival/departure 時間計算時間進度。
"""

import json
import os
from typing import Dict, List

# 路徑設定
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEDULE_DIR = os.path.join(PROJECT_ROOT, "public/data/schedules")
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "public/data/station_progress.json")


def calculate_time_progress(stations: List[Dict]) -> Dict[str, float]:
    """
    從時刻表的站點資料計算時間進度 (0-1)

    stations: [{"station_id": "R02", "arrival": 0, "departure": 40}, ...]
    """
    if not stations:
        return {}

    if len(stations) == 1:
        return {stations[0]['station_id']: 0.0}

    # 使用 arrival 時間計算進度（更準確反映列車到達各站的時間點）
    first_arrival = stations[0]['arrival']
    last_arrival = stations[-1]['arrival']
    total_time = last_arrival - first_arrival

    if total_time <= 0:
        # 如果總時間為 0，使用均勻分布
        return {
            s['station_id']: i / (len(stations) - 1)
            for i, s in enumerate(stations)
        }

    progress = {}
    for station in stations:
        time_elapsed = station['arrival'] - first_arrival
        progress[station['station_id']] = time_elapsed / total_time

    return progress


def load_schedule(track_id: str) -> Dict:
    """載入時刻表"""
    filepath = os.path.join(SCHEDULE_DIR, f"{track_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    print("🔄 重建 station_progress.json (使用時間進度)")
    print("=" * 50)

    # 載入現有的 station_progress
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        old_progress = json.load(f)

    print(f"📊 現有軌道數: {len(old_progress)}")

    # 新的進度資料
    new_progress = {}
    updated_count = 0
    skipped_count = 0

    for track_id in old_progress.keys():
        schedule = load_schedule(track_id)

        if not schedule:
            print(f"  ⚠️  {track_id}: 找不到時刻表，保留原值")
            new_progress[track_id] = old_progress[track_id]
            skipped_count += 1
            continue

        departures = schedule.get('departures', [])
        if not departures:
            print(f"  ⚠️  {track_id}: 無班次資料，保留原值")
            new_progress[track_id] = old_progress[track_id]
            skipped_count += 1
            continue

        # 使用第一班車的站點時間資料
        stations = departures[0].get('stations', [])
        if not stations:
            print(f"  ⚠️  {track_id}: 無站點資料，保留原值")
            new_progress[track_id] = old_progress[track_id]
            skipped_count += 1
            continue

        # 計算時間進度
        time_progress = calculate_time_progress(stations)
        new_progress[track_id] = time_progress
        updated_count += 1

        # 顯示對比（只顯示差異較大的）
        old_values = old_progress[track_id]
        max_diff = 0
        for station_id, new_val in time_progress.items():
            old_val = old_values.get(station_id, 0)
            diff = abs(new_val - old_val)
            max_diff = max(max_diff, diff)

        if max_diff > 0.1:  # 差異超過 10% 才顯示
            print(f"  ✅ {track_id}: 最大差異 {max_diff:.1%}")

    print()
    print(f"📈 更新統計:")
    print(f"   更新: {updated_count} 條軌道")
    print(f"   跳過: {skipped_count} 條軌道")

    # 詳細對比機場捷運
    print()
    print("=" * 50)
    print("🔍 機場捷運 A-2-1 (直達車往台北) 進度對比:")
    print("-" * 50)
    print(f"{'站點':<8} {'舊(距離)':<12} {'新(時間)':<12} {'差異':<10}")
    print("-" * 50)

    if 'A-2-1' in old_progress and 'A-2-1' in new_progress:
        old_a2 = old_progress['A-2-1']
        new_a2 = new_progress['A-2-1']
        for station_id in new_a2.keys():
            old_val = old_a2.get(station_id, 0)
            new_val = new_a2[station_id]
            diff = new_val - old_val
            print(f"{station_id:<8} {old_val:<12.4f} {new_val:<12.4f} {diff:+.4f}")

    # 寫入新檔案
    print()
    print("=" * 50)

    # 備份原檔
    backup_file = PROGRESS_FILE + ".backup"
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(old_progress, f, indent=2, ensure_ascii=False)
    print(f"💾 已備份原檔至: {backup_file}")

    # 寫入新檔
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_progress, f, indent=2, ensure_ascii=False)
    print(f"✅ 已更新: {PROGRESS_FILE}")

    print()
    print("🎉 完成！請重新載入頁面驗證動畫時間")


if __name__ == "__main__":
    main()
