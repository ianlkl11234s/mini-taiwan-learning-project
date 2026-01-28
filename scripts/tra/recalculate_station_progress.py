#!/usr/bin/env python3
"""
recalculate_station_progress.py - 重新計算所有 OD 軌道的 station_progress

用於軌道座標修正後重新計算 station_progress。
"""

import json
import os
import glob
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
PROGRESS_FILE = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')
STATIONS_FILE = os.path.join(DATA_DIR, 'stations_snapped.geojson')


def euclidean_distance(c1, c2):
    """歐幾里得距離"""
    return math.sqrt((c2[0] - c1[0])**2 + (c2[1] - c1[1])**2)


def load_stations():
    """載入車站座標"""
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    stations = {}
    for feature in data.get('features', []):
        sid = feature.get('properties', {}).get('station_id', '')
        coord = feature.get('geometry', {}).get('coordinates', [])
        if sid and coord:
            stations[sid] = coord
    return stations


def calculate_progress_for_track(track_coords, station_coords, existing_progress):
    """
    計算單一軌道的 station_progress
    
    Args:
        track_coords: 軌道座標列表
        station_coords: 所有車站座標 {station_id: [lon, lat]}
        existing_progress: 現有的 progress 資料 {station_id: progress}
    
    Returns:
        新的 progress 資料
    """
    if not track_coords or len(track_coords) < 2:
        return existing_progress
    
    # 計算累積距離
    cum_distances = [0.0]
    for i in range(1, len(track_coords)):
        dist = euclidean_distance(track_coords[i-1], track_coords[i])
        cum_distances.append(cum_distances[-1] + dist)
    
    total_length = cum_distances[-1]
    if total_length == 0:
        return existing_progress
    
    # 只計算現有 progress 中的車站
    new_progress = {}
    
    for station_id in existing_progress.keys():
        if station_id not in station_coords:
            # 保留原值
            new_progress[station_id] = existing_progress[station_id]
            continue
        
        sc = station_coords[station_id]
        
        # 找最近的軌道線段
        min_dist_sq = float('inf')
        best_progress = 0.0
        
        for i in range(len(track_coords) - 1):
            a = track_coords[i]
            b = track_coords[i + 1]
            
            # 計算點到線段的投影
            dx = b[0] - a[0]
            dy = b[1] - a[1]
            seg_len_sq = dx * dx + dy * dy
            
            if seg_len_sq == 0:
                t = 0
            else:
                t = ((sc[0] - a[0]) * dx + (sc[1] - a[1]) * dy) / seg_len_sq
                t = max(0, min(1, t))
            
            proj_x = a[0] + t * dx
            proj_y = a[1] + t * dy
            dist_sq = (sc[0] - proj_x) ** 2 + (sc[1] - proj_y) ** 2
            
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                seg_start_dist = cum_distances[i]
                seg_length = math.sqrt(seg_len_sq)
                best_progress = (seg_start_dist + t * seg_length) / total_length
        
        new_progress[station_id] = round(best_progress, 6)
    
    return new_progress


def main():
    print('=== 重新計算 station_progress ===\n')
    
    # 載入車站座標
    print('載入車站座標...')
    station_coords = load_stations()
    print(f'  共 {len(station_coords)} 站\n')
    
    # 載入現有 progress
    print('載入現有 progress...')
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        all_progress = json.load(f)
    print(f'  共 {len(all_progress)} 軌道\n')
    
    # 處理每條軌道
    print('重新計算...')
    updated_count = 0
    
    for track_id, existing_progress in all_progress.items():
        track_file = os.path.join(TRACKS_OD_DIR, f'{track_id}.geojson')
        
        if not os.path.exists(track_file):
            continue
        
        try:
            with open(track_file, 'r', encoding='utf-8') as f:
                geojson = json.load(f)
            
            geom = geojson['features'][0]['geometry']
            coords = geom['coordinates']
            
            # 計算新的 progress
            new_progress = calculate_progress_for_track(
                coords, station_coords, existing_progress
            )
            
            # 檢查是否有變化
            changed = False
            for sid in existing_progress:
                old_val = existing_progress.get(sid, 0)
                new_val = new_progress.get(sid, 0)
                if abs(old_val - new_val) > 0.0001:
                    changed = True
                    break
            
            if changed:
                all_progress[track_id] = new_progress
                updated_count += 1
        
        except Exception as e:
            print(f'  ✗ {track_id}: {e}')
    
    print(f'  更新 {updated_count} 軌道\n')
    
    # 儲存
    print('儲存...')
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)
    
    print(f'✓ 完成')


if __name__ == '__main__':
    main()
