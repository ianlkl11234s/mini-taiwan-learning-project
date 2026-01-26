#!/usr/bin/env python3
"""
04_analyze_missing_od.py - 分析缺少的 O-D 軌道

功能：
1. 比較現有 O-D 軌道與 TDX 時刻表需求
2. 列出需要新建的 O-D 軌道
3. 分析可以從哪些基礎軌道擷取

使用方式：
    python scripts/tra/prepare_real_timetable/04_analyze_missing_od.py

輸入：
    public/data/tra/data/od_to_base_track.json
    public/data/tra/tracks_od/*.geojson
    public/data/tra/tracks_od/od_station_progress.json

產出：
    public/data/tra/data/missing_od_tracks.json
"""

import json
import os
import glob
from typing import Dict, List, Set
from collections import defaultdict

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
INPUT_DIR = os.path.join(DATA_DIR, 'data')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
OUTPUT_DIR = INPUT_DIR


def load_existing_od_tracks() -> Set[str]:
    """載入現有的 O-D 軌道清單"""
    od_tracks = set()

    # 從 GeoJSON 檔案名稱提取
    pattern = os.path.join(TRACKS_OD_DIR, "*.geojson")
    for filepath in glob.glob(pattern):
        filename = os.path.basename(filepath)
        # 移除 .geojson 副檔名
        track_id = filename.replace(".geojson", "")
        od_tracks.add(track_id)

    return od_tracks


def load_od_station_progress() -> Dict:
    """載入現有的 O-D 車站進度表"""
    progress_file = os.path.join(TRACKS_OD_DIR, "od_station_progress.json")
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_od_mapping() -> Dict:
    """載入 O-D 對照表"""
    mapping_file = os.path.join(INPUT_DIR, "od_to_base_track.json")
    if not os.path.exists(mapping_file):
        print(f"錯誤: 找不到對照表: {mapping_file}")
        print("請先執行 03_build_od_mapping.py")
        return None

    with open(mapping_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_od_track_id(origin_id: str, dest_id: str, base_tracks: List[str]) -> str:
    """產生 O-D 軌道 ID"""
    # 使用簡短車站代碼
    station_codes = {
        # 西部幹線北段
        "0900": "KL", "0920": "BD", "0930": "QD", "1000": "TP",
        "1040": "SL", "1080": "BC",
        # 竹南-新竹
        "1210": "HC", "1250": "ZN",
        # 山線
        "3330": "CG", "3360": "CH",
        # 海線
        "2260": "ZF",
        # 南段
        "4270": "ZZ", "4340": "ZY",
        # 宜蘭/北迴
        "7000": "HL", "7120": "SA", "7130": "SX", "7190": "YL",
        # 屏東/南迴
        "5000": "PD", "5120": "PL", "6000": "TT",
        # 支線
        "1193": "CC", "1199": "NB", "1205": "LJ",
        "4271": "SL2", "4275": "SHL",
        "3430": "ES", "3436": "CT",
        "7331": "SD", "7339": "JT",
        "7361": "RF", "7369": "BD2",
    }

    origin_code = station_codes.get(origin_id, origin_id[-2:])
    dest_code = station_codes.get(dest_id, dest_id[-2:])

    # 使用主要路線作為前綴
    prefix = base_tracks[0] if base_tracks else "XX"

    return f"{prefix}-{origin_code}-{dest_code}"


def match_existing_track(origin_id: str, dest_id: str, existing_tracks: Set[str],
                          od_progress: Dict) -> str:
    """嘗試匹配現有的 O-D 軌道"""
    # 檢查是否有包含起點和終點的現有軌道
    for track_id in existing_tracks:
        progress = od_progress.get(track_id, {})
        station_ids = list(progress.keys())

        if origin_id in station_ids and dest_id in station_ids:
            # 檢查方向是否正確
            origin_idx = station_ids.index(origin_id)
            dest_idx = station_ids.index(dest_id)
            if origin_idx < dest_idx:
                return track_id

    return None


def main():
    print("=" * 60)
    print("Phase 0.4: 分析缺少的 O-D 軌道")
    print("=" * 60)

    # 載入資料
    print("\n[1/4] 載入資料...")
    od_mapping_data = load_od_mapping()
    if not od_mapping_data:
        return False

    od_mapping = od_mapping_data.get("od_mapping", {})
    print(f"  ✓ 載入 {len(od_mapping)} 個 O-D 組合需求")

    existing_tracks = load_existing_od_tracks()
    print(f"  ✓ 現有 {len(existing_tracks)} 條 O-D 軌道")

    od_progress = load_od_station_progress()
    print(f"  ✓ 載入 {len(od_progress)} 條軌道的車站進度")

    # 分析每個 O-D 組合
    print("\n[2/4] 分析 O-D 覆蓋情況...")

    covered = []      # 已有完全匹配的軌道
    can_extract = []  # 可從現有軌道擷取
    need_new = []     # 需要新建

    for od_key, mapping in od_mapping.items():
        origin_id = mapping["origin_id"]
        dest_id = mapping["destination_id"]
        base_tracks = mapping["base_tracks"]
        train_count = mapping["train_count"]

        # 嘗試匹配現有軌道
        matched_track = match_existing_track(origin_id, dest_id, existing_tracks, od_progress)

        if matched_track:
            covered.append({
                "od_key": od_key,
                "matched_track": matched_track,
                "train_count": train_count,
            })
        else:
            # 檢查是否可以從基礎軌道擷取
            can_extract_from = []
            for track_id, progress in od_progress.items():
                station_ids = list(progress.keys())
                if origin_id in station_ids and dest_id in station_ids:
                    origin_idx = station_ids.index(origin_id)
                    dest_idx = station_ids.index(dest_id)
                    if origin_idx < dest_idx:
                        can_extract_from.append(track_id)

            if can_extract_from:
                can_extract.append({
                    "od_key": od_key,
                    "origin_id": origin_id,
                    "origin": mapping["origin"],
                    "destination_id": dest_id,
                    "destination": mapping["destination"],
                    "base_tracks": base_tracks,
                    "train_count": train_count,
                    "train_types": mapping["train_types"],
                    "extract_from": can_extract_from,
                    "suggested_id": generate_od_track_id(origin_id, dest_id, base_tracks),
                })
            else:
                need_new.append({
                    "od_key": od_key,
                    "origin_id": origin_id,
                    "origin": mapping["origin"],
                    "destination_id": dest_id,
                    "destination": mapping["destination"],
                    "base_tracks": base_tracks,
                    "train_count": train_count,
                    "train_types": mapping["train_types"],
                    "suggested_id": generate_od_track_id(origin_id, dest_id, base_tracks),
                })

    # 統計
    total_trains_covered = sum(x["train_count"] for x in covered)
    total_trains_extractable = sum(x["train_count"] for x in can_extract)
    total_trains_new = sum(x["train_count"] for x in need_new)
    total_trains = total_trains_covered + total_trains_extractable + total_trains_new

    print(f"\n  覆蓋情況:")
    print(f"    ✓ 已覆蓋: {len(covered)} O-D ({total_trains_covered} 班, {total_trains_covered*100/total_trains:.1f}%)")
    print(f"    ◐ 可擷取: {len(can_extract)} O-D ({total_trains_extractable} 班, {total_trains_extractable*100/total_trains:.1f}%)")
    print(f"    ✗ 需新建: {len(need_new)} O-D ({total_trains_new} 班, {total_trains_new*100/total_trains:.1f}%)")

    # 按路線分類可擷取的 O-D
    print("\n[3/4] 分類待處理的 O-D...")

    by_route = defaultdict(list)
    for item in can_extract + need_new:
        main_route = item["base_tracks"][0] if item["base_tracks"] else "OTHER"
        by_route[main_route].append(item)

    print("\n  按主要路線分類:")
    for route, items in sorted(by_route.items(), key=lambda x: -sum(i["train_count"] for i in x[1])):
        train_count = sum(i["train_count"] for i in items)
        extractable = len([i for i in items if i in can_extract])
        new_needed = len([i for i in items if i in need_new])
        print(f"    {route}: {len(items)} O-D ({train_count} 班) - 可擷取 {extractable}, 需新建 {new_needed}")

    # 儲存結果
    print("\n[4/4] 儲存分析結果...")

    output_data = {
        "metadata": {
            "title": "O-D 軌道缺口分析",
            "generated_at": __import__('datetime').datetime.now().isoformat(),
            "total_od_pairs": len(od_mapping),
            "covered_count": len(covered),
            "can_extract_count": len(can_extract),
            "need_new_count": len(need_new),
            "coverage_percentage": total_trains_covered * 100 / total_trains if total_trains > 0 else 0,
        },
        "summary": {
            "covered_trains": total_trains_covered,
            "extractable_trains": total_trains_extractable,
            "new_needed_trains": total_trains_new,
            "total_trains": total_trains,
        },
        "covered": covered,
        "can_extract": sorted(can_extract, key=lambda x: -x["train_count"]),
        "need_new": sorted(need_new, key=lambda x: -x["train_count"]),
        "by_route": {route: sorted(items, key=lambda x: -x["train_count"])
                     for route, items in by_route.items()},
    }

    output_file = os.path.join(OUTPUT_DIR, "missing_od_tracks.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"  ✓ 儲存完成: {output_file}")

    # 顯示最急需處理的 O-D
    print("\n  Top 10 需處理的 O-D (按班次排序):")
    all_pending = sorted(can_extract + need_new, key=lambda x: -x["train_count"])
    for i, item in enumerate(all_pending[:10], 1):
        status = "可擷取" if item in can_extract else "需新建"
        print(f"    {i}. {item['od_key']}: {item['train_count']} 班 ({status}) → {item['suggested_id']}")

    print("\n" + "=" * 60)
    print("Phase 0 完成！")
    print("=" * 60)
    print("\n下一步:")
    print("  1. 檢視 missing_od_tracks.json 了解需要處理的 O-D")
    print("  2. 執行 Phase 1: 批次產生 O-D 軌道")
    print("     python scripts/tra/build_od_tracks.py")

    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
