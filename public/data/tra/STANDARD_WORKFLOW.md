# TRA 軌道建立標準流程

> 建立時間：2026-01-13
> 最後更新：2026-01-14

---

## 標準流程概覽

```
Step 1: 建立 Golden Track (顯示軌道)
    ↓
Step 2: 建立 O-D Track (列車計算軌道)
    ↓
Step 3: 計算 Station Progress
    ↓
Step 4: 建立測試時刻表
    ↓
Step 5: 驗證 → 修正 → 驗證
    ↓
Step 6: 下一段軌道
```

---

## Step 1: 建立 Golden Track

**目的**：建立顯示用的軌道

**輸出檔案**：
- `tracks_golden/{TRACK_ID}-0.geojson` (方向 0)
- `tracks_golden/{TRACK_ID}-1.geojson` (方向 1)

**格式**：
```json
{
  "type": "Feature",
  "properties": {
    "track_id": "WL-N-SL-BD-0",
    "line_id": "WL-N",
    "direction": 0,
    "name": "縱貫線北段 (樹林→八堵)",
    "origin": "樹林",
    "destination": "八堵"
  },
  "geometry": {
    "type": "LineString",
    "coordinates": [[lng, lat], ...]
  }
}
```

**載入設定** (`useTraData.ts`)：
```typescript
const TRA_TRACK_IDS = [
  'WL-N-SL-BD-0', 'WL-N-SL-BD-1',  // Step 1: 樹林→八堵
];
```

---

## Step 2: 建立 O-D Track

**目的**：建立列車位置計算用的軌道

**輸出檔案**：
- `tracks_od/{OD_TRACK_ID}.geojson`

**格式**：
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {
      "track_id": "WL-SL-BD-0",
      "name": "縱貫線北段 (樹林→八堵)",
      "origin": "樹林",
      "destination": "八堵",
      "direction": 0
    },
    "geometry": {
      "type": "LineString",
      "coordinates": [[lng, lat], ...]
    }
  }]
}
```

**載入設定** (`useTraData.ts`)：
```typescript
const OD_TRACK_IDS = [
  'WL-SL-BD-0',   // 樹林→八堵
  'WL-BD-SL-1',   // 八堵→樹林
];
```

---

## Step 3: 計算 Station Progress

**目的**：計算每個站點在軌道上的 progress 值 (0.0 ~ 1.0)

**輸出檔案**：
- `tracks_od/od_station_progress.json`

**格式**：
```json
{
  "WL-SL-BD-0": {
    "1040": 0.0,      // 樹林 (起點)
    "1030": 0.076,    // 浮洲
    "1020": 0.142,    // 板橋
    ...
    "0920": 1.0       // 八堵 (終點)
  }
}
```

**計算方法**（使用投影法）：
1. 計算軌道總長度
2. 對每個站點，遍歷所有軌道線段：
   - 將站點**投影**到線段上（而非找最近點）
   - 計算投影點到線段起點的距離
3. 找到最佳投影位置（投影點在線段內且距離最近）
4. 累積距離 / 總長度 = progress

**重要**：必須使用「投影法」而非「最近點法」，避免停站時列車偏移

**距離計算**：使用歐幾里得距離（平面，度為單位），不要使用 Haversine 球面距離

---

## Step 4: 建立測試時刻表

**目的**：建立測試用的時刻表

**輸出檔案**：
- `schedules_od/{OD_TRACK_ID}.json`

**格式**：
```json
{
  "track_id": "WL-SL-BD-0",
  "departures": [{
    "train_id": "WL-SL-BD-0-06",
    "train_no": "TEST06",
    "train_type": "區間",
    "departure_time": "06:00:00",
    "od_track_id": "WL-SL-BD-0",
    "origin_station": "樹林",
    "destination_station": "八堵",
    "total_travel_time": 2160,
    "stations": [
      {"station_id": "1040", "arrival": 0, "departure": 60},
      {"station_id": "1030", "arrival": 180, "departure": 240},
      ...
    ]
  }]
}
```

**重要**：`arrival` 和 `departure` 必須是**相對秒數**（從列車發車時間開始計算）

**載入設定** (`useTraData.ts`)：
```typescript
const SCHEDULE_IDS = [
  'WL-SL-BD-0',   // 樹林→八堵
  'WL-BD-SL-1',   // 八堵→樹林
];
```

---

## Step 5: 驗證

**驗證項目**：
1. ✅ 軌道連續顯示，沒有斷開
2. ✅ 列車沿軌道移動，沒有亂跳
3. ⚠️ 停站時位置對齊站點
4. ✅ 列車方向正確

**如有問題**：
- 軌道斷開 → 檢查座標，手繪補正
- 列車亂跳 → 檢查 station_progress
- 停站偏移 → 調整站點座標或 station_progress

---

## Step 6: TraTrainEngine 映射

**更新** `src/engines/TraTrainEngine.ts` 的 `getTrackIdFromOdTrackId()` 函數：

```typescript
// WL 西部幹線：WL-SL-BD-0 → WL-N-SL-BD-0
if (lineId === 'WL') {
  const direction = parts[parts.length - 1];
  return `WL-N-SL-BD-${direction}`;
}
```

---

## 檔案結構總覽

```
public/data/tra/
├── tracks_golden/
│   ├── WL-N-SL-BD-0.geojson    # 顯示軌道 (樹林→八堵)
│   └── WL-N-SL-BD-1.geojson
├── tracks_od/
│   ├── WL-SL-BD-0.geojson      # O-D 軌道
│   ├── WL-BD-SL-1.geojson
│   └── od_station_progress.json
└── schedules_od/
    ├── WL-SL-BD-0.json          # 時刻表
    └── WL-BD-SL-1.json
```

---

## 命名規則

| 類型 | 格式 | 範例 |
|------|------|------|
| 顯示軌道 | `{LINE}-{ORIGIN}-{DEST}-{DIR}` | `WL-N-SL-BD-0` |
| O-D 軌道 | `{LINE}-{ORIGIN}-{DEST}-{DIR}` | `WL-SL-BD-0` |
| 時刻表 | 同 O-D 軌道 | `WL-SL-BD-0.json` |

---

## 實作進度

| Step | 路段 | 顯示軌道 | O-D 軌道 | Progress | 時刻表 | 驗證 |
|------|------|----------|----------|----------|--------|------|
| 1 | 樹林↔八堵 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | 八堵↔蘇澳 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2+ | 樹林↔蘇澳 (合併) | - | ✅ | ✅ | ✅ | ✅ |
| 3 | 八堵↔基隆 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | 蘇澳↔花蓮 | 📋 | 📋 | 📋 | 📋 | 📋 |

---

## 關鍵注意事項

### 1. 時刻表時間格式
- ❌ **錯誤**：使用絕對秒數（如 06:00 = 21600）
- ✅ **正確**：使用相對秒數（從發車時間起算，起點 arrival = 0）

```json
// 正確範例
{"station_id": "1040", "arrival": 0, "departure": 60},
{"station_id": "1030", "arrival": 180, "departure": 240}
```

### 2. Station Progress 計算
- ❌ **錯誤**：使用「最近點」方法（會有偏移）
- ✅ **正確**：使用「投影法」（投影到軌道線段上）

### 3. 距離計算
- ❌ **錯誤**：Haversine 球面距離（與引擎不一致）
- ✅ **正確**：歐幾里得距離（平面，度為單位）

### 4. 檔案格式
- Golden Track：`Feature` 或 `FeatureCollection` 均可（loader 已支援）
- O-D Track：`FeatureCollection` 包含一個 `Feature`

### 5. Track ID 映射
- 新增路段時，需更新 `TraTrainEngine.ts` 的 `getTrackIdFromOdTrackId()` 函數
- 確保 O-D Track ID 正確對應到 Golden Track ID

---

## 常見問題排解

| 現象 | 原因 | 解決方法 |
|------|------|----------|
| 列車不動 | 時刻表使用絕對時間 | 改用相對秒數 |
| 列車亂跳 | station_progress 不正確 | 重新計算投影 |
| 停站偏移 | 使用最近點法計算 | 改用投影法 |
| 軌道不顯示 | 檔案格式不符或 ID 未加入 | 檢查格式和 useTraData.ts |
| 列車顏色錯誤 | Track ID 映射錯誤 | 更新 getTrackIdFromOdTrackId() |
| 列車走直線 | 反向軌道未正確建立 | 使用 `list(reversed(coords))` 建立反向軌道 |
| 地圖出現青色線 | O-D 軌道測試圖層顯示中 | App.tsx 中 `tra-od-tracks-line` opacity 設為 0 |
| 終點站列車偏移 | 軌道終點與站點有距離 | 延伸軌道座標到站點位置（直線連結即可） |

---

## 合併軌道建立 (進階)

當需要建立跨區段的完整 O-D 軌道時（如樹林↔蘇澳 = WL + YL）：

### 步驟

1. **合併座標**：將兩段軌道座標串接（移除重複的交界點）
2. **建立正向軌道**：`YL-SL-SA-0.geojson`
3. **建立反向軌道**：使用 `list(reversed(coords))` 建立 `YL-SA-SL-1.geojson`
4. **計算 Station Progress**：使用投影法在合併軌道上計算

### 重要注意

- ⚠️ 反向軌道**必須**是正向軌道的完整反向
- ⚠️ 不要分段反向再合併，會造成座標錯誤
- ✅ 正確做法：先合併正向 → 整體反向

### 範例

```python
# 正確做法
with open('YL-SL-SA-0.geojson') as f:
    data0 = json.load(f)
coords0 = data0['features'][0]['geometry']['coordinates']

# 建立反向軌道
coords_reversed = list(reversed(coords0))

# 驗證
assert coords_reversed[0] == coords0[-1]  # 反向起點 = 正向終點
assert coords_reversed[-1] == coords0[0]  # 反向終點 = 正向起點
```

---

## 檔案歸檔

舊的或待處理的 O-D 軌道應移至 `tracks_archive/tracks_od_pending/`，避免被錯誤載入。
