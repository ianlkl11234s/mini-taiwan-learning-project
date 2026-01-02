#!/usr/bin/env python3
"""
建立高雄輕軌車站 GeoJSON

從 TDX 資料生成車站 GeoJSON：
- klrt_stations.geojson (包含座標、線序、累積距離)

Usage:
    python scripts/build_klrt_stations.py
"""

import json
from pathlib import Path

# 路徑設定
DATA_DIR = Path(__file__).parent.parent / "data-klrt"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "data-klrt" / "stations"


def build_klrt_stations():
    """建立高雄輕軌車站 GeoJSON"""

    # 確保輸出目錄存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n=== 建立高雄輕軌車站 GeoJSON ===\n")

    # 1. 讀取車站資料
    print("[1/3] 讀取車站資料...")
    with open(RAW_DIR / "klrt_stations.json", 'r', encoding='utf-8') as f:
        stations_data = json.load(f)

    # 建立 StationID -> 車站資料 的映射
    stations_map = {}
    for station in stations_data:
        stations_map[station['StationID']] = station

    print(f"      載入 {len(stations_map)} 個車站")

    # 2. 讀取車站線序資料
    print("[2/3] 讀取車站線序...")
    with open(RAW_DIR / "klrt_station_of_line.json", 'r', encoding='utf-8') as f:
        line_data = json.load(f)

    # 收集所有線路的車站
    all_station_sequences = {}
    for line in line_data:
        line_id = line.get('LineID', line.get('LineNo', 'N/A'))
        for seq_info in line.get('Stations', []):
            station_id = seq_info['StationID']
            if station_id not in all_station_sequences:
                all_station_sequences[station_id] = {
                    'line_id': line_id,
                    'sequence': seq_info['Sequence'],
                    'cumulative_distance': seq_info.get('CumulativeDistance', 0)
                }

    print(f"      載入 {len(all_station_sequences)} 個車站順序")

    # 3. 合併資料並建立 GeoJSON
    print("[3/3] 建立 GeoJSON...")
    features = []

    for station_id, station in stations_map.items():
        seq_info = all_station_sequences.get(station_id, {})

        feature = {
            "type": "Feature",
            "properties": {
                "station_id": station['StationID'],
                "station_uid": station['StationUID'],
                "name_zh": station['StationName']['Zh_tw'],
                "name_en": station['StationName']['En'],
                "line_id": seq_info.get('line_id', 'C'),  # 輕軌為 C 線
                "sequence": seq_info.get('sequence', 0),
                "cumulative_distance": seq_info.get('cumulative_distance', 0),
                "city": station.get('LocationCity', '高雄市'),
                "address": station.get('StationAddress', '')
            },
            "geometry": {
                "type": "Point",
                "coordinates": [
                    station['StationPosition']['PositionLon'],
                    station['StationPosition']['PositionLat']
                ]
            }
        }
        features.append(feature)

    # 按線路和順序排序
    features.sort(key=lambda f: (
        f['properties']['line_id'],
        f['properties']['sequence']
    ))

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    # 寫入檔案
    output_path = OUTPUT_DIR / "klrt_stations.geojson"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print("\n=== 建立完成 ===")
    print(f"輸出檔案: {output_path}")
    print(f"車站數量: {len(features)}")

    # 顯示環狀線車站
    print("\nC 環狀線車站 (順時針方向):")
    current_line = None
    for f in features:
        props = f['properties']
        if props['line_id'] != current_line:
            current_line = props['line_id']
        print(f"  {props['sequence']:2d}. {props['name_zh']} ({props['station_id']}) - {props['cumulative_distance']:.2f} km")

    # 檢查環狀線特性
    if features:
        first_station = features[0]['properties']
        last_station = features[-1]['properties']
        print(f"\n環狀線檢查:")
        print(f"  起點: {first_station['name_zh']} ({first_station['station_id']})")
        print(f"  終點: {last_station['name_zh']} ({last_station['station_id']})")
        total_distance = last_station['cumulative_distance']
        print(f"  總長: {total_distance:.2f} km")


if __name__ == '__main__':
    build_klrt_stations()
