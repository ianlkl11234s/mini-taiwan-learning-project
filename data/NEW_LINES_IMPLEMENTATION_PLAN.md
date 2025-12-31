# 新線路實作計畫

> 建立日期: 2025-12-31
> 狀態: 規劃中

---

## 核心策略：以 StationTimeTable 為主

**優先使用 StationTimeTable API**，因為：
- ✅ 包含實際發車時刻（非推算）
- ✅ 包含首班車從不同站出發的設定
- ✅ 包含平日/假日區分 (`ServiceDay.ServiceTag`)
- ✅ 包含直達車/普通車區分 (`TrainType`)

**資料篩選條件**：
- 使用 `ServiceDay.ServiceTag = '平日'` (週一至週五)
- 或 `ServiceDay.Monday = True AND ServiceDay.Saturday = False`

---

## TDX API 資料盤點結果

| 系統 | 代碼 | Station | Shape | S2STime | Frequency | FirstLast | **TimeTable** |
|------|------|---------|-------|---------|-----------|-----------|---------------|
| 安坑輕軌 | NTALRT | ✅ 9站 | ✅ 1條 | ❌ | ❌ | ❌ | **✅ 38筆** |
| 淡海輕軌 | NTDLRT | ✅ 14站 | ✅ 1條 | ❌ | ❌ | ❌ | **✅ 84筆** |
| 環狀線 | NTMC | ✅ 14站 | ✅ 1條 | ✅ 1筆 | ✅ 2筆 | ✅ 26筆 | **❌** |
| 桃園機捷 | TYMC | ✅ 22站 | ✅ 1條 | ✅ 4筆 | ✅ 1筆 | ✅ 160筆 | **✅ 128筆** |

---

## 實作優先順序（以 TimeTable 為主）

### 1. 🟢 安坑輕軌 (NTALRT) - 最簡單
- **TimeTable**: ✅ 38 筆（有實際時刻表）
- **站數**: 9 站 (K01-K09)
- **路線**: 單一路線 K-1
- **顏色**: `#8cc540` (草綠色)
- **實作方式**: 直接使用 StationTimeTable
- **預計工作量**: 2 小時

### 2. 🟢 淡海輕軌 (NTDLRT) - 簡單
- **TimeTable**: ✅ 84 筆（有實際時刻表）
- **站數**: 14 站 (V01-V11 綠山線, V26-V28 藍海線)
- **路線**: V-1 綠山線
- **顏色**: `#0ab4a6` (青綠色)
- **實作方式**: 直接使用 StationTimeTable
- **預計工作量**: 2 小時

### 3. 🟢 桃園機場捷運 (TYMC) - 中等
- **TimeTable**: ✅ 128 筆（有實際時刻表）
- **站數**: 22 站 (A1-A21)
- **路線**: A-1 普通車, A-2 直達車
- **顏色**: `#9e3a9e` (紫色)
- **實作方式**: 直接使用 StationTimeTable
- **複雜度**: 需處理 TrainType (1=普通, 2=直達)
- **預計工作量**: 3 小時

### 4. 🟡 環狀線 (NTMC) - 需推算
- **TimeTable**: ❌ 無
- **站數**: 14 站 (Y07-Y20)
- **路線**: Y-1
- **顏色**: `#fedb00` (黃色)
- **實作方式**: 用 Frequency + S2STravelTime 推算
- **預計工作量**: 3 小時

---

## StationTimeTable 資料結構

```json
{
  "RouteID": "K-1",
  "LineID": "K",
  "StationID": "K01",
  "StationName": {"Zh_tw": "雙城", "En": "Shuangcheng"},
  "Direction": 0,
  "DestinationStaionID": "K09",
  "ServiceDay": {
    "ServiceTag": "平日",
    "Monday": true, "Tuesday": true, "Wednesday": true,
    "Thursday": true, "Friday": true,
    "Saturday": false, "Sunday": false
  },
  "Timetables": [
    {"Sequence": 1, "ArrivalTime": "06:00", "DepartureTime": "06:00"},
    {"Sequence": 2, "ArrivalTime": "06:12", "DepartureTime": "06:12"},
    ...
  ]
}
```

**處理邏輯**：
1. 篩選 `ServiceDay.ServiceTag = '平日'`
2. 依 `Direction` 分組（0=去程, 1=回程）
3. 取起點站的 Timetables 作為發車時刻
4. 結合其他站的時刻計算站間時間

---

## 每條線路的實作步驟

### 通用流程（TimeTable 為主）

```
1. 下載 TDX 資料
   - Station API → 車站座標
   - Shape API → 軌道幾何 (WKT)
   - StationTimeTable API → 實際時刻表 (篩選平日)

2. 建立 {line}_stations.geojson
   - 從 Station API 轉換

3. 建立軌道 GeoJSON
   - 解析 WKT MULTILINESTRING
   - 連接分段、截斷至車站範圍
   - 校準座標（處理轉乘站）
   - 輸出: {LINE}-1-0.geojson, {LINE}-1-1.geojson

4. 建立時刻表 JSON（從 StationTimeTable）
   - 篩選 ServiceDay.ServiceTag = '平日'
   - 依 Direction 分組
   - 從各站時刻推算站間時間
   - 輸出: {LINE}-1-0.json, {LINE}-1-1.json

5. 更新 station_progress.json
   - 計算各站在軌道上的進度值

6. 更新前端
   - useData.ts: 新增軌道 ID
   - App.tsx: 新增顏色、圖例
   - LineFilter.tsx: 新增篩選按鈕

7. 測試驗證
```

### 時刻表處理邏輯

**從 StationTimeTable 建立時刻表**：

```python
# 1. 取得起點站的發車時刻
origin_timetables = [t for t in data if t['StationID'] == origin_station]
departures = origin_timetables[0]['Timetables']

# 2. 從各站時刻推算站間時間
for station in station_order:
    station_times = get_station_timetables(station)
    # 用相鄰站的時間差計算 TravelTime

# 3. 建立與現有格式相容的時刻表
schedule = {
    "track_id": "K-1-0",
    "departures": [
        {
            "departure_time": "06:00:00",
            "train_id": "K-1-0-001",
            "stations": [
                {"station_id": "K01", "arrival": 0, "departure": 25},
                {"station_id": "K02", "arrival": 120, "departure": 145},
                ...
            ]
        }
    ]
}
```

### 各線路特殊處理

**安坑輕軌 (K)**：
- 單一路線 K-1，最簡單
- 9 站，無分支

**淡海輕軌 (V)**：
- 綠山線 V-1 (V01-V11)
- 藍海線可能是 V-2 (V26-V28)
- 需確認兩條線是否獨立

**桃園機捷 (A)**：
- TrainType: 1=普通車 (A-1), 2=直達車 (A-2)
- 直達車跳過部分站
- 需從 StoppingPatternID 判斷停靠站

**環狀線 (Y)** - 無 TimeTable，需推算：
- 用 Frequency 計算班距
- 用 S2STravelTime 計算站間時間
- 用 FirstLastTimetable 取得首末班時間

---

## 前端顏色配置

```typescript
const LINE_COLORS = {
  // 現有
  R: '#d90023',   // 紅線
  O: '#f8b61c',   // 橘線
  G: '#008659',   // 綠線
  BL: '#0070c0',  // 藍線
  BR: '#c48c31',  // 文湖線

  // 新增
  Y: '#fedb00',   // 環狀線 (黃)
  A: '#9e3a9e',   // 機場捷運 (紫)
  V: '#0ab4a6',   // 淡海輕軌 (青綠)
  K: '#8cc540',   // 安坑輕軌 (草綠)
};
```

---

## 檔案結構規劃

```
public/data/
├── stations/
│   ├── yellow_line_stations.geojson    # Y 環狀線
│   ├── airport_line_stations.geojson   # A 機場捷運
│   ├── danhai_lrt_stations.geojson     # V 淡海輕軌
│   └── ankeng_lrt_stations.geojson     # K 安坑輕軌
├── tracks/
│   ├── Y-1-0.geojson, Y-1-1.geojson
│   ├── A-1-0.geojson, A-1-1.geojson, A-2-0.geojson, A-2-1.geojson
│   ├── V-1-0.geojson, V-1-1.geojson
│   └── K-1-0.geojson, K-1-1.geojson
└── schedules/
    ├── Y-1-0.json, Y-1-1.json
    ├── A-1-0.json, A-1-1.json, A-2-0.json, A-2-1.json
    ├── V-1-0.json, V-1-1.json
    └── K-1-0.json, K-1-1.json

scripts/
├── build_yellow_line.py    # 環狀線
├── build_airport_line.py   # 機場捷運
├── build_danhai_lrt.py     # 淡海輕軌
└── build_ankeng_lrt.py     # 安坑輕軌
```

---

## 建議實作順序（以 TimeTable 為主）

1. **安坑輕軌** (NTALRT/K) - 最簡單，9站單一路線，有完整時刻表
2. **淡海輕軌** (NTDLRT/V) - 有時刻表，14站
3. **桃園機場捷運** (TYMC/A) - 有時刻表，需處理直達/普通車
4. **環狀線** (NTMC/Y) - 無時刻表，需用班距推算

---

## 待確認事項

- [ ] 環狀線第二階段 (Y01-Y06) 何時開通？
- [ ] 淡海輕軌藍海線 (V26-V28) 資料是否完整？
- [ ] 機場捷運直達車停靠站規則 (StoppingPatternID)
- [ ] 各線路營運時間確認
- [ ] 確認 StationTimeTable 的 Sequence 是否對應同一班車

---

## 參考資訊

### TDX API 端點
```
Station:          /v2/Rail/Metro/Station/{系統}
Shape:            /v2/Rail/Metro/Shape/{系統}
StationTimeTable: /v2/Rail/Metro/StationTimeTable/{系統}
S2STravelTime:    /v2/Rail/Metro/S2STravelTime/{系統}
Frequency:        /v2/Rail/Metro/Frequency/{系統}
FirstLastTimetable: /v2/Rail/Metro/FirstLastTimetable/{系統}
```

### 系統代碼
| 系統 | 代碼 | 站點前綴 |
|------|------|----------|
| 安坑輕軌 | NTALRT | K |
| 淡海輕軌 | NTDLRT | V |
| 環狀線 | NTMC | Y |
| 桃園機捷 | TYMC | A |
| 台北捷運 | TRTC | R/O/G/BL/BR |
| 高雄捷運 | KRTC | R/O |
| 高雄輕軌 | KLRT | C |
