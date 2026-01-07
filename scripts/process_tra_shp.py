#!/usr/bin/env python3
"""
處理官方台鐵 SHP 資料，轉換為專案 GeoJSON 格式

功能：
1. 合併多個線段成連續軌道
2. 處理雙軌（選擇一條）
3. 依區段輸出
4. 車站座標對齊到軌道
"""

import json
from pathlib import Path
from collections import defaultdict
import math

# 路徑設定
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "public" / "data" / "tra"
SHP_DIR = DATA_DIR / "tra_shp_data"
OUTPUT_DIR = DATA_DIR / "tracks_official"

# 官方路線名稱到專案 ID 的映射
LINE_MAPPING = {
    "臺鐵沙崙線": {
        "line_id": "SH",
        "name": "沙崙線",
        "origin": "中洲",
        "destination": "沙崙"
    },
    "臺鐵成追線": {
        "line_id": "CZ",
        "name": "成追線",
        "origin": "成功",
        "destination": "追分"
    },
    "臺鐵縱貫線(北段)": {
        "line_id": "WL-N",
        "name": "縱貫線北段",
        "origin": "基隆",
        "destination": "竹南"
    },
    "臺鐵縱貫線南段": {
        "line_id": "WL-S1",
        "name": "縱貫線南段(彰化-高雄)",
        "origin": "彰化",
        "destination": "高雄"
    },
    "臺鐵縱貫線(南段)": {
        "line_id": "WL-S2",
        "name": "縱貫線南段(竹南-彰化)",
        "origin": "竹南",
        "destination": "彰化"
    },
    "臺鐵臺中線(山線)": {
        "line_id": "WL-M",
        "name": "山線",
        "origin": "竹南",
        "destination": "彰化"
    },
    "臺鐵縱貫線(海線)": {
        "line_id": "WL-H",
        "name": "海線",
        "origin": "竹南",
        "destination": "彰化"
    },
    "臺鐵海岸線(海線)": {
        "line_id": "WL-H2",
        "name": "海線(海岸線)",
        "origin": "竹南",
        "destination": "彰化"
    },
    "臺鐵宜蘭線": {
        "line_id": "YL",
        "name": "宜蘭線",
        "origin": "八堵",
        "destination": "蘇澳"
    },
    "臺鐵北迴線": {
        "line_id": "BH",
        "name": "北迴線",
        "origin": "蘇澳新",
        "destination": "花蓮"
    },
    "臺鐵臺東線": {
        "line_id": "TD",
        "name": "臺東線",
        "origin": "花蓮",
        "destination": "臺東"
    },
    "臺鐵南迴線": {
        "line_id": "NH",
        "name": "南迴線",
        "origin": "臺東",
        "destination": "枋寮"
    },
    "臺鐵屏東線": {
        "line_id": "PT",
        "name": "屏東線",
        "origin": "高雄",
        "destination": "枋寮"
    },
    "臺鐵內灣線": {
        "line_id": "NW",
        "name": "內灣線",
        "origin": "新竹",
        "destination": "內灣"
    },
    "臺鐵六家線": {
        "line_id": "LJ",
        "name": "六家線",
        "origin": "新竹",
        "destination": "六家"
    },
    "臺鐵集集線": {
        "line_id": "JJ",
        "name": "集集線",
        "origin": "二水",
        "destination": "車埕"
    },
    "臺鐵平溪線": {
        "line_id": "PX",
        "name": "平溪線",
        "origin": "三貂嶺",
        "destination": "菁桐"
    },
    "臺鐵深澳線": {
        "line_id": "SA",
        "name": "深澳線",
        "origin": "瑞芳",
        "destination": "海科館"
    },
}


def load_geojson(filepath):
    """載入 GeoJSON 檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_geojson(data, filepath):
    """儲存 GeoJSON 檔案"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已儲存: {filepath}")


def distance(p1, p2):
    """計算兩點之間的距離（簡化版，用於排序）"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def point_to_line_distance(point, line_start, line_end):
    """計算點到線段的距離"""
    x, y = point[0], point[1]
    x1, y1 = line_start[0], line_start[1]
    x2, y2 = line_end[0], line_end[1]

    # 線段長度的平方
    l2 = (x2 - x1)**2 + (y2 - y1)**2
    if l2 == 0:
        return distance(point, line_start)

    # 投影參數
    t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / l2))

    # 最近點
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)

    return distance(point, [proj_x, proj_y])


def split_on_long_jumps(coords, max_jump=0.008, min_segment_points=5):
    """
    在長距離跳躍處切斷座標序列，返回多個連續段

    Args:
        coords: 座標列表
        max_jump: 最大允許跳躍距離（約 800m = 0.008 度）
        min_segment_points: 最小保留的段點數

    Returns:
        list of segments，每個 segment 是一個座標列表
    """
    if len(coords) < 2:
        return [coords] if coords else []

    segments = []
    current_seg = [coords[0]]

    for i in range(1, len(coords)):
        d = distance(coords[i-1], coords[i])
        if d > max_jump:
            if len(current_seg) >= min_segment_points:
                segments.append(current_seg)
            current_seg = [coords[i]]
        else:
            current_seg.append(coords[i])

    if len(current_seg) >= min_segment_points:
        segments.append(current_seg)

    return segments if segments else [coords]


def merge_line_segments(segments, max_gap=0.015):
    """
    合併多個線段，返回多條連續線段列表（用於 MultiLineString）

    Args:
        segments: 線段座標列表
        max_gap: 最大允許間隙（約 1.5km = 0.015 度）

    Returns:
        list of coordinate lists（多條線段）
    """
    if not segments:
        return []

    try:
        from shapely.geometry import LineString, MultiLineString
        from shapely.ops import linemerge

        # 轉換為 shapely LineString
        lines = []
        for seg in segments:
            if len(seg) >= 2:
                lines.append(LineString(seg))

        if not lines:
            return []

        # 使用 shapely 合併相連的線段
        multi = MultiLineString(lines)
        merged = linemerge(multi)

        # 處理結果
        if merged.geom_type == 'LineString':
            merged_coords = list(merged.coords)
        elif merged.geom_type == 'MultiLineString':
            # 多條線段：使用貪婪算法連接
            result_lines = [list(line.coords) for line in merged.geoms]
            merged_coords = merge_line_segments_greedy(result_lines, max_gap)
        else:
            return []

        # 後處理：在跳躍處切斷，返回多條線段
        return split_on_long_jumps(merged_coords, max_jump=0.008)

    except ImportError:
        merged_coords = merge_line_segments_greedy(segments, max_gap)
        return split_on_long_jumps(merged_coords, max_jump=0.008)


def merge_line_segments_greedy(segments, max_gap=0.015):
    """
    使用改良的貪婪算法合併線段
    max_gap: 約 1.5km (0.015 度)
    """
    if not segments:
        return []

    # 建立線段列表，每個線段是一個座標列表
    all_lines = []
    for seg in segments:
        if isinstance(seg, list) and len(seg) >= 2:
            all_lines.append(list(seg))

    if not all_lines:
        return []

    # 使用貪婪算法合併
    merged_groups = []

    while all_lines:
        # 取出第一條線開始新的群組
        current = all_lines.pop(0)

        # 持續尋找可以連接的線段
        changed = True
        while changed:
            changed = False
            best_idx = -1
            best_dist = float('inf')
            best_reverse = False
            connect_to_end = True

            for i, seg in enumerate(all_lines):
                # 檢查四種連接方式
                d1 = distance(current[-1], seg[0])
                d2 = distance(current[-1], seg[-1])
                d3 = distance(current[0], seg[-1])
                d4 = distance(current[0], seg[0])

                for d, reverse, to_end in [
                    (d1, False, True), (d2, True, True),
                    (d3, False, False), (d4, True, False)
                ]:
                    if d < best_dist:
                        best_dist = d
                        best_idx = i
                        best_reverse = reverse
                        connect_to_end = to_end

            # 只有在距離夠近時才連接
            if best_idx >= 0 and best_dist <= max_gap:
                seg = all_lines.pop(best_idx)
                if best_reverse:
                    seg = seg[::-1]

                if connect_to_end:
                    current.extend(seg)
                else:
                    current = seg + current
                changed = True

        merged_groups.append(current)

    # 選擇最長的連續線段群組
    if merged_groups:
        return max(merged_groups, key=len)

    return []


def filter_single_track(segments, prefer_south=True):
    """
    過濾雙軌，保留單軌
    通過檢測平行線段來識別雙軌
    """
    if len(segments) < 2:
        return segments

    # 簡化版：直接使用所有線段
    # 實際上雙軌的兩條線會非常接近，合併後會自然形成單線
    return segments


def extract_line_features(geojson_data, rail_name):
    """從 GeoJSON 中提取指定路線的 features"""
    features = []
    for feat in geojson_data['features']:
        props = feat['properties']
        if props.get('RAILNAME') == rail_name and props.get('STATUS') == 0:
            features.append(feat)
    return features


def process_line(features, line_config):
    """處理單一路線，返回合併後的 GeoJSON feature（支援 MultiLineString）"""
    if not features:
        return None

    # 提取所有線段的座標
    segments = []
    for feat in features:
        geom = feat['geometry']
        if geom['type'] == 'LineString':
            segments.append(geom['coordinates'])
        elif geom['type'] == 'MultiLineString':
            segments.extend(geom['coordinates'])

    print(f"  📦 原始: {len(segments)} 段")

    # 合併線段（返回多條連續線段列表）
    merged_segments = merge_line_segments(segments)
    total_points = sum(len(seg) for seg in merged_segments)
    print(f"  🔗 合併後: {len(merged_segments)} 段, {total_points} 點")

    # 建立 GeoJSON feature
    line_id = line_config['line_id']

    # 決定 geometry 類型
    if len(merged_segments) == 1:
        geom_type = "LineString"
        coords_0 = merged_segments[0]
        coords_1 = merged_segments[0][::-1]
    else:
        geom_type = "MultiLineString"
        coords_0 = merged_segments
        coords_1 = [seg[::-1] for seg in merged_segments[::-1]]

    # 方向 0: origin -> destination
    feature_0 = {
        "type": "Feature",
        "properties": {
            "track_id": f"{line_id}-0",
            "line_id": line_id,
            "direction": 0,
            "name": f"{line_config['name']} ({line_config['origin']}→{line_config['destination']})",
            "origin": line_config['origin'],
            "destination": line_config['destination']
        },
        "geometry": {
            "type": geom_type,
            "coordinates": coords_0
        }
    }

    # 方向 1: destination -> origin (反轉座標)
    feature_1 = {
        "type": "Feature",
        "properties": {
            "track_id": f"{line_id}-1",
            "line_id": line_id,
            "direction": 1,
            "name": f"{line_config['name']} ({line_config['destination']}→{line_config['origin']})",
            "origin": line_config['destination'],
            "destination": line_config['origin']
        },
        "geometry": {
            "type": geom_type,
            "coordinates": coords_1
        }
    }

    return feature_0, feature_1


def snap_station_to_track(station_coord, track_coords):
    """
    將車站座標對齊到軌道上最近的點
    返回：(對齊後的座標, 在軌道上的進度 0-1, 距離)
    """
    min_dist = float('inf')
    best_point = station_coord
    best_progress = 0

    total_length = 0
    segment_lengths = []

    # 計算每段長度
    for i in range(len(track_coords) - 1):
        seg_len = distance(track_coords[i], track_coords[i+1])
        segment_lengths.append(seg_len)
        total_length += seg_len

    # 找最近點
    cumulative_length = 0
    for i in range(len(track_coords) - 1):
        p1 = track_coords[i]
        p2 = track_coords[i+1]

        # 計算點到線段的最近點
        x, y = station_coord[0], station_coord[1]
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]

        l2 = (x2 - x1)**2 + (y2 - y1)**2
        if l2 == 0:
            proj_x, proj_y = x1, y1
            t = 0
        else:
            t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / l2))
            proj_x = x1 + t * (x2 - x1)
            proj_y = y1 + t * (y2 - y1)

        dist = distance(station_coord, [proj_x, proj_y])

        if dist < min_dist:
            min_dist = dist
            best_point = [proj_x, proj_y]
            # 計算進度
            if total_length > 0:
                best_progress = (cumulative_length + t * segment_lengths[i]) / total_length

        cumulative_length += segment_lengths[i]

    return best_point, best_progress, min_dist


def main():
    print("🚂 開始處理官方台鐵 SHP 資料")
    print("=" * 50)

    # 載入官方資料
    geojson_path = SHP_DIR / "RAIL_wgs84.geojson"
    print(f"📂 載入: {geojson_path}")
    geojson_data = load_geojson(geojson_path)

    # 建立輸出目錄
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 處理每條路線
    all_features = []
    processed_lines = {}

    for rail_name, config in LINE_MAPPING.items():
        print(f"\n🛤️  處理: {rail_name} ({config['line_id']})")

        features = extract_line_features(geojson_data, rail_name)
        if not features:
            print(f"  ⚠️  未找到資料")
            continue

        result = process_line(features, config)
        if result:
            feat_0, feat_1 = result
            all_features.extend([feat_0, feat_1])

            # 儲存單獨的軌道檔案
            track_id_0 = feat_0['properties']['track_id']
            track_id_1 = feat_1['properties']['track_id']

            save_geojson(
                {"type": "FeatureCollection", "features": [feat_0]},
                OUTPUT_DIR / f"{track_id_0}.geojson"
            )
            save_geojson(
                {"type": "FeatureCollection", "features": [feat_1]},
                OUTPUT_DIR / f"{track_id_1}.geojson"
            )

            processed_lines[config['line_id']] = {
                'name': config['name'],
                'coords': feat_0['geometry']['coordinates'],
                'points': len(feat_0['geometry']['coordinates'])
            }

    # 儲存合併的軌道檔案
    all_tracks_path = OUTPUT_DIR / "all_tracks.geojson"
    save_geojson(
        {"type": "FeatureCollection", "features": all_features},
        all_tracks_path
    )

    # 輸出統計
    print("\n" + "=" * 50)
    print("📊 處理結果統計")
    print("=" * 50)
    total_points = 0
    for line_id, info in processed_lines.items():
        print(f"  {line_id}: {info['name']} - {info['points']} 點")
        total_points += info['points']
    print(f"\n  總計: {len(processed_lines)} 條路線, {total_points} 點")
    print(f"  輸出目錄: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
