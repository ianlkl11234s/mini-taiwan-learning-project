#!/usr/bin/env python3
"""
build_special_tracks.py - 建立特殊軌道（V 形路徑）

用於處理需要在某站折返的特殊路線，例如：
- 海線 → 彰化 → 山線（山海線互轉）
- 彰化 → 二水 → 集集線

這些路線的特點是：列車在某站改變方向，所以需要合併兩條方向相反的軌道。
"""

import json
import os
import math
from typing import Dict, List, Tuple

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
PROGRESS_FILE = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')


def load_station_progress() -> Dict[str, Dict[str, float]]:
    """載入車站進度表"""
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_station_progress(data: Dict[str, Dict[str, float]]):
    """儲存車站進度表"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_track_geojson(track_id: str) -> Dict:
    """載入軌道 GeoJSON"""
    filepath = os.path.join(TRACKS_OD_DIR, f"{track_id}.geojson")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_coordinates(geojson: Dict) -> List[List[float]]:
    """從 GeoJSON 取得座標"""
    features = geojson.get('features', [])
    if not features:
        return []
    geometry = features[0].get('geometry', {})
    return geometry.get('coordinates', [])


def euclidean_distance(coord1: List[float], coord2: List[float]) -> float:
    """計算歐幾里得距離"""
    dx = coord2[0] - coord1[0]
    dy = coord2[1] - coord1[1]
    return math.sqrt(dx * dx + dy * dy)


def calculate_cumulative_distances(coords: List[List[float]]) -> List[float]:
    """計算累積距離"""
    distances = [0.0]
    for i in range(1, len(coords)):
        dist = euclidean_distance(coords[i-1], coords[i])
        distances.append(distances[-1] + dist)
    return distances


def extract_segment(
    coords: List[List[float]],
    progress_map: Dict[str, float],
    start_station: str,
    end_station: str
) -> Tuple[List[List[float]], Dict[str, float]]:
    """
    擷取軌道區段

    Returns:
        (座標列表, 車站進度表)
    """
    start_prog = progress_map[start_station]
    end_prog = progress_map[end_station]

    # 計算累積距離
    cum_distances = calculate_cumulative_distances(coords)
    total_length = cum_distances[-1]

    if total_length == 0:
        return coords, progress_map

    # 計算擷取範圍
    start_dist = start_prog * total_length
    end_dist = end_prog * total_length

    # 確保方向正確
    if start_dist > end_dist:
        start_dist, end_dist = end_dist, start_dist

    # 擷取座標
    extracted = []
    for i, (coord, cum_dist) in enumerate(zip(coords, cum_distances)):
        if cum_dist >= start_dist - 0.0001 and cum_dist <= end_dist + 0.0001:
            extracted.append(coord)

    # 確保至少有起點和終點
    if len(extracted) < 2:
        start_idx = 0
        end_idx = len(coords) - 1
        for i, cum_dist in enumerate(cum_distances):
            if cum_dist <= start_dist:
                start_idx = i
            if cum_dist <= end_dist:
                end_idx = i
        extracted = coords[start_idx:end_idx+1]

    # 擷取車站進度
    segment_length = end_prog - start_prog
    new_progress = {}
    for station_id, prog in progress_map.items():
        if prog >= start_prog - 0.0001 and prog <= end_prog + 0.0001:
            new_prog = (prog - start_prog) / segment_length if segment_length > 0 else 0
            new_progress[station_id] = round(max(0, min(1, new_prog)), 6)

    return extracted, new_progress


def merge_v_shaped_tracks(
    track1_id: str,
    track1_start: str,
    track1_end: str,
    track2_id: str,
    track2_start: str,
    track2_end: str,
    output_id: str,
    station_progress: Dict[str, Dict[str, float]]
) -> Tuple[List[List[float]], Dict[str, float]]:
    """
    合併 V 形路徑的兩條軌道

    track1: 第一段（例如：海線 通霄→彰化）
    track2: 第二段（例如：山線 彰化→豐原）

    注意：兩段軌道在轉折站（如彰化）會合
    """
    # 載入軌道
    geojson1 = load_track_geojson(track1_id)
    geojson2 = load_track_geojson(track2_id)

    coords1 = get_coordinates(geojson1)
    coords2 = get_coordinates(geojson2)

    progress1 = station_progress[track1_id]
    progress2 = station_progress[track2_id]

    # 擷取第一段
    seg1_coords, seg1_progress = extract_segment(
        coords1, progress1, track1_start, track1_end
    )

    # 擷取第二段
    seg2_coords, seg2_progress = extract_segment(
        coords2, progress2, track2_start, track2_end
    )

    # 確認方向並調整
    # 第一段：起點 progress 應該 < 終點 progress
    if progress1[track1_start] > progress1[track1_end]:
        seg1_coords = list(reversed(seg1_coords))
        seg1_progress = {k: 1.0 - v for k, v in seg1_progress.items()}

    # 第二段：起點 progress 應該 < 終點 progress
    if progress2[track2_start] > progress2[track2_end]:
        seg2_coords = list(reversed(seg2_coords))
        seg2_progress = {k: 1.0 - v for k, v in seg2_progress.items()}

    # 計算各段長度
    len1 = sum(euclidean_distance(seg1_coords[i], seg1_coords[i+1])
               for i in range(len(seg1_coords)-1))
    len2 = sum(euclidean_distance(seg2_coords[i], seg2_coords[i+1])
               for i in range(len(seg2_coords)-1))
    total_len = len1 + len2

    if total_len == 0:
        return [], {}

    ratio1 = len1 / total_len
    ratio2 = len2 / total_len

    # 合併座標（去除第二段的第一個點，因為和第一段終點重複）
    merged_coords = seg1_coords + seg2_coords[1:]

    # 合併 station_progress
    merged_progress = {}

    # 第一段的車站
    for station_id, prog in seg1_progress.items():
        merged_progress[station_id] = round(prog * ratio1, 6)

    # 第二段的車站（跳過轉折站，因為已經在第一段）
    for station_id, prog in seg2_progress.items():
        if station_id not in merged_progress:
            merged_progress[station_id] = round(ratio1 + prog * ratio2, 6)

    # 確保起點是 0，終點是 1
    min_prog = min(merged_progress.values())
    max_prog = max(merged_progress.values())
    if max_prog > min_prog:
        for station_id in merged_progress:
            normalized = (merged_progress[station_id] - min_prog) / (max_prog - min_prog)
            merged_progress[station_id] = round(normalized, 6)

    return merged_coords, merged_progress


def create_geojson(
    coords: List[List[float]],
    track_id: str,
    source_tracks: List[str]
) -> Dict:
    """建立 GeoJSON"""
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "source_tracks": source_tracks,
                "point_count": len(coords),
                "generated_by": "build_special_tracks.py",
                "track_type": "v-shaped"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }


def build_special_track(config: Dict, station_progress: Dict[str, Dict[str, float]]) -> bool:
    """建立特殊軌道"""
    output_id = config['output_id']

    print(f"\n建立特殊軌道: {output_id}")
    print(f"  路徑: {config['description']}")

    coords, progress = merge_v_shaped_tracks(
        config['track1_id'],
        config['track1_start'],
        config['track1_end'],
        config['track2_id'],
        config['track2_start'],
        config['track2_end'],
        output_id,
        station_progress
    )

    if not coords or not progress:
        print(f"  ❌ 建立失敗")
        return False

    print(f"  座標點: {len(coords)}")
    print(f"  車站數: {len(progress)}")

    # 顯示車站進度
    sorted_stations = sorted(progress.items(), key=lambda x: x[1])
    print(f"  起點: {sorted_stations[0]}")
    print(f"  終點: {sorted_stations[-1]}")

    # 儲存 GeoJSON
    geojson = create_geojson(coords, output_id, [config['track1_id'], config['track2_id']])
    output_path = os.path.join(TRACKS_OD_DIR, f"{output_id}.geojson")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 儲存 GeoJSON")

    # 更新 station_progress
    station_progress[output_id] = progress

    return True


# 特殊軌道配置
SPECIAL_TRACKS = [
    # === 山海線互轉（經彰化）===
    # 海線 → 山線（北上）
    {
        'output_id': 'SP-C-CH-M-0',
        'description': '海線(通霄/大甲/沙鹿) → 彰化 → 山線(豐原/臺中/苗栗)',
        'track1_id': 'WL-C-ZN-CH-1',  # 竹南→彰化(海線)
        'track1_start': '1250',  # 竹南
        'track1_end': '3360',    # 彰化
        'track2_id': 'WL-M-CH-ZN-1',  # 彰化→竹南(山線)
        'track2_start': '3360',  # 彰化
        'track2_end': '1250',    # 竹南
    },
    # 山線 → 海線（南下）
    {
        'output_id': 'SP-M-CH-C-1',
        'description': '山線(苗栗/臺中/豐原) → 彰化 → 海線(沙鹿/大甲/通霄)',
        'track1_id': 'WL-M-ZN-CH-0',  # 竹南→彰化(山線)
        'track1_start': '1250',  # 竹南
        'track1_end': '3360',    # 彰化
        'track2_id': 'WL-C-CH-ZN-0',  # 彰化→竹南(海線)
        'track2_start': '3360',  # 彰化
        'track2_end': '1250',    # 竹南
    },

    # === 集集線 ===
    # 彰化 → 車埕
    {
        'output_id': 'SP-CH-JJ-0',
        'description': '彰化 → 二水 → 集集線(車埕)',
        'track1_id': 'WL-CH-ZY-0',  # 彰化→潮州
        'track1_start': '3360',  # 彰化
        'track1_end': '3430',    # 二水
        'track2_id': 'JJ-ES-CT',  # 二水→車埕
        'track2_start': '3430',  # 二水
        'track2_end': '3436',    # 車埕
    },
    # 車埕 → 彰化
    {
        'output_id': 'SP-JJ-CH-1',
        'description': '集集線(車埕) → 二水 → 彰化',
        'track1_id': 'JJ-CT-ES',  # 車埕→二水
        'track1_start': '3436',  # 車埕
        'track1_end': '3430',    # 二水
        'track2_id': 'WL-ZY-CH-1',  # 潮州→彰化
        'track2_start': '3430',  # 二水
        'track2_end': '3360',    # 彰化
    },

    # === 海線-北段互轉（經竹南）===
    # 海線 → 北段
    {
        'output_id': 'SP-C-ZN-N-0',
        'description': '海線(大甲) → 竹南 → 北段(新竹)',
        'track1_id': 'WL-C-CH-ZN-0',  # 彰化→竹南(海線)
        'track1_start': '3360',  # 彰化（含大甲等海線車站）
        'track1_end': '1250',    # 竹南
        'track2_id': 'WL-ZN-SL-0',  # 竹南→樹林(北段)
        'track2_start': '1250',  # 竹南
        'track2_end': '1040',    # 樹林（含新竹等北段車站）
    },
    # 北段 → 海線
    {
        'output_id': 'SP-N-ZN-C-1',
        'description': '北段(竹北) → 竹南 → 海線(沙鹿)',
        'track1_id': 'WL-SL-ZN-1',  # 樹林→竹南(北段)
        'track1_start': '1040',  # 樹林（含竹北等北段車站）
        'track1_end': '1250',    # 竹南
        'track2_id': 'WL-C-ZN-CH-1',  # 竹南→彰化(海線)
        'track2_start': '1250',  # 竹南
        'track2_end': '3360',    # 彰化（含沙鹿等海線車站）
    },
]


def main():
    print("=" * 50)
    print("建立特殊軌道（V 形路徑）")
    print("=" * 50)

    # 載入 station_progress
    station_progress = load_station_progress()

    success_count = 0
    fail_count = 0

    for config in SPECIAL_TRACKS:
        try:
            if build_special_track(config, station_progress):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
            fail_count += 1

    # 儲存更新後的 station_progress
    save_station_progress(station_progress)
    print(f"\n✓ 更新 station_progress")

    print(f"\n結果: 成功 {success_count}, 失敗 {fail_count}")

    return fail_count == 0


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
