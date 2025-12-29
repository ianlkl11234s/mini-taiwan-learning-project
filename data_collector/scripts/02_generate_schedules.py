#!/usr/bin/env python3
"""
02_generate_schedules.py - 產生紅線精確時刻表

使用 S2STravelTime API 資料產生精確的時刻表，包含：
- 真實的站間運行時間 (60-175秒不等)
- 真實的停站時間 (23-37秒不等)

輸入：
- raw_data/trtc_s2s_travel_time.json: 站間運行時間 (來自 TDX API)
- raw_data/trtc_frequency.json: 班距資料

輸出：
- output/schedules/R-1-0.json: 象山→淡水 發車時刻表
- output/schedules/R-1-1.json: 淡水→象山 發車時刻表
- output/schedules/R-2-0.json: 大安→北投 發車時刻表
- output/schedules/R-2-1.json: 北投→大安 發車時刻表
- output/schedules/R-3-0.json: 北投→新北投 發車時刻表
- output/schedules/R-3-1.json: 新北投→北投 發車時刻表
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
RAW_DATA_DIR = SCRIPT_DIR.parent / "raw_data"
OUTPUT_DIR = SCRIPT_DIR.parent / "output"
SCHEDULES_DIR = OUTPUT_DIR / "schedules"


@dataclass
class TravelSegment:
    """站間運行資料"""
    from_station: str
    to_station: str
    run_time: int      # 運行秒數
    stop_time: int     # 停站秒數 (到達 to_station 後的停站時間)


@dataclass
class TrackDefinition:
    """軌道定義"""
    track_id: str
    route_id: str
    direction: int     # 0 or 1
    name: str
    origin: str
    destination: str
    stations: List[str] = field(default_factory=list)
    segments: List[TravelSegment] = field(default_factory=list)


def load_json(filepath: Path) -> Any:
    """載入 JSON 檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filepath: Path, data: Any) -> None:
    """儲存 JSON 檔案"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 已儲存: {filepath}")


def time_to_seconds(time_str: str) -> int:
    """將時間字串轉換為當日秒數"""
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2]) if len(parts) > 2 else 0
    return hours * 3600 + minutes * 60 + seconds


def seconds_to_time(seconds: int) -> str:
    """將秒數轉換為時間字串"""
    seconds = seconds % 86400
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def parse_s2s_travel_time(s2s_data: List[Dict]) -> Dict[str, List[TravelSegment]]:
    """
    解析 S2STravelTime API 資料

    Returns:
        Dict mapping route_id to list of TravelSegment
    """
    result = {}

    for route in s2s_data:
        route_id = route.get("RouteID", "")
        travel_times = route.get("TravelTimes", [])

        segments = []
        for tt in travel_times:
            segments.append(TravelSegment(
                from_station=tt["FromStationID"],
                to_station=tt["ToStationID"],
                run_time=tt["RunTime"],
                stop_time=tt["StopTime"]
            ))

        result[route_id] = segments

    return result


def reverse_segments(segments: List[TravelSegment]) -> List[TravelSegment]:
    """
    反轉站間運行資料 (用於反方向)

    注意：停站時間需要重新分配
    - 原本: A --run--> B (stop at B)
    - 反轉: B --run--> A (stop at A)
    """
    reversed_segs = []

    # 反轉順序
    for i in range(len(segments) - 1, -1, -1):
        seg = segments[i]
        # 取下一站的停站時間作為本站的停站時間 (反轉後)
        next_stop_time = segments[i-1].stop_time if i > 0 else 0

        reversed_segs.append(TravelSegment(
            from_station=seg.to_station,
            to_station=seg.from_station,
            run_time=seg.run_time,
            stop_time=next_stop_time
        ))

    # 最後一站 (原本的起站) 使用原本第一站的停站時間
    if reversed_segs and segments:
        reversed_segs[-1] = TravelSegment(
            from_station=reversed_segs[-1].from_station,
            to_station=reversed_segs[-1].to_station,
            run_time=reversed_segs[-1].run_time,
            stop_time=segments[-1].stop_time  # 使用原本終點站的停站時間
        )

    return reversed_segs


def build_track_definitions(s2s_segments: Dict[str, List[TravelSegment]]) -> Dict[str, TrackDefinition]:
    """建立軌道定義"""
    tracks = {}

    # R-1: 象山-淡水 (全線)
    if "R-1" in s2s_segments:
        segs = s2s_segments["R-1"]
        # API 資料是 R28→R02，我們需要反轉為 R02→R28 (象山→淡水)
        segs_0 = reverse_segments(segs)  # R02→R28
        segs_1 = segs  # R28→R02

        stations_0 = [segs_0[0].from_station] + [s.to_station for s in segs_0]
        stations_1 = [segs_1[0].from_station] + [s.to_station for s in segs_1]

        tracks["R-1-0"] = TrackDefinition(
            track_id="R-1-0",
            route_id="R-1",
            direction=0,
            name="象山 → 淡水",
            origin="R02",
            destination="R28",
            stations=stations_0,
            segments=segs_0
        )
        tracks["R-1-1"] = TrackDefinition(
            track_id="R-1-1",
            route_id="R-1",
            direction=1,
            name="淡水 → 象山",
            origin="R28",
            destination="R02",
            stations=stations_1,
            segments=segs_1
        )

    # R-2: 大安-北投 (中段)
    if "R-2" in s2s_segments:
        segs = s2s_segments["R-2"]
        # API 資料是 R22→R05，我們需要反轉為 R05→R22 (大安→北投)
        segs_0 = reverse_segments(segs)  # R05→R22
        segs_1 = segs  # R22→R05

        stations_0 = [segs_0[0].from_station] + [s.to_station for s in segs_0]
        stations_1 = [segs_1[0].from_station] + [s.to_station for s in segs_1]

        tracks["R-2-0"] = TrackDefinition(
            track_id="R-2-0",
            route_id="R-2",
            direction=0,
            name="大安 → 北投",
            origin="R05",
            destination="R22",
            stations=stations_0,
            segments=segs_0
        )
        tracks["R-2-1"] = TrackDefinition(
            track_id="R-2-1",
            route_id="R-2",
            direction=1,
            name="北投 → 大安",
            origin="R22",
            destination="R05",
            stations=stations_1,
            segments=segs_1
        )

    # R-3: 北投-新北投 (支線)
    if "R-3" in s2s_segments:
        segs = s2s_segments["R-3"]
        # API 資料是 R22→R22A
        segs_0 = segs  # R22→R22A
        segs_1 = reverse_segments(segs)  # R22A→R22

        stations_0 = [segs_0[0].from_station] + [s.to_station for s in segs_0]
        stations_1 = [segs_1[0].from_station] + [s.to_station for s in segs_1]

        tracks["R-3-0"] = TrackDefinition(
            track_id="R-3-0",
            route_id="R-3",
            direction=0,
            name="北投 → 新北投",
            origin="R22",
            destination="R22A",
            stations=stations_0,
            segments=segs_0
        )
        tracks["R-3-1"] = TrackDefinition(
            track_id="R-3-1",
            route_id="R-3",
            direction=1,
            name="新北投 → 北投",
            origin="R22A",
            destination="R22",
            stations=stations_1,
            segments=segs_1
        )

    return tracks


def build_station_times(segments: List[TravelSegment]) -> List[Dict]:
    """
    建立各站時刻序列 (使用精確的站間時間)

    Returns:
        各站時刻序列，格式：
        [
            { "station_id": "R02", "arrival": 0, "departure": 25 },
            { "station_id": "R03", "arrival": 118, "departure": 143 },
            ...
        ]
    """
    result = []
    current_time = 0

    # 起點站
    first_station = segments[0].from_station
    # 起點站的停站時間：使用一個合理的預設值 (25秒)
    first_stop_time = 25
    result.append({
        "station_id": first_station,
        "arrival": 0,
        "departure": first_stop_time
    })
    current_time = first_stop_time

    # 中間站和終點站
    for i, seg in enumerate(segments):
        arrival = current_time + seg.run_time

        if i == len(segments) - 1:
            # 終點站：不需要停站時間
            departure = arrival
        else:
            # 中間站：使用 API 提供的停站時間
            departure = arrival + seg.stop_time

        result.append({
            "station_id": seg.to_station,
            "arrival": arrival,
            "departure": departure
        })
        current_time = departure

    return result


def get_frequency_for_route(
    frequency_data: List[Dict],
    route_id: str,
    is_weekday: bool = True
) -> List[Dict]:
    """取得特定路線的班距資料"""
    service_tag = "平日" if is_weekday else "假日"

    for freq in frequency_data:
        if freq.get('RouteID') == route_id:
            service_day = freq.get('ServiceDay', {})
            if service_day.get('ServiceTag') == service_tag:
                return freq.get('Headways', [])

    return []


def generate_departure_times(
    headways: List[Dict],
    operation_start: str = "06:00",
    operation_end: str = "24:00"
) -> List[str]:
    """根據班距資料產生發車時刻列表"""
    departures = []

    sorted_headways = sorted(headways, key=lambda h: time_to_seconds(h['StartTime']))

    op_start_sec = time_to_seconds(operation_start)
    op_end_sec = time_to_seconds(operation_end)

    if op_end_sec <= op_start_sec:
        op_end_sec += 86400

    current_time = op_start_sec

    while current_time < op_end_sec:
        headway_mins = 10  # 預設 10 分鐘
        current_time_of_day = current_time % 86400

        for hw in sorted_headways:
            hw_start = time_to_seconds(hw['StartTime'])
            hw_end = time_to_seconds(hw['EndTime'])

            if hw_end <= hw_start:
                hw_end += 86400

            if hw_start <= current_time_of_day < hw_end:
                min_hw = hw.get('MinHeadwayMins', 8)
                max_hw = hw.get('MaxHeadwayMins', 10)
                avg_hw = (min_hw + max_hw) / 2
                if avg_hw > 0:
                    headway_mins = avg_hw
                break

        departures.append(seconds_to_time(current_time % 86400))
        current_time += int(headway_mins * 60)

    return departures


def generate_schedule_for_track(
    track: TrackDefinition,
    frequency_data: List[Dict],
    is_weekday: bool = True
) -> Dict:
    """為單一軌道產生時刻表"""

    # 取得班距資料
    headways = get_frequency_for_route(frequency_data, track.route_id, is_weekday)

    if not headways:
        print(f"  ⚠️ 找不到 {track.route_id} 的班距資料，使用預設值")
        headways = [{"StartTime": "06:00", "EndTime": "24:00", "MinHeadwayMins": 8, "MaxHeadwayMins": 10}]

    # 產生發車時刻
    departure_times = generate_departure_times(headways)

    # 使用精確的站間時間建立各站時刻
    station_times_template = build_station_times(track.segments)
    total_travel_time = station_times_template[-1]["arrival"]

    # 產生每班車的時刻表
    departures = []
    for i, dep_time in enumerate(departure_times):
        departures.append({
            "departure_time": dep_time,
            "train_id": f"{track.track_id}-{i+1:03d}",
            "stations": station_times_template,
            "total_travel_time": total_travel_time
        })

    return {
        "track_id": track.track_id,
        "route_id": track.route_id,
        "name": track.name,
        "origin": track.origin,
        "destination": track.destination,
        "stations": track.stations,
        "travel_time_seconds": total_travel_time,
        "travel_time_minutes": round(total_travel_time / 60, 1),
        "is_weekday": is_weekday,
        "departure_count": len(departures),
        "departures": departures,
        "_meta": {
            "data_source": "TDX S2STravelTime API",
            "generated_by": "02_generate_schedules.py",
            "uses_accurate_travel_times": True
        }
    }


def main():
    """主程式"""
    print("=" * 60)
    print("02_generate_schedules.py - 產生紅線精確時刻表")
    print("=" * 60)

    # 載入 S2STravelTime 資料
    print("\n載入 S2STravelTime 資料...")
    s2s_filepath = RAW_DATA_DIR / "trtc_s2s_travel_time.json"
    if not s2s_filepath.exists():
        print(f"  ✗ 找不到 {s2s_filepath}")
        print("  請先執行 00_fetch_s2s_travel_time.py")
        return

    s2s_data = load_json(s2s_filepath)
    print(f"  ✓ 載入 {len(s2s_data)} 條路線資料")

    # 解析站間運行時間
    s2s_segments = parse_s2s_travel_time(s2s_data)

    # 建立軌道定義
    tracks = build_track_definitions(s2s_segments)
    print(f"  ✓ 建立 {len(tracks)} 條軌道定義")

    # 載入班距資料
    print("\n載入班距資料...")
    frequency_data = load_json(RAW_DATA_DIR / "trtc_frequency.json")
    print(f"  ✓ 載入 {len(frequency_data)} 筆班距資料")

    # 產生各軌道時刻表
    print("\n產生時刻表...")

    for track_id, track in tracks.items():
        print(f"\n處理 {track_id}: {track.name}")
        print(f"  車站數: {len(track.stations)}")

        schedule = generate_schedule_for_track(track, frequency_data)

        print(f"  行駛時間: {schedule['travel_time_minutes']} 分鐘 (精確)")
        print(f"  產生班次: {schedule['departure_count']} 班")
        print(f"  首班車: {schedule['departures'][0]['departure_time']}")
        print(f"  末班車: {schedule['departures'][-1]['departure_time']}")

        # 顯示範例站點時間
        first_train = schedule['departures'][0]
        print(f"  範例 (首班車前3站):")
        for st in first_train['stations'][:3]:
            print(f"    {st['station_id']}: 到站 {st['arrival']}s, 離站 {st['departure']}s")

        # 儲存
        filepath = SCHEDULES_DIR / f"{track_id}.json"
        save_json(filepath, schedule)

    # 統計摘要
    print("\n" + "=" * 60)
    print("統計摘要")
    print("=" * 60)

    total_trains = 0
    for track_id in tracks:
        schedule = load_json(SCHEDULES_DIR / f"{track_id}.json")
        count = schedule['departure_count']
        travel_time = schedule['travel_time_minutes']
        total_trains += count
        print(f"  {track_id}: {count} 班, {travel_time} 分鐘")

    print(f"\n  總計: {total_trains} 班列車")

    # 比較舊版 vs 新版
    print("\n" + "=" * 60)
    print("精確度改善")
    print("=" * 60)
    print("  舊版: 站間時間平均分配, 停站固定 40 秒")
    print("  新版: 使用 TDX S2STravelTime API 精確資料")
    print("  改善: 站間時間 60-175 秒, 停站 23-37 秒")

    print("\n" + "=" * 60)
    print("完成！")
    print(f"輸出目錄: {SCHEDULES_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
