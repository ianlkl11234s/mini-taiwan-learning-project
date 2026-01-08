#!/usr/bin/env python3
"""
合併剩餘的已完成 gap 到對應的軌道檔案

根據 gaps_to_fill.geojson 的 LineString 索引:
- [0]  17 點: 臺北 → 松山     → WL-N (縱貫線北段)
- [2]  18 點: 歸來 → 屏東     → PT (屏東線)
- [3] 131 點: 枋寮 → 林邊     → PT (屏東線)
- [4] 341 點: 太麻里 → 枋野   → NH (南迴線)
- [5]  55 點: 瑞芳 → 四腳亭   → YL (宜蘭線)
"""

import json
from pathlib import Path

# 路徑設定
BASE_DIR = Path(__file__).parent.parent / "public" / "data" / "tra"
GAPS_FILE = BASE_DIR / "gaps_to_fill.geojson"
TRACKS_DIR = BASE_DIR / "tracks_official"

# 待合併的 gap (使用 LineString 索引)
GAPS_TO_MERGE = [
    {"index": 0, "track": "WL-N", "name": "臺北 → 松山 (gap-10)"},
    {"index": 2, "track": "PT", "name": "歸來 → 屏東 (gap-08)"},
    {"index": 3, "track": "PT", "name": "枋寮 → 林邊 (gap-07)"},
    {"index": 4, "track": "NH", "name": "太麻里 → 枋野 (gap-06)"},
    {"index": 5, "track": "YL", "name": "瑞芳 → 四腳亭 (gap-17)"},
]


def load_geojson(path):
    """載入 GeoJSON 檔案"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_geojson(data, path):
    """儲存 GeoJSON 檔案"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def count_total_points(track_data):
    """計算軌道總點數"""
    if not track_data['features']:
        return 0
    coords = track_data['features'][0]['geometry']['coordinates']
    return sum(len(seg) for seg in coords)


def count_segments(track_data):
    """計算軌道 segment 數"""
    if not track_data['features']:
        return 0
    return len(track_data['features'][0]['geometry']['coordinates'])


def main():
    print("=" * 60)
    print("合併剩餘 Gap 到軌道檔案")
    print("=" * 60)

    # 載入 gaps_to_fill.geojson
    print(f"\n📂 載入 gaps_to_fill.geojson...")
    gaps_data = load_geojson(GAPS_FILE)

    # 提取所有 LineString 座標
    linestrings = []
    for feature in gaps_data['features']:
        if feature['geometry']['type'] == 'LineString':
            linestrings.append(feature['geometry']['coordinates'])

    print(f"   共 {len(linestrings)} 條 LineString")

    # 準備合併資料
    print(f"\n📋 待合併的 Gap:")
    merge_data = []
    for gap in GAPS_TO_MERGE:
        idx = gap["index"]
        if idx < len(linestrings):
            coords = linestrings[idx]
            merge_data.append({
                "track": gap["track"],
                "name": gap["name"],
                "coords": coords,
                "points": len(coords)
            })
            print(f"   [{idx}] {gap['name']}: {len(coords)} 點 → {gap['track']}")
        else:
            print(f"   ⚠️ [{idx}] {gap['name']}: 索引超出範圍")

    # 按軌道分組
    track_updates = {}
    for item in merge_data:
        track_id = item["track"]
        if track_id not in track_updates:
            track_updates[track_id] = []
        track_updates[track_id].append(item)

    # 逐一更新軌道檔案
    print(f"\n🔧 開始合併...")
    results = []

    for track_id, gaps in track_updates.items():
        print(f"\n📦 處理 {track_id} 軌道...")

        for direction in [0, 1]:
            track_file = TRACKS_DIR / f"{track_id}-{direction}.geojson"

            if not track_file.exists():
                print(f"   ⚠️ {track_file.name} 不存在")
                continue

            track_data = load_geojson(track_file)
            before_points = count_total_points(track_data)
            before_segs = count_segments(track_data)

            # 加入新的 segments
            geometry = track_data['features'][0]['geometry']

            for gap in gaps:
                geometry['coordinates'].append(gap["coords"])
                print(f"   ✅ 加入 {gap['name']} ({gap['points']} 點)")

            after_points = count_total_points(track_data)
            after_segs = count_segments(track_data)

            # 儲存
            save_geojson(track_data, track_file)
            print(f"   💾 {track_file.name}: {before_points}→{after_points} 點, {before_segs}→{after_segs} segs")

            results.append({
                "file": track_file.name,
                "before": before_points,
                "after": after_points,
                "added": after_points - before_points
            })

    # 總結
    print(f"\n" + "=" * 60)
    print("📊 合併完成總結")
    print("=" * 60)

    total_added = 0
    for r in results:
        print(f"   {r['file']}: +{r['added']} 點 ({r['before']} → {r['after']})")
        total_added += r['added']

    print(f"\n   總計新增: {total_added} 點")
    print(f"\n✅ 完成！請執行 station snapping 驗證對齊狀況。")


if __name__ == "__main__":
    main()
