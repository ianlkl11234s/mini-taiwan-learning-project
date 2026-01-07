#!/usr/bin/env python3
"""
將車站座標對齊到官方軌道資料上

功能：
1. 讀取現有車站資料
2. 對齊每個車站到最近的軌道點
3. 更新車站的 line_id 為對應軌道
4. 輸出對齊後的車站 GeoJSON
"""

import json
from pathlib import Path
import math

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "public" / "data" / "tra"
TRACKS_DIR = DATA_DIR / "tracks_official"
STATIONS_FILE = DATA_DIR / "stations.geojson"
OUTPUT_FILE = DATA_DIR / "stations_snapped.geojson"


def load_geojson(filepath):
    """載入 GeoJSON 檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_geojson(data, filepath):
    """儲存 GeoJSON 檔案"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已儲存: {filepath}")


def distance(p1, p2):
    """計算兩點之間的距離（簡化版）"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def point_to_line_segment(point, p1, p2):
    """
    計算點到線段的最近點
    返回: (最近點座標, 距離, 在線段上的位置 t)
    """
    x, y = point[0], point[1]
    x1, y1 = p1[0], p1[1]
    x2, y2 = p2[0], p2[1]

    l2 = (x2 - x1)**2 + (y2 - y1)**2
    if l2 == 0:
        return [x1, y1], distance(point, p1), 0

    t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / l2))
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)

    return [proj_x, proj_y], distance(point, [proj_x, proj_y]), t


def snap_to_single_line(station_coord, line_coords):
    """
    將車站座標對齊到單一 LineString 上最近的點
    返回: (對齊後的座標, 距離, 在線段上的進度 0-1)
    """
    min_dist = float('inf')
    best_point = station_coord
    best_progress = 0

    # 計算總長度
    total_length = 0
    segment_lengths = []
    for i in range(len(line_coords) - 1):
        seg_len = distance(line_coords[i], line_coords[i+1])
        segment_lengths.append(seg_len)
        total_length += seg_len

    if total_length == 0:
        return station_coord, float('inf'), 0

    # 找最近點
    cumulative_length = 0
    for i in range(len(line_coords) - 1):
        nearest, dist, t = point_to_line_segment(
            station_coord, line_coords[i], line_coords[i+1]
        )

        if dist < min_dist:
            min_dist = dist
            best_point = nearest
            best_progress = (cumulative_length + t * segment_lengths[i]) / total_length

        cumulative_length += segment_lengths[i]

    return best_point, min_dist, best_progress


def snap_to_track(station_coord, track_coords, geom_type="LineString"):
    """
    將車站座標對齊到軌道上最近的點
    支援 LineString 和 MultiLineString 格式
    返回: (對齊後的座標, 距離, 在軌道上的進度 0-1)
    """
    if geom_type == "LineString":
        return snap_to_single_line(station_coord, track_coords)

    # MultiLineString: 遍歷所有線段找最近點
    min_dist = float('inf')
    best_point = station_coord
    best_progress = 0

    # 計算所有線段的總長度
    total_length = 0
    line_lengths = []
    for line in track_coords:
        line_len = 0
        for i in range(len(line) - 1):
            line_len += distance(line[i], line[i+1])
        line_lengths.append(line_len)
        total_length += line_len

    if total_length == 0:
        return station_coord, float('inf'), 0

    # 遍歷每條線段
    cumulative_length = 0
    for line_idx, line in enumerate(track_coords):
        snapped, dist, progress = snap_to_single_line(station_coord, line)

        if dist < min_dist:
            min_dist = dist
            best_point = snapped
            # 計算在整體軌道上的進度
            best_progress = (cumulative_length + progress * line_lengths[line_idx]) / total_length

        cumulative_length += line_lengths[line_idx]

    return best_point, min_dist, best_progress


def main():
    print("🚉 開始車站座標對齊")
    print("=" * 50)

    # 載入車站資料
    print(f"📂 載入車站: {STATIONS_FILE}")
    stations = load_geojson(STATIONS_FILE)
    print(f"  共 {len(stations['features'])} 個車站")

    # 載入所有軌道
    print(f"\n📂 載入軌道: {TRACKS_DIR}")
    tracks = {}
    for track_file in TRACKS_DIR.glob("*-0.geojson"):
        track_data = load_geojson(track_file)
        if track_data['features']:
            feat = track_data['features'][0]
            track_id = feat['properties']['track_id']
            line_id = feat['properties']['line_id']
            geom_type = feat['geometry']['type']
            tracks[line_id] = {
                'coords': feat['geometry']['coordinates'],
                'track_id': track_id,
                'name': feat['properties']['name'],
                'geom_type': geom_type
            }
            if geom_type == "MultiLineString":
                print(f"  📋 {line_id}: MultiLineString ({len(feat['geometry']['coordinates'])} 段)")
    print(f"  共 {len(tracks)} 條軌道")

    # 對齊車站
    print("\n🔧 開始對齊車站...")
    snapped_features = []
    stats = {'matched': 0, 'too_far': 0, 'updated': 0}

    for station in stations['features']:
        station_coord = station['geometry']['coordinates']
        station_name = station['properties']['name']
        original_line_id = station['properties'].get('line_id', '')

        # 找最近的軌道
        best_line_id = None
        best_snapped = station_coord
        best_dist = float('inf')
        best_progress = 0

        for line_id, track_info in tracks.items():
            snapped, dist, progress = snap_to_track(
                station_coord, track_info['coords'], track_info['geom_type']
            )

            # 距離閾值：約 500 公尺 (在經緯度上約 0.005 度)
            if dist < best_dist:
                best_dist = dist
                best_line_id = line_id
                best_snapped = snapped
                best_progress = progress

        # 更新車站資料
        new_station = {
            "type": "Feature",
            "properties": {
                **station['properties'],
                "original_coords": station_coord,
                "snapped_distance": round(best_dist * 111000, 2)  # 約轉換為公尺
            },
            "geometry": {
                "type": "Point",
                "coordinates": [round(best_snapped[0], 6), round(best_snapped[1], 6)]
            }
        }

        # 如果找到匹配的軌道且距離合理 (< 2km)
        if best_dist < 0.02:  # 約 2.2 公里
            new_station['properties']['matched_line_id'] = best_line_id
            new_station['properties']['track_progress'] = round(best_progress, 6)
            stats['matched'] += 1

            if best_dist > 0.001:  # 超過 100 公尺才算有更新
                stats['updated'] += 1
        else:
            stats['too_far'] += 1
            print(f"  ⚠️  {station_name}: 距離最近軌道 {round(best_dist * 111, 2)} km")

        snapped_features.append(new_station)

    # 儲存結果
    output_data = {
        "type": "FeatureCollection",
        "features": snapped_features
    }
    save_geojson(output_data, OUTPUT_FILE)

    # 統計
    print("\n" + "=" * 50)
    print("📊 對齊統計")
    print("=" * 50)
    print(f"  ✅ 成功匹配: {stats['matched']} 站")
    print(f"  🔄 座標更新: {stats['updated']} 站")
    print(f"  ⚠️  距離過遠: {stats['too_far']} 站")
    print(f"\n  輸出檔案: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
