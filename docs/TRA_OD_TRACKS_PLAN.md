# 台鐵 O-D 專屬軌道方案

## 問題回顧

原 NetworkTraTrainEngine 方案使用 `route_segments` 動態切換軌道，導致：
- 在軌道切換點（如北新竹）出現**不自然的抖動與跳轉**
- 原因：兩條軌道的幾何形狀在交會點並非完全重合，切換時產生位置跳躍

## 新方案：O-D 專屬軌道

### 核心概念
為每個獨特的「起迄組合」預先建立一條**合併後的專屬軌道**。

```
舊方案：列車動態切換軌道
  新竹→內灣 = [WL-N-0: 新竹→北新竹] → [NW-0: 北新竹→內灣]
  問題：在北新竹切換時產生跳躍

新方案：列車在單一專屬軌道上移動
  新竹→內灣 = 專屬軌道 "NW-HC-NB" (一條連續幾何)
  優點：無需切換，完全平滑
```

### 優勢
- **消除抖動**：列車始終在同一條軌道上，無切換點
- **簡化邏輯**：引擎只需要單軌道插值，不需要跨軌道混合
- **效能更好**：預計算完成後，運行時只需查表

---

## O-D 組合盤點

### NW 線 (內灣線)
根據時刻表分析：
| O-D | 班次 | 涉及軌道 | 專屬軌道 ID |
|-----|------|----------|------------|
| 新竹→內灣 | 7 | WL-N + NW | NW-HC-NB |
| 內灣→新竹 | 8 | NW + WL-N | NW-NB-HC |
| 竹中→內灣 | 11 | NW (部分) | NW-JJ-NB |
| 內灣→竹中 | 11 | NW (部分) | NW-NB-JJ |
| 新竹→竹東 | 1 | WL-N + NW (部分) | NW-HC-JD |

### LJ 線 (六家線)
| O-D | 班次 | 涉及軌道 | 專屬軌道 ID |
|-----|------|----------|------------|
| 新竹→六家 | 35 | WL-N + LJ | LJ-HC-LJ |
| 六家→新竹 | 35 | LJ + WL-N | LJ-LJ-HC |

### 命名規則
```
{線路}-{起站代碼}-{迄站代碼}
HC = 新竹 Hsinchu
NB = 內灣 Neiwan
JJ = 竹中 Zhuzhong
JD = 竹東 Zhudong
LJ = 六家 Liujia
```

---

## 軌道建立原理

### 資料來源
- `all_tracks.geojson`：36 條高精度軌道 (LineString/MultiLineString)
- `station_network_positions.json`：車站在各軌道上的進度值

### 合併邏輯

**情境 1：新竹→內灣 (跨線)**
```
1. 從 WL-N-0 提取：新竹(0.16242) → 北新竹(0.173672) 段
2. 從 NW-0 提取：北新竹(0.998) → 內灣(0.006743) 段
3. 在北新竹站座標處接合兩段
4. 重新計算車站進度值
```

**情境 2：竹中→內灣 (單線部分)**
```
1. 從 NW-0 提取：竹中(0.444313) → 內灣(0.006743) 段
2. 無需接合
3. 重新計算車站進度值
```

### 接合處理
```python
# 確保接合點座標一致
junction_coord = station_network_positions["1190"]["coordinates"]  # 北新竹
segment_1[-1] = junction_coord  # WL-N 段末端
segment_2[0] = junction_coord   # NW 段起點
combined = segment_1 + segment_2[1:]  # 合併，避免重複點
```

---

## 實現步驟

### Phase 1：O-D 專屬軌道生成腳本 ✅ 優先

**檔案**：`scripts/tra/build_od_tracks.py`

**功能**：
1. 讀取時刻表，盤點所有唯一 O-D 組合
2. 根據起迄站決定需要的軌道段
3. 從 `all_tracks.geojson` 提取座標
4. 在接合點合併軌道
5. 計算各站進度值
6. 輸出到 `public/data/tra/tracks_od/`

**輸出格式**：
```json
// tracks_od/NW-HC-NB.geojson
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {
      "track_id": "NW-HC-NB",
      "origin": "新竹",
      "destination": "內灣",
      "origin_station_id": "1210",
      "destination_station_id": "1208",
      "source_tracks": ["WL-N-0", "NW-0"]
    },
    "geometry": {
      "type": "LineString",
      "coordinates": [...]
    }
  }]
}

// tracks_od/od_station_progress.json
{
  "NW-HC-NB": {
    "1210": 0.0,      // 新竹 (起點)
    "1190": 0.0812,   // 北新竹
    "1191": 0.1234,   // 千甲
    ...
    "1208": 1.0       // 內灣 (終點)
  }
}
```

### Phase 2：更新時刻表結構

**檔案**：`scripts/tra/update_schedules_with_od.py`

**功能**：
1. 讀取現有 `schedules_network/*.json`
2. 為每個 departure 添加 `od_track_id` 欄位
3. 輸出到 `schedules_od/` 目錄

**更新後結構**：
```json
{
  "departure_time": "06:02:00",
  "train_id": "NW-0_06:02:00",
  "od_track_id": "NW-HC-NB",  // 新增：使用哪條 O-D 軌道
  "stations": [...],
  "route_segments": [...]      // 保留作為參考
}
```

### Phase 3：簡化引擎邏輯

**檔案**：`src/engines/NetworkTraTrainEngine.ts`

**修改重點**：
```typescript
// 舊邏輯：動態找軌道段
const segment = findCurrentSegment(departure.route_segments, elapsedTime);
const trackCoords = trackMap.get(segment.track_id);
const progress = interpolateInSegment(segment, elapsedTime);

// 新邏輯：直接使用 O-D 軌道
const odTrackId = departure.od_track_id;
const odTrackCoords = odTrackMap.get(odTrackId);
const progress = calculateProgress(departure.stations, elapsedTime);
const position = interpolateOnTrack(odTrackCoords, progress);
```

**新增資料載入**：
- `useTraData.ts` 載入 `tracks_od/*.geojson`
- `useTraData.ts` 載入 `od_station_progress.json`

### Phase 4：驗證與測試

**視覺驗證**：
- [ ] 新竹→內灣列車全程平滑移動
- [ ] 竹中→內灣列車在 NW 線部分平滑移動
- [ ] 新竹→六家列車經北新竹平滑轉入 LJ

**Console 驗證**：
- [ ] 列印列車使用的 od_track_id
- [ ] 確認進度值 0→1 單調遞增

---

## 關鍵檔案

### 需新建
| 檔案 | 說明 |
|------|------|
| `scripts/tra/build_od_tracks.py` | O-D 軌道生成腳本 |
| `scripts/tra/update_schedules_with_od.py` | 時刻表更新腳本 |
| `public/data/tra/tracks_od/*.geojson` | O-D 專屬軌道檔案 |
| `public/data/tra/tracks_od/od_station_progress.json` | O-D 軌道車站進度 |
| `public/data/tra/schedules_od/*.json` | 更新後時刻表 |

### 需修改
| 檔案 | 修改內容 |
|------|----------|
| `src/engines/NetworkTraTrainEngine.ts` | 改用 O-D 軌道計算位置 |
| `src/hooks/useTraData.ts` | 載入 O-D 軌道資料 |
| `src/types/schedule.ts` | 新增 od_track_id 欄位 |

### 參考檔案
| 檔案 | 用途 |
|------|------|
| `public/data/tra/tracks_official/all_tracks.geojson` | 軌道座標來源 |
| `public/data/tra/station_network_positions.json` | 車站進度參考 |
| `public/data/tra/schedules_network/*.json` | 現有時刻表 |

---

## 驗證方式

1. **生成驗證**：執行腳本後檢查 `tracks_od/` 目錄
   - 確認 NW-HC-NB.geojson 座標連續
   - 確認北新竹站在接合處無重複點

2. **視覺驗證**：啟動應用觀察列車
   - 新竹發車列車應沿 WL-N 開到北新竹
   - 在北新竹平滑轉入 NW 線
   - 全程無抖動或跳躍

3. **數值驗證**：Console 輸出
   - 列車進度應為 0→1 單調遞增
   - 座標變化應連續平滑
