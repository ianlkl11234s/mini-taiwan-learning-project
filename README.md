# Mini Taiwan

台灣交通運輸模擬 - 在地圖上視覺化呈現列車運行狀態

![React](https://img.shields.io/badge/React-19.2-blue) ![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue) ![Mapbox](https://img.shields.io/badge/Mapbox%20GL-3.17-orange) ![Three.js](https://img.shields.io/badge/Three.js-0.182-green) ![Vite](https://img.shields.io/badge/Vite-7.2-purple)

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
- **多城市切換** - 支援台北 (TPE)、台中 (TXG)、高雄 (KHH)、花蓮 (HUN)、台東 (TTT) 五城市快速切換
- **Mapbox 地圖視覺化** - 使用 Mapbox GL JS 呈現精美地圖
- **完整路網支援** - 支援台北捷運、台中捷運、高雄捷運、高雄輕軌、台灣高鐵、台鐵 (992 班)
- **2D / 3D 模式切換** - 支援平面與立體視角，3D 模式下列車以方塊呈現
- **列車跟隨模式** - 點擊列車可開啟跟隨，自動追蹤列車位置
- **日夜主題切換** - 支援 Auto（隨時間自動切換）、Dawn、Day、Dusk、Night、Dark 六種主題
- **時間控制** - 可調整模擬速度 (1x-300x) 與跳轉時間
- **延長日時間軸** - 支援營運時間 06:00 至隔日 01:30
- **路線篩選** - 依城市與路線分類篩選
- **碰撞偵測** - 自動偵測列車碰撞並視覺化標示
- **停站動畫** - 列車到站時會有視覺狀態變化

## 支援路線

### 台北都會區 (TPE)

| 路線 | 代碼 | 車站數 | 營運模式 |
|------|------|--------|----------|
| 🔴 淡水信義線 | R | 28 站 | 全程車、區間車、新北投支線 |
| 🟢 松山新店線 | G | 20 站 | 全程車、小碧潭支線 |
| 🟠 中和新蘆線 | O | 27 站 | 迴龍線、蘆洲線 |
| 🔵 板南線 | BL | 23 站 | 全程車、區間車 |
| 🟤 文湖線 | BR | 24 站 | 全自動無人駕駛 |
| 🟡 環狀線 | Y | 14 站 | 第一階段 |
| 🟣 桃園機場捷運 | A | 22 站 | 普通車、直達車、加班直達車 |
| 💚 安坑輕軌 | K | 9 站 | 輕軌 |
| 🩵 淡海輕軌 | V | 11 站 | 綠山線 |
| 🚡 貓空纜車 | MK | 4 站 | 纜車（三段式顯示控制） |

### 高雄都會區 (KHH)

| 路線 | 代碼 | 車站數 | 營運模式 |
|------|------|--------|----------|
| 🔴 高雄捷運紅線 | R | 24 站 | 小港 ↔ 岡山 |
| 🟠 高雄捷運橘線 | O | 14 站 | 哈瑪星 ↔ 大寮 |
| 💚 高雄輕軌環狀線 | C | 38 站 | 順時針、逆時針 |

### 台中都會區 (TXG)

| 路線 | 代碼 | 車站數 | 營運模式 |
|------|------|--------|----------|
| 💚 台中捷運綠線 | G | 18 站 | 北屯總站 ↔ 高鐵台中站 |

### 台灣高鐵 (THSR)

| 路線 | 代碼 | 車站數 | 營運模式 |
|------|------|--------|----------|
| 🟧 台灣高鐵 | THSR | 12 站 | 南港 ↔ 左營 |

### 台鐵 (TRA)

| 路線 | 代碼 | 說明 | 班次 |
|------|------|------|------|
| 🚃 西部幹線 | WL | 基隆 ↔ 高雄（含山線/海線） | 主要幹線 |
| 🚃 宜蘭線 | YL | 八堵 ↔ 蘇澳（含蘇澳支線） | 環島東部 |
| 🚃 北迴線 | BH | 蘇澳新 ↔ 花蓮 | 環島東部 |
| 🚃 臺東線 | TL | 花蓮 ↔ 臺東 | 環島東部 |
| 🚃 南迴線 | SK | 臺東 ↔ 高雄（枋寮） | 環島南部 |
| 🚃 屏東線 | PT | 高雄 ↔ 枋寮 | 南部支線 |
| 🚃 平溪線 | PX | 三貂嶺 ↔ 菁桐 | 支線 |
| 🚃 內灣線 | NW | 竹中 ↔ 內灣 | 支線 |
| 🚃 六家線 | LJ | 竹中 ↔ 六家 | 支線 |
| 🚃 沙崙線 | SH | 臺南 ↔ 沙崙 | 支線 |
| 🚃 集集線 | JJ | 二水 ↔ 車埕 | 支線 |
| 🚃 成追線 | CZ | 成功 ↔ 追分 | 支線 |
| 🚃 深澳線 | SA | 瑞芳 ↔ 八斗子 | 支線 |
| 🚃 基隆支線 | KL | 八堵 ↔ 基隆 | 支線 |

> 台鐵總計 992 班列車（含區間車、自強號、普悠瑪、太魯閣等各車種），覆蓋 17 條路線、180 條 O-D 專屬軌道

## 技術架構

```
┌───────────────────────────────────────────────────────────────────────┐
│                              App.tsx                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────────────┐ │
│  │  Mapbox GL  │  │ TimeEngine  │  │         Train Engines          │ │
│  │   (地圖)    │  │  (時間模擬)  │  │ TRTC/THSR/KRTC/KLRT/TMRT/TRA  │ │
│  └─────────────┘  └─────────────┘  └────────────────────────────────┘ │
│         ↑               ↓                       ↓                      │
│         └───────────────┴───────────────────────┘                      │
│                           Data Hooks                                   │
│   useData / useThsrData / useKrtcData / useKlrtData / useTmrtData      │
│                         / useTraData                                   │
└───────────────────────────────────────────────────────────────────────┘
```

### 核心模組

| 模組 | 檔案 | 說明 |
|------|------|------|
| TimeEngine | `src/engines/TimeEngine.ts` | 模擬時間引擎，支援暫停、加速、跳轉 |
| TrainEngine | `src/engines/TrainEngine.ts` | 台北捷運列車狀態管理 |
| ThsrTrainEngine | `src/engines/ThsrTrainEngine.ts` | 高鐵列車引擎 |
| KrtcTrainEngine | `src/engines/KrtcTrainEngine.ts` | 高雄捷運列車引擎 |
| KlrtTrainEngine | `src/engines/KlrtTrainEngine.ts` | 高雄輕軌列車引擎 |
| TmrtTrainEngine | `src/engines/TmrtTrainEngine.ts` | 台中捷運列車引擎 |
| TraTrainEngine | `src/engines/TraTrainEngine.ts` | 台鐵列車引擎 |
| Train3DLayer | `src/layers/Train3DLayer.ts` | 台北捷運 3D 圖層 |
| Thsr3DLayer | `src/layers/Thsr3DLayer.ts` | 高鐵 3D 圖層 |
| Krtc3DLayer | `src/layers/Krtc3DLayer.ts` | 高雄捷運 3D 圖層 |
| Klrt3DLayer | `src/layers/Klrt3DLayer.ts` | 高雄輕軌 3D 圖層 |
| Tmrt3DLayer | `src/layers/Tmrt3DLayer.ts` | 台中捷運 3D 圖層 |
| Tra3DLayer | `src/layers/Tra3DLayer.ts` | 台鐵 3D 圖層 |
| useData | `src/hooks/useData.ts` | 台北捷運資料載入 |
| useThsrData | `src/hooks/useThsrData.ts` | 高鐵資料載入 |
| useKrtcData | `src/hooks/useKrtcData.ts` | 高雄捷運資料載入 |
| useKlrtData | `src/hooks/useKlrtData.ts` | 高雄輕軌資料載入 |
| useTmrtData | `src/hooks/useTmrtData.ts` | 台中捷運資料載入 |
| useTraData | `src/hooks/useTraData.ts` | 台鐵資料載入 |
| CitySelector | `src/components/CitySelector.tsx` | 城市快速切換 |
| LineFilter | `src/components/LineFilter.tsx` | 路線篩選 |
| TrainInfoPanel | `src/components/TrainInfoPanel.tsx` | 列車跟隨資訊面板 |

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
mini-taiwan/
├── src/                          # React 原始碼
│   ├── components/               # UI 元件
│   │   ├── CitySelector.tsx      # 城市選擇器
│   │   ├── LineFilter.tsx        # 路線篩選
│   │   ├── TimeControl.tsx       # 時間控制面板
│   │   ├── ThemeToggle.tsx       # 主題切換
│   │   ├── TrainInfoPanel.tsx    # 列車資訊面板
│   │   ├── TrainHistogram.tsx    # 列車數量直方圖
│   │   └── MobileMapStyleSelector.tsx  # 行動裝置地圖樣式選擇
│   ├── engines/                  # 核心引擎
│   │   ├── TimeEngine.ts         # 時間模擬引擎
│   │   ├── TrainEngine.ts        # 台北捷運列車引擎
│   │   ├── ThsrTrainEngine.ts    # 高鐵列車引擎
│   │   ├── KrtcTrainEngine.ts    # 高雄捷運列車引擎
│   │   ├── KlrtTrainEngine.ts    # 高雄輕軌列車引擎
│   │   ├── TmrtTrainEngine.ts    # 台中捷運列車引擎
│   │   └── TraTrainEngine.ts     # 台鐵列車引擎
│   ├── layers/                   # 3D 圖層
│   │   ├── Train3DLayer.ts       # 台北捷運 3D 圖層
│   │   ├── TrainSymbolLayer.ts   # 列車符號圖層
│   │   ├── Thsr3DLayer.ts        # 高鐵 3D 圖層
│   │   ├── Krtc3DLayer.ts        # 高雄捷運 3D 圖層
│   │   ├── Klrt3DLayer.ts        # 高雄輕軌 3D 圖層
│   │   ├── Tmrt3DLayer.ts        # 台中捷運 3D 圖層
│   │   └── Tra3DLayer.ts         # 台鐵 3D 圖層
│   ├── hooks/                    # React Hooks
│   │   ├── useData.ts            # 台北捷運資料載入
│   │   ├── useThsrData.ts        # 高鐵資料載入
│   │   ├── useKrtcData.ts        # 高雄捷運資料載入
│   │   ├── useKlrtData.ts        # 高雄輕軌資料載入
│   │   ├── useTmrtData.ts        # 台中捷運資料載入
│   │   ├── useTraData.ts         # 台鐵資料載入
│   │   └── useAllTrains.ts       # 全系統列車整合
│   ├── constants/                # 常數定義
│   │   ├── lineInfo.ts           # 台北捷運路線資訊
│   │   ├── thsrInfo.ts           # 高鐵路線資訊
│   │   ├── krtcInfo.ts           # 高雄捷運路線資訊
│   │   ├── klrtInfo.ts           # 高雄輕軌路線資訊
│   │   ├── tmrtInfo.ts           # 台中捷運路線資訊
│   │   └── traInfo.ts            # 台鐵路線資訊
│   └── types/                    # TypeScript 型別
├── public/data/                  # 靜態資料
│   ├── trtc/                     # 台北捷運資料
│   │   ├── tracks/               # 軌道 GeoJSON
│   │   ├── schedules/            # 時刻表 JSON
│   │   ├── station_progress.json # 車站進度對照表
│   │   └── *_stations.geojson    # 各路線車站資料
│   ├── thsr/                     # 高鐵資料
│   │   ├── tracks/
│   │   ├── schedules/
│   │   ├── stations/
│   │   └── station_progress.json
│   ├── krtc/                     # 高雄捷運資料
│   │   ├── tracks/
│   │   ├── schedules/
│   │   ├── stations/
│   │   └── station_progress.json
│   ├── klrt/                     # 高雄輕軌資料
│   │   ├── tracks/
│   │   ├── schedules/
│   │   ├── stations/
│   │   └── station_progress.json
│   ├── tmrt/                     # 台中捷運資料
│   │   ├── tracks/
│   │   ├── schedules/
│   │   ├── stations/
│   │   └── station_progress.json
│   └── tra/                      # 台鐵資料
│       ├── tracks_golden/        # 精修軌道（顯示用）
│       ├── tracks_official/      # 官方軌道（顯示用）
│       ├── tracks_od/            # O-D 計算用軌道
│       │   └── od_station_progress.json
│       ├── schedules_real/       # 時刻表
│       │   └── master_schedule.json
│       ├── stations.geojson      # 原始車站座標
│       └── stations_snapped.geojson  # 對齊後車站座標
├── data/                         # 原始 TDX 資料
│   ├── tdx_metro_test/           # 台北捷運原始資料
│   ├── tdx_klrt/                 # 高雄輕軌原始資料
│   └── ...
├── scripts/                      # 資料處理腳本
│   ├── fetch_*.py                # 取得各系統 TDX 資料
│   ├── build_*.py                # 建立各系統軌道/時刻表
│   └── tra/                      # 台鐵專用腳本
│       ├── build_*_od_tracks.py  # 建立 O-D 軌道
│       ├── calc_progress.py      # 計算站點進度
│       └── prepare_real_timetable/  # 時刻表轉換
└── docs/                         # 技術文件
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

### 環狀線特殊處理 (高雄輕軌)

高雄輕軌是環狀線，起點和終點都是 C1 籬仔內站：

```
順時針 (KLRT-C-0): C1 → C2 → ... → C37 → C1
逆時針 (KLRT-C-1): C1 → C37 → ... → C2 → C1
```

終點站的進度值設為 1.0（而非回到 0.0），確保列車正確停在軌道末端。

## 碰撞偵測系統

### 問題背景

淡水信義線有多種營運模式共用同一實體軌道，當兩輛不同路線的列車在同一物理位置時，需要視覺化區分。

### 視覺效果

- **正常行駛**：白色邊框圓點
- **停站中**：較大圓點 + 脈動效果
- **碰撞中**：黃色邊框 + 警示光暈 + 位置偏移

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

## 環境變數

```env
VITE_MAPBOX_TOKEN=your_mapbox_token_here
```

取得 Mapbox Token: https://account.mapbox.com/access-tokens/

## 技術棧

| 層級 | 技術 |
|------|------|
| 前端 | React 19.2 + TypeScript 5.9 + Vite 7.2 |
| 地圖 | Mapbox GL JS 3.17 |
| 3D 渲染 | Three.js 0.182 |
| 軌道資料 | TDX 運輸資料流通服務 |
| 時刻表資料 | Eric Yu 開源專案 + TDX API |

## 開發歷程

### 2026-02-28
- 🔧 新增蘇澳支線軌道（手繪 36 點 + 精修合併）
  - 蘇澳站從北迴線上移至正確的支線位置
  - 新增 YL-BD-SX / YL-SL-SX 截斷軌道（供通過蘇澳新的列車使用）
  - 修正 15 班蘇澳相關列車的 OD 軌道指派
  - 更新 stations_snapped.geojson 蘇澳站座標
- 🔧 移除彰化三角環迴路，修正 112 條 OD 軌道
- 🔧 重新計算全部 206 條軌道的 station_progress

### 2026-02-03
- 🔧 修正台中捷運 (TMRT) 站點 ID 與台北捷運綠線衝突問題
  - 將 TMRT 所有站點 ID 加上 `T` 前綴（G0→TG0, G10→TG10）
  - 修復「豐樂公園→新店」「南屯」等錯誤顯示
- 🔧 修正高雄捷運 (KRTC) 站點 ID 與台北捷運橘線衝突問題
  - 將 KRTC 所有站點 ID 加上 `K` 前綴（O1→KO1, R3→KR3）
  - 修復「鳳山→南勢角」等錯誤顯示
- 🔧 修正台鐵彰化區域軌道跳躍問題
  - 新增手繪軌道 `CH-north-draft.geojson` 修復 87 條 OD 軌道
  - 更新顯示軌道 WL-M/WL-S 正確連接彰化站
- 🔧 新增新烏日站 (3340) 到 stations_snapped 和 108 條軌道的 station_progress
- 🔧 重新計算 94 條經過彰化的軌道 station_progress

### 2026-01-31
- ✨ 新增台鐵跨線列車動態路線顯示（根據當前站點顯示所在路線，如「屏東線 (南下)」）
- ✨ 新增時刻表資料來源說明區塊（在說明與公告 Modal 中）
- ✨ 城市選擇器新增花蓮 (HUN) 與台東 (TTT)
- 🔧 修正台鐵方向顯示邏輯（宜蘭線/北迴線/臺東線的北上南下判斷）
- 🔧 更新使用說明，新增 TRA 相關說明

### 2026-01-28
- ✨ 台鐵 Phase 2 完成 - 宜蘭線/北迴線 O-D 軌道
- 🔧 改進軌道配對算法，加入中間站單調性檢查
- 🔧 修正 station_progress normalization 造成的 5-6km 位置偏差

### 2026-01-27
- ✨ 台鐵真實時刻表上線（初期 928 班，後更新至 992 班）
- ✨ 新增 6 條特殊軌道，覆蓋率提升至 99.8%

### 2026-01-24
- ✨ 台鐵 Phase 0-1 完成 - 覆蓋 96.3% 班次
- 🔧 修正平溪線方向顯示問題

### 2026-01-08
- ✨ 新增平溪線 64 班列車
- 🔧 改進 2D 跟隨模式，列車固定在畫面中央

### 2026-01-04
- 🎨 品牌更新為 Mini Taiwan
- ✨ 列車統計改為各系統分開顯示 (TPE/KHH/LRT/TXG/HSR/TRA)
- ✨ 列車數趨勢圖改為所有系統總和（排除纜車）
- 🔧 修正全線軌道折角問題（KLRT/KRTC/TRTC 共 118 站）

### 2026-01-03
- ✨ 新增台中捷運 (TMRT) 完整支援
  - 綠線 (G)：北屯總站 ↔ 高鐵台中站
  - 18 站時刻表模擬
  - 2D/3D 模式列車顯示

### 2026-01-02
- ✨ 新增高雄輕軌 (KLRT) 完整支援
  - 38 站環狀線（C1-C37 + C21A）
  - 順時針/逆時針雙向營運
  - 2D/3D 模式列車顯示
- ✨ 新增高雄捷運 (KRTC) 完整支援
  - 紅線 (R)：小港 ↔ 岡山
  - 橘線 (O)：哈瑪星 ↔ 大寮
- ✨ 新增台灣高鐵 (THSR) 完整支援
  - 南港 ↔ 左營
  - 12 站時刻表模擬
- ✨ 新增城市選擇器 (TPE / TXG / KHH)
- 🔧 重整資料夾結構
  - `public/data/` → `public/data/trtc/`
  - `public/data-klrt/` → `public/data/klrt/`
  - `public/data-krtc/` → `public/data/krtc/`
  - `public/data-thsr/` → `public/data/thsr/`

### 2026-01-01
- ✨ 新增 2D / 3D 模式切換功能，3D 模式使用 Three.js 渲染立體列車
- ✨ 新增列車跟隨模式，點擊列車可自動追蹤位置並顯示詳細資訊
- ✨ 新增日夜主題切換功能（Auto / Dawn / Day / Dusk / Night / Dark）
- ✨ 新增貓空纜車 (MK) 支援，含三段式顯示控制
- ✨ 新增 MRT / Cable 分類篩選器
- ✨ 所有 UI 面板支援主題自動切換（明/暗色配合地圖主題）
- ✨ 軌道圖層加入 emissive-strength，夜間模式保持明亮
- 🎨 新增列車數量趨勢直方圖
- 🎨 優化 3D 跟隨模式視角控制，允許自由旋轉
- 🐛 修正地圖樣式切換後圖層消失問題
- 🐛 修正啟動時地圖樣式閃爍問題
- ⚡ 優化 3D 模式效能（材質共用、節流渲染）

### 2025-12-31
- ✨ 新增新北環狀線 (Y) 完整實作
- ✨ 新增桃園機場捷運 (A) - 支援普通車、基本直達車、加班直達車三種營運模式
- ✨ 新增安坑輕軌 (K) 與淡海輕軌 (V)
- ✨ 新增文湖線 (BR) 完整實作
- 🐛 修正機場捷運直達車時間（根據官方時刻表校準為 39 分鐘）
- 🐛 修正 station_progress 車站對齊問題

### 2025-12-30
- ✨ 新增中和新蘆線 (O) 模擬
- ✨ 新增松山新店線 (G) 含小碧潭支線
- ✨ 新增板南線 (BL) 模擬
- ✨ 新增 UI 增強功能（路線篩選、時間控制優化）
- 🐛 修正多條路線軌道校準問題
- 🐛 排除不同線路的碰撞檢測

### 2025-12-29
- ✨ 新增首班車專用軌道解決中途站出發問題
- ✨ 新增延長日時間軸 (06:00 ~ 隔日 01:30)
- ✨ UI 優化 - 速度控制、圖例、時間軸調整
- 🐛 修正首班車軌道座標對齊問題

### 專案初期
- 🎉 使用 Eric Yu 開源時刻表資料
- 🎉 淡水信義線 (R) 基礎實作
- 🎉 整合 Mapbox GL JS 地圖視覺化

## 授權

MIT License
