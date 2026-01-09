# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mini Taiwan 是一個台灣交通運輸即時模擬系統，在 Mapbox 地圖上視覺化呈現列車運行狀態。支援台北捷運、高雄捷運、高雄輕軌、台中捷運、台灣高鐵和台鐵。

## Development Commands

```bash
npm run dev      # 啟動開發伺服器 (http://localhost:5173)
npm run build    # TypeScript 檢查 + Vite 構建
npm run lint     # ESLint 檢查
npm run preview  # 預覽構建結果
```

## Environment Setup

需要 Mapbox Token：
```bash
cp .env.example .env
# 編輯 .env，填入 VITE_MAPBOX_TOKEN
```

## Architecture

### Core Flow
```
TimeEngine (模擬時間) → TrainEngine (計算列車狀態) → 3DLayer/SymbolLayer (渲染)
                    ↓
              Data Hooks (載入軌道/時刻表/車站)
```

### Key Patterns

**新增運輸系統的標準模組**：
1. `src/engines/{System}TrainEngine.ts` - 列車狀態計算
2. `src/layers/{System}3DLayer.ts` - 3D 渲染 (Three.js + Mapbox CustomLayer)
3. `src/hooks/use{System}Data.ts` - 資料載入 Hook
4. `src/constants/{system}Info.ts` - 路線顏色、名稱、車站資訊
5. `public/data/{system}/` - 軌道 GeoJSON + 時刻表 JSON

**列車位置計算**：
- 使用 `station_progress.json` 將車站映射到軌道上的進度值 (0-1)
- 根據時刻表計算區段進度，線性插值得到經緯度座標
- 時間單位：當天秒數 (0-86399)，營運時間 06:00-01:30

**O-D 專屬軌道系統 (TRA)**：
- 避免動態軌道切換造成的抖動
- 為每個起迄對預先合併完整軌道
- 詳見 `docs/TRA_OD_IMPLEMENTATION_GUIDE.md`

### Critical Files

| 檔案 | 說明 |
|------|------|
| `src/App.tsx` | 主應用 (126KB)，整合所有系統 |
| `src/engines/TimeEngine.ts` | 時間模擬引擎 |
| `src/engines/ODTrainEngine.ts` | TRA O-D 專屬軌道引擎 |
| `src/components/TrainInfoPanel.tsx` | 列車資訊面板 |

## Technical Implementation Details

### 列車位置插值演算法

```typescript
// 1. 從時刻表找出當前狀態：停站中 or 行駛中
// 2. 若停站中：位置 = 該站的 progress 值
// 3. 若行駛中：
//    - 區段進度 = (當前時間 - 離站時間) / (下站到達 - 離站時間)
//    - 位置 = lerp(起站progress, 終站progress, 區段進度)
// 4. 將 progress 轉換為軌道上的經緯度座標

function interpolateOnLineString(coords: [number, number][], progress: number): [number, number] {
  const totalLength = calculateTotalLength(coords);
  const targetDistance = totalLength * progress;
  // 沿軌道累積距離找到對應點
}
```

### 3D Layer 實作 (Mapbox CustomLayerInterface)

```typescript
class Train3DLayer implements mapboxgl.CustomLayerInterface {
  id = 'train-3d-layer';
  type: 'custom' = 'custom';
  renderingMode: '3d' = '3d';

  onAdd(map: mapboxgl.Map, gl: WebGLRenderingContext) {
    // 初始化 Three.js scene, camera, renderer
    // 建立共用 geometry 和 material
  }

  render(gl: WebGLRenderingContext, matrix: number[]) {
    // 更新列車 mesh 位置和旋轉
    // 使用 Mapbox 投影矩陣渲染
  }
}
```

### 列車方向計算

```typescript
// 找最近的軌道線段，計算該線段方向
private calculateBearing(train: Train): number {
  const track = this.tracks.get(train.trackId);
  const coords = track.geometry.coordinates;

  // 找到列車位置最近的軌道線段
  let closestSegment = findClosestSegment(train.position, coords);

  // 計算線段方向角
  const p1 = lngLatToMeters(coords[closestSegment]);
  const p2 = lngLatToMeters(coords[closestSegment + 1]);
  return Math.atan2(p2.y - p1.y, p2.x - p1.x) * 180 / Math.PI;
}
```

### App.tsx 整合新系統的關鍵步驟

```typescript
// 1. 新增 ref
const system3DLayerRef = useRef<System3DLayer | null>(null);

// 2. 載入資料的 useEffect
useEffect(() => {
  if (!map.current || !mapLoaded || !use3DMode) return;
  if (systemState === 'hidden') return;

  const layer = new System3DLayer(tracks);
  layer.setStations(stationCoordinates);
  layer.setOnSelect(handleSelectTrain);
  system3DLayerRef.current = layer;
  map.current.addLayer(layer);

  return () => {
    if (map.current?.getLayer('system-3d-layer')) {
      map.current.removeLayer('system-3d-layer');
    }
  };
}, [mapLoaded, tracks, use3DMode, systemState, styleVersion]);

// 3. 更新列車的 useEffect
useEffect(() => {
  if (!system3DLayerRef.current) return;
  system3DLayerRef.current.updateTrains(trains);
}, [trains]);

// 4. 在 selectedTrain useMemo 加入查找
const selectedTrain = useMemo(() => {
  // ... 其他系統查找 ...
  const train = systemTrains.find(t => t.trainId === selectedTrainId);
  if (train) return train;
  return null;
}, [selectedTrainId, systemTrains]);
```

### 環狀線特殊處理 (KLRT)

```typescript
// 環狀線起點終點都是同一站 (C1)
// 順時針: C1 → C2 → ... → C37 → C1 (progress 0 → 1)
// 逆時針: C1 → C37 → ... → C2 → C1 (progress 0 → 1)
// 終點站 progress = 1.0，不是回到 0.0
```

### TrainInfoPanel 列車類型判斷

```typescript
// 判斷列車類型的優先順序
const isThsr = train.trackId.startsWith('THSR');
const isKrtc = train.trackId.startsWith('KRTC');
const isKlrt = train.trackId.startsWith('KLRT');
const isTmrt = train.trackId.startsWith('TMRT');
const isTra = train.trackId.startsWith('NW') ||
              train.trackId.startsWith('LJ') ||
              train.trackId.startsWith('SH') ||
              train.trackId.startsWith('WL');

// 根據類型選擇對應的 getLineName/getLineColor
const lineName = isThsr ? getThsrLineName(train.trackId)
  : isKrtc ? getKrtcLineName(train.trackId)
  : isTra ? getTraLineName(train.trackId)
  : getLineName(train.trackId);  // 預設 MRT
```

## Data Format

**軌道 GeoJSON**：
```json
{
  "properties": { "track_id": "R-1-0", "route_id": "R-1", "direction": 0 },
  "geometry": { "type": "LineString", "coordinates": [[121.xxx, 25.xxx], ...] }
}
```

**時刻表 JSON**：
```json
{
  "track_id": "R-1-0",
  "departures": [{
    "train_id": "R-1-0-001",
    "departure_time": "06:00:00",
    "stations": [
      { "station_id": "R02", "arrival": 0, "departure": 40 },
      { "station_id": "R03", "arrival": 140, "departure": 180 }
    ]
  }]
}
```

## Important Conventions

**TRA 雙引擎架構 - 避免重複渲染**：
- TRA 有兩套列車引擎：
  - `TraTrainEngine`：使用 `useTraData` 載入 `/data/tra/schedules/` 的時刻表
  - `ODTrainEngine`：使用 `useODTraData` 載入 `/data/tra/schedules_od/` 的時刻表
- **重要**：將路線遷移到 O-D 系統時，必須：
  1. 在 `useODTraData.ts` 的 `OD_TRACK_IDS` 和 `SCHEDULE_IDS` 加入新路線
  2. **同時**從 `useTraData.ts` 的 `TRA_SCHEDULE_IDS` 移除該路線
  3. 否則會導致同一列車被兩個引擎渲染，出現「幽靈列車」
- 目前所有支線 (NW, LJ, SH, PX, JJ, CZ) 都由 `ODTrainEngine` 處理
- `TRA_SCHEDULE_IDS` 應保持為空陣列

**TRA/THSR station_id 衝突**：
- TRA 和 THSR 使用相同的 station_id 編號 (如 0990, 1000, 1010)
- TRA 車站**不加入**共用 `stationNames` Map
- 在 `TrainInfoPanel` 中使用 `TRA_STATION_NAMES` 獨立查找

**O-D 軌道方向對映**：
- `ODTrainEngine.ts` 的 `getTrackIdFromOdTrackId()` 函數將 O-D 軌道 ID 轉換為顯示用 trackId
- 新增支線時，必須在 `mainStations` 物件加入該線的「起點站代碼」
- 起點站 = 方向 0 的終點（通常是連接幹線的車站）
- 範例：`'SH': 'TN'` 表示沙崙線的起點是臺南 (TN)，往沙崙 (SL) 是方向 1

**距離計算**：
- Python 腳本和 TypeScript 引擎都必須使用**歐幾里得距離**（平面，度為單位）
- 不要使用 Haversine（球面距離），否則 station_progress 會對不上

**3D Layer 列車尺寸 (公尺)**：
| 系統 | 長度 | 寬度 | 高度 |
|------|------|------|------|
| TRTC | 160 | 90 | 90 |
| TRA | 200 | 85 | 80 |
| THSR | 250 | 80 | 70 |

## Documentation

- `docs/METRO_IMPLEMENTATION_GUIDE.md` - 新增捷運/輕軌系統通用指南
- `docs/TRA_OD_IMPLEMENTATION_GUIDE.md` - TRA O-D 軌道系統實作細節
- `docs/TRA_IMPLEMENTATION_ROADMAP.md` - TRA 路線實作規劃藍圖
- `docs/LINE_ADDITION_GUIDE.md` - 新增路線步驟
- `docs/LINE_ADDITION_TROUBLESHOOTING.md` - 常見問題排解

## Python Scripts

資料處理腳本位於 `scripts/` 目錄，需要 Python 虛擬環境：
```bash
source venv/bin/activate
python scripts/tra/build_od_tracks.py
```

TDX API 資料來源：https://tdx.transportdata.tw/
