#!/usr/bin/env python3
"""
build_crossline_tracks.py - 建立跨線 O-D 軌道

功能：
合併多段軌道建立跨線列車專用 OD 軌道。
與 merge_tracks.py 不同，這裡使用「距離比例縮放」而非「座標投影」
來計算 station_progress，避免 L 形路線投影錯誤。

使用方式：
    python scripts/tra/prepare_real_timetable/build_crossline_tracks.py
"""

import json
import os
import math
from typing import Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
PROGRESS_FILE = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')


def load_progress():
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_progress(data):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_geojson(track_id):
    path = os.path.join(TRACKS_OD_DIR, f"{track_id}.geojson")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_coords(geojson):
    return geojson['features'][0]['geometry']['coordinates']


def euclidean_dist(a, b):
    return math.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2)


def track_length(coords):
    total = 0.0
    for i in range(1, len(coords)):
        total += euclidean_dist(coords[i-1], coords[i])
    return total


def extract_segment_coords(coords, start_prog, end_prog):
    """從軌道座標中擷取 [start_prog, end_prog] 區段"""
    cum = [0.0]
    for i in range(1, len(coords)):
        cum.append(cum[-1] + euclidean_dist(coords[i-1], coords[i]))
    total = cum[-1]
    if total == 0:
        return coords

    start_dist = start_prog * total
    end_dist = end_prog * total

    extracted = []
    for i, (c, d) in enumerate(zip(coords, cum)):
        if d >= start_dist and d <= end_dist:
            extracted.append(c)
        elif d > end_dist:
            break

    if len(extracted) < 2:
        si = 0
        ei = len(coords) - 1
        for i, d in enumerate(cum):
            if d <= start_dist: si = i
            if d <= end_dist: ei = i
        extracted = coords[si:ei+1]

    return extracted


def extract_segment_progress(progress_map, origin_id, dest_id):
    """擷取子區段的 station_progress 並重新歸一化到 [0, 1]"""
    op = progress_map[origin_id]
    dp = progress_map[dest_id]
    seg_len = dp - op
    if seg_len == 0:
        return {origin_id: 0.0, dest_id: 1.0}

    result = {}
    for sid, p in progress_map.items():
        if p >= op and p <= dp:
            result[sid] = round((p - op) / seg_len, 6)
    return result


def build_crossline_track(
    segments: List[Dict],
    output_id: str,
    all_progress: Dict
) -> Tuple[List, Dict]:
    """
    建立跨線軌道

    segments: list of {source_track, origin, dest}
    每個 segment 從 source_track 擷取 origin→dest 區段

    station_progress 使用距離比例縮放，不做座標投影
    """
    all_coords = []
    all_seg_progress = []
    seg_lengths = []

    for seg in segments:
        src = seg['source_track']
        origin = seg['origin']
        dest = seg['dest']

        prog_map = all_progress[src]
        op = prog_map[origin]
        dp = prog_map[dest]

        # 擷取座標
        geojson = load_geojson(src)
        coords = get_coords(geojson)
        seg_coords = extract_segment_coords(coords, op, dp)

        # 擷取 station_progress
        seg_prog = extract_segment_progress(prog_map, origin, dest)

        seg_len = track_length(seg_coords)
        seg_lengths.append(seg_len)
        all_coords.append(seg_coords)
        all_seg_progress.append(seg_prog)

        print(f"  Segment {src}: {origin}→{dest}, {len(seg_coords)} pts, {len(seg_prog)} stations, len={seg_len:.6f}")

    # 合併座標
    total_length = sum(seg_lengths)
    merged_coords = list(all_coords[0])

    for i in range(1, len(all_coords)):
        next_coords = all_coords[i]
        # 檢查是否需要跳過第一個點（避免重複）
        if merged_coords and next_coords:
            d = euclidean_dist(merged_coords[-1], next_coords[0])
            if d < 0.001:
                merged_coords.extend(next_coords[1:])
            else:
                merged_coords.extend(next_coords)

    # 合併 station_progress（距離比例縮放）
    merged_progress = {}
    cum_length = 0.0

    for i, (seg_prog, seg_len) in enumerate(zip(all_seg_progress, seg_lengths)):
        ratio_start = cum_length / total_length if total_length > 0 else 0
        ratio_end = (cum_length + seg_len) / total_length if total_length > 0 else 1
        seg_range = ratio_end - ratio_start

        for sid, p in seg_prog.items():
            new_p = ratio_start + p * seg_range
            # 如果同一站已存在（連接站），取後一段的值
            merged_progress[sid] = round(new_p, 6)

        cum_length += seg_len

    # 驗證單調性
    sorted_stations = sorted(merged_progress.items(), key=lambda x: x[1])
    print(f"  Merged: {len(merged_coords)} pts, {len(merged_progress)} stations")
    print(f"  First: {sorted_stations[0][0]}={sorted_stations[0][1]}")
    print(f"  Last:  {sorted_stations[-1][0]}={sorted_stations[-1][1]}")

    return merged_coords, merged_progress


def save_track(output_id, coords, progress, source_tracks, all_progress):
    """儲存軌道 GeoJSON 和更新 station_progress"""
    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": output_id,
                "source_tracks": source_tracks,
                "point_count": len(coords),
                "generated_by": "build_crossline_tracks.py"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }

    path = os.path.join(TRACKS_OD_DIR, f"{output_id}.geojson")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    all_progress[output_id] = progress
    print(f"  ✓ Saved {output_id}.geojson ({len(coords)} pts, {len(progress)} stations)")


def main():
    print("=" * 60)
    print("建立跨線 O-D 軌道")
    print("=" * 60)

    all_progress = load_progress()

    # ============================================================
    # 1. OD-ZN-FY-C: 竹南→豐原 via 海線+成追線+山線 (for LC-2611)
    #    修正：原走彰化，改走成追線（追分→成功→烏日）
    # ============================================================
    print("\n[1] OD-ZN-FY-C: 竹南→豐原 (海線+成追+山線)")
    coords, progress = build_crossline_track([
        {'source_track': 'BB-ZN-ZY-C-1', 'origin': '1250', 'dest': '2260'},  # 海線: 竹南→追分
        {'source_track': 'CZ-ZF-CG', 'origin': '2260', 'dest': '3330'},      # 成追線: 追分→成功
        {'source_track': 'BB-ZY-ZN-M-0', 'origin': '3330', 'dest': '3230'},  # 山線: 烏日→豐原
    ], 'OD-ZN-FY-C', all_progress)
    save_track('OD-ZN-FY-C', coords, progress, ['BB-ZN-ZY-C-1', 'CZ-ZF-CG', 'BB-ZY-ZN-M-0'], all_progress)

    # ============================================================
    # 2. OD-FY-ZN-C: 豐原→竹南 via 山線+成追線+海線 (for LC-2602)
    #    修正：原走彰化，改走成追線（烏日→成功→追分）
    # ============================================================
    print("\n[2] OD-FY-ZN-C: 豐原→竹南 (山線+成追+海線)")
    coords, progress = build_crossline_track([
        {'source_track': 'BB-ZN-ZY-M-1', 'origin': '3230', 'dest': '3330'},  # 山線: 豐原→烏日
        {'source_track': 'CZ-CG-ZF', 'origin': '3330', 'dest': '2260'},      # 成追線: 成功→追分
        {'source_track': 'BB-ZY-ZN-C-0', 'origin': '2260', 'dest': '1250'},  # 海線: 追分→竹南
    ], 'OD-FY-ZN-C', all_progress)
    save_track('OD-FY-ZN-C', coords, progress, ['BB-ZN-ZY-M-1', 'CZ-CG-ZF', 'BB-ZY-ZN-C-0'], all_progress)

    # ============================================================
    # 3. OD-CZ-HL: 潮州→花蓮 via 西幹+宜蘭 (for TC-PP-172, TC-PP-176, CG-554)
    # ============================================================
    print("\n[3] OD-CZ-HL: 潮州→花蓮 (西幹+宜蘭)")
    coords, progress = build_crossline_track([
        {'source_track': 'BB-CZ-KL-0', 'origin': '5050', 'dest': '0920'},  # 西幹: 潮州→八堵
        {'source_track': 'YL-SL-HL-0', 'origin': '0920', 'dest': '7000'},  # 宜蘭: 八堵→花蓮
    ], 'OD-CZ-HL', all_progress)
    save_track('OD-CZ-HL', coords, progress, ['BB-CZ-KL-0', 'YL-SL-HL-0'], all_progress)

    # ============================================================
    # 4. OD-HL-CZ: 花蓮→潮州 via 宜蘭+西幹 (for TC-PP-175, TC-PP-181)
    # ============================================================
    print("\n[4] OD-HL-CZ: 花蓮→潮州 (宜蘭+西幹)")
    coords, progress = build_crossline_track([
        {'source_track': 'YL-HL-SL-1', 'origin': '7000', 'dest': '0920'},  # 宜蘭: 花蓮→八堵
        {'source_track': 'BB-KL-CZ-1', 'origin': '0920', 'dest': '5050'},  # 西幹: 八堵→潮州
    ], 'OD-HL-CZ', all_progress)
    save_track('OD-HL-CZ', coords, progress, ['YL-HL-SL-1', 'BB-KL-CZ-1'], all_progress)

    # ============================================================
    # 5. OD-NK-TT: 南港→台東 via 西幹+南迴 (for TC-161, PP-165)
    # ============================================================
    print("\n[5] OD-NK-TT: 南港→台東 (西幹+南迴)")
    coords, progress = build_crossline_track([
        {'source_track': 'BB-KL-CZ-1', 'origin': '0980', 'dest': '4340'},  # 西幹: 南港→新左營
        {'source_track': 'SK-ZY-TT-1', 'origin': '4340', 'dest': '6000'},  # 南迴: 新左營→台東
    ], 'OD-NK-TT', all_progress)
    save_track('OD-NK-TT', coords, progress, ['BB-KL-CZ-1', 'SK-ZY-TT-1'], all_progress)

    # ============================================================
    # 6. OD-TT-NK: 台東→七堵 via 南迴+西幹 (for PP-162, TC-168)
    #    延伸到七堵(0930) 以涵蓋 TC-168 (台東→七堵)
    #    PP-162 (台東→南港) 也能 fuzzy match 到此軌道
    # ============================================================
    print("\n[6] OD-TT-NK: 台東→七堵 (南迴+西幹)")
    coords, progress = build_crossline_track([
        {'source_track': 'SK-TT-ZY-0', 'origin': '6000', 'dest': '4340'},  # 南迴: 台東→新左營
        {'source_track': 'BB-CZ-KL-0', 'origin': '4340', 'dest': '0930'},  # 西幹: 新左營→七堵
    ], 'OD-TT-NK', all_progress)
    save_track('OD-TT-NK', coords, progress, ['SK-TT-ZY-0', 'BB-CZ-KL-0'], all_progress)

    # ============================================================
    # 7. OD-CY-SHL: 嘉義→沙崙 (主線+沙崙支線)
    #    修正：原軌道誤走主線到新左營，應在臺南轉沙崙支線
    # ============================================================
    print("\n[7] OD-CY-SHL: 嘉義→沙崙 (主線+沙崙支線)")
    coords, progress = build_crossline_track([
        {'source_track': 'BB-KL-CZ-1', 'origin': '4080', 'dest': '4220'},  # 主線: 嘉義→臺南
        {'source_track': 'SH-TN-SL', 'origin': '4220', 'dest': '4272'},    # 沙崙支線: 臺南→沙崙
    ], 'OD-CY-SHL', all_progress)
    save_track('OD-CY-SHL', coords, progress, ['BB-KL-CZ-1', 'SH-TN-SL'], all_progress)

    # ============================================================
    # 8. OD-SHL-CY: 沙崙→嘉義 (沙崙支線+主線)
    # ============================================================
    print("\n[8] OD-SHL-CY: 沙崙→嘉義 (沙崙支線+主線)")
    coords, progress = build_crossline_track([
        {'source_track': 'SH-SL-TN', 'origin': '4272', 'dest': '4220'},    # 沙崙支線: 沙崙→臺南
        {'source_track': 'BB-CZ-KL-0', 'origin': '4220', 'dest': '4080'},  # 主線: 臺南→嘉義
    ], 'OD-SHL-CY', all_progress)
    save_track('OD-SHL-CY', coords, progress, ['SH-SL-TN', 'BB-CZ-KL-0'], all_progress)

    # ============================================================
    # 9. OD-大甲-FY: 大甲→豐原 via 海線+成追線+山線
    #    海線到追分，成追線到成功(烏日)，山線到豐原
    # ============================================================
    print("\n[9] OD-大甲-FY: 大甲→豐原 (海線+成追+山線)")
    coords, progress = build_crossline_track([
        {'source_track': 'BB-ZN-ZY-C-1', 'origin': '2200', 'dest': '2260'},  # 海線: 大甲→追分
        {'source_track': 'CZ-ZF-CG', 'origin': '2260', 'dest': '3330'},      # 成追線: 追分→成功
        {'source_track': 'BB-ZY-ZN-M-0', 'origin': '3330', 'dest': '3230'},  # 山線: 烏日→豐原
    ], 'OD-大甲-FY', all_progress)
    save_track('OD-大甲-FY', coords, progress, ['BB-ZN-ZY-C-1', 'CZ-ZF-CG', 'BB-ZY-ZN-M-0'], all_progress)

    # ============================================================
    # 10. OD-FY-大甲: 豐原→大甲 via 山線+成追線+海線
    # ============================================================
    print("\n[10] OD-FY-大甲: 豐原→大甲 (山線+成追+海線)")
    coords, progress = build_crossline_track([
        {'source_track': 'BB-ZN-ZY-M-1', 'origin': '3230', 'dest': '3330'},  # 山線: 豐原→烏日
        {'source_track': 'CZ-CG-ZF', 'origin': '3330', 'dest': '2260'},      # 成追線: 成功→追分
        {'source_track': 'BB-ZY-ZN-C-0', 'origin': '2260', 'dest': '2200'},  # 海線: 追分→大甲
    ], 'OD-FY-大甲', all_progress)
    save_track('OD-FY-大甲', coords, progress, ['BB-ZN-ZY-M-1', 'CZ-CG-ZF', 'BB-ZY-ZN-C-0'], all_progress)

    # ============================================================
    # 11. OD-大甲-TC: 大甲→臺中 via 海線+成追線+山線
    # ============================================================
    print("\n[11] OD-大甲-TC: 大甲→臺中 (海線+成追+山線)")
    coords, progress = build_crossline_track([
        {'source_track': 'BB-ZN-ZY-C-1', 'origin': '2200', 'dest': '2260'},  # 海線: 大甲→追分
        {'source_track': 'CZ-ZF-CG', 'origin': '2260', 'dest': '3330'},      # 成追線: 追分→成功
        {'source_track': 'BB-ZY-ZN-M-0', 'origin': '3330', 'dest': '3300'},  # 山線: 烏日→臺中
    ], 'OD-大甲-TC', all_progress)
    save_track('OD-大甲-TC', coords, progress, ['BB-ZN-ZY-C-1', 'CZ-ZF-CG', 'BB-ZY-ZN-M-0'], all_progress)

    # ============================================================
    # 12. OD-TC-大甲: 臺中→大甲 via 山線+成追線+海線
    # ============================================================
    print("\n[12] OD-TC-大甲: 臺中→大甲 (山線+成追+海線)")
    coords, progress = build_crossline_track([
        {'source_track': 'BB-ZN-ZY-M-1', 'origin': '3300', 'dest': '3330'},  # 山線: 臺中→烏日
        {'source_track': 'CZ-CG-ZF', 'origin': '3330', 'dest': '2260'},      # 成追線: 成功→追分
        {'source_track': 'BB-ZY-ZN-C-0', 'origin': '2260', 'dest': '2200'},  # 海線: 追分→大甲
    ], 'OD-TC-大甲', all_progress)
    save_track('OD-TC-大甲', coords, progress, ['BB-ZN-ZY-M-1', 'CZ-CG-ZF', 'BB-ZY-ZN-C-0'], all_progress)

    # ============================================================
    # 13. OD-大甲-ML: 大甲→苗栗 via 海線+成追線+山線
    # ============================================================
    print("\n[13] OD-大甲-ML: 大甲→苗栗 (海線+成追+山線)")
    coords, progress = build_crossline_track([
        {'source_track': 'BB-ZN-ZY-C-1', 'origin': '2200', 'dest': '2260'},  # 海線: 大甲→追分
        {'source_track': 'CZ-ZF-CG', 'origin': '2260', 'dest': '3330'},      # 成追線: 追分→成功
        {'source_track': 'BB-ZY-ZN-M-0', 'origin': '3330', 'dest': '3160'},  # 山線: 烏日→苗栗
    ], 'OD-大甲-ML', all_progress)
    save_track('OD-大甲-ML', coords, progress, ['BB-ZN-ZY-C-1', 'CZ-ZF-CG', 'BB-ZY-ZN-M-0'], all_progress)

    # 儲存 station_progress
    save_progress(all_progress)
    print("\n✓ 所有跨線軌道建立完成")


if __name__ == '__main__':
    main()
