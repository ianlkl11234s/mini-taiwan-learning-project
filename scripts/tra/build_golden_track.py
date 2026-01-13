#!/usr/bin/env python3
"""
黃金軌道建構器
從 TDX 原始資料 + 手繪修正 → 產生黃金版本

用法:
    python build_golden_track.py YL     # 重建 YL 軌道
    python build_golden_track.py KL     # 重建 KL 軌道 (純手繪)
    python build_golden_track.py --all  # 重建所有有問題的軌道
"""

import json
import math
import sys
from pathlib import Path
from datetime import datetime

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "public" / "data" / "tra"
GOLDEN_DIR = DATA_DIR / "tracks_golden"
TRACKS_OFFICIAL = DATA_DIR / "tracks_official"
HANDDRAWN_DIR = DATA_DIR / "tracks_handdrawn"

# 車站座標對映（用於定位手繪區段的插入位置）
STATION_COORDS = {
    # YL 宜蘭線問題區段相關車站
    '7290': [121.944621, 25.015687],  # 福隆
    '7300': [121.908749, 25.021829],  # 貢寮
    '7310': [121.866816, 25.038463],  # 雙溪
    '7320': [121.851905, 25.0586],    # 牡丹
    '7350': [121.82724, 25.087149],   # 猴硐
    '7360': [121.806254, 25.109005],  # 瑞芳
    # KL 基隆支線
    '0900': [121.739237, 25.133096],  # 基隆
    '0910': [121.742387, 25.123064],  # 三坑
    '0920': [121.728826, 25.108610],  # 八堵
}


def euclidean_distance(p1, p2):
    """計算歐幾里得距離（度為單位）"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def find_nearest_index(coords, target_point, search_radius=0.01):
    """
    在軌道座標中找到最接近目標點的索引
    search_radius: 搜尋範圍（度），約 1km
    """
    min_dist = float('inf')
    min_idx = -1

    for i, coord in enumerate(coords):
        dist = euclidean_distance(coord, target_point)
        if dist < min_dist:
            min_dist = dist
            min_idx = i

    if min_dist > search_radius:
        return -1, min_dist

    return min_idx, min_dist


def load_handdrawn_segment(filepath):
    """載入手繪區段，回傳座標列表"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for feature in data['features']:
        if feature['geometry']['type'] == 'LineString':
            return feature['geometry']['coordinates']

    return []


def replace_segment(coords, start_idx, end_idx, replacement_coords):
    """
    用 replacement_coords 替換 coords[start_idx:end_idx]
    確保連接點平滑
    """
    # 前段 + 替換段 + 後段
    new_coords = coords[:start_idx] + replacement_coords + coords[end_idx:]
    return new_coords


def rebuild_yl_track(direction=0):
    """
    重建 YL 宜蘭線軌道
    direction: 0=南下(臺北→花蓮), 1=北上(花蓮→臺北)
    """
    track_id = f"YL-{direction}"
    print(f"\n🔧 重建 {track_id}...")

    # 載入現有軌道
    golden_file = GOLDEN_DIR / f"{track_id}.geojson"
    if not golden_file.exists():
        print(f"❌ 找不到黃金軌道: {golden_file}")
        return False

    with open(golden_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    coords = data['features'][0]['geometry']['coordinates']
    original_count = len(coords)
    print(f"   原始點數: {original_count}")

    # 手繪區段清單（根據方向決定順序）
    yl_handdrawn_dir = HANDDRAWN_DIR / "YL"
    if not yl_handdrawn_dir.exists():
        print(f"❌ 找不到 YL 手繪目錄: {yl_handdrawn_dir}")
        return False

    # 定義手繪區段及其起迄車站
    segments = [
        ('7290-7300-福隆貢寮.geojson', '7290', '7300'),
        ('7300-7310-貢寮雙溪.geojson', '7300', '7310'),
        ('7310-7320-雙溪牡丹.geojson', '7310', '7320'),
        ('7350-7360-猴硐瑞芳.geojson', '7350', '7360'),
    ]

    # 北上方向需要反轉
    if direction == 1:
        segments = list(reversed(segments))
        for i, (filename, from_st, to_st) in enumerate(segments):
            segments[i] = (filename, to_st, from_st)

    replacements_made = 0

    for filename, from_station, to_station in segments:
        segment_file = yl_handdrawn_dir / filename
        if not segment_file.exists():
            print(f"   ⚠️ 找不到手繪區段: {filename}")
            continue

        # 載入手繪座標
        handdrawn_coords = load_handdrawn_segment(segment_file)
        if not handdrawn_coords:
            print(f"   ⚠️ 無法載入手繪區段: {filename}")
            continue

        # 北上方向需要反轉手繪座標
        if direction == 1:
            handdrawn_coords = list(reversed(handdrawn_coords))

        # 找到起點和終點在軌道中的位置
        from_coord = STATION_COORDS.get(from_station)
        to_coord = STATION_COORDS.get(to_station)

        if not from_coord or not to_coord:
            print(f"   ⚠️ 找不到車站座標: {from_station} 或 {to_station}")
            continue

        start_idx, start_dist = find_nearest_index(coords, from_coord)
        end_idx, end_dist = find_nearest_index(coords, to_coord)

        if start_idx < 0 or end_idx < 0:
            print(f"   ⚠️ 找不到插入位置: {from_station}→{to_station}")
            print(f"      start_idx={start_idx}, end_idx={end_idx}")
            continue

        # 確保順序正確
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
            handdrawn_coords = list(reversed(handdrawn_coords))

        # 替換區段
        old_segment_len = end_idx - start_idx
        coords = replace_segment(coords, start_idx, end_idx + 1, handdrawn_coords)

        print(f"   ✅ {from_station}→{to_station}: 替換 {old_segment_len} pts → {len(handdrawn_coords)} pts")
        replacements_made += 1

        # 需要更新後續的 end_idx 計算，因為軌道長度已變化

    # 更新軌道資料
    data['features'][0]['geometry']['coordinates'] = coords
    data['features'][0]['properties']['rebuilt_at'] = datetime.now().isoformat()
    data['features'][0]['properties']['rebuilds'] = replacements_made

    # 儲存
    with open(golden_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"   📊 完成: {original_count} → {len(coords)} pts, {replacements_made} 區段替換")

    # 驗證
    validate_track(coords, track_id)

    return True


def validate_track(coords, track_id, max_jump_km=0.5):
    """驗證軌道品質"""
    max_jump_deg = max_jump_km / 111.0
    issues = []

    for i in range(len(coords) - 1):
        dist = euclidean_distance(coords[i], coords[i+1])
        if dist > max_jump_deg:
            dist_km = dist * 111
            issues.append((i, dist_km))

    if issues:
        print(f"   ⚠️ {track_id} 有 {len(issues)} 個座標跳躍:")
        for idx, dist in issues[:5]:
            print(f"      index {idx}: {dist:.2f}km")
        if len(issues) > 5:
            print(f"      ... 還有 {len(issues) - 5} 個")
    else:
        print(f"   ✅ {track_id} 驗證通過!")


def main():
    print("=" * 60)
    print("黃金軌道建構器")
    print("=" * 60)

    if len(sys.argv) < 2:
        print("\n用法:")
        print("  python build_golden_track.py YL      # 重建 YL 軌道")
        print("  python build_golden_track.py --all   # 重建所有有問題的軌道")
        return

    target = sys.argv[1].upper()

    if target == 'YL':
        rebuild_yl_track(direction=0)
        rebuild_yl_track(direction=1)
    elif target == '--ALL':
        rebuild_yl_track(direction=0)
        rebuild_yl_track(direction=1)
        # 可以加入其他路線
    else:
        print(f"❌ 未知的目標: {target}")
        print("   支援: YL, --all")

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
