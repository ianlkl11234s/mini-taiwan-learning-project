# 文湖線 (Brown Line) 資料研究報告

> 測試日期: 2025-12-31
> 專案: Mini Tokyo 3D 台北捷運視覺化

---

## 摘要

本報告評估從 TDX API 取得文湖線資料的可行性，並調查 Moovit App 等替代資料來源。
結論：**TDX API 提供完整資料，足以生成文湖線時刻表**。

---

## 一、TDX API 測試結果

### 1.1 測試成功的 API 端點

| API 端點 | 用途 | 文湖線筆數 | 狀態 |
|---------|------|-----------|------|
| `/v2/Rail/Metro/Shape/TRTC` | 軌道圖資 (WKT 格式) | 1 | ✅ 成功 |
| `/v2/Rail/Metro/Frequency/TRTC` | 班距頻率 | 2 (平日/假日) | ✅ 成功 |
| `/v2/Rail/Metro/S2STravelTime/TRTC` | 站間行駛時間 | 1 (23站間資料) | ✅ 成功 |
| `/v2/Rail/Metro/FirstLastTimetable/TRTC` | 首末班車時刻 | 46 | ✅ 成功 |
| `/v2/Rail/Metro/Station/TRTC` | 車站座標 | 24 | ✅ 成功 |
| `/V3/Map/Rail/Network/Line/OperatorCode/TRTC` | 路線圖資 | 1 | ✅ 成功 |

### 1.2 測試失敗的 API (速率限制)

| API 端點 | 錯誤 |
|---------|------|
| `/v2/Rail/Metro/Line/TRTC` | 429 Too Many Requests |
| `/V3/Map/Rail/Network/Station/OperatorCode/TRTC` | 429 Too Many Requests |

> 注意：這些 API 實際上可用，只是測試時因連續請求觸發速率限制

---

## 二、資料結構分析

### 2.1 車站資料 (Station)

**資料檔案**: `data/tdx_metro_test/metro_station_BR_20251231.json`

```json
{
  "StationUID": "TRTC-BR01",
  "StationID": "BR01",
  "StationName": {
    "Zh_tw": "動物園",
    "En": "Taipei Zoo"
  },
  "StationPosition": {
    "PositionLon": 121.579501,
    "PositionLat": 24.998205
  }
}
```

**完整車站清單 (BR01-BR24)**:

| ID | 中文名 | 英文名 | 經度 | 緯度 |
|----|--------|--------|------|------|
| BR01 | 動物園 | Taipei Zoo | 121.579501 | 24.998205 |
| BR02 | 木柵 | Muzha | 121.573127 | 24.99824 |
| BR03 | 萬芳社區 | Wanfang Community | 121.568088 | 24.99857 |
| BR04 | 萬芳醫院 | Wanfang Hospital | 121.558092 | 24.99932 |
| BR05 | 辛亥 | Xinhai | 121.557046 | 25.005455 |
| BR06 | 麟光 | Linguang | 121.558834 | 25.018495 |
| BR07 | 六張犁 | Liuzhangli | 121.55302 | 25.02381 |
| BR08 | 科技大樓 | Technology Building | 121.543462 | 25.02612 |
| BR09 | 大安 | Daan | 121.54237 | 25.033311 |
| BR10 | 忠孝復興 | Zhongxiao Fuxing | 121.543703 | 25.041104 |
| BR11 | 南京復興 | Nanjing Fuxing | 121.544303 | 25.052044 |
| BR12 | 中山國中 | Zhongshan Jr. High School | 121.544215 | 25.06085 |
| BR13 | 松山機場 | Songshan Airport | 121.55162 | 25.063111 |
| BR14 | 大直 | Dazhi | 121.54679 | 25.07943 |
| BR15 | 劍南路 | Jiannan Rd. | 121.555582 | 25.08483 |
| BR16 | 西湖 | Xihu | 121.567227 | 25.08216 |
| BR17 | 港墘 | Gangqian | 121.57516 | 25.08007 |
| BR18 | 文德 | Wende | 121.584973 | 25.078567 |
| BR19 | 內湖 | Neihu | 121.594363 | 25.083675 |
| BR20 | 大湖公園 | Dahu Park | 121.602214 | 25.083805 |
| BR21 | 葫洲 | Huzhou | 121.607146 | 25.07271 |
| BR22 | 東湖 | Donghu | 121.611535 | 25.067455 |
| BR23 | 南港軟體園區 | Nangang Software Park | 121.61586 | 25.059911 |
| BR24 | 南港展覽館 | Taipei Nangang Exhibition Center | 121.616861 | 25.054919 |

### 2.2 站間行駛時間 (S2STravelTime)

**資料檔案**: `data/tdx_metro_test/metro_s2s_travel_time_BR_20251231.json`

提供完整的 23 個站間行駛時間：

```json
{
  "Sequence": 1,
  "FromStationID": "BR24",
  "ToStationID": "BR23",
  "RunTime": 78,      // 行駛時間 (秒)
  "StopTime": 0       // 停站時間 (秒)
}
```

**站間時間摘要**:

| 起站 | 迄站 | 行駛時間 | 停站時間 |
|------|------|---------|---------|
| BR24→BR23 | 南港展覽館→南港軟體園區 | 78秒 | 0秒 |
| BR23→BR22 | 南港軟體園區→東湖 | 85秒 | 25秒 |
| BR22→BR21 | 東湖→葫洲 | 78秒 | 25秒 |
| ... | ... | ... | ... |
| BR02→BR01 | 木柵→動物園 | 67秒 | 25秒 |

**全程行駛時間**: 約 34-35 分鐘（單向）+ 停站時間

### 2.3 班距頻率 (Frequency)

**資料檔案**: `data/tdx_metro_test/metro_frequency_BR_20251231.json`

**平日班距**:

| 時段 | 尖峰 | 最短班距 | 最長班距 |
|------|------|---------|---------|
| 06:00-07:00 | 離峰 | 4分 | 10分 |
| 07:00-09:00 | **尖峰** | **2分** | **4分** |
| 09:00-17:00 | 離峰 | 4分 | 10分 |
| 17:00-19:30 | **尖峰** | **2分** | **4分** |
| 19:30-23:00 | 離峰 | 4分 | 10分 |
| 23:00-00:00 | 深夜 | 12分 | 12分 |

**假日班距**:

| 時段 | 最短班距 | 最長班距 |
|------|---------|---------|
| 06:00-23:00 | 4分 | 10分 |
| 23:00-00:00 | 12分 | 12分 |

### 2.4 首末班車時刻 (FirstLastTimetable)

**資料檔案**: `data/tdx_metro_test/metro_first_last_BR_20251231.json`

提供每個車站的首末班車時間，範例：

| 車站 | 往南港展覽館首班 | 往南港展覽館末班 | 往動物園首班 | 往動物園末班 |
|------|---------------|---------------|------------|------------|
| BR01 動物園 | 06:00 | 00:00 | - | - |
| BR02 木柵 | 06:01 | 00:01 | 06:04 | 00:53 |
| BR24 南港展覽館 | - | - | 06:00 | 00:00 |

### 2.5 軌道圖資 (Shape)

**資料檔案**: `data/tdx_metro_test/metro_shape_BR_20251231.json`

提供 WKT MULTILINESTRING 格式的軌道幾何：
- 包含完整文湖線軌道座標
- 需轉換為 GeoJSON LineString 格式

---

## 三、時刻表生成方案

### 3.1 建議方案：班距模擬法

由於文湖線是無人駕駛系統，使用班距頻率動態生成發車時間：

```python
def generate_departures(first_train, last_train, frequency_data):
    departures = []
    current_time = first_train

    while current_time <= last_train:
        # 根據時段取得班距
        headway = get_headway_for_time(current_time, frequency_data)
        departures.append(current_time)
        current_time += headway

    return departures
```

### 3.2 站間時間計算

使用 S2STravelTime API 計算每站到達/離開時間：

```python
def calculate_station_times(departure_time, travel_times):
    stations = []
    cumulative = 0

    for tt in travel_times:
        arrival = cumulative
        departure = arrival + tt['StopTime']
        stations.append({
            'station_id': tt['ToStationID'],
            'arrival': arrival,
            'departure': departure
        })
        cumulative = departure + tt['RunTime']

    return stations
```

### 3.3 預估發車數量

**平日** (06:00-24:00):
- 尖峰 (4.5小時 × 2 = 9小時): 約 9 × 60 / 3 = 180 班
- 離峰 (8小時): 約 8 × 60 / 7 = 68 班
- 深夜 (1小時): 約 5 班
- **總計約 250 班/日**

---

## 四、Moovit App 資料評估

### 4.1 可用資訊

Moovit 提供文湖線以下資訊：
- 營運時間: 06:00 - 00:00
- 班距: 平日 4-7 分鐘 / 假日 7 分鐘
- 全程時間: 約 44 分鐘
- 車站數: 24 站

### 4.2 資料取得方式

| 方式 | 可用性 | 說明 |
|------|--------|------|
| PDF 時刻表 | ✅ | [下載連結](https://appassets.mvtdev.com/map/192/l/3843/48314177.pdf) |
| 線上查詢 | ✅ | Moovit 網站/App |
| API 存取 | ❌ | 無公開 API |
| GTFS 資料 | ❌ | 未提供 |

### 4.3 結論

Moovit **不建議作為資料來源**：
- 無公開 API
- 無 GTFS 格式
- 資料詳細度不及 TDX

---

## 五、其他資料來源

### 5.1 台北捷運官方 API

- **網址**: https://www.metro.taipei/cp.aspx?n=BDEB860F2BE3E249
- **內容**: 提供官方 API 服務，但需申請
- **評估**: 可作為補充資料來源

### 5.2 臺北市資料大平臺

- **網址**: https://data.taipei/
- **內容**: 台北市政府開放資料
- **評估**: 可搜尋捷運相關資料集

### 5.3 GTFS 資料

目前台北捷運**未提供公開 GTFS 格式資料**。

---

## 六、建議實作步驟

### Step 1: 建立車站 GeoJSON

```bash
# 使用 TDX Station API 資料轉換
python scripts/convert_br_stations_to_geojson.py
```

輸出: `public/data/brown_line_stations.geojson`

### Step 2: 建立軌道 GeoJSON

```bash
# 將 WKT Shape 轉換為 GeoJSON
python scripts/convert_br_shape_to_geojson.py
```

輸出:
- `public/data/tracks/BR-1-0.geojson` (往南港展覽館)
- `public/data/tracks/BR-1-1.geojson` (往動物園)

### Step 3: 校準軌道

```bash
# 使用現有校準腳本
python scripts/calibrate_lines_v2.py
```

### Step 4: 生成時刻表

```bash
# 基於 Frequency + S2STravelTime 生成
python scripts/generate_br_schedules.py
```

輸出:
- `public/data/schedules/BR-1-0.json`
- `public/data/schedules/BR-1-1.json`

### Step 5: 更新程式碼

修改以下檔案：
- `src/hooks/useData.ts`: 新增 BR 軌道 ID
- `src/App.tsx`: 新增 BR 顏色設定

---

## 七、結論

### 資料可用性評估

| 資料類型 | TDX API | Moovit | 官方 | 可用性 |
|---------|---------|--------|------|--------|
| 車站座標 | ✅ | ❌ | ✅ | **充足** |
| 軌道幾何 | ✅ | ❌ | ✅ | **充足** |
| 站間時間 | ✅ | ❌ | ❌ | **充足** |
| 班距頻率 | ✅ | ✅ | ✅ | **充足** |
| 固定時刻表 | ❌ | ❌ | ❌ | **需模擬** |

### 最終建議

**使用 TDX API 作為主要資料來源**，原因：
1. 資料完整性最高
2. 提供結構化 JSON 格式
3. 包含站間精確行駛時間
4. 官方認證資料來源

**時刻表生成策略**：
- 使用 Frequency API 的班距資料動態生成發車時間
- 使用 S2STravelTime API 計算每站到達/離開時間
- 使用 FirstLastTimetable API 確定首末班車時間範圍

---

## 附錄：參考資料

- [TDX 運輸資料流通服務平臺](https://tdx.transportdata.tw/)
- [TDX 運輸資料介接指南](https://bookdown.org/chiajungyeh/TDX_Guide/)
- [GitHub - TDX Sample Code](https://github.com/tdxmotc/SampleCode)
- [Moovit 文湖線頁面](https://moovitapp.com/index/en/public_transit-line-文湖線-Taipei-3843-2320662-48314177-0)
- [台北捷運官方 API](https://www.metro.taipei/cp.aspx?n=BDEB860F2BE3E249)
- [Wikipedia - 文湖線](https://zh.wikipedia.org/zh-tw/文湖線)

---

## 附錄：測試資料檔案清單

| 檔案 | 內容 |
|------|------|
| `data/tdx_metro_test/metro_station_BR_20251231.json` | 文湖線車站資料 |
| `data/tdx_metro_test/metro_s2s_travel_time_BR_20251231.json` | 站間行駛時間 |
| `data/tdx_metro_test/metro_frequency_BR_20251231.json` | 班距頻率 |
| `data/tdx_metro_test/metro_first_last_BR_20251231.json` | 首末班車時刻 |
| `data/tdx_metro_test/metro_shape_BR_20251231.json` | 軌道圖資 |
| `data/tdx_metro_test/v3_rail_line_BR_20251231.json` | V3 路線圖資 |
| `data/tdx_metro_test/api_test_report_*.json` | 完整測試報告 |
