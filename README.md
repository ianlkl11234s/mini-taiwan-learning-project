# Mini Taipei

台北捷運即時列車模擬系統 - 在地圖上視覺化呈現列車運行狀態

![React](https://img.shields.io/badge/React-19-blue) ![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue) ![Mapbox](https://img.shields.io/badge/Mapbox%20GL-3.17-orange)

## 致謝與資料來源

本專案使用以下開源資料與專案：

### 靈感來源
- [Mini Tokyo 3D](https://github.com/nagix/mini-tokyo-3d) by [@nagix](https://github.com/nagix) - 超讚的東京交通即時 3D 視覺化專案，讓我能夠學習！

### 時刻表資料
感謝 [@ericyu](https://github.com/ericyu) 的開源專案：
- [TaipeiMetroTimeTable](https://github.com/ericyu/TaipeiMetroTimeTable) - 台北捷運時刻表資料
- [TaipeiMetroRouteInfo](https://github.com/ericyu/TaipeiMetroRouteInfo) - 台北捷運路線資訊

### 軌道與車站資料
- [TDX 運輸資料流通服務](https://tdx.transportdata.tw/) - 提供軌道 GeoJSON 與車站位置

## 功能特色

- **即時列車模擬** - 根據真實時刻表模擬列車運行
- **Mapbox 地圖視覺化** - 使用 Mapbox GL JS 呈現精美的暗色地圖
- **多路線支援** - 淡水信義線主線、區間車、新北投支線
- **時間控制** - 可調整模擬速度 (1x-300x) 與跳轉時間
- **延長日時間軸** - 支援營運時間 06:00 至隔日 01:30
- **碰撞偵測** - 自動偵測列車碰撞並視覺化標示
- **停站動畫** - 列車到站時會有視覺狀態變化

## 技術架構

```
┌─────────────────────────────────────────────────────┐
│                    App.tsx                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  Mapbox GL  │  │ TimeEngine  │  │ TrainEngine │ │
│  │   (地圖)    │  │  (時間模擬)  │  │  (列車邏輯)  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
│         ↑               ↓               ↓          │
│         └───────────────┴───────────────┘          │
│                    useData Hook                     │
│           (載入 GeoJSON + 時刻表資料)               │
└─────────────────────────────────────────────────────┘
```

### 核心模組

| 模組 | 檔案 | 說明 |
|------|------|------|
| TimeEngine | `src/engines/TimeEngine.ts` | 模擬時間引擎，支援暫停、加速、跳轉 |
| TrainEngine | `src/engines/TrainEngine.ts` | 列車狀態管理、位置插值、碰撞偵測 |
| useData | `src/hooks/useData.ts` | 資料載入 Hook，處理 GeoJSON 與時刻表 |
| TimeControl | `src/components/TimeControl.tsx` | 時間控制面板 UI 元件 |

## 快速開始

### 環境需求

- Node.js 18+
- npm 或 yarn
- Mapbox Access Token ([申請連結](https://account.mapbox.com/access-tokens/))

### 安裝步驟

```bash
# 安裝依賴
npm install

# 設定環境變數
cp .env.example .env
# 編輯 .env，填入你的 Mapbox Token

# 啟動開發伺服器
npm run dev
```

開啟 http://localhost:5173 即可看到列車模擬

### 建置生產版本

```bash
npm run build
npm run preview  # 預覽建置結果
```

## 專案結構

```
mini-taipei/
├── src/                      # React 原始碼
│   ├── components/           # UI 元件
│   │   └── TimeControl.tsx   # 時間控制面板
│   ├── engines/              # 核心引擎
│   │   ├── TimeEngine.ts     # 時間模擬引擎
│   │   └── TrainEngine.ts    # 列車運算引擎
│   ├── hooks/                # React Hooks
│   │   └── useData.ts        # 資料載入
│   └── types/                # TypeScript 型別
├── public/data/              # 靜態資料
│   ├── tracks/               # 軌道 GeoJSON (19 條)
│   ├── schedules/            # 時刻表 JSON (19 個)
│   ├── station_progress.json # 車站進度對照表
│   └── red_line_stations.geojson
├── tools/data_collector/     # 資料轉換工具
│   ├── convert_ericyu_timetable.py
│   ├── create_intermediate_tracks.py
│   └── source/               # 原始資料
└── docs/                     # 內部文件
```

---

# 技術文件

## 列車動畫原理

### 車站進度映射 (Station Progress)

每條軌道是一條 LineString，列車位置用 **進度值 (0-1)** 表示：

```
軌道起點 ─────●─────●─────●─────●───── 軌道終點
  0.0       0.25    0.5   0.75      1.0
           站A     站B    站C
```

`station_progress.json` 儲存每個車站在各軌道上的實際進度：

```json
{
  "R-1-0": {
    "R02": 0.0,      // 象山站：軌道起點
    "R03": 0.0276,   // 台北101站
    "R04": 0.0657,   // 信義安和站
    ...
    "R28": 1.0       // 淡水站：軌道終點
  }
}
```

### 位置插值演算法

列車位置根據時刻表計算：

```
1. 從時刻表找出當前狀態：停站中 or 行駛中
2. 若停站中：位置 = 該站的 progress 值
3. 若行駛中：
   - 計算區段進度 = (當前時間 - 離站時間) / (下站到達 - 離站時間)
   - 位置 = 線性插值(起站progress, 終站progress, 區段進度)
4. 將 progress 轉換為實際經緯度座標
```

```typescript
// TrainEngine.ts 核心邏輯
function interpolateBetweenStations(
  coords: [number, number][],
  fromProgress: number,  // 起站進度 (如 0.25)
  toProgress: number,    // 終站進度 (如 0.5)
  segmentProgress: number // 區段進度 (0-1)
): [number, number] {
  const actualProgress = fromProgress + (toProgress - fromProgress) * segmentProgress;
  return interpolateOnLineString(coords, actualProgress);
}
```

## 碰撞偵測系統

### 問題背景

淡水信義線有多種營運模式共用同一實體軌道：
- R-1 全程車 (象山 ↔ 淡水)
- R-2 區間車 (象山 ↔ 北投)
- R-4 北段車 (北投 ↔ 淡水)

當兩輛不同路線的列車在同一物理位置時，需要視覺化區分。

### 解決方案

```typescript
// 定義共用軌道區段
const SHARED_TRACK_SEGMENTS = {
  'R-1-0': ['R05', 'R06', ..., 'R22'],  // 大安到北投
  'R-2-0': ['R05', 'R06', ..., 'R22'],  // 相同區段
  ...
};

// 碰撞偵測流程
1. 將列車按行駛方向分組
2. 檢查同方向列車間的距離
3. 若距離 < 閾值 (約 50 公尺)：
   - 標記為碰撞狀態
   - 計算垂直於軌道的偏移向量
   - 分別向兩側偏移顯示
```

### 視覺效果

- **正常行駛**：白色邊框圓點
- **停站中**：較大圓點 + 脈動效果
- **碰撞中**：黃色邊框 + 警示光暈 + 位置偏移

## 首班車問題與解決方案

### 問題描述

首班車常從中途站發車（如大安、雙連），而非起點站（象山、淡水）。若使用完整軌道計算進度，會出現「瞬移」現象：

```
問題：大安站首班車使用 R-1-0 軌道
- R-1-0 定義：象山 (0.0) → 淡水 (1.0)
- 大安站在 R-1-0 的進度：0.104
- 首班車從進度 0.104 開始，但時刻表的「相對時間」從 0 開始
- 導致列車一開始就「飛」到錯誤位置
```

### 解決方案：專用軌道

為每個「非標準起點」的班次建立專屬軌道：

```
標準軌道：
R-1-0: 象山 (0.0) ────────────────────── 淡水 (1.0)

首班車專用軌道：
R-5-0: 大安 (0.0) ────────────────────── 淡水 (1.0)
R-6-0: 雙連 (0.0) ────────────────────── 淡水 (1.0)
...
```

### 軌道分類

| 軌道 ID | 類型 | 起點 → 終點 | 用途 |
|---------|------|-------------|------|
| R-1-0/1 | 主線 | 象山 ↔ 淡水 | 全程車 |
| R-2-0/1 | 區間 | 象山 ↔ 北投 | 南段區間車 |
| R-3-0/1 | 支線 | 北投 ↔ 新北投 | 新北投支線 |
| R-4-0/1 | 北段 | 北投 ↔ 淡水 | 北段區間車 |
| R-5-0 ~ R-8-0 | 首班車 | 中途站 → 淡水 | 北上首班車 |
| R-9-1 ~ R-15-1 | 首班車 | 中途站 → 象山 | 南下首班車 |

### 軌道可見性

首班車專用軌道設為透明 (opacity: 0)，因為它們與主線物理重疊：

```typescript
// App.tsx
'line-opacity': [
  'case',
  ['in', 'R-1', ['get', 'track_id']], 0.8,  // 主線可見
  ['in', 'R-3', ['get', 'track_id']], 0.8,  // 支線可見
  0.0  // 其他透明 (避免重複顯示)
]
```

## 延長日時間處理

### 問題背景

捷運營運時間橫跨午夜（末班車約 01:00-01:30 抵達），傳統 0-24 時制無法連續表示。

### 解決方案

使用「延長日」概念：

```
傳統時制：00:00 ─────────────────────── 23:59
          │                               │
          └─── 跳回開頭 ←─────────────────┘

延長日時制：06:00 ──────────────────────────── 01:30 (25:30)
            │        │        │        │        │
          06:00   12:00   18:00   24:00   01:30
```

```typescript
// TimeControl.tsx
function toExtendedSeconds(standardSeconds: number): number {
  // 凌晨 00:00-05:59 視為 24:00-29:59
  if (standardSeconds < 6 * 3600) {
    return standardSeconds + 24 * 3600;
  }
  return standardSeconds;
}
```

---

## 資料收集與轉換工具

### 工具概覽

```
tools/data_collector/
├── convert_ericyu_timetable.py  # 時刻表轉換 (主要工具)
├── create_intermediate_tracks.py # 首班車軌道建立
└── source/
    └── ericyu_R.json            # Eric Yu 時刻表原始資料
```

### 轉換流程

本專案參考 [Eric Yu 的 TaipeiMetroTimeTable](https://github.com/ericyu/TaipeiMetroTimeTable) 格式設計，轉換工具可套用至 TDX 取得的其他路線資料：

```bash
cd tools/data_collector

# 1. 轉換時刻表
python convert_ericyu_timetable.py

# 2. 建立首班車專用軌道 (如有需要)
python create_intermediate_tracks.py
```

### 轉換器輸出

```
輸出目錄: public/data/schedules/
  ✅ R-1-0.json: 133 班車
  ✅ R-1-1.json: 133 班車
  ✅ R-2-0.json: 120 班車
  ...
  ✅ R-15-1.json: 1 班車 (首班車專用)
```

### 擴展至其他路線

1. 從 TDX 取得該路線的時刻表資料
2. 轉換為 Eric Yu 格式 (或直接修改轉換器)
3. 準備軌道 GeoJSON 與車站資料
4. 建立 `station_progress.json` 映射
5. 更新前端載入新軌道

## 資料格式規格

### 軌道資料 (GeoJSON)

```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {
      "track_id": "R-1-0",
      "route_id": "R-1",
      "direction": 0,
      "name": "象山 → 淡水",
      "color": "#d90023"
    },
    "geometry": {
      "type": "LineString",
      "coordinates": [[121.xxx, 25.xxx], ...]
    }
  }]
}
```

### 時刻表資料 (JSON)

```json
{
  "track_id": "R-1-0",
  "route_id": "R-1",
  "name": "象山 → 淡水",
  "origin": "R02",
  "destination": "R28",
  "stations": ["R02", "R03", ...],
  "departure_count": 133,
  "departures": [{
    "train_id": "R-1-0-001",
    "departure_time": "06:00:00",
    "origin_station": "R02",
    "total_travel_time": 3240,
    "stations": [
      { "station_id": "R02", "arrival": 0, "departure": 40 },
      { "station_id": "R03", "arrival": 140, "departure": 180 },
      ...
    ]
  }]
}
```

### 車站進度映射 (JSON)

```json
{
  "R-1-0": {
    "R02": 0.0,
    "R03": 0.027612,
    ...
    "R28": 1.0
  },
  "R-5-0": {
    "R05": 0.0,
    "R06": 0.020248,
    ...
    "R28": 1.0
  }
}
```

## 環境變數

```env
VITE_MAPBOX_TOKEN=your_mapbox_token_here
```

取得 Mapbox Token: https://account.mapbox.com/access-tokens/

## 技術棧

| 層級 | 技術 |
|------|------|
| 前端 | React 19 + TypeScript + Vite |
| 地圖 | Mapbox GL JS |
| 軌道資料 | TDX 運輸資料流通服務 |
| 時刻表資料 | Eric Yu 開源專案 |

## 授權

MIT License
