# 軌道運輸系統實作通用指南

> 適用於台灣各捷運、輕軌系統的 Mini Tokyo 3D 整合指南

**建立日期**: 2026-01-02
**適用系統**: TRTC、KRTC、TYMC、KLRT、TMRT、NTMC 等

---

## 一、總覽

本文件提供標準化的實作流程，可用於新增任何台灣軌道運輸系統至 Mini Tokyo 3D 地圖。

### 1.1 支援的系統類型

| 類型 | 代碼 | 範例 |
|------|------|------|
| 捷運 (Metro) | MRT | TRTC、KRTC、TYMC、TMRT |
| 輕軌 (Light Rail) | LRT | KLRT、NTDLRT |
| 纜車 (Cable) | CBL | MK (貓空纜車) |
| 高鐵 (HSR) | HSR | THSR |

### 1.2 TDX 系統代碼對照

| 系統 | OperatorCode | RailSystem | 名稱 |
|------|--------------|------------|------|
| TRTC | TRTC | TRTC | 台北捷運 |
| KRTC | KRTC | KRTC | 高雄捷運 |
| TYMC | TYMC | TYMC | 桃園捷運 |
| KLRT | KLRT | KLRT | 高雄輕軌 |
| TMRT | TMRT | TMRT | 台中捷運 |
| NTMC | NTMC | NTMC | 新北捷運 (淡海/安坑) |

---

## 二、TDX API 參考

### 2.1 必要 API 端點

| API | 用途 | 優先級 |
|-----|------|--------|
| `/v2/Rail/Metro/Station/{RailSystem}` | 車站座標與基本資訊 | P0 |
| `/v2/Rail/Metro/Shape/{RailSystem}` | 軌道幾何 (WKT) | P0 |
| `/v2/Rail/Metro/StationOfLine/{RailSystem}` | 站序與線路關係 | P0 |
| `/v2/Rail/Metro/StationTimeTable/{RailSystem}` | 時刻表 | P1 |
| `/v2/Rail/Metro/S2STravelTime/{RailSystem}` | 站間行車時間 | P1 |
| `/v2/Rail/Metro/FirstLastTimetable/{RailSystem}` | 首末班車資訊 | P2 |

### 2.2 API 可用性矩陣

```
✅ = 有資料  ⚠️ = 部分資料  ❌ = 無資料
```

| 系統 | Station | Shape | StationOfLine | StationTimeTable | S2STravelTime |
|------|---------|-------|---------------|------------------|---------------|
| TRTC | ✅ | ✅ | ✅ | ⚠️ (部分線路) | ✅ |
| KRTC | ✅ | ✅ | ✅ | ✅ | ✅ |
| TYMC | ✅ | ✅ | ✅ | ✅ | ✅ |
| KLRT | ✅ | ✅ | ✅ | ✅ | ✅ |
| TMRT | ✅ | ✅ | ✅ | ✅ | ✅ |
| NTMC | ✅ | ✅ | ✅ | ⚠️ | ✅ |

### 2.3 輕軌專用 API

輕軌系統使用不同的 API 路徑：

```
/v2/Rail/THSR/...     → 高鐵
/v2/Rail/TRA/...      → 台鐵
/v2/Rail/Metro/...    → 捷運 (含輕軌)
```

高雄輕軌 (KLRT) 使用 Metro API，系統代碼為 `KLRT`。

---

## 三、資料處理流程

### 3.1 標準處理步驟

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: 資料擷取                                           │
├─────────────────────────────────────────────────────────────┤
│  1. 呼叫 Station API → 取得車站座標                          │
│  2. 呼叫 Shape API → 取得軌道幾何                            │
│  3. 呼叫 StationOfLine API → 取得站序                        │
│  4. 呼叫 StationTimeTable API → 取得時刻表                   │
│  5. 呼叫 S2STravelTime API → 取得站間時間                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: 資料轉換                                           │
├─────────────────────────────────────────────────────────────┤
│  1. WKT → GeoJSON 軌道檔案                                   │
│  2. 計算各站 progress (0-1)                                  │
│  3. 建立時刻表 JSON                                          │
│  4. 偵測首班車發車站                                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: 整合驗證                                           │
├─────────────────────────────────────────────────────────────┤
│  1. 校準車站位置與軌道                                        │
│  2. 驗證時刻表完整性                                          │
│  3. 測試首末班車顯示                                          │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 檔案命名規範

```
public/
├── data-{system}/              # 例: data-krtc/
│   ├── tracks/
│   │   ├── {SYSTEM}-{LINE}-0.geojson   # 往終點方向
│   │   └── {SYSTEM}-{LINE}-1.geojson   # 往起點方向
│   ├── schedules/
│   │   └── {system}_schedules.json     # 時刻表
│   └── stations/
│       └── {system}_stations.json      # 車站資訊
```

**Track ID 命名規則**:
```
{SYSTEM}-{LINE}-{DIRECTION}

SYSTEM: 大寫系統代碼 (KRTC, KLRT, TMRT)
LINE:   大寫線路代碼 (R, O, G, C)
DIRECTION: 0 = 順向, 1 = 逆向
```

範例:
- `KRTC-R-0` → 高雄捷運紅線 往小港
- `KRTC-R-1` → 高雄捷運紅線 往南岡山
- `KLRT-C-0` → 高雄輕軌環狀線 順時針
- `TMRT-G-0` → 台中捷運綠線 往高鐵台中站

---

## 四、軌道處理

### 4.1 WKT 轉 GeoJSON

TDX Shape API 回傳 WKT 格式：

```
MULTILINESTRING ((
  120.123 22.456,
  120.124 22.457,
  ...
))
```

轉換腳本：

```python
import json
import re

def wkt_to_geojson(wkt_string: str, track_id: str) -> dict:
    """將 WKT MULTILINESTRING 轉換為 GeoJSON"""

    # 提取座標
    pattern = r'MULTILINESTRING\s*\(\(([^)]+)\)\)'
    match = re.search(pattern, wkt_string, re.IGNORECASE)

    if not match:
        raise ValueError("無法解析 WKT 格式")

    coords_str = match.group(1)
    coordinates = []

    for point in coords_str.split(','):
        lon, lat = map(float, point.strip().split())
        coordinates.append([lon, lat])

    return {
        "type": "Feature",
        "properties": {
            "id": track_id,
            "type": "track"
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates
        }
    }
```

### 4.2 車站 Progress 計算

每個車站需要計算其在軌道上的相對位置 (0-1)：

```python
import math

def calculate_station_progress(
    track_coords: list[list[float]],
    station_coords: list[tuple[float, float]]
) -> list[float]:
    """計算各站在軌道上的 progress 值"""

    # 計算軌道總長度
    total_length = 0
    segment_lengths = []

    for i in range(len(track_coords) - 1):
        dx = track_coords[i+1][0] - track_coords[i][0]
        dy = track_coords[i+1][1] - track_coords[i][1]
        length = math.sqrt(dx*dx + dy*dy)
        segment_lengths.append(length)
        total_length += length

    # 為每個車站找最近的軌道點
    progress_list = []

    for station_lon, station_lat in station_coords:
        min_dist = float('inf')
        best_progress = 0
        cumulative = 0

        for i, (lon, lat) in enumerate(track_coords):
            dist = math.sqrt(
                (lon - station_lon)**2 +
                (lat - station_lat)**2
            )

            if dist < min_dist:
                min_dist = dist
                best_progress = cumulative / total_length if total_length > 0 else 0

            if i < len(segment_lengths):
                cumulative += segment_lengths[i]

        progress_list.append(round(best_progress, 4))

    return progress_list
```

### 4.3 軌道方向判斷

```python
def determine_direction(stations: list[dict], line_direction: int) -> str:
    """根據站序判斷軌道方向"""

    # direction 0: 通常是往終點站 (較大站號)
    # direction 1: 通常是往起點站 (較小站號)

    first_station = stations[0]['StationName']['Zh_tw']
    last_station = stations[-1]['StationName']['Zh_tw']

    if line_direction == 0:
        return f"往{last_station}"
    else:
        return f"往{first_station}"
```

---

## 五、時刻表處理

### 5.1 StationTimeTable 結構

TDX 回傳格式：

```json
{
  "StationID": "R02",
  "StationName": { "Zh_tw": "象山", "En": "Xiangshan" },
  "Timetables": [
    {
      "TripID": "R02-0-0647",
      "Direction": 0,
      "DepartureTime": "06:47"
    },
    ...
  ]
}
```

### 5.2 時刻表轉換

```python
def convert_timetable(
    station_timetables: list[dict],
    s2s_times: list[dict],
    line_id: str
) -> dict:
    """將 StationTimeTable 轉換為列車時刻表"""

    # 建立站間時間對照表
    travel_times = {}
    for item in s2s_times:
        key = (item['FromStationID'], item['ToStationID'])
        travel_times[key] = item['RunTime']  # 秒

    # 從起點站收集所有班次
    trains = {}

    for station in station_timetables:
        station_id = station['StationID']

        for trip in station['Timetables']:
            trip_id = trip['TripID']
            direction = trip['Direction']
            dep_time = trip['DepartureTime']

            # 建立列車記錄
            train_key = f"{line_id}-{direction}-{trip_id}"

            if train_key not in trains:
                trains[train_key] = {
                    'trainId': train_key,
                    'direction': direction,
                    'stations': []
                }

            trains[train_key]['stations'].append({
                'stationId': station_id,
                'departure': dep_time
            })

    return {'trains': list(trains.values())}
```

### 5.3 首班車偵測邏輯

首班車可能從非起點站發車，需要特別處理：

```python
def detect_first_trains(station_timetables: list[dict]) -> list[dict]:
    """偵測首班車，包含非起點站發車的班次"""

    first_trains = []

    # 按方向分組
    by_direction = {0: [], 1: []}

    for station in station_timetables:
        station_id = station['StationID']

        for trip in station['Timetables']:
            direction = trip['Direction']
            dep_time = trip['DepartureTime']

            by_direction[direction].append({
                'stationId': station_id,
                'tripId': trip['TripID'],
                'time': dep_time,
                'timeMinutes': time_to_minutes(dep_time)
            })

    # 找出每個方向的首班車
    for direction, trips in by_direction.items():
        if not trips:
            continue

        # 按時間排序
        trips.sort(key=lambda x: x['timeMinutes'])

        # 首班車
        first = trips[0]
        first_trains.append({
            'direction': direction,
            'stationId': first['stationId'],
            'departureTime': first['time'],
            'isTerminalOrigin': is_terminal_station(first['stationId'], direction)
        })

    return first_trains

def time_to_minutes(time_str: str) -> int:
    """將 HH:MM 轉為分鐘數"""
    h, m = map(int, time_str.split(':'))
    return h * 60 + m

def is_terminal_station(station_id: str, direction: int) -> bool:
    """判斷是否為起點站"""
    # 需根據各系統定義
    pass
```

### 5.4 時刻表格式

輸出格式 (`{system}_schedules.json`)：

```json
{
  "version": "1.0",
  "generatedAt": "2026-01-02T12:00:00Z",
  "system": "KRTC",
  "lines": {
    "R": {
      "name": "紅線",
      "trains": [
        {
          "trainId": "KRTC-R-0-0600",
          "direction": 0,
          "originStation": "R24",
          "destinationStation": "R03",
          "isFirstTrain": false,
          "stations": [
            { "stationId": "R24", "arrival": null, "departure": "06:00" },
            { "stationId": "R23", "arrival": "06:02", "departure": "06:02" },
            ...
          ]
        }
      ]
    }
  },
  "firstTrains": [
    {
      "line": "R",
      "direction": 0,
      "stationId": "R24",
      "departureTime": "06:00",
      "isTerminalOrigin": true
    },
    {
      "line": "R",
      "direction": 0,
      "stationId": "R10",
      "departureTime": "05:55",
      "isTerminalOrigin": false,
      "note": "從高雄車站發車"
    }
  ]
}
```

---

## 六、引擎實作

### 6.1 通用列車引擎結構

```typescript
// src/engines/{System}TrainEngine.ts

export interface MetroTrain {
  trainId: string;
  trackId: string;
  direction: number;
  progress: number;
  position: [number, number];
  status: 'waiting' | 'running' | 'stopped' | 'arrived';
  originStation: string;
  destinationStation: string;
  previousStation?: string;
  nextStation?: string;
  previousDepartureTime?: string;
  nextArrivalTime?: string;
}

export class MetroTrainEngine {
  private trains: Map<string, MetroTrain> = new Map();
  private schedules: ScheduleData;
  private tracks: Map<string, TrackData> = new Map();
  private stationProgress: Map<string, number> = new Map();

  constructor(config: MetroConfig) {
    this.loadData(config);
  }

  async loadData(config: MetroConfig): Promise<void> {
    // 載入軌道
    for (const trackId of config.trackIds) {
      const track = await fetch(`/data-${config.system}/tracks/${trackId}.geojson`);
      this.tracks.set(trackId, await track.json());
    }

    // 載入時刻表
    const schedules = await fetch(`/data-${config.system}/schedules/${config.system}_schedules.json`);
    this.schedules = await schedules.json();

    // 載入車站 progress
    // ...
  }

  update(currentTime: Date): MetroTrain[] {
    const activeTrains: MetroTrain[] = [];
    const timeMinutes = currentTime.getHours() * 60 + currentTime.getMinutes();

    for (const line of Object.values(this.schedules.lines)) {
      for (const trainData of line.trains) {
        const train = this.updateTrain(trainData, timeMinutes);
        if (train) {
          activeTrains.push(train);
        }
      }
    }

    return activeTrains;
  }

  private updateTrain(trainData: TrainSchedule, currentTime: number): MetroTrain | null {
    // 計算列車狀態和位置
    // ...
  }
}
```

### 6.2 Progress 插值計算

```typescript
function interpolateOnLineString(
  coordinates: [number, number][],
  progress: number
): [number, number] {
  if (progress <= 0) return coordinates[0];
  if (progress >= 1) return coordinates[coordinates.length - 1];

  // 計算軌道總長度
  let totalLength = 0;
  const segmentLengths: number[] = [];

  for (let i = 0; i < coordinates.length - 1; i++) {
    const dx = coordinates[i + 1][0] - coordinates[i][0];
    const dy = coordinates[i + 1][1] - coordinates[i][1];
    const length = Math.sqrt(dx * dx + dy * dy);
    segmentLengths.push(length);
    totalLength += length;
  }

  // 找到 progress 對應的位置
  const targetLength = progress * totalLength;
  let cumulative = 0;

  for (let i = 0; i < segmentLengths.length; i++) {
    const nextCumulative = cumulative + segmentLengths[i];

    if (nextCumulative >= targetLength) {
      const t = (targetLength - cumulative) / segmentLengths[i];
      return [
        coordinates[i][0] + t * (coordinates[i + 1][0] - coordinates[i][0]),
        coordinates[i][1] + t * (coordinates[i + 1][1] - coordinates[i][1])
      ];
    }

    cumulative = nextCumulative;
  }

  return coordinates[coordinates.length - 1];
}
```

---

## 七、首班車處理

### 7.1 非起點站首班車

某些首班車從中間站發車：

```
台北捷運紅線範例：
- 正常首班: R22 淡水 → R02 象山 (05:30)
- 中站首班: R13 台北車站 → R02 象山 (05:25)
```

### 7.2 偵測邏輯

```typescript
interface FirstTrainInfo {
  trainId: string;
  line: string;
  direction: number;
  originStation: string;
  departureTime: string;
  isTerminalOrigin: boolean;
}

function detectFirstTrains(schedules: ScheduleData): FirstTrainInfo[] {
  const firstTrains: FirstTrainInfo[] = [];

  for (const [lineId, line] of Object.entries(schedules.lines)) {
    // 按方向分組
    const byDirection = new Map<number, TrainSchedule[]>();

    for (const train of line.trains) {
      const dir = train.direction;
      if (!byDirection.has(dir)) {
        byDirection.set(dir, []);
      }
      byDirection.get(dir)!.push(train);
    }

    // 每個方向找最早發車
    for (const [direction, trains] of byDirection) {
      // 找出所有站的最早發車時間
      const earliestByStation = new Map<string, { train: TrainSchedule; time: number }>();

      for (const train of trains) {
        const firstStop = train.stations[0];
        const timeMinutes = timeToMinutes(firstStop.departure);

        if (!earliestByStation.has(firstStop.stationId) ||
            timeMinutes < earliestByStation.get(firstStop.stationId)!.time) {
          earliestByStation.set(firstStop.stationId, { train, time: timeMinutes });
        }
      }

      // 找出全線最早的
      let globalEarliest: { train: TrainSchedule; time: number; stationId: string } | null = null;

      for (const [stationId, info] of earliestByStation) {
        if (!globalEarliest || info.time < globalEarliest.time) {
          globalEarliest = { ...info, stationId };
        }
      }

      if (globalEarliest) {
        const terminalStation = getTerminalStation(lineId, direction);

        firstTrains.push({
          trainId: globalEarliest.train.trainId,
          line: lineId,
          direction,
          originStation: globalEarliest.stationId,
          departureTime: globalEarliest.train.stations[0].departure,
          isTerminalOrigin: globalEarliest.stationId === terminalStation
        });
      }
    }
  }

  return firstTrains;
}
```

### 7.3 UI 標示

首班車可加上特殊標示：

```typescript
// 在列車資訊面板顯示
function getTrainLabel(train: MetroTrain, firstTrains: FirstTrainInfo[]): string {
  const isFirst = firstTrains.some(ft => ft.trainId === train.trainId);

  if (isFirst) {
    const info = firstTrains.find(ft => ft.trainId === train.trainId)!;
    if (!info.isTerminalOrigin) {
      return `首班車 (從${getStationName(info.originStation)}發車)`;
    }
    return '首班車';
  }

  return '';
}
```

---

## 八、系統特定注意事項

### 8.1 高雄捷運 (KRTC)

| 線路 | 代碼 | 車站數 | 方向 0 | 方向 1 |
|------|------|--------|--------|--------|
| 紅線 | R | 25 | 往小港 | 往南岡山 |
| 橘線 | O | 14 | 往大寮 | 往西子灣 |

```
Track IDs:
- KRTC-R-0, KRTC-R-1
- KRTC-O-0, KRTC-O-1
```

### 8.2 高雄輕軌 (KLRT)

環狀線特殊處理：

| 線路 | 代碼 | 車站數 | 方向 0 | 方向 1 |
|------|------|--------|--------|--------|
| 環狀線 | C | 37 | 順時針 | 逆時針 |

```
Track IDs:
- KLRT-C-0 (順時針)
- KLRT-C-1 (逆時針)

注意：環狀線的 progress 處理需特殊計算
```

### 8.3 台中捷運 (TMRT)

| 線路 | 代碼 | 車站數 | 方向 0 | 方向 1 |
|------|------|--------|--------|--------|
| 綠線 | G | 18 | 往高鐵台中站 | 往北屯總站 |

```
Track IDs:
- TMRT-G-0, TMRT-G-1
```

### 8.4 桃園捷運 (TYMC)

| 線路 | 代碼 | 車站數 | 方向 0 | 方向 1 |
|------|------|--------|--------|--------|
| 機場線 | A | 21 | 往機場 | 往台北車站 |

```
Track IDs:
- TYMC-A-0, TYMC-A-1
```

### 8.5 台北捷運有時刻表的線路

以下線路可從 TDX 取得完整時刻表：

| 線路 | 有時刻表 | 備註 |
|------|----------|------|
| 紅線 (R) | ⚠️ 部分 | 非全線 |
| 淡海輕軌 (V) | ✅ | NTMC |
| 安坑輕軌 (K) | ✅ | NTMC |

---

## 九、資料處理腳本

### 9.1 通用下載腳本

```python
#!/usr/bin/env python3
"""下載軌道系統資料"""

import json
import sys
sys.path.insert(0, '/path/to/tdx_api_docs')

from src import TDXAuth, TDXClient

def download_system_data(system: str, output_dir: str):
    """下載指定系統的所有資料"""

    auth = TDXAuth()
    client = TDXClient(auth)

    endpoints = [
        ('Station', f'/v2/Rail/Metro/Station/{system}', {}),
        ('Shape', f'/v2/Rail/Metro/Shape/{system}', {}),
        ('StationOfLine', f'/v2/Rail/Metro/StationOfLine/{system}', {}),
        ('StationTimeTable', f'/v2/Rail/Metro/StationTimeTable/{system}', {}),
        ('S2STravelTime', f'/v2/Rail/Metro/S2STravelTime/{system}', {}),
    ]

    for name, endpoint, params in endpoints:
        print(f"下載 {name}...")
        data = client.get('basic', endpoint, params)

        with open(f'{output_dir}/{system}_{name}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  ✅ 儲存 {len(data) if isinstance(data, list) else 1} 筆")

if __name__ == '__main__':
    system = sys.argv[1] if len(sys.argv) > 1 else 'KRTC'
    output_dir = sys.argv[2] if len(sys.argv) > 2 else './data'

    download_system_data(system, output_dir)
```

### 9.2 軌道轉換腳本

```python
#!/usr/bin/env python3
"""轉換軌道資料為 GeoJSON"""

import json
import re
from pathlib import Path

def process_shape(shape_data: list, system: str, output_dir: str):
    """處理 Shape 資料"""

    for line in shape_data:
        line_id = line['LineID']
        direction = line['Direction']
        geometry = line['Geometry']

        # 轉換 WKT
        geojson = wkt_to_geojson(geometry, f"{system}-{line_id}-{direction}")

        # 儲存
        output_path = Path(output_dir) / 'tracks' / f"{system}-{line_id}-{direction}.geojson"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)

        print(f"✅ {output_path.name}")

def wkt_to_geojson(wkt: str, track_id: str) -> dict:
    """WKT 轉 GeoJSON"""
    pattern = r'MULTILINESTRING\s*\(\(([^)]+)\)\)'
    match = re.search(pattern, wkt, re.IGNORECASE)

    if not match:
        # 嘗試 LINESTRING
        pattern = r'LINESTRING\s*\(([^)]+)\)'
        match = re.search(pattern, wkt, re.IGNORECASE)

    if not match:
        raise ValueError(f"無法解析 WKT: {wkt[:50]}...")

    coords = []
    for point in match.group(1).split(','):
        parts = point.strip().split()
        coords.append([float(parts[0]), float(parts[1])])

    return {
        "type": "Feature",
        "properties": {"id": track_id, "type": "track"},
        "geometry": {"type": "LineString", "coordinates": coords}
    }
```

---

## 十、檢查清單

### 10.1 新系統上線檢查

- [ ] 所有 API 資料已下載並驗證
- [ ] 軌道 GeoJSON 檔案已產生
- [ ] 車站座標已確認正確
- [ ] 站序與 progress 已計算
- [ ] 時刻表格式正確
- [ ] 首班車資訊已偵測
- [ ] 引擎程式碼已實作
- [ ] UI 整合完成
- [ ] 全時段測試通過

### 10.2 常見問題

| 問題 | 可能原因 | 解決方案 |
|------|----------|----------|
| 列車位置偏移 | progress 計算錯誤 | 重新計算站點 progress |
| 列車消失 | 時刻表時間格式 | 確認 HH:MM 格式 |
| 首班車錯誤 | 未考慮中站發車 | 使用 detectFirstTrains |
| 軌道斷開 | WKT 解析問題 | 檢查座標連續性 |

---

## 十一、相關文件

| 文件 | 說明 |
|------|------|
| `docs/AI_DEVELOPMENT_GUIDE.md` | 開發標準與校準方法 |
| `docs/THSR_TRACK_CALIBRATION.md` | 高鐵校準參考 |
| `docs/KRTC_IMPLEMENTATION_PLAN.md` | 高雄捷運實作計畫 |
| `docs/THSR_TRAIN_COLLISION.md` | 碰撞檢測技術 |

---

## 十二、更新日誌

| 日期 | 版本 | 更新內容 |
|------|------|----------|
| 2026-01-02 | 1.0 | 初版建立 |
