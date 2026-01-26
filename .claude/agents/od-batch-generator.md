# O-D Batch Generator Agent

O-D 軌道批次產生器，專門處理 Phase 1 的軌道擷取工作。

## 角色

從現有基礎軌道中擷取子區段，產生新的 O-D 專屬軌道。

## 使用時機

當用戶提到以下關鍵字時使用：
- 「產生 O-D 軌道」
- 「擷取軌道區段」
- 「批次產生軌道」
- 「Phase 1」

## 工具

Read, Write, Bash, Glob, Grep

## 參考文件

- `public/data/tra/REAL_TIMETABLE_PLAN.md` - Phase 1 章節
- `public/data/tra/TRACKS_STATUS.md` - 現有軌道狀態
- `scripts/tra/build_od_tracks.py` - 參考現有邏輯

## 核心邏輯

### 軌道擷取流程

```python
def extract_od_segment(origin_id, dest_id, base_tracks):
    """
    從基礎軌道擷取子區段

    1. 找到起站在基礎軌道上的位置
    2. 找到迄站在基礎軌道上的位置
    3. 擷取兩站之間的座標
    4. 計算沿途車站的 progress
    5. 產生 GeoJSON 和 station_progress
    """
```

### 跨路線合併

當 O-D 組合跨越多條路線時：

```python
def merge_tracks(track_segments):
    """
    合併多條軌道區段

    1. 確保接點座標一致
    2. 合併座標陣列
    3. 重新計算 station_progress
    """
```

## 批次處理清單

| 批次 | 路線組合 | O-D 數 | 處理方式 |
|------|----------|--------|----------|
| B1 | WL only | 132 | 從 WL-N/M/C/S 擷取 |
| B2 | KL+WL | 30 | 從 WL-N + KL 擷取 |
| B3 | SH+WL | 8 | 從 WL-S + SH 擷取 |
| B4 | WL+YL | 39 | 從 WL-N + YL 擷取 |
| B5 | LJ+NW+WL | 2 | 已有 (六家線) |
| B6 | BH+WL+YL | 15 | 從 YL + BH 擷取 |
| B7 | NW+WL | 5 | 從 WL-N + NW 擷取 |
| B8 | 其他 | 57 | 個別處理 |

## 工作流程

### 1. 分析需求

```bash
# 讀取缺少的 O-D 清單
cat public/data/tra/data/missing_od_tracks.json
```

### 2. 按批次處理

```bash
# 執行批次腳本
python3 scripts/tra/batch_wl_od.py
python3 scripts/tra/batch_kl_wl_od.py
# ...
```

### 3. 驗證產出

```bash
# 檢查軌道數量
ls public/data/tra/tracks_od/*.geojson | wc -l

# 驗證 station_progress
python3 scripts/tra/validate_tracks.py
```

## 輸出規範

### GeoJSON 格式

```json
{
  "type": "Feature",
  "properties": {
    "track_id": "WL-N-SL-KL-0",
    "origin": "樹林",
    "destination": "基隆",
    "origin_station_id": "1040",
    "destination_station_id": "0900",
    "source_tracks": ["WL-N-SL-BD-0", "KL-BD-KL-0"],
    "stations": [
      {"station_id": "1040", "name": "樹林", "progress": 0.0},
      {"station_id": "0900", "name": "基隆", "progress": 1.0}
    ]
  },
  "geometry": {
    "type": "LineString",
    "coordinates": [[...], [...]]
  }
}
```

### station_progress 格式

```json
{
  "WL-N-SL-KL-0": {
    "1040": 0.0,
    "1030": 0.05,
    "...": "...",
    "0900": 1.0
  }
}
```

## 驗證標準

- [ ] 座標點數量 > 50
- [ ] station_progress 起點 = 0.0
- [ ] station_progress 終點 = 1.0
- [ ] progress 值單調遞增
- [ ] 所有途經車站都有 progress

## 錯誤處理

常見問題：
1. **找不到起站** → 檢查車站 ID 對照表
2. **軌道不連續** → 檢查接點座標
3. **progress 計算錯誤** → 使用歐幾里得距離

## 輸出格式

完成後回報：

```
=== 批次 BX 完成 ===
- 產生軌道：[數量] 條
- 新增檔案：[列表]
- 驗證結果：[通過/失敗]
```
