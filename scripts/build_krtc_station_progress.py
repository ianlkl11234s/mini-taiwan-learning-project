#!/usr/bin/env python3
"""
計算高雄捷運車站進度映射表

功能：
1. 使用 TDX StationOfLine 的累積距離計算進度 (0-1)
2. 輸出 station_progress.json

使用方式：
    python scripts/build_krtc_station_progress.py

輸入：
    - data-krtc/raw/krtc_station_of_line.json

輸出：
    - public/data-krtc/station_progress.json
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# 路徑設定
RAW_DIR = Path(__file__).parent.parent / "data-krtc" / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "data-krtc"
OUTPUT_FILE = OUTPUT_DIR / "station_progress.json"

# 軌道配置
TRACKS = [
    ('KRTC-O-0', 'O', 0),  # 橘線 Direction 0 (哈瑪星→大寮)
    ('KRTC-O-1', 'O', 1),  # 橘線 Direction 1 (大寮→哈瑪星)
    ('KRTC-R-0', 'R', 0),  # 紅線 Direction 0 (小港→岡山)
    ('KRTC-R-1', 'R', 1),  # 紅線 Direction 1 (岡山→小港)
]


def load_station_of_line() -> List[Dict[str, Any]]:
    """載入車站線序資料"""
    with open(RAW_DIR / "krtc_station_of_line.json", 'r', encoding='utf-8') as f:
        return json.load(f)


def get_line_stations(line_data: List[Dict], line_id: str) -> List[Dict]:
    """取得指定線路的車站列表（含累積距離）"""
    for line in line_data:
        if line.get('LineID') == line_id:
            return line.get('Stations', [])
    return []


def build_station_progress_from_distance(
    stations: List[Dict],
    direction: int
) -> Dict[str, float]:
    """
    使用累積距離計算車站進度

    參數：
        stations: 車站列表（含 CumulativeDistance）
        direction: 0 = 正向, 1 = 反向

    返回：
        { station_id: progress }
    """
    if not stations:
        return {}

    # 計算總距離
    total_distance = stations[-1].get('CumulativeDistance', 0)
    if total_distance == 0:
        return {}

    progress_map: Dict[str, float] = {}

    # 根據方向決定順序
    if direction == 1:
        # 反向：進度從終點站開始
        ordered_stations = list(reversed(stations))
        for i, station in enumerate(ordered_stations):
            station_id = station['StationID']
            # 反向時：進度 = (總距離 - 當站累積距離) / 總距離
            cumulative = station.get('CumulativeDistance', 0)
            progress = (total_distance - cumulative) / total_distance
            progress_map[station_id] = round(progress, 6)
    else:
        # 正向
        for station in stations:
            station_id = station['StationID']
            cumulative = station.get('CumulativeDistance', 0)
            progress = cumulative / total_distance
            progress_map[station_id] = round(progress, 6)

    return progress_map


def validate_progress(progress_map: Dict[str, float]) -> bool:
    """驗證進度值是否單調遞增"""
    values = list(progress_map.values())
    for i in range(1, len(values)):
        if values[i] < values[i - 1]:
            return False
    return True


def main():
    print("=" * 50)
    print("高雄捷運車站進度計算腳本")
    print("=" * 50)

    # 載入資料
    print("\n載入車站線序資料...")
    line_data = load_station_of_line()
    print(f"  載入 {len(line_data)} 條線路")

    all_progress: Dict[str, Dict[str, float]] = {}

    for track_id, line_id, direction in TRACKS:
        print(f"\n處理 {track_id}...")

        # 取得線路車站
        stations = get_line_stations(line_data, line_id)
        print(f"  車站數量: {len(stations)}")

        if not stations:
            print(f"  ⚠️ 警告：找不到 {line_id} 線車站")
            continue

        # 計算進度
        progress_map = build_station_progress_from_distance(stations, direction)
        print(f"  進度映射: {len(progress_map)} 站")

        # 驗證
        is_valid = validate_progress(progress_map)
        if is_valid:
            print("  ✅ 進度值單調遞增")
        else:
            print("  ⚠️ 警告：進度值非單調遞增！")

        # 顯示進度值
        print("  進度值:")
        if direction == 1:
            display_stations = list(reversed(stations))
        else:
            display_stations = stations

        for station in display_stations:
            station_id = station['StationID']
            name = station.get('StationName', {}).get('Zh_tw', station_id)
            progress = progress_map.get(station_id, 0)
            print(f"    {name} ({station_id}): {progress:.6f}")

        all_progress[track_id] = progress_map

    # 儲存結果
    print(f"\n儲存到 {OUTPUT_FILE}...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)
    print("  ✅ 完成")

    # 輸出摘要
    print("\n" + "=" * 50)
    print("完成！")
    print("=" * 50)
    print(f"\n產出檔案: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
