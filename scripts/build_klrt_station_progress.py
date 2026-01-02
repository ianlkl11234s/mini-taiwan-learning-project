#!/usr/bin/env python3
"""
計算高雄輕軌車站進度映射表

功能：
1. 使用 TDX StationOfLine 的累積距離計算進度 (0-1)
2. 處理環狀線特性
3. 輸出 station_progress.json

環狀線特性：
- 起點和終點是同一站 (C1 籬仔內)
- Direction 0 = 順時針：C1(0) -> C2 -> ... -> C37 -> C1(1)
- Direction 1 = 逆時針：C1(0) -> C37 -> ... -> C2 -> C1(1)

使用方式：
    python scripts/build_klrt_station_progress.py

輸入：
    - data-klrt/raw/klrt_station_of_line.json

輸出：
    - public/data-klrt/station_progress.json
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# 路徑設定
RAW_DIR = Path(__file__).parent.parent / "data-klrt" / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "data-klrt"
OUTPUT_FILE = OUTPUT_DIR / "station_progress.json"

# 軌道配置
TRACKS = [
    ('KLRT-C-0', 'C', 0),  # 環狀線 Direction 0 (順時針)
    ('KLRT-C-1', 'C', 1),  # 環狀線 Direction 1 (逆時針)
]


def load_station_of_line() -> List[Dict[str, Any]]:
    """載入車站線序資料"""
    with open(RAW_DIR / "klrt_station_of_line.json", 'r', encoding='utf-8') as f:
        return json.load(f)


def get_line_stations(line_data: List[Dict], line_id: str) -> List[Dict]:
    """取得指定線路的車站列表（含累積距離）"""
    for line in line_data:
        if line.get('LineID') == line_id:
            return line.get('Stations', [])
    return []


def build_circular_station_progress(
    stations: List[Dict],
    direction: int
) -> Dict[str, float]:
    """
    計算環狀線車站進度

    環狀線特性：
    - 起點和終點是同一站 (C1)
    - 進度從 0 到 1 代表一圈
    - Direction 0：順時針，C1(0) → C2 → ... → C37 → C1(1)
    - Direction 1：逆時針，C1(0) → C37 → ... → C2 → C1(1)
                   軌道幾何是反向的，所以要特殊處理

    參數：
        stations: 車站列表（含 CumulativeDistance，順時針方向）
        direction: 0 = 順時針, 1 = 逆時針

    返回：
        { station_id: progress }
        進度值對應軌道幾何上的位置 (0-1)
    """
    if not stations:
        return {}

    # 計算總距離（環狀線的總長度）
    total_distance = stations[-1].get('CumulativeDistance', 0)
    if total_distance == 0:
        return {}

    progress_map: Dict[str, float] = {}

    if direction == 0:
        # 順時針：C1(0) → C2 → ... → C37 → C1(1)
        # 軌道幾何順序：起點=C1, 終點=C1
        # 進度 = 累積距離 / 總距離
        for station in stations:
            station_id = station['StationID']
            cumulative = station.get('CumulativeDistance', 0)
            progress = cumulative / total_distance
            progress_map[station_id] = round(progress, 6)
    else:
        # 逆時針：C1(0) → C37 → ... → C2 → C1(1)
        # 軌道幾何是反向的：起點=C1, 經過 C37, C36, ..., C2, 終點=C1
        #
        # 逆時針軌道使用反向累積距離計算進度
        # 順時針方向 C37 的累積距離接近 total（在圈的末端）
        # 逆時針軌道上，C37 應該在起點附近（接近 0）
        #
        # 計算方法：使用 1 - (順時針進度) 來反轉，但要處理 C1 的特殊情況
        # C1: 順時針進度 = 0, 逆時針進度 = 0 (起點)
        # C37: 順時針進度 ≈ 1, 逆時針進度 = 1 - 1 = 0? 不對
        #
        # 更好的方法：直接使用站序計算均勻進度
        # 因為環狀線站距相對均勻，使用序號計算足夠準確

        origin = stations[0]['StationID']  # C1
        rest_stations = stations[1:]  # [C2, C3, ..., C37]

        # 逆時針順序：C1 → C37 → C36 → ... → C2
        # 在逆時針軌道上的進度：
        # - C1: 0.0 (起點)
        # - C37: 小值（第一站）
        # - C2: 接近 1（最後一站）

        # C1 起點
        progress_map[origin] = 0.0

        # 其餘站按逆時針順序（C37, C36, ..., C2）
        ccw_order = list(reversed(rest_stations))  # [C37, C36, ..., C2]
        n = len(stations)  # 38 站

        for i, station in enumerate(ccw_order):
            station_id = station['StationID']
            # 第 i+1 個站（C1 是第 0 個）
            # 進度值從 1/38 到 37/38
            progress = (i + 1) / n
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
    print("高雄輕軌車站進度計算腳本")
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
        progress_map = build_circular_station_progress(stations, direction)
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

        # 只顯示前 10 站和最後 3 站
        display_count = len(display_stations)
        for i, station in enumerate(display_stations):
            station_id = station['StationID']
            name = station.get('StationName', {}).get('Zh_tw', station_id)
            progress = progress_map.get(station_id, 0)
            if i < 10 or i >= display_count - 3:
                print(f"    {name} ({station_id}): {progress:.6f}")
            elif i == 10:
                print(f"    ... (共 {display_count} 站)")

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

    # 顯示環狀線特性
    if all_progress:
        first_track = list(all_progress.keys())[0]
        progress = all_progress[first_track]
        stations_list = list(progress.keys())
        if stations_list:
            first_station = stations_list[0]
            last_station = stations_list[-1]
            print(f"\n環狀線特性確認:")
            print(f"  起點站: {first_station} (progress={progress[first_station]:.6f})")
            print(f"  終點站: {last_station} (progress={progress[last_station]:.6f})")
            print(f"  注意: 環狀線的終點會回到起點 (progress=1.0)")


if __name__ == '__main__':
    main()
