# TRA 真實時刻表實作計畫

> 建立時間：2026-01-25
> 狀態：規劃中

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

**結論**：現有軌道可支援所有路線組合，新的 O-D 軌道可透過「從現有軌道擷取子區段」產生。

---

## Phase 1：O-D 軌道精細化

### 1.1 確認資料來源
- [ ] 確認 TDX API 時刻表日期（目前 2026-01-13）
- [ ] 決定是否使用更新的時刻表資料
- [ ] 確認 TDX API 存取權限

### 1.2 建立軌道擷取機制
- [ ] 建立腳本 `extract_od_segment.py`
  - 輸入：起站 ID、迄站 ID、基礎軌道
  - 輸出：新的 O-D 軌道 GeoJSON + station_progress
- [ ] 支援跨路線軌道合併

### 1.3 按路線組合處理

| 優先級 | 路線組合 | O-D 組合數 | 班次數 | 處理方式 |
|--------|----------|------------|--------|----------|
| P1 | WL only | 132 | 323 | 從 WL-N/M/C/S 擷取 |
| P2 | KL+WL | 30 | 124 | 從 WL-N + KL 擷取 |
| P3 | SH+WL | 8 | 73 | 從 WL-S + SH 擷取 |
| P4 | WL+YL | 39 | 73 | 從 WL-N + YL 擷取 |
| P5 | LJ+NW+WL | 2 | 70 | 已有 (六家線) |
| P6 | BH+WL+YL | 15 | 46 | 從 YL+BH 擷取 |
| P7 | NW+WL | 5 | 43 | 從 WL-N + NW 擷取 |
| P8 | 其他 | 57 | 176 | 個別處理 |

### 1.4 預計產出
- 建立 `tracks_od/` 下新增約 50-80 條細分軌道
- 更新 `od_station_progress.json`

---

## Phase 2：車種與停靠站配置

### 2.1 車種資料結構

```typescript
// src/constants/traTrainTypes.ts
export interface TraTrainType {
  id: string;           // 'TC', 'PP', 'TZ', 'CK', 'FX', 'LC'
  name: string;         // '自強', '普悠瑪', '太魯閣', '區間快', '復興', '區間'
  color: string;        // 列車顏色 (用於 3D 渲染)
  priority: number;     // 顯示優先級 (越高越優先)
}
```

### 2.2 車種清單

| 代碼 | 車種 | 班次數 | 顏色建議 | 特性 |
|------|------|--------|----------|------|
| TC | 自強(3000) | ~50 | 橘色 | EMU3000，只停大站 |
| PP | 普悠瑪 | ~30 | 紅色 | 傾斜式列車 |
| TZ | 太魯閣 | ~30 | 紅色 | 傾斜式列車 |
| CK | 區間快 | ~100 | 藍色 | 停較多站 |
| FX | 復興 | ~400 | 藍色 | 各站停靠 |
| LC | 區間 | ~200 | 藍色 | 各站停靠 |
| OTHER | 其他 | ~100 | 灰色 | 臨時車、觀光列車 |

### 2.3 停靠站規則
- [ ] 建立 `traStopPatterns.ts`：各車種停靠站清單
- [ ] 根據 TDX 時刻表解析每班車的實際停靠站
- [ ] 計算站間行駛時間（依車種調整）

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
- [ ] 建立 `scripts/tra/convert_tdx_timetable.py`
- [ ] 自動對應 O-D 軌道（根據起迄站匹配）
- [ ] 轉換時間為相對秒數
- [ ] 驗證站點存在於 station_progress

### 3.4 時刻表檔案結構

```
schedules_od/
├── by_train_type/          # 按車種分類
│   ├── TC.json             # 所有自強號
│   ├── PP.json             # 所有普悠瑪
│   └── ...
├── by_od/                  # 按 O-D 分類 (現有結構)
│   ├── YL-SL-HL-0.json
│   └── ...
└── master_schedule.json    # 完整時刻表索引
```

---

## Phase 4：驗證與調整

### 4.1 自動驗證腳本
- [ ] `validate_schedule_stations.py`：檢查時刻表站點是否存在於軌道
- [ ] `validate_travel_time.py`：檢查站間時間是否合理
- [ ] `detect_train_collision.py`：檢查同軌道列車是否重疊

### 4.2 視覺驗證
- [ ] 在地圖上測試各車種列車運行
- [ ] 確認停站位置正確
- [ ] 確認列車顏色區分
- [ ] 測試高密度時段（如早晨尖峰）

---

## Phase 5：前端整合

### 5.1 TraTrainEngine 更新
- [ ] 支援車種識別
- [ ] 根據車種設定列車顏色
- [ ] 優化大量列車渲染效能

### 5.2 UI 更新
- [ ] TrainInfoPanel 顯示車種資訊
- [ ] 新增車種篩選功能（可選）
- [ ] 新增時刻表查詢功能（可選）

---

## 所需 TDX API

| API 端點 | 用途 | 備註 |
|----------|------|------|
| `/v2/Rail/TRA/GeneralTrainTimetable/Today` | 當日所有列車時刻表 | 主要資料來源 |
| `/v2/Rail/TRA/DailyTrainTimetable/Today` | 當日實際運行時刻表 | 含臨時調整 |
| `/v2/Rail/TRA/Station` | 車站基本資料 | 已有備份 |
| `/v2/Rail/TRA/Shape` | 軌道形狀 | 已有備份 |

---

## 預計工具/Agent

### 建議建立的工具

| 工具名稱 | 用途 |
|----------|------|
| `extract_od_segment.py` | 從現有軌道擷取子區段 |
| `convert_tdx_timetable.py` | TDX 時刻表轉換 |
| `validate_schedule.py` | 時刻表驗證 |
| `batch_generate_od.py` | 批次產生 O-D 軌道 |

### 建議建立的 Agent

| Agent 名稱 | 用途 |
|------------|------|
| `timetable-converter` | 自動化時刻表轉換流程 |
| `od-track-generator` | 自動化 O-D 軌道產生 |

---

## 里程碑

| 里程碑 | 內容 | 預計完成條件 |
|--------|------|--------------|
| M1 | Phase 1 完成 | 所有 288 O-D 軌道可用 |
| M2 | Phase 2 完成 | 車種資料結構定義完成 |
| M3 | Phase 3 完成 | 928 班時刻表轉換完成 |
| M4 | Phase 4 完成 | 驗證通過，列車正常運行 |
| M5 | Phase 5 完成 | 前端整合完成 |

---

## 參考文件

- `od_complete_analysis.json`：O-D 組合分析資料
- `OD_COMPLETE_LIST.md`：O-D 組合清單 (Markdown)
- `TRACKS_STATUS.md`：軌道狀態追蹤
- `STANDARD_WORKFLOW.md`：軌道建立標準流程

---

## 更新紀錄

### 2026-01-25
- 初版計畫建立
- 完成現況分析
- 定義 5 個 Phase
