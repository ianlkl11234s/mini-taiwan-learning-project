#!/usr/bin/env python3
"""
TRA 軌道驗證工具
檢查軌道跳躍、急轉彎、回頭路段
"""

import json
import math
import sys
from pathlib import Path

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent.parent
TRACKS_OD_DIR = PROJECT_ROOT / "public/data/tra/tracks_od"
TRACKS_GOLDEN_DIR = PROJECT_ROOT / "public/data/tra/tracks_golden"


def euclidean_distance(p1, p2):
    """計算兩點間的歐幾里得距離 (度)"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def calculate_bearing(p1, p2):
    """計算從 p1 到 p2 的方位角 (度)"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.degrees(math.atan2(dx, dy))


def angle_diff(a1, a2):
    """計算兩個角度的差值 (0-180)"""
    diff = abs(a1 - a2) % 360
    return min(diff, 360 - diff)


def load_track(filepath):
    """載入軌道資料"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 處理不同的 GeoJSON 格式
    if data.get('type') == 'FeatureCollection':
        return data['features'][0]['geometry']['coordinates']
    elif data.get('type') == 'Feature':
        return data['geometry']['coordinates']
    else:
        return data['geometry']['coordinates']


def check_large_jumps(coords, track_id, threshold_km=1.0):
    """檢查軌道中的大跳躍"""
    issues = []
    threshold_deg = threshold_km / 111

    for i in range(len(coords) - 1):
        dist = euclidean_distance(coords[i], coords[i+1])
        if dist > threshold_deg:
            dist_km = dist * 111
            issues.append({
                'type': 'LARGE_JUMP',
                'track_id': track_id,
                'index': i,
                'distance_km': round(dist_km, 2),
                'from_coord': coords[i],
                'to_coord': coords[i+1],
                'message': f'[{track_id}] 索引 {i} 有 {dist_km:.1f}km 跳躍'
            })

    return issues


def check_sharp_turns(coords, track_id, threshold_degrees=120):
    """檢查急轉彎 (方向變化超過閾值)"""
    issues = []

    if len(coords) < 3:
        return issues

    for i in range(1, len(coords) - 1):
        # 計算前後兩段的方向
        bearing1 = calculate_bearing(coords[i-1], coords[i])
        bearing2 = calculate_bearing(coords[i], coords[i+1])

        turn_angle = angle_diff(bearing1, bearing2)

        if turn_angle > threshold_degrees:
            issues.append({
                'type': 'SHARP_TURN',
                'track_id': track_id,
                'index': i,
                'turn_angle': round(turn_angle, 1),
                'coord': coords[i],
                'message': f'[{track_id}] 索引 {i} 有 {turn_angle:.0f}° 急轉彎'
            })

    return issues


def check_backtracking(coords, track_id, window=5):
    """檢查回頭路段 (短距離內方向反轉)"""
    issues = []

    if len(coords) < window * 2:
        return issues

    for i in range(window, len(coords) - window):
        # 計算前後兩個窗口的整體方向
        bearing_before = calculate_bearing(coords[i-window], coords[i])
        bearing_after = calculate_bearing(coords[i], coords[i+window])

        turn_angle = angle_diff(bearing_before, bearing_after)

        if turn_angle > 150:  # 接近 180 度表示回頭
            issues.append({
                'type': 'BACKTRACKING',
                'track_id': track_id,
                'index': i,
                'turn_angle': round(turn_angle, 1),
                'coord': coords[i],
                'message': f'[{track_id}] 索引 {i} 疑似回頭路段 ({turn_angle:.0f}°)'
            })

    return issues


def check_duplicate_points(coords, track_id, threshold_m=1):
    """檢查重複點位"""
    issues = []
    threshold_deg = threshold_m / 111000

    for i in range(len(coords) - 1):
        dist = euclidean_distance(coords[i], coords[i+1])
        if dist < threshold_deg:
            issues.append({
                'type': 'DUPLICATE_POINT',
                'track_id': track_id,
                'index': i,
                'distance_m': round(dist * 111000, 2),
                'message': f'[{track_id}] 索引 {i} 與 {i+1} 重複 (距離 {dist*111000:.1f}m)'
            })

    return issues


def validate_track(filepath, verbose=True):
    """驗證單一軌道"""
    track_id = filepath.stem
    coords = load_track(filepath)
    all_issues = []

    # 1. 檢查大跳躍
    issues = check_large_jumps(coords, track_id)
    all_issues.extend(issues)

    # 2. 檢查急轉彎
    issues = check_sharp_turns(coords, track_id)
    all_issues.extend(issues)

    # 3. 檢查回頭路段
    issues = check_backtracking(coords, track_id)
    all_issues.extend(issues)

    # 4. 檢查重複點位 (僅統計，不報告)
    # issues = check_duplicate_points(coords, track_id)
    # all_issues.extend(issues)

    return all_issues


def validate_all_tracks(track_dir, pattern="*.geojson", verbose=True):
    """驗證目錄中的所有軌道"""
    all_issues = []

    track_files = list(Path(track_dir).glob(pattern))

    for filepath in track_files:
        issues = validate_track(filepath, verbose=False)
        all_issues.extend(issues)

    if verbose:
        print(f"=== TRA 軌道驗證報告 ===")
        print(f"軌道數量: {len(track_files)}")
        print(f"問題總數: {len(all_issues)}")
        print()

        if all_issues:
            # 按類型分組
            by_type = {}
            for issue in all_issues:
                t = issue['type']
                if t not in by_type:
                    by_type[t] = []
                by_type[t].append(issue)

            for issue_type, issues in by_type.items():
                if issue_type == 'LARGE_JUMP':
                    print(f"❌ 大跳躍 ({len(issues)} 處):")
                elif issue_type == 'SHARP_TURN':
                    print(f"⚠️ 急轉彎 ({len(issues)} 處):")
                elif issue_type == 'BACKTRACKING':
                    print(f"⚠️ 回頭路段 ({len(issues)} 處):")

                for issue in issues[:5]:  # 只顯示前 5 個
                    print(f"   {issue['message']}")
                if len(issues) > 5:
                    print(f"   ... 還有 {len(issues)-5} 處")
                print()
        else:
            print("✅ 未發現問題")

    return all_issues


def main():
    """主程式"""
    import argparse
    parser = argparse.ArgumentParser(description='TRA 軌道驗證工具')
    parser.add_argument('--od', action='store_true', help='驗證 O-D 軌道')
    parser.add_argument('--golden', action='store_true', help='驗證 Golden 軌道')
    parser.add_argument('--file', type=str, help='驗證指定檔案')
    args = parser.parse_args()

    all_issues = []

    if args.file:
        issues = validate_track(Path(args.file))
        all_issues.extend(issues)
        for issue in issues:
            print(issue['message'])
    else:
        if args.od or (not args.od and not args.golden):
            print("--- O-D 軌道 ---")
            issues = validate_all_tracks(TRACKS_OD_DIR)
            all_issues.extend(issues)

        if args.golden:
            print("--- Golden 軌道 ---")
            issues = validate_all_tracks(TRACKS_GOLDEN_DIR)
            all_issues.extend(issues)

    sys.exit(1 if all_issues else 0)


if __name__ == "__main__":
    main()
