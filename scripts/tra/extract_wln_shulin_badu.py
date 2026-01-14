#!/usr/bin/env python3
"""
從 WL-N 軌道中擷取「樹林→八堵」區段
排除竹南以南和基隆支線

輸出:
- tracks_golden/WL-N-SL-BD-0.geojson (樹林→八堵 方向0)
- tracks_golden/WL-N-SL-BD-1.geojson (八堵→樹林 方向1)
"""

import json
import math
from pathlib import Path
from datetime import datetime

# 路徑設定
PROJECT_ROOT = Path(__file__).parent.parent.parent
TRACKS_OFFICIAL = PROJECT_ROOT / "public/data/tra/tracks_official"
TRACKS_GOLDEN = PROJECT_ROOT / "public/data/tra/tracks_golden"
STATIONS_FILE = PROJECT_ROOT / "public/data/tra/stations_snapped.geojson"

# 車站座標
SHULIN = [121.424411, 24.991235]  # 樹林 (1040)
BADU = [121.728959, 25.108559]    # 八堵 (0920)

def distance(c1, c2):
    """計算兩點距離（公里）"""
    return math.sqrt((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2) * 111

def find_nearest_point(segments, target, exclude_segments=None):
    """在軌道段落中找到最接近目標的點"""
    exclude_segments = exclude_segments or []
    best = {"seg": -1, "idx": -1, "dist": float('inf'), "coord": None}
    
    for seg_idx, seg in enumerate(segments):
        if seg_idx in exclude_segments:
            continue
        for pt_idx, pt in enumerate(seg):
            d = distance(pt, target)
            if d < best["dist"]:
                best = {"seg": seg_idx, "idx": pt_idx, "dist": d, "coord": pt}
    
    return best

def extract_segment(segments, start_seg, start_idx, end_seg, end_idx):
    """從多段落軌道中擷取指定區段"""
    coords = []
    
    for seg_idx in range(start_seg, end_seg + 1):
        seg = segments[seg_idx]
        
        if seg_idx == start_seg:
            s_idx = start_idx
        else:
            s_idx = 0
        
        if seg_idx == end_seg:
            e_idx = end_idx + 1
        else:
            e_idx = len(seg)
        
        coords.extend(seg[s_idx:e_idx])
    
    return coords

def validate_track(coords, name):
    """驗證軌道品質"""
    issues = []
    max_gap = 0
    
    for i in range(len(coords) - 1):
        d = distance(coords[i], coords[i+1])
        if d > max_gap:
            max_gap = d
        if d > 0.5:  # 超過 500m
            issues.append(f"座標跳躍 @ index {i}: {d*1000:.0f}m")
    
    print(f"\n📋 {name} 驗證結果:")
    print(f"   總點數: {len(coords)}")
    print(f"   最大間距: {max_gap*1000:.0f}m")
    if issues:
        print(f"   ⚠️ 發現 {len(issues)} 個問題:")
        for issue in issues[:5]:
            print(f"      - {issue}")
    else:
        print(f"   ✅ 無座標跳躍問題")
    
    return len(issues) == 0

def main():
    print("=" * 60)
    print("🚂 擷取 WL-N 樹林→八堵 區段")
    print("=" * 60)
    
    # 確保輸出目錄存在
    TRACKS_GOLDEN.mkdir(parents=True, exist_ok=True)
    
    # 處理兩個方向
    for direction in [0, 1]:
        print(f"\n{'='*60}")
        print(f"處理方向 {direction}")
        print("="*60)
        
        # 讀取原始軌道
        input_file = TRACKS_OFFICIAL / f"WL-N-{direction}.geojson"
        with open(input_file, "r") as f:
            track = json.load(f)
        
        # 取得段落
        if track["type"] == "FeatureCollection":
            geom = track["features"][0]["geometry"]
        else:
            geom = track["geometry"]
        
        if geom["type"] == "MultiLineString":
            segments = geom["coordinates"]
        else:
            segments = [geom["coordinates"]]
        
        print(f"原始軌道段落數: {len(segments)}")
        
        # 排除基隆支線段落（緯度 > 25.115）
        keelung_segments = []
        for i, seg in enumerate(segments):
            max_lat = max(p[1] for p in seg)
            if max_lat > 25.115:
                keelung_segments.append(i)
        
        print(f"基隆支線段落: {keelung_segments}")
        
        # 找樹林和八堵的位置
        shulin = find_nearest_point(segments, SHULIN, keelung_segments)
        badu = find_nearest_point(segments, BADU, keelung_segments)
        
        print(f"樹林站: 段落 {shulin['seg']}, 點 {shulin['idx']}, 距離 {shulin['dist']*1000:.0f}m")
        print(f"八堵站: 段落 {badu['seg']}, 點 {badu['idx']}, 距離 {badu['dist']*1000:.0f}m")
        
        # 根據方向決定起終點
        if direction == 0:
            # 方向 0: 往八堵方向 (樹林→八堵)
            if shulin['seg'] < badu['seg'] or (shulin['seg'] == badu['seg'] and shulin['idx'] < badu['idx']):
                start, end = shulin, badu
            else:
                start, end = badu, shulin
        else:
            # 方向 1: 往樹林方向 (八堵→樹林)
            if badu['seg'] < shulin['seg'] or (badu['seg'] == shulin['seg'] and badu['idx'] < shulin['idx']):
                start, end = badu, shulin
            else:
                start, end = shulin, badu
        
        # 擷取座標
        coords = extract_segment(segments, start['seg'], start['idx'], end['seg'], end['idx'])
        
        # 驗證
        track_name = f"WL-N-SL-BD-{direction}"
        is_valid = validate_track(coords, track_name)
        
        # 建立輸出 GeoJSON
        output = {
            "type": "Feature",
            "properties": {
                "track_id": f"WL-N-SL-BD-{direction}",
                "line_id": "WL-N",
                "direction": direction,
                "name": "縱貫線北段 (樹林→八堵)" if direction == 0 else "縱貫線北段 (八堵→樹林)",
                "origin": "樹林" if direction == 0 else "八堵",
                "destination": "八堵" if direction == 0 else "樹林",
                "origin_id": "1040" if direction == 0 else "0920",
                "destination_id": "0920" if direction == 0 else "1040",
                "extracted_from": f"WL-N-{direction}.geojson",
                "extracted_at": datetime.now().isoformat(),
                "point_count": len(coords),
                "excludes_keelung_branch": True
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }
        
        # 儲存
        output_file = TRACKS_GOLDEN / f"WL-N-SL-BD-{direction}.geojson"
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✅ 已儲存: {output_file}")
        print(f"   起點: [{coords[0][0]:.6f}, {coords[0][1]:.6f}]")
        print(f"   終點: [{coords[-1][0]:.6f}, {coords[-1][1]:.6f}]")

if __name__ == "__main__":
    main()
