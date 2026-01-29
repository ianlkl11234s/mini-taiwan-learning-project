# TRA 台鐵開發完整指南

> 版本：1.0.0
> 建立日期：2026-01-29
> 本文件整合了 Mini Taiwan 專案中 TRA 台鐵系統開發的所有經驗、最佳實踐、維護流程與問題排解方法。

---

## 目錄

1. [系統概述](#1-系統概述)
2. [專案結構](#2-專案結構)
3. [核心概念](#3-核心概念)
4. [關鍵規則（必讀）](#4-關鍵規則必讀)
5. [新增路線流程](#5-新增路線流程)
6. [更新時刻表流程](#6-更新時刻表流程)
7. [常見問題與解決方案](#7-常見問題與解決方案)
8. [驗證工具使用](#8-驗證工具使用)
9. [經驗教訓（踩坑指南）](#9-經驗教訓踩坑指南)
10. [附錄](#10-附錄)

---

## 1. 系統概述

### 1.1 什麼是 O-D 專屬軌道系統？

TRA 使用 **Origin-Destination (O-D) 專屬軌道**設計。每班列車有專屬的軌道檔案，從起點到終點使用同一條軌道，不進行動態切換。

**為什麼採用這個設計？**

傳統做法讓列車在運行時動態切換軌道會導致：
- **軌道切換時的抖動**：列車在切換點位置跳躍
- **方向計算錯誤**：列車朝向在切換時突然改變

O-D 專屬軌道解決方案：
- 為每個起迄對預先合併好完整軌道
- 列車從頭到尾只使用一條軌道
- 消除切換點問題

### 1.2 系統現況

截至 2026-01-29：
- **列車班次**：992 班（TDX 真實時刻表）
- **O-D 軌道類型**：178 種
- **覆蓋路線**：17 條（西部幹線、東部幹線、南迴線、各支線）
- **Backward 問題**：0（已全部解決）

### 1.3 核心模組

| 模組 | 檔案位置 | 說明 |
|------|----------|------|
| TraTrainEngine | `src/engines/TraTrainEngine.ts` | 列車狀態計算引擎 |
| Tra3DLayer | `src/layers/Tra3DLayer.ts` | 3D 渲染層 |
| useTraData | `src/hooks/useTraData.ts` | 資料載入 Hook |
| traInfo | `src/constants/traInfo.ts` | 路線/車站資訊常數 |

---

## 2. 專案結構

```
public/data/tra/
├── docs/                          # 文件目錄
│   ├── TRA_DEVELOPMENT_GUIDE.md   # 本文件
│   ├── TRACKS_STATUS.md           # 軌道狀態追蹤
│   ├── STANDARD_WORKFLOW.md       # 標準工作流程
│   └── archive/                   # 已歸檔文件
│
├── tracks_golden/                 # 🏆 黃金版本（前端載入來源）
├── tracks_od/                     # O-D 專屬軌道（列車位置計算）
│   └── od_station_progress.json   # 車站進度映射（核心檔案！）
├── tracks_handdrawn/              # 手繪修正（永不覆蓋）
├── tracks_official/               # TDX 原始資料（fallback）
│
├── schedules_real/                # 真實時刻表
│   └── master_schedule.json       # 主時刻表（992 班）
├── schedules_od/                  # O-D 測試時刻表（備用）
│
├── stations.geojson               # 車站原始座標
├── stations_snapped.geojson       # 投影到軌道上的車站座標
└── all_tracks_backup.geojson      # Optra 備份資料（優先使用）

scripts/tra/
├── validate_*.py                  # 驗證工具
├── build_*_od_tracks.py           # 軌道建立工具
└── prepare_real_timetable/        # TDX 時刻表轉換工具
```

### 2.1 軌道檔案類型說明

| 目錄 | 用途 | 說明 |
|------|------|------|
| `tracks_golden/` | 顯示軌道 | 前端載入用，在地圖上繪製軌道線 |
| `tracks_od/` | 計算軌道 | 列車位置計算用，包含 station_progress |
| `tracks_handdrawn/` | 手繪修正 | 修正 TDX 原始資料的問題路段 |
| `tracks_official/` | 原始資料 | TDX API 取得的原始軌道 |

---

## 3. 核心概念

### 3.1 station_progress

`station_progress` 是車站在軌道上的相對位置，範圍 0.0 ~ 1.0。

```json
{
  "YL-SL-SA-0": {
    "1040": 0.0,      // 樹林 (起點)
    "1030": 0.076,    // 浮洲
    ...
    "5000": 1.0       // 蘇澳 (終點)
  }
}
```

**規則**：
- 起點站 progress = 0.0
- 終點站 progress = 1.0
- 數值必須**單調遞增**（不能有倒退）

### 3.2 軌道命名規則

```
{路線代碼}-{起點代碼}-{終點代碼}-{方向}

範例：
- WL-N-SL-BD-0  = 西部幹線北段 樹林→八堵 方向0
- YL-SL-SA-0    = 宜蘭線 樹林→蘇澳 方向0
- PX-SD-JT      = 平溪線 三貂嶺→菁桐
```

### 3.3 路線代碼對照

| 代碼 | 路線 | 起訖站 |
|------|------|--------|
| WL-N | 西部幹線北段 | 竹南-八堵 |
| WL-M | 西部幹線山線 | 竹南-彰化 |
| WL-C | 西部幹線海線 | 竹南-彰化 |
| WL-S | 西部幹線南段 | 彰化-新左營 |
| YL | 宜蘭線 | 八堵-蘇澳 |
| BH | 北迴線 | 蘇澳新-花蓮 |
| TL | 臺東線 | 花蓮-臺東 |
| SK | 南迴線 | 臺東-新左營 |
| PT | 屏東線 | 新左營-枋寮 |
| NW | 內灣線 | 新竹-內灣 |
| LJ | 六家線 | 竹中-六家 |
| SH | 沙崙線 | 中洲-沙崙 |
| PX | 平溪線 | 三貂嶺-菁桐 |
| SA | 深澳線 | 瑞芳-八斗子 |
| JJ | 集集線 | 二水-車埕 |
| CZ | 成追線 | 成功-追分 |
| KL | 基隆支線 | 八堵-基隆 |

---

## 4. 關鍵規則（必讀）

### 4.1 距離計算必須使用歐幾里得距離

**這是最重要的規則！Python 和 TypeScript 必須一致！**

```python
# ✅ 正確 - 歐幾里得距離（平面，度為單位）
def calculate_distance(coord1, coord2):
    dx = coord2[0] - coord1[0]
    dy = coord2[1] - coord1[1]
    return math.sqrt(dx * dx + dy * dy)

# ❌ 錯誤 - Haversine 球面距離
from geopy.distance import geodesic  # 禁用！
```

TypeScript 引擎使用：
```typescript
const dx = coords[i + 1][0] - coords[i][0];
const dy = coords[i + 1][1] - coords[i][1];
const segmentLength = Math.sqrt(dx * dx + dy * dy);
```

**後果**：如果 Python 用 Haversine 而 TypeScript 用 Euclidean，列車停站位置會偏移數百公尺！

### 4.2 station_progress 使用投影法計算

```python
def project_to_segment(p, a, b):
    """將點 p 投影到線段 ab 上"""
    ax, ay = a
    bx, by = b
    px, py = p
    dx = bx - ax
    dy = by - ay
    len_sq = dx*dx + dy*dy
    if len_sq == 0:
        return list(a), float('inf'), 0
    t = max(0, min(1, ((px-ax)*dx + (py-ay)*dy) / len_sq))
    proj = [ax + t*dx, ay + t*dy]
    dist = math.sqrt((px-proj[0])**2 + (py-proj[1])**2)
    return proj, dist, t
```

**注意**：必須使用「投影法」而非「最近點法」，避免停站時列車偏移。

### 4.3 TRA station_id 衝突

TRA 和 THSR 使用相同的 station_id 編號系統！

| station_id | THSR 站名 | TRA 站名 |
|------------|-----------|----------|
| 0990 | 南港 | 松山 |
| 1000 | 台北 | 臺北 |
| 1010 | 板橋 | 萬華 |

**解決方案**：
- TRA 車站**不加入**共用 `stationNames` Map
- 使用 `TRA_STATION_NAMES` 獨立查找
- 在 `TrainInfoPanel.tsx` 中根據列車類型分開查找

### 4.4 時刻表時間格式

使用**相對秒數**（從發車時間起算）：

```json
// ✅ 正確 - 相對秒數
{"station_id": "1040", "arrival": 0, "departure": 60},
{"station_id": "1030", "arrival": 180, "departure": 240}

// ❌ 錯誤 - 絕對時間字串
{"station_id": "1040", "arrival": "06:00", "departure": "06:01"}
```

### 4.5 車站編號規則

**必須使用新編號！** 舊編號對照：

| 舊編號 | 新編號 | 車站 |
|--------|--------|------|
| 3250 | 3240 | 潭子 |
| 3260 | 3243 | 頭家厝 |
| 3270 | 3245 | 松竹 |
| 3280 | 3247 | 太原 |
| 3290 | 3249 | 精武 |
| 3340 | 3325 | 新烏日 |
| 3350 | 3330 | 成功 |

---

## 5. 新增路線流程

### Step 1: 資料盤點

1. 讀取 `TRACKS_STATUS.md` 確認現況
2. 檢查 Optra 備份是否有該路線：
   ```bash
   python3 -c "
   import json
   with open('public/data/tra/all_tracks_backup.geojson') as f:
       data = json.load(f)
   for feat in data['features']:
       if '{LINE}' in feat['properties'].get('line_id', ''):
           print(feat['properties'])
   "
   ```

### Step 2: 建立 Golden Track

```bash
# 從備份或 TDX 提取軌道
python3 scripts/tra/build_{line}_od_tracks.py
```

輸出檔案：
- `tracks_golden/{TRACK_ID}-0.geojson` (方向 0)
- `tracks_golden/{TRACK_ID}-1.geojson` (方向 1)

### Step 3: 建立 O-D Track

```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {
      "track_id": "YL-SL-SA-0",
      "origin": "樹林",
      "destination": "蘇澳",
      "direction": 0
    },
    "geometry": {
      "type": "LineString",
      "coordinates": [[lng, lat], ...]
    }
  }]
}
```

### Step 4: 計算 Station Progress

```bash
python3 scripts/tra/calc_progress.py <track_id> --apply
```

驗證規則：
- 起點 = 0.0, 終點 = 1.0
- 數值單調遞增
- 車站到軌道距離 < 50m

### Step 5: 建立測試時刻表

```bash
python3 scripts/tra/build_{line}_schedules.py
```

### Step 6: 程式碼整合

更新以下檔案：
1. `src/constants/traInfo.ts` - 新增路線和車站名稱
2. `src/engines/TraTrainEngine.ts` - O-D 軌道 ID 對映
3. `src/hooks/useTraData.ts` - 載入設定

### Step 7: 驗證

```bash
# 車站驗證
python3 scripts/tra/validate_stations.py

# 軌道驗證
python3 scripts/tra/validate_tracks.py --od

# 啟動開發伺服器測試
npm run dev
```

驗證項目：
- [ ] 列車沿軌道移動（無跳躍）
- [ ] 列車停在正確站點位置
- [ ] 資訊面板顯示正確
- [ ] 無控制台錯誤

### Step 8: 更新狀態文件

更新 `TRACKS_STATUS.md` 記錄：
- 路線狀態
- 已知問題與修正
- 更新日期

---

## 6. 更新時刻表流程

### 6.1 從 TDX 取得最新時刻表

```bash
cd scripts/tra/prepare_real_timetable
python3 01_fetch_tdx_timetable.py
```

### 6.2 轉換時刻表格式

```bash
python3 05_convert_tdx_timetable.py
```

輸出：`schedules_real/master_schedule.json`

### 6.3 驗證轉換結果

檢查：
- 總班次數是否合理
- 所有列車都有 `od_track_id`
- 無 backward 問題（station_progress 單調遞增）

### 6.4 時刻表格式說明

```json
{
  "train_id": "TC-110",
  "train_no": "110",
  "train_type": "自強(3000)",
  "train_type_code": "TC",
  "departure_time": "06:00:00",
  "od_track_id": "YL-SL-HL-0",
  "total_travel_time": 7200,
  "stations": [
    {"station_id": "1040", "arrival": 0, "departure": 120}
  ]
}
```

### 6.5 車種代碼對映

| TDX TrainTypeName | Code | 顏色 |
|-------------------|------|------|
| 自強(3000) | TC | 橘色 |
| 普悠瑪 | PP | 紅色 |
| 太魯閣 | TZ | 紅色 |
| 區間快 | CK | 藍色 |
| 區間 | LC | 淺藍 |
| 復興 | FX | 淺藍 |

---

## 7. 常見問題與解決方案

### Q1: 列車不動

**原因**：時刻表使用絕對時間而非相對秒數

**解決**：
```json
// 改為相對秒數
{"station_id": "1040", "arrival": 0, "departure": 60}
```

### Q2: 列車瞬間跳躍

**原因**：時刻表站點不在 od_station_progress.json 中

**解決**：
1. 檢查 station_id 是否正確
2. 確認該站在目標 O-D 軌道的 progress 中

### Q3: 列車走直線

**原因**：O-D 軌道座標點太少

**解決**：
1. 檢查 geojson 座標點數量（應 > 100）
2. 如有共線區段，使用高精度軌道座標

### Q4: 停站位置偏移

**原因**：Python 使用 Haversine 而非 Euclidean 計算距離

**解決**：統一使用歐幾里得距離

### Q5: 資訊面板顯示錯誤站名

**原因**：TRA station_id 與 THSR 衝突

**解決**：使用 `TRA_STATION_NAMES` 獨立查找

### Q6: 軌道有大跳躍（>1km）

**原因**：TDX 原始軌道資料有缺口

**解決**：
1. 使用 geojson.io 或 QGIS 手繪修正
2. 存放在 `tracks_handdrawn/` 目錄
3. 使用 `build_golden_track.py` 合併

### Q7: 終點站列車偏移

**原因**：軌道終點與站點有距離

**解決**：延伸軌道座標到站點位置（直線連結即可）

### Q8: 列車倒退（backward）

**原因**：station_progress 不是單調遞增

**解決**：
1. 檢查軌道方向是否正確
2. 重新計算 station_progress
3. 使用 `validate_tracks.py --check-backward` 驗證

---

## 8. 驗證工具使用

### 8.1 車站驗證

```bash
python3 scripts/tra/validate_stations.py
```

檢查項目：
- 重複 station_id
- 使用舊編號
- 名稱錯誤
- 距離過近

### 8.2 軌道驗證

```bash
python3 scripts/tra/validate_tracks.py --od
```

檢查項目：
- 大跳躍 (>1km)
- 急轉彎 (>120°)
- 回頭路段

### 8.3 車站投影

```bash
python3 scripts/tra/snap_stations.py <track_id> <station_ids...> --apply
```

將車站座標投影到軌道上。

### 8.4 進度值計算

```bash
python3 scripts/tra/calc_progress.py <track_id> --apply
```

重新計算指定軌道的 station_progress。

### 8.5 共用車站同步

```bash
python3 scripts/tra/sync_shared_stations.py --check
```

確保跨路線共用車站座標一致。

---

## 9. 經驗教訓（踩坑指南）

### 9.1 距離計算不一致（嚴重度：⭐⭐⭐⭐⭐）

**問題**：Python 用 Haversine，TypeScript 用 Euclidean，導致停站偏移。

**教訓**：永遠使用歐幾里得距離，不要引入任何 geodesic 相關的套件。

### 9.2 MultiLineString 段落亂序（嚴重度：⭐⭐⭐⭐）

**問題**：TDX 軌道資料的 MultiLineString 段落順序可能錯亂。

**解決方案**：使用 `reorder_multilinestring_by_geography()` 按地理位置排序。

```python
def reorder_multilinestring_by_geography(segments):
    """按地理位置排序 MultiLineString 段落"""
    # 從任意一段開始，找最近的下一段連接
    ...
```

### 9.3 舊版車站編號（嚴重度：⭐⭐⭐）

**問題**：TDX 可能回傳舊版車站編號，導致找不到 progress。

**解決方案**：建立舊→新編號對照表，自動轉換。

### 9.4 南迴線不經高雄站（嚴重度：⭐⭐⭐）

**問題**：SK 南迴線實際上是「鳳山→新左營」直達，不經過高雄市區。

**教訓**：不同物理路徑需要不同 O-D 軌道，即使終點相同。

### 9.5 手繪軌道被覆蓋（嚴重度：⭐⭐⭐）

**問題**：重新執行腳本後，辛苦手繪的修正被覆蓋。

**解決方案**：
- 手繪存放在 `tracks_handdrawn/`，永不自動覆蓋
- 使用 `build_golden_track.py` 合併 TDX + 手繪

### 9.6 時刻表時間格式（嚴重度：⭐⭐）

**問題**：時刻表使用字串格式 "06:00" 而非秒數 0。

**解決方案**：統一使用相對秒數，arrival/departure 從發車時間起算。

### 9.7 共用車站座標不一致（嚴重度：⭐⭐）

**問題**：同一車站在不同路線的座標不同，導致地圖上顯示多個點。

**解決方案**：使用 `sync_shared_stations.py` 確保一致性。

### 9.8 軌道與站點不一致的顯示（嚴重度：⭐）

**問題**：站點標記位置與列車停靠位置不同。

**解決方案**：使用投影法將站點座標投影到軌道上，確保一致。

---

## 10. 附錄

### 10.1 列車尺寸參數

| 系統 | 長度 (m) | 寬度 (m) | 高度 (m) |
|------|---------|---------|---------|
| TRTC 捷運 | 160 | 90 | 90 |
| TRA 台鐵 | 200 | 85 | 80 |
| THSR 高鐵 | 250 | 80 | 70 |

### 10.2 相關文件

| 文件 | 用途 |
|------|------|
| `TRACKS_STATUS.md` | 軌道狀態追蹤 |
| `STANDARD_WORKFLOW.md` | 標準工作流程 |
| `TRA_OD_IMPLEMENTATION_GUIDE.md` | O-D 系統實作指南 |

### 10.3 Agent 使用

| Agent | 用途 |
|-------|------|
| `tra-route-builder` | 新增台鐵路線 |
| `transport-validator` | 驗證資料格式 |

### 10.4 快速檢查清單

新增路線：
- [ ] 讀取 `TRACKS_STATUS.md`
- [ ] 軌道座標點 > 100
- [ ] station_progress 使用歐幾里得距離
- [ ] 起點 = 0.0, 終點 = 1.0
- [ ] 時刻表站數正確
- [ ] `traInfo.ts` 新增資訊
- [ ] `useTraData.ts` 新增載入
- [ ] `TraTrainEngine.ts` 新增對映
- [ ] 測試列車運行
- [ ] 更新 `TRACKS_STATUS.md`

更新時刻表：
- [ ] 執行 TDX 抓取腳本
- [ ] 執行轉換腳本
- [ ] 檢查班次數量
- [ ] 檢查無 backward 問題
- [ ] 測試列車運行

---

## 更新紀錄

| 日期 | 版本 | 說明 |
|------|------|------|
| 2026-01-29 | 1.0.0 | 初版，整合所有開發經驗 |
