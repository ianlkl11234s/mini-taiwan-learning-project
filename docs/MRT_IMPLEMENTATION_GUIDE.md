# 捷運路線實作指南

> 本文檔記錄 Mini Taipei V3 專案中實作捷運列車模擬的完整流程、經驗與注意事項。

## 目錄

1. [需要提供的資料](#1-需要提供的資料)
2. [實作步驟與優先順序](#2-實作步驟與優先順序)
3. [核心概念與運作流程](#3-核心概念與運作流程)
4. [程式碼架構](#4-程式碼架構)
5. [時刻表協調策略](#5-時刻表協調策略)
6. [權衡與限制](#6-權衡與限制)
7. [常見問題與解決方案](#7-常見問題與解決方案)
8. [檢查清單](#8-檢查清單)

---

## 1. 需要提供的資料

### 1.1 必要資料

| 資料類型 | 說明 | 檔案格式 | 範例 |
|---------|------|----------|------|
| **軌道幾何** | 每條軌道的地理座標線段 | GeoJSON | `R-1-0.geojson` |
| **車站位置** | 所有車站的座標點 | GeoJSON | `red_line_stations.geojson` |
| **時刻表** | 每條軌道的發車時間與站間時間 | JSON | `R-2-0.json` |
| **車站進度映射** | 每個車站在軌道上的實際進度 (0-1) | JSON | `station_progress.json` |

### 1.2 路線結構資訊

請提供以下路線規劃資訊：

```yaml
路線名稱: 淡水信義線
路線代碼: R (紅線)

主線 (R-1):
  - R-1-0: 象山 → 淡水 (北上)
  - R-1-1: 淡水 → 象山 (南下)
  車站數: 27 站 (R02-R28)

支線 (R-2，新北投支線):
  - R-2-0: 北投 → 大安 (南下，與主線共用)
  - R-2-1: 大安 → 北投 (北上，與主線共用)
  車站數: 18 站 (R05-R22)

共用區段: R05 (北投) 至 R22 (大安)
```

### 1.3 時刻表參數

```yaml
# 每條軌道需要的參數
track_id: "R-1-0"
route_id: "R-1"
name: "淡水信義線 北上"
origin: "R02"          # 起點站代碼
destination: "R28"     # 終點站代碼
stations: ["R02", "R03", ...]  # 依序的車站列表

# 時間參數
travel_time_seconds: 86        # 站間行車時間 (秒)
dwell_time_seconds: 40         # 停站時間 (秒)
first_departure: "06:00:00"    # 首班車
last_departure: "23:54:00"     # 末班車

# 班距資訊 (可選，若有變動班距)
headway_pattern:
  - time_range: ["06:00", "07:00"]
    headway_minutes: 9
  - time_range: ["07:00", "09:00"]
    headway_minutes: 6
  - time_range: ["09:00", "16:30"]
    headway_minutes: 9
```

---

## 2. 實作步驟與優先順序

### Phase 1: 基礎資料準備 (最重要！)

```
┌─────────────────────────────────────────────────────────┐
│  1. 軌道幾何建立                                          │
│     ├─ 繪製/匯入每條軌道的 GeoJSON LineString            │
│     ├─ 確保方向正確 (起點→終點)                          │
│     └─ 驗證：在地圖上視覺化確認                          │
│                                                         │
│  2. 車站位置標定                                          │
│     ├─ 建立車站 GeoJSON Point                            │
│     └─ 確保 station_id 與時刻表一致                      │
│                                                         │
│  3. 車站進度計算 ⭐ 關鍵步驟                              │
│     ├─ 使用線段投影算法計算每站在軌道上的 progress (0-1) │
│     ├─ 每條軌道需要獨立計算                              │
│     └─ 輸出: station_progress.json                       │
└─────────────────────────────────────────────────────────┘
```

**車站進度計算的重要性：**
- 如果使用均勻分布 (stationIndex / totalStations)，列車會停在錯誤位置
- 必須根據實際軌道幾何計算每站的 progress 值
- 這決定了列車是否能精確停在車站位置

### Phase 2: 時刻表建立

```
┌─────────────────────────────────────────────────────────┐
│  4. 生成基礎時刻表                                        │
│     ├─ 根據班距生成每班車的發車時間                      │
│     ├─ 計算每站的到達/離開時間                           │
│     └─ 格式: 見下方 JSON 結構                            │
│                                                         │
│  5. 共用區段協調 ⭐ 關鍵步驟                              │
│     ├─ 識別共用軌道區段                                  │
│     ├─ 計算時間偏移量                                    │
│     └─ 統一行車速度                                      │
└─────────────────────────────────────────────────────────┘
```

### Phase 3: 整合與驗證

```
┌─────────────────────────────────────────────────────────┐
│  6. 程式碼整合                                            │
│     ├─ 更新 useData.ts 載入新軌道                        │
│     ├─ 更新 TRACK_IDS 常數                               │
│     └─ 更新軌道顏色 TRACK_COLORS                         │
│                                                         │
│  7. 碰撞檢測設定                                          │
│     ├─ 更新 SHARED_TRACK_SEGMENTS                        │
│     └─ 驗證無碰撞                                        │
│                                                         │
│  8. 視覺化驗證                                            │
│     ├─ 播放模擬，觀察列車移動                            │
│     ├─ 確認停站位置正確                                  │
│     └─ 確認無碰撞發生                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 核心概念與運作流程

### 3.1 列車位置計算流程

```
┌──────────────────────────────────────────────────────────────────┐
│                      列車位置計算流程                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   currentTimeSeconds (當前時間)                                   │
│         │                                                        │
│         ▼                                                        │
│   ┌─────────────────┐                                            │
│   │ 計算 elapsedTime │  elapsed = currentTime - departureTime    │
│   │ (已過時間)       │                                            │
│   └────────┬────────┘                                            │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────────────────────────────┐                    │
│   │         findCurrentSegment()            │                    │
│   │  根據 elapsedTime 找到目前所在區段        │                    │
│   ├─────────────────────────────────────────┤                    │
│   │  if (elapsed < arrival[i])              │                    │
│   │      → status: 'waiting'                │                    │
│   │  if (arrival[i] <= elapsed < departure[i])│                  │
│   │      → status: 'stopped' at station[i]  │                    │
│   │  if (departure[i] <= elapsed < arrival[i+1])│                │
│   │      → status: 'running'                │                    │
│   │      → segmentProgress = (elapsed - dep) / travelTime       │
│   └────────┬────────────────────────────────┘                    │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────────────────────────────┐                    │
│   │      getStationProgress()               │                    │
│   │  從 station_progress.json 取得          │                    │
│   │  fromProgress, toProgress               │                    │
│   └────────┬────────────────────────────────┘                    │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────────────────────────────┐                    │
│   │   interpolateBetweenStationsWithProgress │                   │
│   │                                         │                    │
│   │   actualProgress = fromProgress +       │                    │
│   │     (toProgress - fromProgress) *       │                    │
│   │     segmentProgress                     │                    │
│   └────────┬────────────────────────────────┘                    │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────────────────────────────┐                    │
│   │      interpolateOnLineString()          │                    │
│   │  在軌道幾何上插值取得 [lng, lat]         │                    │
│   └────────┬────────────────────────────────┘                    │
│            │                                                     │
│            ▼                                                     │
│      position: [lng, lat]  ← 列車位置                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 時間軸結構

```
時刻表結構 (每班車)
────────────────────────────────────────────────────────────────────

departure_time: "06:00:00"  ← 發車時間 (也是第一站到達時間)

stations: [
  { station_id: "R02", arrival: 0,    departure: 40   },  ← 停站 40 秒
  { station_id: "R03", arrival: 126,  departure: 166  },  ← 行車 86 秒後到達
  { station_id: "R04", arrival: 252,  departure: 292  },
  ...
]

時間線示意:
0s        40s       126s      166s      252s      292s
├──停站──┼──行車───┼──停站──┼──行車───┼──停站──┼──...
   R02                R03                R04

arrival[i+1] = departure[i] + travel_time (86s)
departure[i] = arrival[i] + dwell_time (40s)
```

### 3.3 碰撞檢測邏輯

```
┌──────────────────────────────────────────────────────────────────┐
│                       碰撞檢測流程                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   1. 分組：依方向將列車分成                                       │
│      ├─ direction0Trains: R-1-0, R-2-0, R-3-0... (同向)          │
│      └─ direction1Trains: R-1-1, R-2-1, R-3-1... (同向)          │
│                                                                  │
│   2. 過濾：只檢查在共用區段的列車                                 │
│      if (isOnSharedSegment(train))                               │
│                                                                  │
│   3. 排除車站同時停靠：                                           │
│      if (trainA.status === 'stopped' &&                          │
│          trainB.status === 'stopped') {                          │
│        continue;  // 車站有多月台，不算碰撞                       │
│      }                                                           │
│                                                                  │
│   4. 計算地理距離：                                               │
│      dist = sqrt((posA.lng - posB.lng)² + (posA.lat - posB.lat)²)│
│                                                                  │
│   5. 判定碰撞：                                                   │
│      if (dist < COLLISION_THRESHOLD) {  // 0.0005 ≈ 50m          │
│        標記碰撞，計算垂直偏移以視覺分離                           │
│      }                                                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

⚠️ 重要：碰撞檢測比較的是「地理座標」，不是「進度值」！
   不同軌道的 progress 值無法直接比較。
```

---

## 4. 程式碼架構

### 4.1 檔案結構

```
viewer/
├── public/
│   └── data/
│       ├── tracks/
│       │   ├── R-1-0.geojson    # 軌道幾何
│       │   ├── R-1-1.geojson
│       │   ├── R-2-0.geojson
│       │   └── R-2-1.geojson
│       ├── schedules/
│       │   ├── R-1-0.json       # 時刻表
│       │   ├── R-1-1.json
│       │   ├── R-2-0.json
│       │   └── R-2-1.json
│       ├── red_line_stations.geojson
│       └── station_progress.json
│
├── src/
│   ├── App.tsx                  # 主應用程式
│   ├── engines/
│   │   ├── TimeEngine.ts        # 時間引擎
│   │   └── TrainEngine.ts       # 列車引擎 ⭐
│   ├── hooks/
│   │   └── useData.ts           # 資料載入
│   ├── components/
│   │   └── TimeControl.tsx      # 時間控制面板
│   └── types/
│       ├── track.ts
│       └── schedule.ts
```

### 4.2 新增路線需要修改的檔案

```typescript
// 1. hooks/useData.ts - 新增軌道 ID
const TRACK_IDS = [
  'R-1-0', 'R-1-1',  // 淡水信義線
  'R-2-0', 'R-2-1',  // 新北投支線
  'G-1-0', 'G-1-1',  // ⬅ 新增: 松山新店線
];

// 2. App.tsx - 新增軌道顏色
const TRACK_COLORS: Record<string, string> = {
  'R-1-0': '#d90023', 'R-1-1': '#d90023',
  'R-2-0': '#e63946', 'R-2-1': '#e63946',
  'G-1-0': '#008659', 'G-1-1': '#008659',  // ⬅ 新增
};

// 3. TrainEngine.ts - 新增共用區段
const SHARED_TRACK_SEGMENTS: Record<string, string[]> = {
  // 紅線
  'R-1-0': ['R05', 'R06', ...],
  'R-2-0': ['R05', 'R06', ...],
  // 綠線 (如有共用區段)
  'G-1-0': ['G10', 'G11', ...],
};
```

### 4.3 時刻表 JSON 結構

```json
{
  "track_id": "R-2-0",
  "route_id": "R-2",
  "name": "新北投支線 南下",
  "origin": "R05",
  "destination": "R22",
  "stations": ["R05", "R06", "R07", ...],
  "travel_time_minutes": 35.7,
  "dwell_time_seconds": 40,
  "is_weekday": true,
  "departure_count": 133,
  "departures": [
    {
      "departure_time": "06:04:00",
      "train_id": "R-2-0-001",
      "stations": [
        { "station_id": "R05", "arrival": 0,   "departure": 40  },
        { "station_id": "R06", "arrival": 126, "departure": 166 },
        ...
      ],
      "total_travel_time": 2142
    },
    ...
  ]
}
```

### 4.4 車站進度 JSON 結構

```json
{
  "R-1-0": {
    "R02": 0.0,
    "R03": 0.027612,
    "R04": 0.065704,
    ...
    "R28": 1.0
  },
  "R-1-1": {
    "R28": 0.0,
    "R27": 0.075662,
    ...
    "R02": 1.0
  }
}
```

---

## 5. 時刻表協調策略

### 5.1 共用區段問題

當兩條路線共用同一段軌道時，必須協調時刻表以避免碰撞。

```
問題示意：

R-1-0 ─────●────●────●────●────●─────→  淡水
           R05  R06  R07  R08  R09

R-2-0 ─────●────●────●────●────●─────→  北投
           R05  R06  R07  R08  R09

⚠️ 如果 R-1-0 和 R-2-0 同時發車，會在共用區段碰撞！
```

### 5.2 偏移量計算公式

```
目標：R-2 列車在 R-1 列車「離開共用區段起點」後一段時間才進入

方向 0 (北上，起點是 R05):
  R-1-0 到達 R05 的時間: 0 秒 (起點)
  R-1-0 離開 R05 的時間: 40 秒 (停站時間)

  R-2-0 偏移量 = R-1-0 離開時間 + 安全間隔
              = 40 + 200 ≈ 4 分鐘

方向 1 (南下，起點是 R22/R28):
  R-1-1 從 R28 出發到 R22 的時間: 12.6 分鐘 (計算得出)
  R-2-1 從 R22 出發

  R-2-1 偏移量 = R-1-1 到達 R22 時間 + R-1-1 離開 R22 時間 + 安全間隔
              = 12.6 分 + 40 秒 + 4 分 ≈ 17 分鐘

⭐ 關鍵：反方向的偏移量通常需要更大！
```

### 5.3 統一行車速度

```
問題：不同路線原始行車速度可能不同

R-1: 86 秒/站
R-2: 75 秒/站 (原始)

如果速度不同，即使有偏移量，較快的列車最終還是會追上較慢的！

解決方案：統一行車速度
R-1: 86 秒/站
R-2: 86 秒/站 (修改後)
```

---

## 6. 權衡與限制

### 6.1 犧牲的精準度

| 項目 | 實際情況 | 模擬處理 | 影響 |
|------|---------|---------|------|
| **行車時間** | 每站間時間可能不同 | 統一為 86 秒/站 | ⚠️ 中等影響 |
| **停站時間** | 尖峰/離峰可能不同 | 統一為 40 秒 | 低影響 |
| **班距** | 變動班距 (6/9/12 分) | 保留變動班距 | ✅ 無影響 |
| **偏移量** | 可能需要動態調整 | 使用固定偏移量 | ⚠️ 末班車可能有問題 |
| **車站月台** | 同站多月台不碰撞 | 雙方停站時跳過檢測 | ✅ 已處理 |

### 6.2 已知限制

```
1. 固定偏移量限制
   ├─ 當班距變化時 (6分→9分→12分)，固定偏移量可能不夠
   └─ 解決方案：可實作動態偏移量，但增加複雜度

2. 行車速度統一
   ├─ 犧牲了站間時間的精確性
   └─ 權衡：確保無碰撞 > 精確時刻表

3. 末班車問題
   ├─ 接近末班車時，班距可能擴大
   └─ 可能需要特殊處理最後幾班車

4. 轉乘站處理
   ├─ 目前假設車站有多月台，雙方停站不算碰撞
   └─ 如需更精確，需區分月台
```

### 6.3 建議優化方向

```
短期 (Quick Wins):
  □ 使用實際站間時間 (每段不同)
  □ 根據時段調整停站時間

中期 (Enhancements):
  □ 動態偏移量計算
  □ 根據前車位置自動調整速度

長期 (Future):
  □ 真實 GTFS 資料整合
  □ 列車調度算法
```

---

## 7. 常見問題與解決方案

### 7.1 列車停在錯誤位置

```
問題：列車沒有停在車站位置，而是在站間
原因：station_progress.json 未正確計算

解決：
1. 使用線段投影算法計算每站的 progress
2. 確保每條軌道都有獨立的 progress 映射

驗證程式碼:
python3 -c "
import json
with open('station_progress.json') as f:
    data = json.load(f)

for track_id, stations in data.items():
    print(f'{track_id}:')
    for station_id, progress in stations.items():
        print(f'  {station_id}: {progress:.4f}')
"
```

### 7.2 列車碰撞

```
問題：兩列車在共用區段重疊
可能原因：
  1. 偏移量不足
  2. 行車速度不一致
  3. 碰撞檢測邏輯錯誤

排查步驟：
1. 確認偏移量計算正確
2. 確認所有共用軌道的行車速度一致
3. 檢查 SHARED_TRACK_SEGMENTS 設定

驗證程式碼：見專案中的 Python 碰撞檢測腳本
```

### 7.3 頁面載入後列車不動

```
問題：列車標記顯示但不移動
原因：useEffect 依賴項導致 race condition

解決：
1. 新增 timeEngineReady 狀態變數
2. 確保 TrainEngine 在 TimeEngine 準備好後才初始化
3. 合併相關 useEffect

程式碼參考: App.tsx 中的 useEffect 處理
```

### 7.4 碰撞誤判 (車站同時停靠)

```
問題：兩列車在同一車站停靠被判定為碰撞
原因：碰撞檢測沒有排除車站停靠情況

解決：
if (trainA.status === 'stopped' && trainB.status === 'stopped') {
  continue;  // 跳過，車站有多月台
}
```

---

## 8. 檢查清單

### 新增路線前確認

- [ ] 軌道幾何 GeoJSON 已準備
- [ ] 車站位置 GeoJSON 已準備
- [ ] 時刻表參數已確認 (班距、首末班、站間時間)
- [ ] 共用區段已識別

### 資料處理

- [ ] 軌道幾何方向正確 (起點→終點)
- [ ] station_progress.json 已計算
- [ ] 時刻表 JSON 已生成
- [ ] 共用區段偏移量已計算

### 程式碼更新

- [ ] TRACK_IDS 已更新
- [ ] TRACK_COLORS 已更新
- [ ] SHARED_TRACK_SEGMENTS 已更新

### 驗證

- [ ] 視覺化確認軌道正確顯示
- [ ] 列車停站位置正確
- [ ] 無碰撞事件
- [ ] 首班車/末班車正常運行

---

## 附錄 A: 車站進度計算腳本

```python
"""
計算車站在軌道上的實際進度
使用點到線段最近點投影算法
"""

import json
import math

def load_track(track_id):
    with open(f'tracks/{track_id}.geojson') as f:
        data = json.load(f)
    return data['features'][0]['geometry']['coordinates']

def load_stations():
    with open('red_line_stations.geojson') as f:
        data = json.load(f)
    return {
        f['properties']['station_id']: f['geometry']['coordinates']
        for f in data['features']
    }

def distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def calculate_total_length(coords):
    return sum(distance(coords[i], coords[i+1])
               for i in range(len(coords)-1))

def project_point_to_line(point, line_coords):
    """找到點在線段上的投影位置"""
    min_dist = float('inf')
    best_progress = 0
    total_length = calculate_total_length(line_coords)
    accumulated = 0

    for i in range(len(line_coords) - 1):
        seg_start = line_coords[i]
        seg_end = line_coords[i + 1]
        seg_length = distance(seg_start, seg_end)

        # 計算點到線段的投影
        if seg_length > 0:
            t = max(0, min(1, (
                (point[0] - seg_start[0]) * (seg_end[0] - seg_start[0]) +
                (point[1] - seg_start[1]) * (seg_end[1] - seg_start[1])
            ) / (seg_length ** 2)))

            proj_x = seg_start[0] + t * (seg_end[0] - seg_start[0])
            proj_y = seg_start[1] + t * (seg_end[1] - seg_start[1])

            dist = distance(point, [proj_x, proj_y])

            if dist < min_dist:
                min_dist = dist
                best_progress = (accumulated + t * seg_length) / total_length

        accumulated += seg_length

    return best_progress

def calculate_station_progress(track_id, station_ids):
    coords = load_track(track_id)
    stations = load_stations()

    progress_map = {}
    for station_id in station_ids:
        if station_id in stations:
            progress = project_point_to_line(stations[station_id], coords)
            progress_map[station_id] = round(progress, 6)

    return progress_map

# 使用範例
if __name__ == '__main__':
    result = {}

    # R-1-0: 象山 → 淡水
    result['R-1-0'] = calculate_station_progress(
        'R-1-0',
        ['R02', 'R03', 'R04', ..., 'R28']
    )

    # 輸出結果
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

## 附錄 B: 時刻表生成腳本

```python
"""
生成時刻表 JSON
"""

import json

def generate_schedule(
    track_id,
    route_id,
    name,
    origin,
    destination,
    stations,
    departures,  # 發車時間列表 ["06:00:00", "06:09:00", ...]
    travel_time=86,
    dwell_time=40,
    offset_seconds=0  # 偏移量
):
    def time_to_seconds(t):
        h, m, s = map(int, t.split(':'))
        return h * 3600 + m * 60 + s

    def seconds_to_time(s):
        return f'{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}'

    schedule = {
        'track_id': track_id,
        'route_id': route_id,
        'name': name,
        'origin': origin,
        'destination': destination,
        'stations': stations,
        'travel_time_minutes': (travel_time * (len(stations)-1) + dwell_time * len(stations)) / 60,
        'dwell_time_seconds': dwell_time,
        'is_weekday': True,
        'departure_count': len(departures),
        'departures': []
    }

    for idx, dep_time in enumerate(departures):
        dep_seconds = time_to_seconds(dep_time) + offset_seconds
        adjusted_dep_time = seconds_to_time(dep_seconds)

        station_times = []
        current_time = 0

        for i, station_id in enumerate(stations):
            arrival = current_time
            departure = current_time + dwell_time

            station_times.append({
                'station_id': station_id,
                'arrival': arrival,
                'departure': departure if i < len(stations) - 1 else arrival
            })

            current_time = departure + travel_time

        total_travel_time = station_times[-1]['arrival']

        schedule['departures'].append({
            'departure_time': adjusted_dep_time,
            'train_id': f'{track_id}-{idx+1:03d}',
            'stations': station_times,
            'total_travel_time': total_travel_time
        })

    return schedule

# 使用範例
if __name__ == '__main__':
    # 生成基礎發車時間列表
    base_departures = []
    current = 6 * 3600  # 06:00
    end = 23 * 3600 + 54 * 60  # 23:54
    headway = 9 * 60  # 9 分鐘

    while current <= end:
        h, m, s = current // 3600, (current % 3600) // 60, current % 60
        base_departures.append(f'{h:02d}:{m:02d}:{s:02d}')
        current += headway

    # 生成時刻表
    schedule = generate_schedule(
        track_id='R-2-0',
        route_id='R-2',
        name='新北投支線 南下',
        origin='R05',
        destination='R22',
        stations=['R05', 'R06', 'R07', ...],
        departures=base_departures,
        offset_seconds=4 * 60  # +4 分鐘偏移
    )

    with open('R-2-0.json', 'w') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)
```

---

*文檔版本: 1.0*
*最後更新: 2025-01-XX*
*作者: Claude Code*
