# Mini Taipei V3 - 列車追蹤精確度改善計畫

## 專案目標

改善列車模擬的精確度，解決「追車」與「列車重疊」問題，使用 TDX 官方 API 資料產生更貼近實際營運的時刻表。

---

## 問題診斷

### 現狀問題

| 問題 | 原因 | 影響 |
|------|------|------|
| 同方向列車追車 | TrainEngine 使用線性插值，忽略停站時間 | 前車應停站但繼續滑行，被後車追上 |
| 不同路線列車重疊 | R-1/R-2 排程獨立產生，無協調機制 | 共用區段出現重疊 |
| 停站時間不準確 | 假設固定 40 秒 | 實際 23-37 秒不等 |
| 站間時間不準確 | 假設平均分配 | 實際 60-175 秒不等 |

### 資料來源比較

| 來源 | 站間時間 | 停站時間 | 精確度 |
|------|----------|----------|--------|
| **目前** (假設) | 平均分配 | 固定 40 秒 | ⭐ |
| **S2STravelTime API** | 精確到秒 | 精確到秒 | ⭐⭐⭐⭐⭐ |

---

## 實作架構

```
┌─────────────────────────────────────────────────────────────────┐
│                        資料流架構                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TDX API                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ S2STravelTime   │  │ Frequency       │  │ StationTimeTable│  │
│  │ (站間運行時間)   │  │ (班距資料)       │  │ (參考驗證)      │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │            │
│           ▼                    ▼                    ▼            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │           02_generate_schedules.py (P0)                     ││
│  │  - 使用精確站間時間                                          ││
│  │  - 使用精確停站時間                                          ││
│  │  - 產生協調後的發車時刻 (P3)                                 ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │           schedules/*.json                                  ││
│  │  {                                                          ││
│  │    "departures": [{                                         ││
│  │      "stations": [                                          ││
│  │        { "station_id": "R02", "arrival": 0, "departure": 25}││
│  │        { "station_id": "R03", "arrival": 118, "departure":143}│
│  │      ]                                                      ││
│  │    }]                                                       ││
│  │  }                                                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │           TrainEngine.ts (P1)                               ││
│  │  - 分段插值 (不再是線性)                                     ││
│  │  - 停站時列車靜止                                           ││
│  │  - 精確位置計算                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │           Map.tsx / App.tsx (P2)                            ││
│  │  - R-1 主線紅色                                             ││
│  │  - R-2 共用區段透明                                         ││
│  │  - 視覺層級處理                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## P0: 精確時刻表產生

### 目標
使用 TDX S2STravelTime API 資料，產生精確的站間運行時間與停站時間。

### 任務清單

#### P0-1: 下載 S2STravelTime API 資料
```
檔案: data_collector/scripts/00_fetch_s2s_travel_time.py
輸出: data_collector/raw_data/trtc_s2s_travel_time.json
```

**API 端點:**
```
GET https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/S2STravelTime/TRTC
```

**回傳格式:**
```json
{
  "RouteID": "R-1",
  "TravelTimes": [
    {
      "FromStationID": "R28",
      "ToStationID": "R27",
      "RunTime": 175,    // 運行秒數
      "StopTime": 0      // 停站秒數 (起站為 0)
    }
  ]
}
```

#### P0-2: 重寫時刻表產生腳本
```
檔案: data_collector/scripts/02_generate_schedules.py
修改:
  - 讀取 S2STravelTime 資料
  - 用精確的 RunTime + StopTime 計算各站時刻
  - 移除「平均分配」假設
```

**新的計算邏輯:**
```python
# 舊邏輯 (不準確)
segment_time = total_travel_time / num_segments  # 平均分配

# 新邏輯 (精確)
for segment in s2s_travel_times:
    arrival = current_time + segment['RunTime']
    departure = arrival + segment['StopTime']
    current_time = departure
```

#### P0-3: 產生並驗證新時刻表
```
輸出: data_collector/output/schedules/*.json
驗證: 比對 TDX StationTimeTable API 的實際發車時刻
```

### 驗收標準
- [ ] 時刻表使用精確的站間運行時間 (60-175秒不等)
- [ ] 時刻表使用精確的停站時間 (23-37秒不等)
- [ ] 全程時間與 TDX 官方資料誤差 < 2%

---

## P1: TrainEngine 分段插值

### 目標
修改列車引擎，使用時刻表中的詳細站點時間進行分段插值，而非簡單線性插值。

### 任務清單

#### P1-1: 修改 TrainEngine 核心邏輯
```
檔案: viewer/src/engines/TrainEngine.ts
修改: update() 方法
```

**現有邏輯 (問題):**
```typescript
// 線性插值 - 忽略停站
progress = (currentTime - departureTime) / totalTravelTime;
position = interpolateOnLineString(coords, progress);
```

**新邏輯 (分段插值):**
```typescript
// 1. 找到當前所在區段
const segment = findCurrentSegment(stations, elapsedTime);

// 2. 判斷狀態: 停站中 or 行駛中
if (segment.isAtStation) {
  // 停站中 - 位置固定在車站
  position = stationCoordinates[segment.stationIndex];
  status = 'stopped';
} else {
  // 行駛中 - 在兩站間插值
  const segmentProgress = calculateSegmentProgress(segment, elapsedTime);
  position = interpolateBetweenStations(
    coords,
    segment.fromStationIndex,
    segment.toStationIndex,
    segmentProgress
  );
  status = 'running';
}
```

#### P1-2: 實作停站狀態顯示
```
檔案: viewer/src/engines/TrainEngine.ts
新增: Train interface 加入 status 欄位
```

**Train 介面更新:**
```typescript
export interface Train {
  trainId: string;
  trackId: string;
  departureTime: number;
  totalTravelTime: number;
  status: 'waiting' | 'running' | 'stopped' | 'arrived';  // 新增 'stopped'
  progress: number;
  position: [number, number];
  currentStation?: string;  // 新增: 停靠中的車站
}
```

### 驗收標準
- [ ] 列車在車站停靠時位置固定
- [ ] 列車在站間行駛時平滑移動
- [ ] 不再出現同方向追車現象

---

## P2: 視覺優化 (軌道透明化)

### 目標
R-2 路線在與 R-1 共用的區段改為透明，避免視覺上的軌道重疊。

### 任務清單

#### P2-1: 修改軌道樣式
```
檔案: viewer/src/App.tsx
修改: TRACK_COLORS 或軌道圖層樣式
```

**方案 A: 透明度調整**
```typescript
const TRACK_COLORS: Record<string, string> = {
  'R-1-0': '#d90023',      // 主線紅色
  'R-1-1': '#d90023',
  'R-2-0': 'transparent',  // 共用區段透明
  'R-2-1': 'transparent',
  'R-3-0': '#ff6b6b',      // 新北投支線保持可見
  'R-3-1': '#ff6b6b',
};
```

**方案 B: 圖層順序 + 透明度**
```typescript
// R-2 軌道半透明，讓列車可見但軌道不搶眼
paint: {
  'line-color': '#d90023',
  'line-width': 2,
  'line-opacity': 0.3,  // 30% 透明度
}
```

### 驗收標準
- [ ] R-1 主線清晰可見
- [ ] R-2 共用區段不造成視覺干擾
- [ ] R-2 列車仍可見且位置正確

---

## P3: 排程協調

### 目標
確保 R-1 和 R-2 在共用區段的發車時刻有適當間隔，避免物理上不可能的重疊。

### 任務清單

#### P3-1: 分析排程衝突
```
工具: Python 腳本分析
輸出: 衝突報告
```

**衝突檢測邏輯:**
```python
# 對於共用區段的每個車站
for station in shared_stations:  # R05-R22
    # 收集所有路線在該站的到達/離開時間
    all_times = get_all_train_times(station, ['R-1-0', 'R-1-1', 'R-2-0', 'R-2-1'])

    # 檢查時間衝突 (同方向車輛間隔 < 最小安全間隔)
    MIN_HEADWAY = 90  # 秒
    for i, time1 in enumerate(all_times):
        for time2 in all_times[i+1:]:
            if same_direction(time1, time2) and abs(time1 - time2) < MIN_HEADWAY:
                report_conflict(station, time1, time2)
```

#### P3-2: 實作協調機制 (如需要)
```
檔案: data_collector/scripts/02_generate_schedules.py
新增: 發車時刻調整邏輯
```

**協調策略:**
```python
# 策略 1: 錯開發車 (推薦)
# R-1 在整分發車, R-2 在半分發車
r1_departures = generate_departures(route='R-1', offset=0)
r2_departures = generate_departures(route='R-2', offset=30)  # 錯開 30 秒

# 策略 2: 動態調整
# 檢測到衝突時，延後較短路線的發車
if has_conflict(r1_train, r2_train):
    r2_train.departure_time += MIN_HEADWAY
```

### 驗收標準
- [ ] 共用區段同方向列車間隔 >= 90 秒
- [ ] 無物理上不可能的列車重疊
- [ ] 維持合理的班距 (不因協調而過度延誤)

---

## 測試計畫

### 單元測試

| 測試項目 | 測試方法 | 預期結果 |
|----------|----------|----------|
| S2STravelTime 資料完整性 | 檢查所有站間都有資料 | 紅線 27 站，26 個區間 |
| 時刻表站間時間 | 比對 API 原始資料 | 完全一致 |
| 時刻表停站時間 | 比對 API 原始資料 | 完全一致 |
| 全程時間 | 比對官方時刻表 | 誤差 < 2% |

### 整合測試

| 測試項目 | 測試方法 | 預期結果 |
|----------|----------|----------|
| 停站行為 | 在 8:00 觀察台北車站 | 列車停靠 35 秒後離站 |
| 追車問題 | 高速播放觀察 | 同方向列車不重疊 |
| 站間移動 | 觀察中正紀念堂→東門 | 耗時約 175 秒 (最長區間) |

### 視覺測試

| 測試項目 | 測試方法 | 預期結果 |
|----------|----------|----------|
| 08:27 台大醫院站 | 定位到該時間點 | 僅一班列車在站 |
| R-2 軌道顯示 | 檢視共用區段 | 不遮蔽 R-1 主線 |
| 列車平滑度 | 觀察列車移動 | 進出站無跳動 |

### 效能測試

| 測試項目 | 測試方法 | 預期結果 |
|----------|----------|----------|
| 高速播放 (300x) | 長時間播放 | FPS 維持 > 30 |
| 列車數量峰值 | 觀察早上 8:00-9:00 | 正常顯示所有列車 |

---

## 檔案變更清單

### 新增檔案
```
data_collector/scripts/00_fetch_s2s_travel_time.py  # P0-1
data_collector/raw_data/trtc_s2s_travel_time.json   # P0-1 輸出
```

### 修改檔案
```
data_collector/scripts/02_generate_schedules.py     # P0-2
data_collector/output/schedules/*.json              # P0-3 輸出
viewer/src/engines/TrainEngine.ts                   # P1-1, P1-2
viewer/src/App.tsx                                  # P2-1
```

---

## 時程估計

| 階段 | 預估時間 | 依賴 |
|------|----------|------|
| P0 (精確時刻表) | 1-2 小時 | 無 |
| P1 (分段插值) | 2-3 小時 | P0 完成 |
| P2 (視覺優化) | 30 分鐘 | 可獨立進行 |
| P3 (排程協調) | 1-2 小時 | P0 完成後評估是否需要 |
| 測試驗證 | 1 小時 | 全部完成 |

**總計: 5-8 小時**

---

## 風險與備案

| 風險 | 影響 | 備案 |
|------|------|------|
| S2STravelTime 資料不完整 | 無法產生精確時刻表 | 使用 StationTimeTable 反推 |
| 分段插值效能問題 | 高速播放卡頓 | 預計算站點座標，減少即時運算 |
| 協調後班距過大 | 模擬不真實 | 接受少量衝突，標記為「調度中」|

---

## 執行順序

```
1. P0-1 → 2. P0-2 → 3. P0-3 → 4. P1-1 → 5. P1-2 → 6. 測試
                                              ↓
                                    (如仍有衝突) → 7. P3-1 → 8. P3-2
                                              ↓
                              (可並行) → P2-1 (視覺優化)
```

準備好開始執行了嗎？
