#!/usr/bin/env python3
"""
建立台灣高鐵車站 GeoJSON

從 TDX 資料生成車站 GeoJSON：
- thsr_stations.geojson (包含座標、線序、累積距離)

Usage:
    python scripts/build_thsr_stations.py
"""

import json
from pathlib import Path

# 路徑設定
DATA_DIR = Path(__file__).parent.parent / "data-thsr"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = DATA_DIR / "stations"


def build_thsr_stations():
    """建立高鐵車站 GeoJSON"""

    # 確保輸出目錄存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n=== 建立台灣高鐵車站 GeoJSON ===\n")

    # 1. 讀取車站資料
    print("[1/3] 讀取車站資料...")
    with open(RAW_DIR / "thsr_stations.json", 'r', encoding='utf-8') as f:
        stations_data = json.load(f)

    # 建立 StationID -> 車站資料 的映射
    stations_map = {}
    for station in stations_data:
        stations_map[station['StationID']] = station

    print(f"      載入 {len(stations_map)} 個車站")

    # 2. 讀取車站線序資料
    print("[2/3] 讀取車站線序...")
    with open(RAW_DIR / "thsr_station_of_line.json", 'r', encoding='utf-8') as f:
        line_data = json.load(f)

    # 取得車站順序與累積距離
    station_sequence = line_data[0]['Stations']  # 只有一條線
    print(f"      載入 {len(station_sequence)} 個車站順序")

    # 3. 合併資料並建立 GeoJSON
    print("[3/3] 建立 GeoJSON...")
    features = []

    for seq_info in station_sequence:
        station_id = seq_info['StationID']
        station = stations_map.get(station_id)

        if not station:
            print(f"      警告: 找不到車站 {station_id}")
            continue

        feature = {
            "type": "Feature",
            "properties": {
                "station_id": station['StationID'],
                "station_uid": station['StationUID'],
                "station_code": station['StationCode'],
                "name_zh": station['StationName']['Zh_tw'],
                "name_en": station['StationName']['En'],
                "sequence": seq_info['Sequence'],
                "cumulative_distance": seq_info['CumulativeDistance'],
                "city": station.get('LocationCity', ''),
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

    # 按順序排序
    features.sort(key=lambda f: f['properties']['sequence'])

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    # 寫入檔案
    output_path = OUTPUT_DIR / "thsr_stations.geojson"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print("\n=== 建立完成 ===")
    print(f"輸出檔案: {output_path}")
    print(f"車站數量: {len(features)}")
    print("\n車站列表:")
    for f in features:
        props = f['properties']
        print(f"  {props['sequence']:2d}. {props['name_zh']} ({props['name_en']}) - {props['cumulative_distance']:.2f} km")


if __name__ == '__main__':
    build_thsr_stations()
