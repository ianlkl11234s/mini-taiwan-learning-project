# Mini Taipei V3 - 系統設計規劃書

## 一、專案概述

### 1.1 專案目標
建立一個台北捷運模擬系統，以 Mini Tokyo 3D 為參考，先從**淡水信義線（紅線）**開始，實現列車在軌道上的動態移動視覺化。

### 1.2 核心特點
- **非即時模式**：基於歷史時刻表資料，而非即時 API
- **時間軸控制**：可拖拉時間軸選擇特定時間點
- **播放速度控制**：支援快轉/慢放倍數調整
- **單向行駛模式**：列車從起點出發，到終點消失，不折返

### 1.3 第一版範圍（MVP）
- 僅實作淡水信義線（紅線 R）
- 使用特定日期的歷史時刻表
- 基本的地圖視覺化與列車動畫

---

## 二、淡水信義線路線分析

### 2.1 紅線營運路線（根據 trtc_routes.json）

```
RouteID  | 路線名稱              | 起站    | 迄站    | 行駛時間
---------|----------------------|---------|---------|----------
R-1      | 象山－淡水            | R02     | R28     | 54 分鐘
R-1      | 淡水－象山            | R28     | R02     | 54 分鐘
R-2      | 大安－北投            | R05     | R22     | 32 分鐘
R-2      | 北投－大安            | R22     | R05     | 32 分鐘
R-3      | 北投－新北投（支線）   | R22     | R22A    | 4 分鐘
R-3      | 新北投－北投（支線）   | R22A    | R22     | 4 分鐘
```

### 2.2 紅線站點資料（根據 trtc_station_of_line.json）

主線站點（共 28 站，從象山到淡水）：
```
R02 象山 → R03 台北101 → R04 信義安和 → R05 大安 → R06 大安森林公園
→ R07 東門 → R08 中正紀念堂 → R09 台大醫院 → R10 台北車站 → R11 中山
→ R12 雙連 → R13 民權西路 → R14 圓山 → R15 劍潭 → R16 士林 → R17 芝山
→ R18 明德 → R19 石牌 → R20 唭哩岸 → R21 奇岩 → R22 北投
→ R23 復興崗 → R24 忠義 → R25 關渡 → R26 竹圍 → R27 紅樹林 → R28 淡水

支線：R22 北投 ↔ R22A 新北投
```

### 2.3 軌道定義（Track）

根據您的需求，每條運行路線會產生**兩個獨立軌道**：

```
Track ID      | 起站        | 迄站        | 對應站點數 | 行駛時間
--------------|-------------|-------------|-----------|----------
R-1-0         | 象山 (R02)  | 淡水 (R28)  | 27        | 54 min
R-1-1         | 淡水 (R28)  | 象山 (R02)  | 27        | 54 min
R-2-0         | 大安 (R05)  | 北投 (R22)  | 18        | 32 min
R-2-1         | 北投 (R22)  | 大安 (R05)  | 18        | 32 min
R-3-0         | 北投 (R22)  | 新北投 (R22A)| 2        | 4 min
R-3-1         | 新北投 (R22A)| 北投 (R22) | 2         | 4 min
```

---

## 三、資料模型設計

### 3.1 核心資料結構

#### 3.1.1 Station（車站）
```typescript
interface Station {
  stationId: string;          // e.g., "R02"
  name: {
    zh_tw: string;            // e.g., "象山"
    en: string;               // e.g., "Xiangshan"
  };
  coordinates: [number, number]; // [lng, lat]
  sequence: number;           // 在路線中的順序
  cumulativeDistance: number; // 累積距離（公里）
}
```

#### 3.1.2 Track（軌道）
```typescript
interface Track {
  trackId: string;            // e.g., "R-1-0"
  routeId: string;            // e.g., "R-1"
  lineId: string;             // e.g., "R"
  direction: 0 | 1;           // 0=去程, 1=回程
  color: string;              // "#d90023"

  startStation: Station;
  endStation: Station;
  stations: Station[];        // 按行駛順序排列的站點

  travelTime: number;         // 全程行駛時間（分鐘）
  geometry: GeoJSON.LineString; // 軌道幾何座標
}
```

#### 3.1.3 Departure（發車班次）
```typescript
interface Departure {
  departureId: string;        // e.g., "R-1-0-W-001"
  trackId: string;            // e.g., "R-1-0"
  departureTime: string;      // "06:00"
  arrivalTime: string;        // "06:54" (計算得出)
  dayType: 'weekday' | 'weekend';
}
```

#### 3.1.4 Train（列車實例）
```typescript
interface Train {
  trainId: string;            // e.g., "R-1-0-W-001"
  trackId: string;
  departure: Departure;

  // 動態狀態
  status: 'waiting' | 'running' | 'arrived';
  progress: number;           // 0-1，行駛進度
  currentPosition: [number, number]; // 當前座標
  currentStationIndex: number; // 當前最近車站索引
}
```

### 3.2 時刻表資料結構

```typescript
interface Schedule {
  date: string;               // "2024-12-29"
  dayType: 'weekday' | 'weekend';
  tracks: {
    [trackId: string]: {
      departures: Departure[];
    };
  };
}
```

---

## 四、位置計算演算法

### 4.1 線性內插法

列車位置根據**出發時間**和**行駛時間**進行線性內插：

```typescript
function calculateTrainPosition(
  train: Train,
  currentTime: Date,
  track: Track
): [number, number] {
  const departureTime = parseTime(train.departure.departureTime);
  const travelTimeMs = track.travelTime * 60 * 1000;

  const elapsed = currentTime.getTime() - departureTime.getTime();
  const progress = Math.min(1, Math.max(0, elapsed / travelTimeMs));

  // 根據 progress 在軌道幾何上內插
  return interpolateOnLineString(track.geometry, progress);
}
```

### 4.2 軌道幾何內插

```typescript
function interpolateOnLineString(
  lineString: GeoJSON.LineString,
  progress: number  // 0-1
): [number, number] {
  const coords = lineString.coordinates;
  const totalLength = calculateTotalLength(coords);
  const targetDistance = totalLength * progress;

  let accumulated = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    const segmentLength = distance(coords[i], coords[i + 1]);
    if (accumulated + segmentLength >= targetDistance) {
      const segmentProgress = (targetDistance - accumulated) / segmentLength;
      return interpolate(coords[i], coords[i + 1], segmentProgress);
    }
    accumulated += segmentLength;
  }

  return coords[coords.length - 1];
}
```

---

## 五、系統架構

### 5.1 整體架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                        Mini Taipei V3                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐   │
│  │   UI Layer  │    │  Time Engine │    │   Map Renderer  │   │
│  │             │    │              │    │                 │   │
│  │ - Timeline  │◄──►│ - Current    │───►│ - MapLibre GL   │   │
│  │ - Speed     │    │   Time       │    │ - Train Layer   │   │
│  │ - Controls  │    │ - Speed      │    │ - Track Layer   │   │
│  │ - Date      │    │ - Animation  │    │ - Station Layer │   │
│  └─────────────┘    └──────────────┘    └─────────────────┘   │
│         │                   │                    ▲              │
│         │                   ▼                    │              │
│         │          ┌──────────────┐              │              │
│         │          │ Train Engine │              │              │
│         └─────────►│              │──────────────┘              │
│                    │ - Position   │                             │
│                    │   Calculator │                             │
│                    │ - State      │                             │
│                    │   Manager    │                             │
│                    └──────────────┘                             │
│                           │                                     │
│                           ▼                                     │
│                    ┌──────────────┐                             │
│                    │  Data Layer  │                             │
│                    │              │                             │
│                    │ - Tracks     │                             │
│                    │ - Schedules  │                             │
│                    │ - Stations   │                             │
│                    └──────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 模組說明

#### 5.2.1 Data Layer（資料層）
- **tracks.json**: 軌道定義與幾何座標
- **stations.json**: 車站資料
- **schedules/{date}.json**: 每日時刻表

#### 5.2.2 Time Engine（時間引擎）
- 管理模擬時間（非真實時間）
- 支援播放/暫停/跳轉
- 播放速度控制（1x, 2x, 5x, 10x...）

#### 5.2.3 Train Engine（列車引擎）
- 根據時刻表生成列車實例
- 計算每輛列車的即時位置
- 管理列車生命週期（出發→行駛→抵達消失）

#### 5.2.4 Map Renderer（地圖渲染器）
- 使用 MapLibre GL JS 渲染底圖
- 軌道線條渲染
- 車站標記渲染
- 列車圖標動態更新

---

## 六、時間控制機制

### 6.1 時間軸 UI 設計

```
┌─────────────────────────────────────────────────────────────┐
│  日期選擇: [2024-12-29 ▼]                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  06:00 ════════════●══════════════════════════════ 24:00   │
│                  ↑                                          │
│              08:35                                          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [⏮] [⏪] [▶/⏸] [⏩] [⏭]     速度: [1x ▼]                │
│                                                             │
│  目前時間: 08:35:42           活躍列車: 12                  │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 時間引擎實作

```typescript
class TimeEngine {
  private simulatedTime: Date;
  private playbackSpeed: number = 1;
  private isPlaying: boolean = false;
  private lastRealTime: number;

  setDate(date: string) {
    // 設定模擬日期
  }

  setTime(time: string) {
    // 跳轉到特定時間
  }

  setSpeed(speed: number) {
    // 設定播放速度 (1, 2, 5, 10, 30, 60...)
  }

  play() {
    this.isPlaying = true;
    this.lastRealTime = Date.now();
    this.tick();
  }

  pause() {
    this.isPlaying = false;
  }

  private tick() {
    if (!this.isPlaying) return;

    const now = Date.now();
    const realElapsed = now - this.lastRealTime;
    const simulatedElapsed = realElapsed * this.playbackSpeed;

    this.simulatedTime = new Date(
      this.simulatedTime.getTime() + simulatedElapsed
    );

    this.lastRealTime = now;

    // 通知訂閱者時間更新
    this.emit('tick', this.simulatedTime);

    requestAnimationFrame(() => this.tick());
  }
}
```

---

## 七、資料準備流程

### 7.1 資料來源

1. **軌道幾何**: `trtc_shape.json` 或 `kepler_mrt_routes.geojson`
2. **車站資料**: `trtc_station_of_line.json`, `trtc_stations.json`
3. **路線定義**: `trtc_routes.json`
4. **班距資訊**: `trtc_frequency.json`
5. **歷史時刻表**: TDX API `/v2/Historical/Rail/Metro/StationTimeTable/Date/{Date}/TRTC`

### 7.2 資料處理腳本

```
data_collector/
├── scripts/
│   ├── 01_fetch_historical_timetable.py   # 抓取歷史時刻表
│   ├── 02_process_stations.py              # 處理車站資料
│   ├── 03_extract_red_line_tracks.py       # 提取紅線軌道
│   ├── 04_generate_track_geometry.py       # 產生軌道幾何
│   └── 05_generate_schedules.py            # 產生發車時刻表
└── output/
    ├── stations.json
    ├── tracks.json
    └── schedules/
        └── 2024-12-29.json
```

### 7.3 TDX 歷史時刻表資料格式

API: `/v2/Historical/Rail/Metro/StationTimeTable/Date/{Date}/TRTC`

```json
{
  "StationID": "R02",
  "StationName": {"Zh_tw": "象山", "En": "Xiangshan"},
  "Direction": 0,
  "DestinationStationID": "R28",
  "DestinationStationName": {"Zh_tw": "淡水", "En": "Tamsui"},
  "Timetables": [
    {
      "TrainNo": "001",
      "DepartureTime": "06:00",
      "Sequence": 1
    },
    // ...
  ]
}
```

### 7.4 產生發車時刻表邏輯

因為 TDX 提供的是**各站發車時間**，需要轉換為**軌道發車時刻表**：

```python
def generate_track_schedule(station_timetable, track):
    """
    從車站時刻表產生軌道發車時刻表
    只取起站的發車時間
    """
    departures = []

    start_station_data = station_timetable.get(track.start_station_id)
    if not start_station_data:
        return departures

    for timetable_entry in start_station_data:
        if timetable_entry['DestinationStationID'] == track.end_station_id:
            departures.append({
                'departureTime': timetable_entry['DepartureTime'],
                'trainNo': timetable_entry.get('TrainNo'),
                'trackId': track.track_id
            })

    return sorted(departures, key=lambda x: x['departureTime'])
```

---

## 八、技術選型

### 8.1 前端技術棧

| 類別 | 選擇 | 說明 |
|-----|------|------|
| 框架 | React 18 + TypeScript | 類型安全、組件化 |
| 地圖 | MapLibre GL JS | 開源、高效能 |
| 狀態管理 | Zustand | 輕量、簡單 |
| 樣式 | Tailwind CSS | 快速開發 |
| 建置 | Vite | 快速、現代 |

### 8.2 關鍵依賴

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "maplibre-gl": "^4.0.0",
    "zustand": "^4.4.0",
    "@turf/turf": "^7.0.0"
  }
}
```

---

## 九、實作順序（分階段）

### Phase 1: 資料準備（1-2 天）
- [ ] 設定 TDX API 認證
- [ ] 抓取指定日期的歷史時刻表
- [ ] 處理紅線車站資料
- [ ] 提取紅線軌道幾何
- [ ] 產生 tracks.json
- [ ] 產生 schedules/2024-12-29.json

### Phase 2: 基礎視覺化（2-3 天）
- [ ] 建立 React + Vite 專案
- [ ] 整合 MapLibre GL JS
- [ ] 渲染紅線軌道
- [ ] 渲染車站標記
- [ ] 基本樣式設定

### Phase 3: 時間引擎（1-2 天）
- [ ] 實作 TimeEngine 類別
- [ ] 播放/暫停控制
- [ ] 速度控制
- [ ] 時間軸 UI

### Phase 4: 列車動畫（2-3 天）
- [ ] 實作 TrainEngine 類別
- [ ] 列車位置計算
- [ ] 列車生命週期管理
- [ ] 列車圖標渲染
- [ ] 動畫流暢度優化

### Phase 5: UI 完善（1-2 天）
- [ ] 完整控制面板
- [ ] 列車資訊顯示
- [ ] 日期選擇器
- [ ] 響應式設計

---

## 十、目錄結構

```
mini-taipei-v3/
├── public/
│   └── data/
│       ├── stations.json
│       ├── tracks.json
│       └── schedules/
│           └── 2024-12-29.json
├── src/
│   ├── components/
│   │   ├── Map/
│   │   │   ├── MapContainer.tsx
│   │   │   ├── TrackLayer.tsx
│   │   │   ├── StationLayer.tsx
│   │   │   └── TrainLayer.tsx
│   │   └── Controls/
│   │       ├── Timeline.tsx
│   │       ├── SpeedControl.tsx
│   │       └── DatePicker.tsx
│   ├── engines/
│   │   ├── TimeEngine.ts
│   │   └── TrainEngine.ts
│   ├── stores/
│   │   └── useSimulationStore.ts
│   ├── types/
│   │   └── index.ts
│   ├── utils/
│   │   ├── interpolation.ts
│   │   └── time.ts
│   ├── App.tsx
│   └── main.tsx
├── data_collector/
│   └── scripts/
│       └── ...
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── DESIGN.md
```

---

## 十一、後續擴展方向

1. **多路線支援**：加入其他捷運線
2. **3D 視覺化**：參考 Mini Tokyo 3D 的立體效果
3. **即時模式**：整合 TDX 即時 API
4. **公車整合**：加入公車路線
5. **歷史回放**：選擇任意歷史日期回放

---

## 附錄 A: 淡水信義線站點詳細座標

（待從 trtc_stations.json 提取）

## 附錄 B: API 參考

### TDX 歷史時刻表 API
- Endpoint: `https://tdx.transportdata.tw/api/basic/v2/Historical/Rail/Metro/StationTimeTable/Date/{Date}/TRTC`
- 認證: Client Credentials OAuth 2.0
- 參數: Date 格式 `YYYY-MM-DD`
