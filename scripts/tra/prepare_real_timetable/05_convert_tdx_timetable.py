#!/usr/bin/env python3
"""
05_convert_tdx_timetable.py - TDX 時刻表轉換為 Mini Taiwan 格式

功能：
1. 讀取 TDX 時刻表
2. 匹配 O-D 軌道
3. 轉換時間格式
4. 輸出 Mini Taiwan 格式時刻表

使用方式：
    python scripts/tra/prepare_real_timetable/05_convert_tdx_timetable.py

輸入：
    public/data/tra/data/tdx_timetable_latest.json
    public/data/tra/tracks_od/od_station_progress.json

產出：
    public/data/tra/schedules_real/master_schedule.json
    public/data/tra/schedules_real/by_od/*.json
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
INPUT_DIR = os.path.join(DATA_DIR, 'data')
TRACKS_OD_DIR = os.path.join(DATA_DIR, 'tracks_od')
OUTPUT_DIR = os.path.join(DATA_DIR, 'schedules_real')

# ============================================================
# Station ID 對照表：TDX 新 ID → 軌道舊 ID
# 台中捷運通車後 TDX 更新的車站編號
# ============================================================
STATION_ID_MAPPING = {
    '3250': '3240',  # 潭子
    '3260': '3243',  # 頭家厝
    '3270': '3245',  # 松竹
    '3280': '3247',  # 太原
    '3290': '3249',  # 精武
    '3340': '3330',  # 新烏日 → 烏日（新烏日與烏日距離極近，合併避免 progress 倒退）
    '3350': '3330',  # 成功
}

# ============================================================
# 車種代碼對照表：TDX 車種名稱 → 車種代碼
# ============================================================
TDX_TRAIN_TYPE_MAPPING = {
    # 傾斜式
    '普悠瑪(普悠瑪)': 'PP',
    '太魯閣(太魯閣)': 'TZ',
    # EMU3000
    '自強(3000)(EMU3000 型電車)': 'TC',
    # 推拉式自強
    '自強(推拉式自強號且無自行車車廂)': 'TC-PP',
    '自強(推拉式自強號且有自行車車廂)': 'TC-PP',
    # DMU3100 柴聯
    '自強(DMU3100 型柴聯)': 'TC-DMU',
    # 莒光
    '莒光(有身障座位)': 'CG',
    '莒光(無身障座位)': 'CG',
    # 區間
    '區間快': 'CK',
    '區間': 'LC',
}


def normalize_station_id(station_id: str) -> str:
    """將 TDX 新 ID 轉換為軌道使用的舊 ID"""
    return STATION_ID_MAPPING.get(station_id, station_id)


def get_train_type_code(tdx_train_type: str) -> str:
    """從 TDX 車種名稱取得車種代碼"""
    return TDX_TRAIN_TYPE_MAPPING.get(tdx_train_type, 'OTHER')


def time_to_seconds(time_str: str) -> int:
    """將時間字串 (HH:MM) 轉換為秒數"""
    try:
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2]) if len(parts) > 2 else 0
        return hours * 3600 + minutes * 60 + seconds
    except:
        return 0


def load_od_station_progress() -> Dict[str, Dict[str, float]]:
    """載入 O-D 軌道的車站 progress"""
    file_path = os.path.join(TRACKS_OD_DIR, 'od_station_progress.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_track_index(od_progress: Dict) -> Dict[Tuple[str, str], List[str]]:
    """建立 (起站, 迄站) → 軌道 ID 的索引"""
    index = defaultdict(list)

    for track_id, stations in od_progress.items():
        if len(stations) < 2:
            continue

        # 用 progress 值找起點(最小)和終點(最大)
        sorted_stations = sorted(stations.items(), key=lambda x: x[1])
        origin = sorted_stations[0][0]
        destination = sorted_stations[-1][0]
        index[(origin, destination)].append(track_id)

    return dict(index)


def find_matching_track(
    origin_id: str,
    dest_id: str,
    stop_ids: List[str],
    track_index: Dict,
    od_progress: Dict
) -> Optional[str]:
    """找到最匹配的軌道 ID（以停靠站覆蓋率為主要依據）"""
    # 轉換 ID
    origin_normalized = normalize_station_id(origin_id)
    dest_normalized = normalize_station_id(dest_id)
    stops_normalized = [normalize_station_id(s) for s in stop_ids]
    stops_set = set(stops_normalized)

    def score_track(track_id: str) -> Tuple[float, float, int, str]:
        """計算軌道的匹配分數（越小越好）"""
        track_stations = od_progress[track_id]
        track_set = set(track_stations.keys())
        coverage = len(stops_set & track_set)
        coverage_ratio = coverage / len(stops_normalized) if stops_normalized else 0

        # 計算中間站單調性（monotonicity）
        # 按列車停靠順序檢查 progress 是否遞增
        prev_prog = -1.0
        forward = 0
        backward = 0
        for sid in stops_normalized:
            if sid in track_stations:
                prog = track_stations[sid]
                if prev_prog >= 0:
                    if prog > prev_prog:
                        forward += 1
                    elif prog < prev_prog:
                        backward += 1
                prev_prog = prog
        total_pairs = forward + backward
        backward_ratio = backward / total_pairs if total_pairs > 0 else 0

        # 主排序：backward 比例（越低越好）
        # 次排序：覆蓋率（越高越好 → 負數越小越好）
        # 三排序：軌道類型優先級
        if track_id.startswith('OD-'):
            type_priority = 0
        elif track_id.startswith('SP-'):
            type_priority = 1
        elif track_id.startswith('BB-'):
            type_priority = 2
        else:
            type_priority = 3

        return (backward_ratio, -coverage_ratio, type_priority, track_id)

    # 精確匹配（起站和迄站完全一致）
    key = (origin_normalized, dest_normalized)
    if key in track_index:
        candidates = track_index[key]
        best = min(candidates, key=score_track)
        return best

    # 模糊匹配（軌道包含起迄站且方向正確）
    candidates = []
    for track_id, stations in od_progress.items():
        if origin_normalized in stations and dest_normalized in stations:
            origin_prog = stations[origin_normalized]
            dest_prog = stations[dest_normalized]
            if origin_prog < dest_prog:
                candidates.append(track_id)

    if candidates:
        best = min(candidates, key=score_track)
        return best

    return None


def convert_train(
    train: Dict,
    track_index: Dict,
    od_progress: Dict,
    station_names: Dict
) -> Optional[Dict]:
    """將 TDX 列車資料轉換為 Mini Taiwan 格式"""
    train_info = train.get('TrainInfo', {})
    stops = train.get('StopTimes', [])

    if not stops or len(stops) < 2:
        return None

    train_no = train_info.get('TrainNo', '')
    train_type_name = train_info.get('TrainTypeName', {}).get('Zh_tw', '區間')
    train_type_code = get_train_type_code(train_type_name)

    origin_id = stops[0]['StationID']
    dest_id = stops[-1]['StationID']
    origin_name = stops[0].get('StationName', {}).get('Zh_tw', '')
    dest_name = stops[-1].get('StationName', {}).get('Zh_tw', '')

    stop_ids = [s['StationID'] for s in stops]

    # 找對應軌道
    track_id = find_matching_track(origin_id, dest_id, stop_ids, track_index, od_progress)

    if not track_id:
        return None

    # 取得首站發車時間（用作基準）
    departure_time = stops[0].get('DepartureTime', '00:00')
    if len(departure_time.split(':')) == 2:
        departure_time += ':00'

    first_departure = time_to_seconds(departure_time)

    # 取得軌道上的車站集合（用於過濾無效站）
    track_station_set = set(od_progress.get(track_id, {}).keys())

    # 轉換停靠站
    converted_stations = []
    prev_departure_sec = 0

    for i, stop in enumerate(stops):
        sid = stop['StationID']
        normalized_sid = normalize_station_id(sid)

        arr_time = stop.get('ArrivalTime', departure_time)
        dep_time = stop.get('DepartureTime', arr_time)

        if len(arr_time.split(':')) == 2:
            arr_time += ':00'
        if len(dep_time.split(':')) == 2:
            dep_time += ':00'

        arrival_sec = time_to_seconds(arr_time) - first_departure
        departure_sec = time_to_seconds(dep_time) - first_departure

        # 處理跨日
        if arrival_sec < 0:
            arrival_sec += 86400
        if departure_sec < 0:
            departure_sec += 86400

        # 首站：強制 arrival = 0, departure = 0
        if i == 0:
            arrival_sec = 0
            departure_sec = 0

        # 跳過不在軌道 station_progress 中的站
        # （列車會在前後站之間平滑移動，不影響整體行程）
        if normalized_sid not in track_station_set:
            continue

        converted_stations.append({
            'station_id': normalized_sid,
            'arrival': arrival_sec,
            'departure': departure_sec
        })

    # 去除重複站（如 3350→3330 映射後與原本的 3330 重複）
    # 保留每個 station_id 的第一次出現
    seen_ids = set()
    deduped_stations = []
    for st in converted_stations:
        if st['station_id'] not in seen_ids:
            seen_ids.add(st['station_id'])
            deduped_stations.append(st)
    converted_stations = deduped_stations

    # 確保至少有 2 站
    if len(converted_stations) < 2:
        return None

    # 計算總行駛時間
    total_time = converted_stations[-1]['arrival']

    return {
        'train_id': f"{train_type_code}-{train_no}",
        'train_no': train_no,
        'train_type': train_type_name,
        'train_type_code': train_type_code,
        'departure_time': departure_time,
        'od_track_id': track_id,
        'origin_station': origin_name,
        'destination_station': dest_name,
        'total_travel_time': total_time,
        'stations': converted_stations
    }


def load_station_names() -> Dict[str, str]:
    """載入車站名稱對照表"""
    file_path = os.path.join(INPUT_DIR, 'station_mapping.json')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('stations', {})
    return {}


def main():
    print("=" * 60)
    print("Phase 3: TDX 時刻表轉換為 Mini Taiwan 格式")
    print("=" * 60)

    # 建立輸出目錄
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    by_od_dir = os.path.join(OUTPUT_DIR, 'by_od')
    os.makedirs(by_od_dir, exist_ok=True)

    # 載入資料
    print("\n[1/4] 載入資料...")

    tdx_file = os.path.join(INPUT_DIR, 'tdx_timetable_latest.json')
    with open(tdx_file, 'r', encoding='utf-8') as f:
        tdx_data = json.load(f)

    timetables = tdx_data.get('timetables', [])
    print(f"  ✓ TDX 時刻表: {len(timetables)} 班")

    od_progress = load_od_station_progress()
    print(f"  ✓ O-D 軌道: {len(od_progress)} 條")

    station_names = load_station_names()
    print(f"  ✓ 車站對照: {len(station_names)} 站")

    # 建立軌道索引
    print("\n[2/4] 建立軌道索引...")
    track_index = build_track_index(od_progress)
    print(f"  ✓ 索引建立完成: {len(track_index)} 組 O-D 對")

    # 轉換時刻表
    print("\n[3/4] 轉換時刻表...")
    converted = []
    failed = []
    by_od = defaultdict(list)

    for train in timetables:
        result = convert_train(train, track_index, od_progress, station_names)
        if result:
            converted.append(result)
            by_od[result['od_track_id']].append(result)
        else:
            train_info = train.get('TrainInfo', {})
            stops = train.get('StopTimes', [])
            failed.append({
                'train_no': train_info.get('TrainNo', ''),
                'origin': stops[0].get('StationName', {}).get('Zh_tw', '') if stops else '',
                'dest': stops[-1].get('StationName', {}).get('Zh_tw', '') if stops else '',
                'origin_id': stops[0]['StationID'] if stops else '',
                'dest_id': stops[-1]['StationID'] if stops else '',
            })

    print(f"  ✓ 轉換成功: {len(converted)} 班")
    print(f"  ✗ 轉換失敗: {len(failed)} 班")

    # 儲存結果
    print("\n[4/4] 儲存結果...")

    # Master schedule
    master = {
        'metadata': {
            'title': 'TRA 真實時刻表',
            'total_trains': len(converted),
            'total_od_tracks': len(by_od),
            'generated_at': datetime.now().isoformat(),
            'source': 'TDX GeneralTrainTimetable',
        },
        'schedules': converted
    }

    master_file = os.path.join(OUTPUT_DIR, 'master_schedule.json')
    with open(master_file, 'w', encoding='utf-8') as f:
        json.dump(master, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 主時刻表: {master_file}")

    # 按 O-D 軌道分類
    for track_id, trains in by_od.items():
        od_file = os.path.join(by_od_dir, f"{track_id}.json")
        od_data = {
            'track_id': track_id,
            'departures': sorted(trains, key=lambda x: x['departure_time'])
        }
        with open(od_file, 'w', encoding='utf-8') as f:
            json.dump(od_data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 分軌道時刻表: {len(by_od)} 個檔案")

    # 儲存失敗清單
    if failed:
        failed_file = os.path.join(OUTPUT_DIR, 'conversion_failed.json')
        with open(failed_file, 'w', encoding='utf-8') as f:
            json.dump({'failed': failed, 'count': len(failed)}, f, ensure_ascii=False, indent=2)
        print(f"  ⚠ 失敗清單: {failed_file}")

    # 統計
    print("\n" + "=" * 60)
    print("轉換統計")
    print("=" * 60)

    # 按車種統計
    type_counts = defaultdict(int)
    for train in converted:
        type_counts[train['train_type_code']] += 1

    print("\n車種分布:")
    for code, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {code}: {count} 班")

    # 轉換率
    success_rate = len(converted) / len(timetables) * 100 if timetables else 0
    print(f"\n轉換率: {success_rate:.1f}% ({len(converted)}/{len(timetables)})")

    # 顯示失敗範例
    if failed:
        print("\n失敗範例 (前 10 班):")
        for f in failed[:10]:
            print(f"  {f['train_no']}: {f['origin']}({f['origin_id']}) → {f['dest']}({f['dest_id']})")

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)

    return len(failed) == 0


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
