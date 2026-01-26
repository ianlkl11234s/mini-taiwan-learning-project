#!/usr/bin/env python3
"""
batch_generate_od.py - 批次產生所有缺少的 O-D 軌道

策略：
1. 先建立骨幹軌道（合併多條基礎軌道）
2. 從骨幹軌道擷取各 O-D 子區段
3. 更新 od_station_progress.json

使用方式：
    python scripts/tra/prepare_real_timetable/batch_generate_od.py
    python scripts/tra/prepare_real_timetable/batch_generate_od.py --dry-run
"""

import json
import os
import argparse
import subprocess
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
PROGRESS_FILE = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')
MISSING_FILE = os.path.join(DATA_DIR, 'data', 'missing_od_tracks.json')
STATION_FILE = os.path.join(DATA_DIR, 'data', 'station_mapping.json')

# 骨幹軌道定義：合併多條基礎軌道以覆蓋更大範圍
BACKBONE_TRACKS = {
    # 西部幹線北段（含基隆）
    "BB-ZN-KL-0": ["WL-ZN-SL-0", "WL-SL-BD-0", "KL-BD-KL-0"],  # 竹南→基隆
    "BB-KL-ZN-1": ["KL-KL-BD-1", "WL-BD-SL-1", "WL-SL-ZN-1"],  # 基隆→竹南

    # 西部幹線全線（山線）
    "BB-ZY-ZN-M-0": ["WL-ZY-CH-1", "WL-M-CH-ZN-1"],  # 新左營→竹南 (山線)
    "BB-ZN-ZY-M-1": ["WL-M-ZN-CH-0", "WL-CH-ZY-0"],  # 竹南→新左營 (山線)

    # 西部幹線全線（海線）
    "BB-ZY-ZN-C-0": ["WL-ZY-CH-1", "WL-C-CH-ZN-0"],  # 新左營→竹南 (海線)
    "BB-ZN-ZY-C-1": ["WL-C-ZN-CH-1", "WL-CH-ZY-0"],  # 竹南→新左營 (海線)

    # 西部幹線 + 北段（山線，到基隆）
    "BB-ZY-KL-M-0": ["WL-ZY-CH-1", "WL-M-CH-ZN-1", "WL-ZN-SL-0", "WL-SL-BD-0", "KL-BD-KL-0"],
    "BB-KL-ZY-M-1": ["KL-KL-BD-1", "WL-BD-SL-1", "WL-SL-ZN-1", "WL-M-ZN-CH-0", "WL-CH-ZY-0"],

    # 沙崙線 + 西部幹線
    "BB-SL-ZY-0": ["SH-SL-TN", "WL-ZY-CH-1"],  # 沙崙→新左營 (先往臺南再南下)
    "BB-ZY-SL-1": ["WL-CH-ZY-0", "SH-TN-SL"],  # 新左營→沙崙

    # 沙崙線 + 北上
    "BB-SL-ZN-0": ["SH-SL-TN", "WL-ZY-CH-1", "WL-M-CH-ZN-1"],  # 沙崙→竹南

    # 屏東線/南迴線 + 西部幹線（山線）
    "BB-CZ-ZN-0": ["PT-PL-ZY-1", "WL-ZY-CH-1", "WL-M-CH-ZN-1"],  # 潮州→竹南 (經新左營)
    "BB-ZN-CZ-1": ["WL-M-ZN-CH-0", "WL-CH-ZY-0", "PT-ZY-PL-0"],  # 竹南→潮州

    # 屏東線/南迴線 + 西部幹線 + 北段（到基隆）
    "BB-CZ-KL-0": ["PT-PL-ZY-1", "WL-ZY-CH-1", "WL-M-CH-ZN-1", "WL-ZN-SL-0", "WL-SL-BD-0", "KL-BD-KL-0"],
    "BB-KL-CZ-1": ["KL-KL-BD-1", "WL-BD-SL-1", "WL-SL-ZN-1", "WL-M-ZN-CH-0", "WL-CH-ZY-0", "PT-ZY-PL-0"],

    # 宜蘭線 + 西部幹線北段
    "BB-SA-ZN-0": ["YL-SA-SL-1", "WL-SL-ZN-1"],  # 蘇澳→竹南
    "BB-ZN-SA-1": ["WL-ZN-SL-0", "YL-SL-SA-0"],  # 竹南→蘇澳

    # 宜蘭線 + 西部幹線（山線，到彰化以南）
    "BB-SA-ZY-0": ["YL-SA-SL-1", "WL-SL-ZN-1", "WL-M-ZN-CH-0", "WL-CH-ZY-0"],  # 蘇澳→新左營
    "BB-ZY-SA-1": ["WL-ZY-CH-1", "WL-M-CH-ZN-1", "WL-ZN-SL-0", "YL-SL-SA-0"],  # 新左營→蘇澳

    # 花蓮方向 + 西部幹線
    "BB-HL-ZN-0": ["YL-HL-SL-1", "WL-SL-ZN-1"],  # 花蓮→竹南
    "BB-ZN-HL-1": ["WL-ZN-SL-0", "YL-SL-HL-0"],  # 竹南→花蓮
    "BB-HL-ZY-0": ["YL-HL-SL-1", "WL-SL-ZN-1", "WL-M-ZN-CH-0", "WL-CH-ZY-0"],  # 花蓮→新左營
    "BB-ZY-HL-1": ["WL-ZY-CH-1", "WL-M-CH-ZN-1", "WL-ZN-SL-0", "YL-SL-HL-0"],  # 新左營→花蓮

    # 臺東方向 + 西部幹線
    "BB-TT-ZN-0": ["YL-TT-SL-1", "WL-SL-ZN-1"],  # 臺東→竹南
    "BB-ZN-TT-1": ["WL-ZN-SL-0", "YL-SL-TT-0"],  # 竹南→臺東
    "BB-TT-ZY-0": ["YL-TT-SL-1", "WL-SL-ZN-1", "WL-M-ZN-CH-0", "WL-CH-ZY-0"],  # 臺東→新左營
    "BB-ZY-TT-1": ["WL-ZY-CH-1", "WL-M-CH-ZN-1", "WL-ZN-SL-0", "YL-SL-TT-0"],  # 新左營→臺東
}


def load_station_progress() -> Dict[str, Dict[str, float]]:
    """載入車站進度表"""
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_station_progress(data: Dict[str, Dict[str, float]]):
    """儲存車站進度表"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_missing_od() -> List[Dict]:
    """載入需要新建的 O-D 清單"""
    with open(MISSING_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('need_new', [])


def load_station_names() -> Dict[str, str]:
    """載入車站名稱對照"""
    with open(STATION_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('id_to_name', {})


def run_merge_tracks(track_ids: List[str], output_id: str, dry_run: bool = False) -> bool:
    """執行軌道合併"""
    cmd = [
        'python3',
        os.path.join(BASE_DIR, 'scripts/tra/prepare_real_timetable/merge_tracks.py'),
        '--tracks', *track_ids,
        '--output-id', output_id
    ]
    if dry_run:
        cmd.append('--dry-run')

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  錯誤: {result.stderr}")
        return False
    return True


def find_covering_track(
    origin_id: str,
    dest_id: str,
    station_progress: Dict[str, Dict[str, float]]
) -> Optional[Tuple[str, float, float]]:
    """找到包含起點和終點的軌道"""
    candidates = []

    for track_id, progress_map in station_progress.items():
        if origin_id in progress_map and dest_id in progress_map:
            origin_prog = progress_map[origin_id]
            dest_prog = progress_map[dest_id]

            if origin_prog < dest_prog:
                station_count = len(progress_map)
                candidates.append((track_id, origin_prog, dest_prog, station_count))

    if not candidates:
        return None

    # 優先選擇涵蓋車站數最多的軌道
    best = max(candidates, key=lambda x: x[3])
    return (best[0], best[1], best[2])


def extract_od_segment(
    source_track: str,
    origin_id: str,
    dest_id: str,
    output_id: str,
    station_progress: Dict[str, Dict[str, float]],
    dry_run: bool = False
) -> Optional[Dict[str, float]]:
    """從軌道擷取 O-D 子區段"""
    import math

    # 取得來源軌道資料
    source_progress = station_progress[source_track]
    origin_prog = source_progress[origin_id]
    dest_prog = source_progress[dest_id]

    # 計算新的 station_progress
    segment_length = dest_prog - origin_prog
    if segment_length <= 0:
        return None

    new_progress = {}
    for station_id, prog in source_progress.items():
        if prog >= origin_prog and prog <= dest_prog:
            new_prog = (prog - origin_prog) / segment_length
            new_progress[station_id] = round(new_prog, 6)

    if dry_run:
        return new_progress

    # 載入來源軌道 GeoJSON
    source_path = os.path.join(TRACKS_OD_DIR, f"{source_track}.geojson")
    with open(source_path, 'r', encoding='utf-8') as f:
        source_geojson = json.load(f)

    coords = source_geojson['features'][0]['geometry']['coordinates']

    # 計算累積距離
    def euclidean_dist(c1, c2):
        return math.sqrt((c2[0]-c1[0])**2 + (c2[1]-c1[1])**2)

    cum_dist = [0.0]
    for i in range(1, len(coords)):
        cum_dist.append(cum_dist[-1] + euclidean_dist(coords[i-1], coords[i]))
    total_len = cum_dist[-1]

    # 擷取座標
    start_dist = origin_prog * total_len
    end_dist = dest_prog * total_len

    extracted = []
    for coord, d in zip(coords, cum_dist):
        if d >= start_dist and d <= end_dist:
            extracted.append(coord)

    if len(extracted) < 2:
        # fallback: 取最近的區段
        start_idx = min(range(len(cum_dist)), key=lambda i: abs(cum_dist[i] - start_dist))
        end_idx = min(range(len(cum_dist)), key=lambda i: abs(cum_dist[i] - end_dist))
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
        extracted = coords[start_idx:end_idx+1]

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


def generate_od_track_id(origin_id: str, dest_id: str, origin_name: str, dest_name: str) -> str:
    """產生 O-D 軌道 ID"""
    # 簡化車站代碼
    def shorten(name):
        mapping = {
            '基隆': 'KL', '八堵': 'BD', '七堵': 'QD', '臺北': 'TP', '樹林': 'SL',
            '板橋': 'BC', '新竹': 'HC', '竹南': 'ZN', '苗栗': 'ML', '彰化': 'CH',
            '臺南': 'TN', '高雄': 'KS', '新左營': 'ZY', '潮州': 'CZ', '枋寮': 'PL',
            '臺東': 'TT', '花蓮': 'HL', '蘇澳': 'SA', '宜蘭': 'YL', '羅東': 'LD',
            '沙崙': 'SHL', '善化': 'SH', '嘉義': 'CY', '后里': 'HL2', '豐原': 'FY',
            '臺中': 'TC', '二水': 'ES', '員林': 'YL2', '田中': 'TZ', '斗六': 'DL',
            '六家': 'LJ', '內灣': 'NB', '竹中': 'CC',
        }
        return mapping.get(name, name[:2])

    return f"OD-{shorten(origin_name)}-{shorten(dest_name)}"


def main():
    parser = argparse.ArgumentParser(description='批次產生 O-D 軌道')
    parser.add_argument('--dry-run', action='store_true', help='只顯示會做什麼')
    parser.add_argument('--limit', type=int, default=0, help='限制處理數量 (0=全部)')
    args = parser.parse_args()

    print("=" * 60)
    print("Phase 1: 批次產生 O-D 軌道")
    print("=" * 60)

    # 載入資料
    print("\n[1/4] 載入資料...")
    station_progress = load_station_progress()
    missing_od = load_missing_od()
    station_names = load_station_names()

    print(f"  現有軌道: {len(station_progress)} 條")
    print(f"  缺少 O-D: {len(missing_od)} 組")

    # 建立骨幹軌道
    print("\n[2/4] 建立骨幹軌道...")

    for bb_id, source_tracks in BACKBONE_TRACKS.items():
        if bb_id in station_progress:
            print(f"  {bb_id}: 已存在，跳過")
            continue

        # 檢查所有來源軌道是否存在
        all_exist = all(t in station_progress for t in source_tracks)
        if not all_exist:
            missing = [t for t in source_tracks if t not in station_progress]
            print(f"  {bb_id}: 來源軌道不存在 {missing}，跳過")
            continue

        print(f"  建立 {bb_id}: {' + '.join(source_tracks)}")
        if not args.dry_run:
            success = run_merge_tracks(source_tracks, bb_id, dry_run=False)
            if success:
                # 重新載入 station_progress
                station_progress = load_station_progress()
                print(f"    ✓ 完成")
            else:
                print(f"    ✗ 失敗")

    # 處理缺少的 O-D
    print("\n[3/4] 產生 O-D 軌道...")

    # 重新載入 station_progress（包含新建的骨幹軌道）
    station_progress = load_station_progress()

    processed = 0
    success_count = 0
    failed = []

    for item in missing_od:
        if args.limit > 0 and processed >= args.limit:
            break

        origin_id = item['origin_id']
        dest_id = item['destination_id']
        origin_name = item['origin']
        dest_name = item['destination']
        od_key = item['od_key']

        # 檢查是否已存在
        output_id = generate_od_track_id(origin_id, dest_id, origin_name, dest_name)
        if output_id in station_progress:
            continue

        # 找到覆蓋的軌道
        result = find_covering_track(origin_id, dest_id, station_progress)

        if not result:
            failed.append({
                'od_key': od_key,
                'origin_id': origin_id,
                'dest_id': dest_id,
                'reason': '找不到覆蓋軌道'
            })
            continue

        source_track, _, _ = result

        print(f"  {od_key} ({origin_id}→{dest_id}) ← {source_track}")

        if not args.dry_run:
            new_progress = extract_od_segment(
                source_track, origin_id, dest_id, output_id,
                station_progress, dry_run=False
            )

            if new_progress:
                station_progress[output_id] = new_progress
                success_count += 1
            else:
                failed.append({
                    'od_key': od_key,
                    'origin_id': origin_id,
                    'dest_id': dest_id,
                    'reason': '擷取失敗'
                })
        else:
            success_count += 1

        processed += 1

    # 儲存更新後的 station_progress
    if not args.dry_run:
        save_station_progress(station_progress)

    # 統計
    print("\n[4/4] 完成統計")
    print(f"  處理: {processed} 個 O-D")
    print(f"  成功: {success_count} 個")
    print(f"  失敗: {len(failed)} 個")

    if failed:
        print("\n  失敗清單:")
        for f in failed[:10]:
            print(f"    {f['od_key']}: {f['reason']}")
        if len(failed) > 10:
            print(f"    ... 還有 {len(failed) - 10} 個")

    if args.dry_run:
        print("\n[Dry run] 未實際寫入檔案")

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)

    return len(failed) == 0


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
