# Schedule Converter Agent

TDX 時刻表轉換器，專門處理 Phase 3 的時刻表轉換工作。

## 角色

將 TDX 原始時刻表轉換為 Mini Taiwan 格式，並匹配對應的 O-D 軌道。

## 使用時機

當用戶提到以下關鍵字時使用：
- 「轉換時刻表」
- 「TDX 轉換」
- 「Phase 3」
- 「產生時刻表」

## 工具

Read, Write, Bash, Glob, Grep

## 參考文件

- `public/data/tra/REAL_TIMETABLE_PLAN.md` - Phase 3 章節
- `scripts/tra/fetch_yl_kl_timetable.py` - 參考現有轉換邏輯
- `public/data/tra/schedules_od/` - 現有時刻表格式

## 格式轉換

### TDX 原始格式

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

### Mini Taiwan 格式

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
    {"station_id": "1040", "station_name": "樹林", "arrival": 0, "departure": 120},
    {"station_id": "7000", "station_name": "花蓮", "arrival": 7200, "departure": 7200}
  ]
}
```

## 車種代碼解析

```python
TRAIN_TYPE_CODES = {
    '自強(3000)': 'TC',
    '普悠瑪': 'PP',
    '太魯閣': 'TZ',
    '區間快': 'CK',
    '復興': 'FX',
    '區間': 'LC',
}

def get_train_type_code(train_type_name):
    for key, code in TRAIN_TYPE_CODES.items():
        if key in train_type_name:
            return code
    return 'OTHER'
```

## O-D 軌道匹配

```python
def match_od_track(origin_id, dest_id, route_lines):
    """
    根據起迄站和途經路線匹配 O-D 軌道

    1. 查詢 od_to_base_track.json 對照表
    2. 找到對應的 O-D 軌道 ID
    3. 如果找不到，標記為需要新建
    """
```

## 時間轉換

```python
def time_to_seconds(time_str, base_time):
    """
    將 HH:MM 轉換為相對秒數

    - base_time: 列車發車時間
    - 處理跨日情況 (如 23:50 → 00:30)
    """
    parts = time_str.split(':')
    total = int(parts[0]) * 3600 + int(parts[1]) * 60

    # 處理跨日
    if total < base_time - 12 * 3600:
        total += 24 * 3600

    return total - base_time
```

## 工作流程

### 1. 讀取 TDX 時刻表

```bash
cat public/data/tra/data/tdx_timetable_*.json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))"
```

### 2. 執行轉換

```bash
python3 scripts/tra/convert_tdx_timetable.py
```

### 3. 產生輸出檔案

```
schedules_od/
├── master_schedule.json    # 索引檔
└── by_od/
    ├── WL-N-SL-KL-0.json
    ├── YL-SL-HL-0.json
    └── ...
```

### 4. 驗證

```bash
# 檢查班次數量
cat schedules_od/master_schedule.json | python3 -c "import json,sys; print(len(json.load(sys.stdin)['trains']))"

# 應該 = 928
```

## master_schedule.json 格式

```json
{
  "generated_at": "2026-01-26T10:00:00",
  "source": "TDX GeneralTrainTimetable",
  "total_trains": 928,
  "trains": [
    {
      "train_id": "TC-110",
      "train_no": "110",
      "train_type_code": "TC",
      "origin": "樹林",
      "destination": "花蓮",
      "departure_time": "06:00:00",
      "od_track_id": "YL-SL-HL-0",
      "schedule_file": "by_od/YL-SL-HL-0.json"
    }
  ],
  "by_train_type": {
    "TC": 50,
    "PP": 30,
    "TZ": 30,
    "CK": 100,
    "FX": 400,
    "LC": 200,
    "OTHER": 118
  }
}
```

## 驗證標準

- [ ] 總班次 = 928
- [ ] 所有班車都有 od_track_id
- [ ] 所有 stations 的 arrival/departure 為正整數
- [ ] total_travel_time > 0
- [ ] 無重複 train_id

## 錯誤處理

常見問題：
1. **找不到 O-D 軌道** → 記錄到 `missing_od_for_schedule.json`
2. **時間格式錯誤** → 記錄並跳過
3. **車站 ID 不存在** → 檢查 station_mapping.json

## 輸出格式

完成後回報：

```
=== 時刻表轉換完成 ===
- 總班次：928
- 成功轉換：925
- 失敗/跳過：3
- 車種分布：
  - TC (自強): 50
  - PP (普悠瑪): 30
  - ...
- 產生檔案：
  - master_schedule.json
  - by_od/*.json (共 X 個)
```
