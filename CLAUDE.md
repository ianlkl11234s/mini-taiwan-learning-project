# Mini Taiwan (mini-taipei-v3)

## Project Overview

Mini Taiwan 是一個台灣交通運輸即時模擬系統，在 Mapbox 地圖上視覺化呈現列車運行狀態。支援台北捷運、高雄捷運、高雄輕軌、台中捷運、台灣高鐵和台鐵。

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite
- **Map**: Mapbox GL JS v3
- **3D Rendering**: Three.js (via Mapbox CustomLayer)
- **Data**: GeoJSON (軌道) + JSON (時刻表)
- **Scripts**: Python 3 (資料處理)

## Development Commands

```bash
npm run dev      # 啟動開發伺服器 (http://localhost:5173)
npm run build    # TypeScript 檢查 + Vite 構建
npm run lint     # ESLint 檢查
```

## Architecture

### Core Flow
```
TimeEngine (模擬時間) → TrainEngine (計算列車狀態) → 3DLayer (渲染)
                    ↓
              Data Hooks (載入軌道/時刻表/車站)
```

### Key Patterns

**新增運輸系統的標準模組**：
1. `src/engines/{System}TrainEngine.ts` - 列車狀態計算
2. `src/layers/{System}3DLayer.ts` - 3D 渲染
3. `src/hooks/use{System}Data.ts` - 資料載入
4. `src/constants/{system}Info.ts` - 路線資訊
5. `public/data/{system}/` - 軌道 + 時刻表

### Critical Files

| 檔案 | 說明 |
|------|------|
| `src/App.tsx` | 主應用整合 |
| `src/engines/TimeEngine.ts` | 時間模擬 |
| `src/engines/TraTrainEngine.ts` | 台鐵引擎 |
| `src/components/TrainInfoPanel.tsx` | 資訊面板 |

## Agent Delegation

主動使用 sub-agent 減少 context 消耗：

| 任務類型 | 使用 Agent | 說明 |
|----------|------------|------|
| 探索程式碼 | `codebase-explorer` | 用 haiku 搜尋，節省 token |
| 規劃複雜功能 | `planner` | 產出計畫後再實作 |
| 新增台鐵路線 | `tra-route-builder` | 自動化 5 階段流程 |
| 驗證資料 | `transport-validator` | 檢查軌道/時刻表格式 |
| 3D 圖層開發 | `mapbox-3d-helper` | Three.js + Mapbox 整合 |

## Data Format

**軌道**: `{ "properties": { "track_id": "R-1-0" }, "geometry": { "type": "LineString" } }`

**時刻表**: `{ "track_id": "R-1-0", "departures": [{ "train_id": "...", "stations": [...] }] }`

## Important Conventions

- **TRA 開發規範**：詳見 `.claude/rules/tra-conventions.md`
- **距離計算**：Python/TypeScript 都用**歐幾里得距離**（非 Haversine）
- **列車尺寸**：TRTC 160m / TRA 200m / THSR 250m

## Documentation

| 文件 | 用途 |
|------|------|
| `docs/TRA_OD_IMPLEMENTATION_GUIDE.md` | TRA O-D 軌道系統 |
| `docs/METRO_IMPLEMENTATION_GUIDE.md` | 捷運/輕軌通用指南 |
| `public/data/tra/TRACKS_STATUS.md` | 軌道處理狀態 |

## Python Scripts

```bash
source venv/bin/activate && python3 scripts/tra/build_od_tracks.py
```
