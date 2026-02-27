#!/usr/bin/env python3
"""
rebuild_affected_od_tracks.py - 重建所有依賴已更新上游軌道的 Layer 5 OD extract 軌道

背景：
  YL 宜蘭線相關軌道已更新（Layer 1-4），需要重建所有依賴這些軌道的 OD 子段。

流程：
  1. 重建 6 條反向 BB 骨幹軌道（使用 merge_tracks.py）
  2. 找出所有 source_track 指向已更新軌道的 OD 軌道
  3. 用 extract_od_segment 邏輯重建每條 OD 軌道
"""

import json
import os
import math
import subprocess
import glob
from typing import Dict, List, Optional, Tuple

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
PROGRESS_FILE = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')
MERGE_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'tra', 'prepare_real_timetable', 'merge_tracks.py')

# ======================================================================
# 已更新的上游軌道（Layer 1-4）
# ======================================================================
UPDATED_UPSTREAM = {
    # YL tracks
    'YL-BD-SA-0', 'YL-BD-SA-1', 'YL-SL-SA-0', 'YL-SL-SA-1',
    'YL-SL-HL-0', 'YL-SL-HL-1', 'YL-SL-TT-0', 'YL-SL-TT-1',
    'YL-SL-ZY-0', 'YL-SL-ZY-1',
    'YL-SA-SL-1', 'YL-HL-SL-1', 'YL-TT-SL-1', 'YL-ZY-SL-1',
    # BB tracks (already rebuilt)
    'BB-SA-ZN-0', 'BB-SA-ZY-0',
    'BB-HL-ZN-0', 'BB-HL-ZY-0',
    'BB-TT-ZN-0', 'BB-TT-ZY-0',
    # OD tracks (already rebuilt)
    'OD-CZ-HL', 'OD-HL-CZ',
}

# 需要先重建的反向 BB 骨幹軌道（使用已更新的 YL 軌道作為組件）
REVERSE_BB_TO_REBUILD = {
    'BB-ZN-SA-1': ['WL-ZN-SL-0', 'YL-SL-SA-0'],
    'BB-ZN-HL-1': ['WL-ZN-SL-0', 'YL-SL-HL-0'],
    'BB-ZN-TT-1': ['WL-ZN-SL-0', 'YL-SL-TT-0'],
    'BB-ZY-SA-1': ['WL-ZY-CH-1', 'WL-M-CH-ZN-1', 'WL-ZN-SL-0', 'YL-SL-SA-0'],
    'BB-ZY-HL-1': ['WL-ZY-CH-1', 'WL-M-CH-ZN-1', 'WL-ZN-SL-0', 'YL-SL-HL-0'],
    'BB-ZY-TT-1': ['WL-ZY-CH-1', 'WL-M-CH-ZN-1', 'WL-ZN-SL-0', 'YL-SL-TT-0'],
}


def euclidean_dist(c1, c2):
    """歐幾里得距離"""
    return math.sqrt((c2[0] - c1[0]) ** 2 + (c2[1] - c1[1]) ** 2)


def load_progress() -> Dict[str, Dict[str, float]]:
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_progress(data: Dict[str, Dict[str, float]]):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def rebuild_backbone(bb_id: str, source_tracks: List[str]) -> bool:
    """使用 merge_tracks.py 重建骨幹軌道"""
    cmd = [
        'python3', MERGE_SCRIPT,
        '--tracks', *source_tracks,
        '--output-id', bb_id,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    錯誤: {result.stderr}")
        return False
    return True


def extract_od_segment(
    source_track: str,
    origin_id: str,
    dest_id: str,
    output_id: str,
    station_progress: Dict[str, Dict[str, float]],
) -> Optional[Dict[str, float]]:
    """從骨幹軌道擷取 O-D 子段（與 batch_generate_od.py 相同邏輯）"""

    source_progress = station_progress.get(source_track)
    if not source_progress:
        return None

    if origin_id not in source_progress or dest_id not in source_progress:
        return None

    origin_prog = source_progress[origin_id]
    dest_prog = source_progress[dest_id]
    segment_length = dest_prog - origin_prog

    if segment_length <= 0:
        return None

    # 計算新的 station_progress
    new_progress = {}
    for station_id, prog in source_progress.items():
        if origin_prog <= prog <= dest_prog:
            new_prog = (prog - origin_prog) / segment_length
            new_progress[station_id] = round(new_prog, 6)

    # 載入來源軌道 GeoJSON
    source_path = os.path.join(TRACKS_OD_DIR, f"{source_track}.geojson")
    if not os.path.exists(source_path):
        return None

    with open(source_path, 'r', encoding='utf-8') as f:
        source_geojson = json.load(f)

    coords = source_geojson['features'][0]['geometry']['coordinates']

    # 計算累積距離
    cum_dist = [0.0]
    for i in range(1, len(coords)):
        cum_dist.append(cum_dist[-1] + euclidean_dist(coords[i - 1], coords[i]))
    total_len = cum_dist[-1]

    # 擷取座標
    start_dist = origin_prog * total_len
    end_dist = dest_prog * total_len

    extracted = []
    for coord, d in zip(coords, cum_dist):
        if start_dist <= d <= end_dist:
            extracted.append(coord)

    if len(extracted) < 2:
        start_idx = min(range(len(cum_dist)), key=lambda i: abs(cum_dist[i] - start_dist))
        end_idx = min(range(len(cum_dist)), key=lambda i: abs(cum_dist[i] - end_dist))
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
        extracted = coords[start_idx:end_idx + 1]

    # 建立新的 GeoJSON
    new_geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": output_id,
                "source_track": source_track,
                "point_count": len(extracted)
            },
            "geometry": {
                "type": "LineString",
                "coordinates": extracted
            }
        }]
    }

    # 儲存
    output_path = os.path.join(TRACKS_OD_DIR, f"{output_id}.geojson")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_geojson, f, ensure_ascii=False, indent=2)

    return new_progress


def find_affected_od_tracks(updated_sources: set) -> List[Dict]:
    """找出所有 source_track 指向已更新軌道的 OD 軌道"""
    affected = []
    for filepath in sorted(glob.glob(os.path.join(TRACKS_OD_DIR, 'OD-*.geojson'))):
        fname = os.path.basename(filepath)
        track_id = fname.replace('.geojson', '')
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            source = data['features'][0]['properties'].get('source_track', '')
            if source in updated_sources:
                affected.append({
                    'track_id': track_id,
                    'source_track': source,
                    'file': filepath,
                })
        except Exception as e:
            print(f"  警告: 無法讀取 {fname}: {e}")
    return affected


def get_od_origin_dest(track_id: str, station_progress: Dict[str, Dict[str, float]]) -> Optional[Tuple[str, str]]:
    """從 station_progress 取得 OD 軌道的 origin 和 destination"""
    progress_map = station_progress.get(track_id)
    if not progress_map:
        return None

    sorted_stations = sorted(progress_map.items(), key=lambda x: x[1])
    if len(sorted_stations) < 2:
        return None

    origin_id = sorted_stations[0][0]   # progress = 0.0
    dest_id = sorted_stations[-1][0]     # progress = 1.0
    return (origin_id, dest_id)


def main():
    print("=" * 70)
    print("重建依賴已更新上游軌道的 Layer 5 OD extract 軌道")
    print("=" * 70)

    # ================================================================
    # Phase 1: 重建反向 BB 骨幹軌道
    # ================================================================
    print("\n[Phase 1] 重建反向 BB 骨幹軌道...")

    bb_success = 0
    bb_failed = 0

    for bb_id, source_tracks in sorted(REVERSE_BB_TO_REBUILD.items()):
        print(f"\n  重建 {bb_id}: {' + '.join(source_tracks)}")
        if rebuild_backbone(bb_id, source_tracks):
            bb_success += 1
            print(f"    ✓ 成功")
        else:
            bb_failed += 1
            print(f"    ✗ 失敗")

    print(f"\n  BB 骨幹重建: {bb_success} 成功, {bb_failed} 失敗")

    # ================================================================
    # Phase 2: 找出所有需要重建的 OD 軌道
    # ================================================================
    print("\n[Phase 2] 掃描需要重建的 OD 軌道...")

    # 合併所有已更新的軌道（包含剛重建的反向 BB）
    all_updated = set(UPDATED_UPSTREAM)
    for bb_id in REVERSE_BB_TO_REBUILD:
        all_updated.add(bb_id)

    affected = find_affected_od_tracks(all_updated)
    print(f"  找到 {len(affected)} 條需要重建的 OD 軌道")

    # 按 source_track 分組顯示
    by_source = {}
    for item in affected:
        src = item['source_track']
        by_source.setdefault(src, []).append(item['track_id'])
    for src, tracks in sorted(by_source.items()):
        print(f"    {src}: {len(tracks)} 條")

    # ================================================================
    # Phase 3: 重建每條 OD 軌道
    # ================================================================
    print("\n[Phase 3] 重建 OD 軌道...")

    # 重新載入 station_progress（包含已重建的 BB 軌道）
    station_progress = load_progress()

    od_success = 0
    od_failed = []

    for item in affected:
        track_id = item['track_id']
        source_track = item['source_track']

        # 取得 origin 和 destination
        od_info = get_od_origin_dest(track_id, station_progress)
        if not od_info:
            od_failed.append((track_id, "找不到 origin/dest"))
            print(f"  ✗ {track_id}: 找不到 station_progress 中的 origin/dest")
            continue

        origin_id, dest_id = od_info

        # 重建
        new_progress = extract_od_segment(
            source_track, origin_id, dest_id, track_id, station_progress
        )

        if new_progress:
            station_progress[track_id] = new_progress
            od_success += 1

            # 簡短進度回報
            sorted_p = sorted(new_progress.items(), key=lambda x: x[1])
            first = sorted_p[0][0]
            last = sorted_p[-1][0]
            n_stations = len(new_progress)
            print(f"  ✓ {track_id} ({first}→{last}, {n_stations}站)")
        else:
            od_failed.append((track_id, "擷取失敗"))
            print(f"  ✗ {track_id}: 擷取失敗 (origin={origin_id}, dest={dest_id})")

    # 儲存更新後的 station_progress
    save_progress(station_progress)
    print(f"\n  ✓ 已更新 od_station_progress.json")

    # ================================================================
    # 摘要
    # ================================================================
    print("\n" + "=" * 70)
    print("重建結果摘要")
    print("=" * 70)
    print(f"  BB 骨幹軌道: {bb_success} 成功 / {bb_failed} 失敗")
    print(f"  OD 軌道:     {od_success} 成功 / {len(od_failed)} 失敗")
    print(f"  合計重建:     {bb_success + od_success} 條軌道")

    if od_failed:
        print(f"\n  失敗清單:")
        for tid, reason in od_failed:
            print(f"    {tid}: {reason}")

    print("=" * 70)
    return len(od_failed) == 0 and bb_failed == 0


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
