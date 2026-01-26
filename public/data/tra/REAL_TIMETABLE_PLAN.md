# TRA 真實時刻表實作計畫

> 建立時間：2026-01-25
> 最後更新：2026-01-26
> 狀態：準備執行

---

## 目標

將目前的測試時刻表替換為 TDX 真實時刻表，實現 928 班列車在地圖上正確運行。

---

## 現況分析

| 項目 | 數量 | 備註 |
|------|------|------|
| 現有 O-D 軌道 | 46 條 | 涵蓋主要路線骨幹 |
| 實際 O-D 組合 | 288 組 | 來自 TDX API |
| 總班次數 | 928 班 | 定期車次 |
| 資料來源日期 | 2026-01-13 | `od_complete_analysis.json` |
| 現有腳本 | 33 個 | 可重用大部分邏輯 |

**結論**：現有軌道可支援所有路線組合，新的 O-D 軌道可透過「從現有軌道擷取子區段」產生。

---

## 系統設計確認

### 列車位置計算機制

```
時刻表 stations[] ──→ 只包含「實際停靠站」
                          ↓
stationProgress{} ──→ 包含「軌道上所有車站」的 progress 值
                          ↓
TraTrainEngine ─────→ 在兩個停靠站之間「沿軌道連續移動」
```

### 自強號與區間車的相容性

- ✅ 兩者使用相同的 O-D 軌道和 stationProgress
- ✅ 差別只在時刻表的 stations 陣列內容
- ✅ 自強號會經過中間站位置，但不停留
- ✅ 速度根據站間時間自動調整

### 關鍵條件

- stationProgress 必須包含時刻表中所有可能的停靠站
- TDX 時刻表的停靠站都是合法車站，不會有問題

---

## Phase 0：資料準備

### 0.1 目標
為後續步驟建立完整的資料基礎。

### 0.2 腳本清單

```
scripts/tra/prepare_real_timetable/
├── 01_fetch_tdx_timetable.py    # 下載最新 TDX 時刻表
├── 02_build_station_mapping.py  # 建立車站 ID ↔ 名稱對照表
├── 03_build_od_mapping.py       # 建立 O-D → 基礎軌道對照表
└── 04_analyze_missing_od.py     # 分析缺少的 O-D 軌道
```

### 0.3 產出檔案

| 檔案 | 說明 |
|------|------|
| `data/tdx_timetable_YYYYMMDD.json` | TDX 原始時刻表 |
| `data/station_mapping.json` | 車站對照表 |
| `data/od_to_base_track.json` | O-D → 基礎軌道對照 |
| `data/missing_od_tracks.json` | 需要新建的 O-D 軌道清單 |

### 0.4 檢查項目

- [x] 確認 TDX API Key 有效 (2026-01-26)
- [x] 測試 `/v3/Rail/TRA/GeneralTrainTimetable` 端點 (2026-01-26)
- [x] 下載最新時刻表資料 (928 班列車，6.21 MB)
- [x] 建立車站對照表 (233 個車站)
- [x] 建立 O-D → 基礎軌道對照表 (288 組)
- [x] 分析 O-D 軌道覆蓋情況

### 0.5 Phase 0 執行結果 (2026-01-26)

| 項目 | 數量 | 說明 |
|------|------|------|
| 總班次 | 928 | TDX GeneralTrainTimetable |
| 總 O-D 組合 | 288 | 起迄站組合 |
| 已覆蓋 | 117 (53.2%) | 494 班列車 |
| 需新建 | 171 (46.8%) | 434 班列車 |

**主要缺口**：
- WL-S (西部幹線南段)：70 O-D，183 班
- WL-ZN-SL (樹林-竹南)：26 O-D，102 班
- WL-C (海線)：24 O-D，61 班
- WL-N (北段)：29 O-D，55 班

---

## Phase 1：O-D 軌道精細化

### 1.1 目標
從現有 46 條軌道擴展到支援 288 組 O-D 組合。

### 1.2 核心工具

```python
# scripts/tra/extract_od_segment.py
# 輸入：起站 ID、迄站 ID、基礎軌道清單
# 輸出：新的 O-D 軌道 GeoJSON + station_progress
```

### 1.3 按優先級批次處理

| 批次 | 路線組合 | O-D 數 | 班次數 | 處理腳本 |
|------|----------|--------|--------|----------|
| B1 | WL only | 132 | 323 | `batch_wl_od.py` |
| B2 | KL+WL | 30 | 124 | `batch_kl_wl_od.py` |
| B3 | SH+WL | 8 | 73 | `batch_sh_wl_od.py` |
| B4 | WL+YL | 39 | 73 | `batch_wl_yl_od.py` |
| B5 | LJ+NW+WL | 2 | 70 | 已有 (六家線) |
| B6 | BH+WL+YL | 15 | 46 | `batch_bh_wl_yl_od.py` |
| B7 | NW+WL | 5 | 43 | `batch_nw_wl_od.py` |
| B8 | 其他 | 57 | 176 | `batch_others_od.py` |

### 1.4 預計產出

- `tracks_od/` 下新增約 50-80 條細分軌道
- 更新 `od_station_progress.json`

### 1.5 驗證標準

- 每條軌道座標點 > 50
- station_progress 起點 = 0.0, 終點 = 1.0
- 所有途經車站都有 progress 值

### 1.6 Phase 1 執行結果 (2026-01-26)

**建立的工具**：
- `scripts/tra/prepare_real_timetable/extract_od_segment.py` - 擷取子區段
- `scripts/tra/prepare_real_timetable/merge_tracks.py` - 合併多條軌道
- `scripts/tra/prepare_real_timetable/batch_generate_od.py` - 批次產生

**骨幹軌道策略**：
建立 27 條骨幹軌道（合併多條基礎軌道），然後從骨幹軌道擷取各 O-D 子區段。

**執行結果**：
| 項目 | 數量 |
|------|------|
| 原始軌道 | 46 條 |
| 新增骨幹軌道 | 27 條 |
| 新增 O-D 軌道 | 153 條 |
| **總計** | **226 條** |

**覆蓋情況**：
| 狀態 | 班次 | 比例 |
|------|------|------|
| ✅ 已覆蓋 | 894 | 96.3% |
| ❌ 未覆蓋 | 34 | 3.7% |

**未覆蓋原因**（共 18 O-D，34 班）：
1. **山海線互轉** (15班)：海線和山線在彰化以北無法直接互轉
2. **集集線** (4班)：彰化↔車埕、彰化↔水里
3. **成追線** (2班)：涉及新烏日站

---

## Phase 2：車種配置 (簡化版)

### 2.1 目標
定義車種顏色，用於 3D 渲染區分。

### 2.2 車種定義

```typescript
// src/constants/traTrainTypes.ts
export const TRA_TRAIN_TYPES: Record<string, { name: string; color: string }> = {
  'TC': { name: '自強(3000)', color: '#FF6B00' },  // 橘色 - EMU3000
  'PP': { name: '普悠瑪', color: '#E53935' },      // 紅色 - 傾斜式
  'TZ': { name: '太魯閣', color: '#E53935' },      // 紅色 - 傾斜式
  'CK': { name: '區間快', color: '#1976D2' },      // 深藍 - 快車
  'FX': { name: '復興', color: '#42A5F5' },        // 淺藍 - 各站停
  'LC': { name: '區間', color: '#42A5F5' },        // 淺藍 - 各站停
  'OTHER': { name: '其他', color: '#9E9E9E' },     // 灰色 - 臨時車
};
```

### 2.3 車種代碼解析規則

| TDX TrainTypeName | 代碼 |
|-------------------|------|
| 自強(3000) | TC |
| 普悠瑪 | PP |
| 太魯閣 | TZ |
| 區間快 | CK |
| 復興 | FX |
| 區間 | LC |
| 其他 | OTHER |

### 2.4 不需要的項目 (已簡化)

- ~~各車種停靠站清單~~ → TDX 時刻表已包含
- ~~站間行駛時間計算~~ → TDX 時刻表已包含

---

## Phase 3：時刻表轉換

### 3.1 TDX 原始格式

```json
{
  "TrainNo": "110",
  "TrainTypeName": { "Zh_tw": "自強(3000)" },
  "StartingStationName": { "Zh_tw": "樹林" },
  "EndingStationName": { "Zh_tw": "花蓮" },
  "StopTimes": [
    {
      "StationID": "1040",
      "StationName": { "Zh_tw": "樹林" },
      "ArrivalTime": "06:00",
      "DepartureTime": "06:02"
    }
  ]
}
```

### 3.2 Mini Taiwan 格式

```json
{
  "train_id": "TC-110",
  "train_no": "110",
  "train_type": "自強(3000)",
  "train_type_code": "TC",
  "departure_time": "06:00:00",
  "od_track_id": "YL-SL-HL-0",
  "origin_station": "樹林",
  "destination_station": "花蓮",
  "total_travel_time": 7200,
  "stations": [
    {"station_id": "1040", "arrival": 0, "departure": 120},
    {"station_id": "1000", "arrival": 1500, "departure": 1620}
  ]
}
```

### 3.3 轉換腳本

```python
# scripts/tra/convert_tdx_timetable.py
# 功能：
# 1. 讀取 TDX 時刻表
# 2. 解析車種代碼
# 3. 匹配 O-D 軌道
# 4. 轉換時間為相對秒數
# 5. 產生 Mini Taiwan 格式
```

### 3.4 輸出結構

```
schedules_od/
├── master_schedule.json    # 索引檔：928 班車基本資訊
└── by_od/                  # 按 O-D 分類
    ├── WL-N-SL-KL-0.json
    └── ...
```

---

## Phase 4：驗證與調整

### 4.1 自動驗證腳本

| 腳本 | 用途 |
|------|------|
| `validate_schedule_stations.py` | 檢查時刻表站點是否存在於 stationProgress |
| `validate_travel_time.py` | 檢查站間時間是否合理 (> 0) |
| `validate_od_coverage.py` | 檢查所有時刻表都有對應的 O-D 軌道 |

### 4.2 視覺驗證

- [ ] 在地圖上測試各車種列車運行
- [ ] 確認停站位置正確
- [ ] 確認列車顏色區分
- [ ] 測試高密度時段（如早晨尖峰 07:00-09:00）

---

## Phase 5：前端整合

### 5.1 TraTrainEngine 更新

- [ ] 支援車種識別 (`train_type_code`)
- [ ] 根據車種設定列車顏色
- [ ] 優化大量列車渲染效能 (928 班)

### 5.2 UI 更新

- [ ] TrainInfoPanel 顯示車種資訊
- [ ] 新增車種篩選功能（可選）
- [ ] 新增時刻表查詢功能（可選）

---

## 時刻表替換流程

### 快速替換步驟

當需要更新時刻表時（如 2 月初更新），只需：

```bash
# 1. 下載新時刻表
python3 scripts/tra/prepare_real_timetable/01_fetch_tdx_timetable.py

# 2. 重新轉換（O-D 軌道不需重建）
python3 scripts/tra/convert_tdx_timetable.py

# 3. 驗證
python3 scripts/tra/validate_all.py
```

### 替換條件

- ✅ 新時刻表的停靠站都在現有 stationProgress 中 → 直接替換
- ⚠️ 新時刻表有新的 O-D 組合 → 需要先執行 Phase 1 新增軌道
- ⚠️ 新時刻表有新的車站 → 需要更新 stationProgress

---

## Agent 配置

### Agent 1: real-timetable-pipeline

**用途**：協調整個流程，追蹤進度

### Agent 2: od-batch-generator

**用途**：批次產生 O-D 軌道 (Phase 1)

### Agent 3: schedule-converter

**用途**：TDX 時刻表轉換 (Phase 3)

---

## 里程碑

| 里程碑 | 內容 | 完成條件 |
|--------|------|----------|
| M0 | Phase 0 完成 | 資料準備完成，對照表建立 |
| M1 | Phase 1 完成 | 所有 288 O-D 軌道可用 |
| M2 | Phase 2 完成 | 車種定義檔建立 |
| M3 | Phase 3 完成 | 928 班時刻表轉換完成 |
| M4 | Phase 4 完成 | 驗證通過，列車正常運行 |
| M5 | Phase 5 完成 | 前端整合完成 |

---

## 所需 TDX API

| API 端點 | 用途 | 備註 |
|----------|------|------|
| `/v2/Rail/TRA/GeneralTrainTimetable/Today` | 當日所有列車時刻表 | 主要資料來源 |
| `/v2/Rail/TRA/DailyTrainTimetable/Today` | 當日實際運行時刻表 | 含臨時調整 |
| `/v2/Rail/TRA/Station` | 車站基本資料 | 已有備份 |

---

## 參考文件

| 文件 | 說明 |
|------|------|
| `docs/OD_COMPLETE_LIST.md` | O-D 組合清單 |
| `TRACKS_STATUS.md` | 軌道狀態追蹤 |
| `STANDARD_WORKFLOW.md` | 軌道建立標準流程 |

---

## 更新紀錄

### 2026-01-26
- 簡化 Phase 2（車種配置）：移除不需要的停靠站規則
- 確認系統設計：自強號與區間車相容性
- 新增時刻表替換流程說明
- 新增 Agent 配置章節

### 2026-01-25
- 初版計畫建立
- 完成現況分析
- 定義 5 個 Phase
