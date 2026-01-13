#!/usr/bin/env python3
"""
提取黃金軌道到 tracks_golden/
從 all_tracks.geojson 和 tracks_od/ 提取已驗證的軌道
"""

import json
import math
from pathlib import Path
from datetime import datetime

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "public" / "data" / "tra"
GOLDEN_DIR = DATA_DIR / "tracks_golden"
TRACKS_OFFICIAL = DATA_DIR / "tracks_official"
TRACKS_OD = DATA_DIR / "tracks_od"
HANDDRAWN_DIR = DATA_DIR / "tracks_handdrawn"


def euclidean_distance(p1, p2):
    """計算歐幾里得距離（度為單位）"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def validate_track(coords, max_jump_km=0.5):
    """
    驗證軌道品質
    回傳 (is_valid, issues_list)
    """
    issues = []
    max_jump_deg = max_jump_km / 111.0  # 約略轉換

    for i in range(len(coords) - 1):
        dist = euclidean_distance(coords[i], coords[i+1])
        if dist > max_jump_deg:
            dist_km = dist * 111
            issues.append(f"Jump at index {i}: {dist_km:.2f}km")

    return len(issues) == 0, issues


def extract_from_all_tracks():
    """從 all_tracks.geojson 提取軌道"""
    all_tracks_file = TRACKS_OFFICIAL / "all_tracks.geojson"

    if not all_tracks_file.exists():
        print(f"❌ 找不到檔案: {all_tracks_file}")
        return {}

    with open(all_tracks_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 要提取的軌道 ID 及其來源說明
    EXTRACT_TRACKS = {
        'YL-0': {'source': 'tdx_with_handdrawn', 'priority': 1},
        'YL-1': {'source': 'tdx_with_handdrawn', 'priority': 1},
        'BH-0': {'source': 'handdrawn_only', 'priority': 1},
        'BH-1': {'source': 'handdrawn_only', 'priority': 1},
        'NW-0': {'source': 'tdx', 'priority': 2},
        'NW-1': {'source': 'tdx', 'priority': 2},
        'LJ-0': {'source': 'tdx', 'priority': 2},
        'LJ-1': {'source': 'tdx', 'priority': 2},
        'SH-0': {'source': 'tdx', 'priority': 2},
        'SH-1': {'source': 'tdx', 'priority': 2},
        'PX-0': {'source': 'tdx', 'priority': 3},
        'PX-1': {'source': 'tdx', 'priority': 3},
        'JJ-0': {'source': 'tdx', 'priority': 3},
        'JJ-1': {'source': 'tdx', 'priority': 3},
        'CZ-0': {'source': 'tdx', 'priority': 3},
        'CZ-1': {'source': 'tdx', 'priority': 3},
    }

    manifest_entries = {}

    for feature in data['features']:
        track_id = feature['properties'].get('track_id', '')

        if track_id not in EXTRACT_TRACKS:
            continue

        geom_type = feature['geometry']['type']
        coords = feature['geometry']['coordinates']

        # 處理 MultiLineString → 合併成 LineString
        if geom_type == 'MultiLineString':
            merged_coords = []
            for line in coords:
                merged_coords.extend(line)
            coords = merged_coords
            geom_type = 'LineString'

        # 驗證軌道品質
        is_valid, issues = validate_track(coords)

        # 取得手繪區段資訊
        route = track_id.split('-')[0]
        handdrawn_segments = []
        handdrawn_dir = HANDDRAWN_DIR / route
        if handdrawn_dir.exists():
            handdrawn_segments = [
                f"tracks_handdrawn/{route}/{f.name}"
                for f in handdrawn_dir.glob("*.geojson")
            ]

        # 建立輸出
        output = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "track_id": track_id,
                    "route_id": route,
                    "direction": int(track_id.split('-')[1]) if '-' in track_id else 0,
                    "golden": True,
                    "source": EXTRACT_TRACKS[track_id]['source']
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                }
            }]
        }

        output_path = GOLDEN_DIR / f"{track_id}.geojson"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        status_icon = '✅' if is_valid else '⚠️'
        print(f"{status_icon} {track_id}: {len(coords)} pts, {EXTRACT_TRACKS[track_id]['source']}")

        if not is_valid:
            for issue in issues[:3]:  # 只顯示前 3 個問題
                print(f"   ⚠️ {issue}")
            if len(issues) > 3:
                print(f"   ... 還有 {len(issues) - 3} 個問題")

        # 記錄到 manifest
        manifest_entries[track_id] = {
            "status": "golden" if is_valid else "needs_review",
            "source": EXTRACT_TRACKS[track_id]['source'],
            "handdrawn_segments": handdrawn_segments,
            "point_count": len(coords),
            "geometry_type": "LineString",
            "validated_at": datetime.now().isoformat(),
            "issues": issues if issues else []
        }

    return manifest_entries


def extract_kl_from_od():
    """從 tracks_od/ 提取 KL 軌道"""
    kl_tracks = {
        'KL-TP-KL': 'KL-0',  # 臺北→基隆 = 方向 0
        'KL-KL-TP': 'KL-1',  # 基隆→臺北 = 方向 1
    }

    manifest_entries = {}

    for od_id, display_id in kl_tracks.items():
        od_file = TRACKS_OD / f"{od_id}.geojson"

        if not od_file.exists():
            print(f"❌ 找不到 KL O-D 軌道: {od_file}")
            continue

        with open(od_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        feature = data['features'][0]
        coords = feature['geometry']['coordinates']

        # 驗證軌道品質
        is_valid, issues = validate_track(coords)

        # 取得手繪區段
        handdrawn_segments = [
            f"tracks_handdrawn/KL/{f.name}"
            for f in (HANDDRAWN_DIR / "KL").glob("*.geojson")
        ] if (HANDDRAWN_DIR / "KL").exists() else []

        # 建立輸出
        output = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "track_id": display_id,
                    "route_id": "KL",
                    "direction": int(display_id.split('-')[1]),
                    "golden": True,
                    "source": "handdrawn_only",
                    "od_track_id": od_id
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                }
            }]
        }

        output_path = GOLDEN_DIR / f"{display_id}.geojson"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        status_icon = '✅' if is_valid else '⚠️'
        print(f"{status_icon} {display_id}: {len(coords)} pts, handdrawn_only (from {od_id})")

        if not is_valid:
            for issue in issues[:3]:
                print(f"   ⚠️ {issue}")

        manifest_entries[display_id] = {
            "status": "golden" if is_valid else "needs_review",
            "source": "handdrawn_only",
            "handdrawn_segments": handdrawn_segments,
            "od_track_id": od_id,
            "point_count": len(coords),
            "geometry_type": "LineString",
            "validated_at": datetime.now().isoformat(),
            "issues": issues if issues else []
        }

    return manifest_entries


def create_manifest(entries):
    """建立 manifest.json"""
    manifest = {
        "version": "1.0.0",
        "generated_at": datetime.now().isoformat(),
        "description": "TRA 黃金軌道 - 單一來源真相",
        "tracks": entries
    }

    manifest_path = GOLDEN_DIR / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n📋 manifest.json 已建立: {len(entries)} 條軌道")


def main():
    print("=" * 60)
    print("提取黃金軌道到 tracks_golden/")
    print("=" * 60)

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    print("\n--- 從 all_tracks.geojson 提取 ---")
    entries = extract_from_all_tracks()

    print("\n--- 從 tracks_od/ 提取 KL ---")
    kl_entries = extract_kl_from_od()
    entries.update(kl_entries)

    print("\n--- 建立 manifest.json ---")
    create_manifest(entries)

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)

    # 統計
    golden_count = sum(1 for e in entries.values() if e['status'] == 'golden')
    review_count = sum(1 for e in entries.values() if e['status'] == 'needs_review')
    print(f"\n📊 統計: {golden_count} 條 ✅ 黃金軌道, {review_count} 條 ⚠️ 需檢查")


if __name__ == "__main__":
    main()
