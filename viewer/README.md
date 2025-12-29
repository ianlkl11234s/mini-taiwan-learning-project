# Mini Taipei 3D

台北捷運即時列車模擬系統，在 3D 地圖上呈現淡水信義線的列車運行狀態。

![Demo](https://img.shields.io/badge/Demo-Live-green) ![React](https://img.shields.io/badge/React-19-blue) ![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue) ![Mapbox](https://img.shields.io/badge/Mapbox%20GL-3.17-orange)

## 功能特色

- **即時列車模擬** - 根據真實時刻表模擬列車運行
- **3D 地圖視覺化** - 使用 Mapbox GL JS 呈現精美的暗色地圖
- **多路線支援** - 淡水信義線主線 (R-1)、象山段 (R-2)、新北投支線 (R-3)
- **時間控制** - 可調整模擬速度 (1x-60x) 與跳轉時間
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

| 模組 | 說明 |
|------|------|
| `TimeEngine` | 模擬時間引擎，支援暫停、加速、跳轉 |
| `TrainEngine` | 列車狀態管理、位置插值、碰撞偵測 |
| `useData` | 資料載入 Hook，處理 GeoJSON 與時刻表 |
| `TimeControl` | 時間控制面板 UI 元件 |

## 快速開始

### 環境需求

- Node.js 18+
- npm 或 yarn
- Mapbox Access Token ([申請連結](https://account.mapbox.com/access-tokens/))

### 安裝步驟

```bash
# 1. 進入專案目錄
cd viewer

# 2. 安裝依賴
npm install

# 3. 設定環境變數
cp .env.example .env
# 編輯 .env，填入你的 Mapbox Token

# 4. 啟動開發伺服器
npm run dev
```

開啟瀏覽器訪問 `http://localhost:5173`

### 建置生產版本

```bash
npm run build
npm run preview  # 預覽建置結果
```

## 專案結構

```
viewer/
├── public/
│   └── data/
│       ├── tracks/           # 軌道 GeoJSON (R-1, R-2, R-3)
│       ├── schedules/        # 時刻表 JSON
│       ├── red_line_stations.geojson  # 車站資料
│       └── station_progress.json      # 車站位置對照表
├── src/
│   ├── components/
│   │   └── TimeControl.tsx   # 時間控制面板
│   ├── engines/
│   │   ├── TimeEngine.ts     # 時間模擬引擎
│   │   └── TrainEngine.ts    # 列車運算引擎
│   ├── hooks/
│   │   └── useData.ts        # 資料載入 Hook
│   ├── types/
│   │   ├── schedule.ts       # 時刻表型別
│   │   └── track.ts          # 軌道型別
│   ├── App.tsx               # 主要應用程式
│   ├── index.css             # 全域樣式
│   └── main.tsx              # 進入點
├── .env.example              # 環境變數範例
├── package.json
└── vite.config.ts
```

## 資料格式

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
      "name": "淡水 → 象山",
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
  "route_id": "R-1",
  "trains": [{
    "train_id": "R101",
    "track_id": "R-1-0",
    "start_time": "06:00:00",
    "schedules": [
      { "station_id": "R28", "arrival": "06:00:00", "departure": "06:00:30" },
      { "station_id": "R27", "arrival": "06:02:00", "departure": "06:02:30" }
    ]
  }]
}
```

## 路線說明

| 路線 ID | 名稱 | 區間 | 說明 |
|---------|------|------|------|
| R-1 | 主線 | 淡水 ↔ 象山 | 完整淡水信義線 |
| R-2 | 共用區段 | 北投 ↔ 象山 | 與 R-1 重疊的區段 |
| R-3 | 新北投支線 | 北投 ↔ 新北投 | 獨立支線 |

## 開發指南

### 新增路線

1. 準備軌道 GeoJSON 檔案 (`public/data/tracks/`)
2. 準備時刻表 JSON 檔案 (`public/data/schedules/`)
3. 更新 `station_progress.json` 加入新車站
4. 在 `App.tsx` 調整軌道顏色與顯示邏輯

### 調整模擬速度

```typescript
// TimeEngine 預設每秒更新 60 次
const engine = new TimeEngine({
  tickRate: 60,  // FPS
  onTick: (time) => { ... }
});
```

## 授權條款

MIT License

## 致謝

- [Mapbox GL JS](https://docs.mapbox.com/mapbox-gl-js/) - 地圖渲染
- [台北捷運公司](https://www.metro.taipei/) - 時刻表參考資料
