#!/usr/bin/env python3
"""
fetch_yl_kl_timetable.py - 從 TDX API 取得宜蘭線和基隆支線時刻表

功能：
1. 從 TDX API 取得當日台鐵時刻表
2. 篩選宜蘭線 (YL) 和基隆支線 (KL) 列車
3. 根據起迄站判斷 O-D 軌道
4. 轉換為專案格式並輸出

使用方式：
    source venv/bin/activate
    python scripts/tra/fetch_yl_kl_timetable.py

環境變數：
    TDX_APP_ID: TDX 應用程式 ID
    TDX_APP_KEY: TDX 應用程式金鑰
"""

import json
import os
import requests
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'public', 'data', 'tra')
OUTPUT_DIR = os.path.join(DATA_DIR, 'schedules_od')
PROGRESS_FILE = os.path.join(DATA_DIR, 'tracks_od', 'od_station_progress.json')

# TDX API 設定
TDX_AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TDX_API_URL = "https://tdx.transportdata.tw/api/basic/v3/Rail/TRA/DailyTrainTimetable/Today"

# ============================================================
# 車站定義
# ============================================================

# 臺北區域車站（起點判斷用）
TAIPEI_AREA = {
    '1000',  # 臺北
    '0990',  # 松山
    '0980',  # 南港
    '0970',  # 汐科
    '0960',  # 汐止
    '0950',  # 五堵
    '0940',  # 百福
    '0930',  # 七堵
    '0920',  # 八堵
}

# 基隆區域車站
KEELUNG_AREA = {
    '0900',  # 基隆
    '0910',  # 三坑
}

# 宜蘭線車站 (八堵往南)
YILAN_LINE_STATIONS = {
    '7390',  # 暖暖
    '7380',  # 四腳亭
    '7360',  # 瑞芳
    '7350',  # 猴硐
    '7330',  # 三貂嶺
    '7320',  # 牡丹
    '7310',  # 雙溪
    '7300',  # 貢寮
    '7290',  # 福隆
    '7280',  # 石城
    '7270',  # 大里
    '7260',  # 大溪
    '7250',  # 龜山
    '7240',  # 外澳
    '7230',  # 頭城
    '7220',  # 頂埔
    '7210',  # 礁溪
    '7200',  # 四城
    '7190',  # 宜蘭
    '7180',  # 二結
    '7170',  # 中里
    '7160',  # 羅東
    '7150',  # 冬山
    '7140',  # 新馬
    '7130',  # 蘇澳新
    '7120',  # 蘇澳
}

# 北迴線車站 (蘇澳新往南)
BEIHUI_LINE_STATIONS = {
    '7110',  # 永樂
    '7100',  # 東澳
    '7090',  # 南澳
    '7080',  # 武塔
    '7070',  # 漢本
    '7060',  # 和平
    '7050',  # 和仁
    '7040',  # 崇德
    '7030',  # 新城
    '7020',  # 景美
    '7010',  # 北埔
    '7000',  # 花蓮
}

# 花蓮區域
HUALIEN_AREA = {'7000'}

# 蘇澳區域
SUAO_AREA = {'7120', '7130'}

# 宜蘭區域（窄範圍）
YILAN_AREA = {'7190', '7180', '7170', '7160'}

# 車站名稱對照
STATION_NAMES = {
    '1000': '臺北', '0990': '松山', '0980': '南港', '0970': '汐科',
    '0960': '汐止', '0950': '五堵', '0940': '百福', '0930': '七堵',
    '0920': '八堵', '0910': '三坑', '0900': '基隆',
    '7390': '暖暖', '7380': '四腳亭', '7360': '瑞芳', '7350': '猴硐',
    '7330': '三貂嶺', '7320': '牡丹', '7310': '雙溪', '7300': '貢寮',
    '7290': '福隆', '7280': '石城', '7270': '大里', '7260': '大溪',
    '7250': '龜山', '7240': '外澳', '7230': '頭城', '7220': '頂埔',
    '7210': '礁溪', '7200': '四城', '7190': '宜蘭', '7180': '二結',
    '7170': '中里', '7160': '羅東', '7150': '冬山', '7140': '新馬',
    '7130': '蘇澳新', '7120': '蘇澳', '7110': '永樂', '7100': '東澳',
    '7090': '南澳', '7080': '武塔', '7070': '漢本', '7060': '和平',
    '7050': '和仁', '7040': '崇德', '7030': '新城', '7020': '景美',
    '7010': '北埔', '7000': '花蓮',
}


def get_tdx_token() -> Optional[str]:
    """從 TDX 取得 access token"""
    app_id = os.environ.get('TDX_APP_ID')
    app_key = os.environ.get('TDX_APP_KEY')

    if not app_id or not app_key:
        print("錯誤: 請設定 TDX_APP_ID 和 TDX_APP_KEY 環境變數")
        return None

    try:
        response = requests.post(
            TDX_AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": app_id,
                "client_secret": app_key,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"取得 TDX token 失敗: {e}")
        return None


def fetch_timetable(token: str) -> Optional[List[Dict]]:
    """從 TDX 取得當日時刻表"""
    try:
        response = requests.get(
            TDX_API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept-Encoding": "gzip, deflate"
            },
            params={"$format": "JSON"}
        )
        response.raise_for_status()
        data = response.json()
        return data.get("TrainTimetables", [])
    except Exception as e:
        print(f"取得時刻表失敗: {e}")
        return None


def time_str_to_seconds(time_str: str) -> int:
    """將時間字串轉換為秒數 (HH:MM 或 HH:MM:SS)"""
    parts = time_str.split(':')
    if len(parts) == 2:
        h, m = int(parts[0]), int(parts[1])
        return h * 3600 + m * 60
    elif len(parts) == 3:
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        return h * 3600 + m * 60 + s
    return 0


def get_train_stations(train: Dict) -> List[str]:
    """取得列車停靠的車站 ID 列表"""
    stops = train.get("StopTimes", [])
    return [stop["StationID"] for stop in stops]


def classify_train(train: Dict) -> Optional[str]:
    """
    分類列車屬於哪條線
    Returns: 'YL' (宜蘭線), 'KL' (基隆線), or None
    """
    stations = get_train_stations(train)
    if not stations:
        return None

    station_set = set(stations)

    # 檢查是否有基隆相關車站
    has_keelung = bool(station_set & KEELUNG_AREA)

    # 檢查是否有宜蘭線車站
    has_yilan = bool(station_set & (YILAN_LINE_STATIONS | BEIHUI_LINE_STATIONS))

    # 基隆線：有基隆區域車站，但沒有宜蘭線車站
    if has_keelung and not has_yilan:
        return 'KL'

    # 宜蘭線：有宜蘭線車站，但沒有基隆區域車站
    if has_yilan and not has_keelung:
        return 'YL'

    return None


def determine_yl_od_track(first_station: str, last_station: str, stations: List[str]) -> Optional[str]:
    """
    判斷宜蘭線列車的 O-D 軌道
    """
    station_set = set(stations)

    # 判斷是否進入花蓮（北迴線）
    has_hualien = bool(station_set & BEIHUI_LINE_STATIONS)

    # 起點在臺北區域 → 南下
    if first_station in TAIPEI_AREA or first_station in YILAN_LINE_STATIONS:
        if last_station in HUALIEN_AREA or (has_hualien and last_station in BEIHUI_LINE_STATIONS):
            return 'YL-TP-HL'
        elif last_station in SUAO_AREA:
            return 'YL-TP-SA'
        elif last_station in YILAN_AREA or last_station in YILAN_LINE_STATIONS:
            return 'YL-TP-YL'

    # 終點在臺北區域 → 北上
    if last_station in TAIPEI_AREA or last_station in YILAN_LINE_STATIONS:
        if first_station in HUALIEN_AREA or (has_hualien and first_station in BEIHUI_LINE_STATIONS):
            return 'YL-HL-TP'
        elif first_station in SUAO_AREA:
            return 'YL-SA-TP'
        elif first_station in YILAN_AREA or first_station in YILAN_LINE_STATIONS:
            return 'YL-YL-TP'

    # 純北迴線列車
    if first_station in HUALIEN_AREA and last_station in SUAO_AREA:
        return 'BH-HL-SX'
    if first_station in SUAO_AREA and last_station in HUALIEN_AREA:
        return 'BH-SX-HL'

    return None


def determine_kl_od_track(first_station: str, last_station: str) -> Optional[str]:
    """
    判斷基隆線列車的 O-D 軌道
    """
    # 往基隆
    if last_station in KEELUNG_AREA:
        return 'KL-TP-KL'
    # 往臺北
    if last_station in TAIPEI_AREA:
        return 'KL-KL-TP'

    return None


def convert_train_to_departure(
    train: Dict,
    od_track_id: str,
    od_station_progress: Dict[str, Dict[str, float]]
) -> Optional[Dict]:
    """
    將 TDX 列車資料轉換為專案格式
    """
    train_info = train.get("TrainInfo", {})
    stops = train.get("StopTimes", [])

    if not stops:
        return None

    train_no = train_info.get("TrainNo", "")
    train_type = train_info.get("TrainTypeName", {}).get("Zh_tw", "區間")

    # 取得此 O-D 軌道的車站進度表
    progress_map = od_station_progress.get(od_track_id, {})

    # 先找出 O-D 軌道上的第一站，用其發車時間作為基準
    base_seconds = 0
    od_first_departure_time = None
    for stop in stops:
        station_id = stop["StationID"]
        if station_id in progress_map:
            od_first_departure_time = stop.get("DepartureTime", "00:00")
            base_seconds = time_str_to_seconds(od_first_departure_time)
            break

    if od_first_departure_time is None:
        return None

    # 轉換各站時刻
    converted_stations = []
    is_first_od_station = True
    for stop in stops:
        station_id = stop["StationID"]

        # 檢查車站是否在此 O-D 軌道的進度表中
        if station_id not in progress_map:
            # 跳過不在此軌道上的車站
            continue

        arrival_time = stop.get("ArrivalTime", stop.get("DepartureTime", "00:00"))
        departure_time_stop = stop.get("DepartureTime", arrival_time)

        arrival_seconds = time_str_to_seconds(arrival_time) - base_seconds
        departure_seconds = time_str_to_seconds(departure_time_stop) - base_seconds

        # 第一站的 arrival 和 departure 都是 0
        if is_first_od_station:
            arrival_seconds = 0
            departure_seconds = 0
            is_first_od_station = False
        else:
            # 處理跨午夜
            if arrival_seconds < 0:
                arrival_seconds += 86400
            if departure_seconds < 0:
                departure_seconds += 86400

        station_name = STATION_NAMES.get(station_id, station_id)

        converted_stations.append({
            "station_id": station_id,
            "station_name": station_name,
            "arrival": arrival_seconds,
            "departure": departure_seconds
        })

    if not converted_stations:
        return None

    # 計算總行車時間
    total_travel_time = converted_stations[-1]["arrival"]

    return {
        "departure_time": f"{od_first_departure_time}:00",
        "train_id": f"{od_track_id.split('-')[0]}-{train_no}",
        "train_no": train_no,
        "train_type": train_type,
        "origin_station": converted_stations[0]["station_id"],
        "destination_station": converted_stations[-1]["station_id"],
        "od_track_id": od_track_id,
        "stations": converted_stations,
        "total_travel_time": total_travel_time
    }


def load_od_station_progress() -> Dict[str, Dict[str, float]]:
    """載入 O-D 車站進度表"""
    if not os.path.exists(PROGRESS_FILE):
        print(f"警告: 進度表檔案不存在: {PROGRESS_FILE}")
        return {}

    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_schedules(schedules: Dict[str, List[Dict]], line_code: str):
    """儲存時刻表"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 分方向儲存
    dir_0_departures = []  # 南下/往基隆
    dir_1_departures = []  # 北上/往臺北

    for od_track_id, departures in schedules.items():
        # 判斷方向
        if od_track_id in ['YL-TP-HL', 'YL-TP-SA', 'YL-TP-YL', 'BH-SX-HL', 'KL-TP-KL']:
            dir_0_departures.extend(departures)
        else:
            dir_1_departures.extend(departures)

    # 按發車時間排序
    dir_0_departures.sort(key=lambda x: time_str_to_seconds(x['departure_time']))
    dir_1_departures.sort(key=lambda x: time_str_to_seconds(x['departure_time']))

    # 儲存方向 0
    output_0 = {
        "track_id": f"{line_code}-0",
        "route_id": line_code,
        "name": f"{line_code} 線時刻表 (南下)",
        "source": "TDX API",
        "generated_at": datetime.now().isoformat(),
        "departure_count": len(dir_0_departures),
        "departures": dir_0_departures
    }

    output_path_0 = os.path.join(OUTPUT_DIR, f"{line_code}-0.json")
    with open(output_path_0, 'w', encoding='utf-8') as f:
        json.dump(output_0, f, ensure_ascii=False, indent=2)
    print(f"  儲存: {output_path_0} ({len(dir_0_departures)} 班)")

    # 儲存方向 1
    output_1 = {
        "track_id": f"{line_code}-1",
        "route_id": line_code,
        "name": f"{line_code} 線時刻表 (北上)",
        "source": "TDX API",
        "generated_at": datetime.now().isoformat(),
        "departure_count": len(dir_1_departures),
        "departures": dir_1_departures
    }

    output_path_1 = os.path.join(OUTPUT_DIR, f"{line_code}-1.json")
    with open(output_path_1, 'w', encoding='utf-8') as f:
        json.dump(output_1, f, ensure_ascii=False, indent=2)
    print(f"  儲存: {output_path_1} ({len(dir_1_departures)} 班)")


def main():
    print("=" * 60)
    print("從 TDX 取得 YL/KL 時刻表")
    print("=" * 60)

    # 取得 TDX token
    print("\n取得 TDX token...")
    token = get_tdx_token()
    if not token:
        return

    print("  ✓ Token 取得成功")

    # 取得時刻表
    print("\n取得當日時刻表...")
    timetables = fetch_timetable(token)
    if not timetables:
        return

    print(f"  ✓ 取得 {len(timetables)} 班列車")

    # 載入 O-D 車站進度表
    print("\n載入 O-D 車站進度表...")
    od_station_progress = load_od_station_progress()
    print(f"  ✓ 載入 {len(od_station_progress)} 條 O-D 軌道")

    # 分類列車
    print("\n分類列車...")
    yl_trains = []
    kl_trains = []
    skipped = 0

    for train in timetables:
        line = classify_train(train)
        if line == 'YL':
            yl_trains.append(train)
        elif line == 'KL':
            kl_trains.append(train)
        else:
            skipped += 1

    print(f"  宜蘭線 (YL): {len(yl_trains)} 班")
    print(f"  基隆線 (KL): {len(kl_trains)} 班")
    print(f"  跳過: {skipped} 班 (非 YL/KL)")

    # 處理宜蘭線
    print("\n處理宜蘭線...")
    yl_schedules: Dict[str, List[Dict]] = {}
    yl_failed = 0

    for train in yl_trains:
        stations = get_train_stations(train)
        if not stations:
            yl_failed += 1
            continue

        first_station = stations[0]
        last_station = stations[-1]

        od_track_id = determine_yl_od_track(first_station, last_station, stations)
        if not od_track_id:
            yl_failed += 1
            continue

        departure = convert_train_to_departure(train, od_track_id, od_station_progress)
        if departure:
            if od_track_id not in yl_schedules:
                yl_schedules[od_track_id] = []
            yl_schedules[od_track_id].append(departure)
        else:
            yl_failed += 1

    yl_total = sum(len(deps) for deps in yl_schedules.values())
    print(f"  成功轉換: {yl_total} 班")
    print(f"  失敗: {yl_failed} 班")

    for od_track_id, deps in sorted(yl_schedules.items()):
        print(f"    {od_track_id}: {len(deps)} 班")

    # 處理基隆線
    print("\n處理基隆線...")
    kl_schedules: Dict[str, List[Dict]] = {}
    kl_failed = 0

    for train in kl_trains:
        stations = get_train_stations(train)
        if not stations:
            kl_failed += 1
            continue

        first_station = stations[0]
        last_station = stations[-1]

        od_track_id = determine_kl_od_track(first_station, last_station)
        if not od_track_id:
            kl_failed += 1
            continue

        departure = convert_train_to_departure(train, od_track_id, od_station_progress)
        if departure:
            if od_track_id not in kl_schedules:
                kl_schedules[od_track_id] = []
            kl_schedules[od_track_id].append(departure)
        else:
            kl_failed += 1

    kl_total = sum(len(deps) for deps in kl_schedules.values())
    print(f"  成功轉換: {kl_total} 班")
    print(f"  失敗: {kl_failed} 班")

    for od_track_id, deps in sorted(kl_schedules.items()):
        print(f"    {od_track_id}: {len(deps)} 班")

    # 儲存時刻表
    print("\n儲存時刻表...")
    save_schedules(yl_schedules, 'YL')
    save_schedules(kl_schedules, 'KL')

    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)
    print("\n下一步:")
    print("1. 更新 useTraData.ts 加入 KL 時刻表載入")
    print("2. 更新 TraTrainEngine.ts 加入 KL 軌道對應")
    print("3. npm run dev 驗證")


if __name__ == '__main__':
    main()
