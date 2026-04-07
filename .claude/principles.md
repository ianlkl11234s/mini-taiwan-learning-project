# 專案運作原則 — Mini Taipei v3

## 支援系統
6 個軌道系統：
- **TRA** (台鐵)
- **THSR** (高鐵)
- **TRTC** (台北捷運)
- **KRTC** (高雄捷運)
- **KLRT** (高雄輕軌)
- **TMRT** (台中捷運)

## 技術棧
- **Frontend**: React 18 + TypeScript + Vite
- **Map**: Mapbox GL JS v3
- **3D**: Three.js (Mapbox CustomLayer)
- **Data**: GeoJSON (軌道) + JSON (時刻表)
- **Scripts**: Python 3 (資料處理)

## 資料處理慣例

### 軌道幾何 (GeoJSON)
- 靜態資料，變更頻率低
- 來源：OSM / TDX 匯出後人工清理
- 輸出目錄：`public/<system>/tracks/`

### 時刻表 (JSON)
- **TRA/THSR**: 每日更新，含當日實際班次
- **捷運**: 固定班表（工作日 vs 假日），不含當日變動
- 匯出腳本：`scripts/export-rail-data.py`

### Supabase 匯出
- 腳本：匯出到 `reference.daily_schedules` 表
- 格式：mini-taipei-v3 的 `convert_*_timetable` 函數
- 被 data-collectors 的 publish task 引用（共用轉換邏輯）

## 視覺化原則

### 列車運行模擬
- 根據時刻表 + 發車時間推算「現在每班車在哪裡」
- 用線性內插（等速假設）
- 在站點停留時間從時刻表取得

### 座標系統
- 列車位置用 Mercator projection
- Three.js 場景統一用 Mapbox 的 CustomLayer 整合

## 開發慣例

### 新增系統
1. 準備軌道 GeoJSON → 放 `public/<system>/tracks/`
2. 準備時刻表 JSON → 放 `public/<system>/schedules/`
3. 在 `systemConfig.ts` 註冊新系統
4. 在 `RailScene` 加顏色設定

### Commit
- TypeScript 檢查：`npx tsc -b`
- Commit message 用繁體中文

## 相依專案

- **mini-taiwan-pulse** — 讀取時刻表模擬
- **gis-platform** — Supabase `reference.daily_schedules` 表
- **data-collectors** — 匯出到 Supabase 的 publish task 重用此專案的轉換函數
