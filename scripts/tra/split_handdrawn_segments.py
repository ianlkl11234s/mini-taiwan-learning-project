#!/usr/bin/env python3
"""
拆分手繪軌道區段到各自的檔案
將 gaps_to_fill.geojson 和 yl_gaps_to_fill.geojson 拆分到 tracks_handdrawn/ 目錄
"""

import json
from pathlib import Path
from datetime import datetime

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "public" / "data" / "tra"
HANDDRAWN_DIR = DATA_DIR / "tracks_handdrawn"

def split_yl_gaps():
    """拆分 YL 手繪區段"""
    yl_gaps_file = DATA_DIR / "tracks_official" / "yl_gaps_to_fill.geojson"

    if not yl_gaps_file.exists():
        print(f"❌ 找不到檔案: {yl_gaps_file}")
        return

    with open(yl_gaps_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    yl_dir = HANDDRAWN_DIR / "YL"
    yl_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for feature in data['features']:
        # 只處理 LineString（軌道區段），跳過 Point（車站參考點）
        if feature['geometry']['type'] != 'LineString':
            continue

        props = feature['properties']
        segment_id = props.get('segment_id', '')
        name = props.get('name', '')
        from_station = props.get('from_station', '')
        to_station = props.get('to_station', '')

        # 建立檔案名稱: 7290-7300-福隆貢寮.geojson
        filename = f"{from_station}-{to_station}-{name.replace('-', '')}.geojson"

        # 建立獨立的 GeoJSON 檔案
        output = {
            "type": "FeatureCollection",
            "metadata": {
                "segment_id": segment_id,
                "name": name,
                "from_station": from_station,
                "to_station": to_station,
                "source": "handdrawn",
                "created_at": datetime.now().isoformat(),
                "point_count": len(feature['geometry']['coordinates'])
            },
            "features": [feature]
        }

        output_path = yl_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"✅ YL: {filename} ({len(feature['geometry']['coordinates'])} 點)")
        count += 1

    print(f"\n📁 YL 手繪區段已拆分: {count} 個檔案 → {yl_dir}")


def split_gaps_to_fill():
    """拆分 gaps_to_fill.geojson 中的 BH 和 KL 區段"""
    gaps_file = DATA_DIR / "gaps_to_fill.geojson"

    if not gaps_file.exists():
        print(f"❌ 找不到檔案: {gaps_file}")
        return

    with open(gaps_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 路線名稱對映
    LINE_TO_ROUTE = {
        '基隆支線': 'KL',
        '北迴線': 'BH',
        '宜蘭線': 'YL',
        '縱貫線': 'WL',  # 西部幹線
        '屏東線': 'PT',
        '南迴線': 'SK',
        '台東線': 'TL',
        '花蓮線': 'HL',
    }

    counts = {}

    for feature in data['features']:
        if feature['geometry']['type'] != 'LineString':
            continue

        props = feature['properties']
        name = props.get('name', '')
        line = props.get('line', '')
        gap_id = props.get('gap_id', '')

        # 判斷路線
        route = LINE_TO_ROUTE.get(line, None)

        # 只處理 KL 和 BH
        if route not in ['KL', 'BH']:
            print(f"⏭️ 跳過 {line}: {name}")
            continue

        route_dir = HANDDRAWN_DIR / route
        route_dir.mkdir(parents=True, exist_ok=True)

        # 從名稱解析起迄站
        # 格式: "八堵 → 三坑"
        parts = name.replace('→', '-').replace(' ', '').split('-')
        from_name = parts[0] if len(parts) >= 1 else ''
        to_name = parts[1] if len(parts) >= 2 else ''

        # 建立檔案名稱
        filename = f"{gap_id}-{from_name}{to_name}.geojson"

        output = {
            "type": "FeatureCollection",
            "metadata": {
                "gap_id": gap_id,
                "name": name,
                "line": line,
                "route": route,
                "from_name": from_name,
                "to_name": to_name,
                "source": "handdrawn",
                "created_at": datetime.now().isoformat(),
                "point_count": len(feature['geometry']['coordinates'])
            },
            "features": [feature]
        }

        output_path = route_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        counts[route] = counts.get(route, 0) + 1
        print(f"✅ {route}: {filename} ({len(feature['geometry']['coordinates'])} 點)")

    for route, count in counts.items():
        print(f"\n📁 {route} 手繪區段: {count} 個檔案")


def main():
    print("=" * 60)
    print("拆分手繪軌道區段")
    print("=" * 60)

    print("\n--- 處理 YL (宜蘭線) ---")
    split_yl_gaps()

    print("\n--- 處理 BH/KL (北迴線/基隆支線) ---")
    split_gaps_to_fill()

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
