# Pre-Commit Validate Hook

## 描述

在 commit 前自動驗證運輸資料檔案的格式和完整性，防止錯誤資料進入版本庫。

## 觸發條件

當以下路徑的檔案被修改並準備 commit 時自動執行：
- `public/data/**/*.json`
- `public/data/**/*.geojson`

## 驗證規則

### 1. JSON 語法檢查

所有 `.json` 和 `.geojson` 檔案必須是有效的 JSON。

```bash
# 驗證指令
for file in $(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(json|geojson)$'); do
  python -m json.tool "$file" > /dev/null || echo "❌ Invalid JSON: $file"
done
```

### 2. 時刻表格式驗證

針對 `schedules/*.json` 和 `schedules_od/*.json`：

```javascript
// 必要欄位
{
  "track_id": "string (required)",
  "route_id": "string (optional)",
  "departures": [
    {
      "train_id": "string (required, unique)",
      "departure_time": "HH:MM:SS or HH:MM (required)",
      "stations": [
        {
          "station_id": "string (required)",
          "arrival": "number >= 0 (required)",
          "departure": "number >= arrival (required)"
        }
      ]
    }
  ]
}
```

**驗證邏輯**：
```python
def validate_schedule(data):
    errors = []

    if 'track_id' not in data:
        errors.append("Missing track_id")

    if 'departures' not in data:
        errors.append("Missing departures")
        return errors

    train_ids = set()
    for i, dep in enumerate(data['departures']):
        # train_id 唯一性
        if dep.get('train_id') in train_ids:
            errors.append(f"Duplicate train_id: {dep['train_id']}")
        train_ids.add(dep.get('train_id'))

        # departure_time 格式
        time_str = dep.get('departure_time', '')
        if not re.match(r'^\d{2}:\d{2}(:\d{2})?$', time_str):
            errors.append(f"Invalid departure_time format: {time_str}")

        # 站點時間遞增
        stations = dep.get('stations', [])
        for j in range(1, len(stations)):
            if stations[j]['arrival'] < stations[j-1]['departure']:
                errors.append(
                    f"Station time not increasing: {dep['train_id']} "
                    f"station {j}"
                )

    return errors
```

### 3. Station Progress 驗證

針對 `station_progress.json` 和 `od_station_progress.json`：

```python
def validate_station_progress(data):
    errors = []

    for track_id, stations in data.items():
        values = list(stations.values())

        # 範圍檢查
        if min(values) != 0.0:
            errors.append(f"{track_id}: 起點 progress != 0.0")
        if max(values) != 1.0:
            errors.append(f"{track_id}: 終點 progress != 1.0")

        # 數值有效性
        for station_id, progress in stations.items():
            if not (0.0 <= progress <= 1.0):
                errors.append(
                    f"{track_id}/{station_id}: "
                    f"progress {progress} out of range"
                )

    return errors
```

### 4. GeoJSON 座標驗證

針對 `tracks/**/*.geojson`：

```python
def validate_track_geojson(data):
    errors = []

    if data.get('type') != 'Feature':
        if data.get('type') == 'FeatureCollection':
            for feature in data.get('features', []):
                errors.extend(validate_track_feature(feature))
        else:
            errors.append("Invalid GeoJSON type")
        return errors

    return validate_track_feature(data)

def validate_track_feature(feature):
    errors = []
    props = feature.get('properties', {})
    geom = feature.get('geometry', {})

    # 必要屬性
    if 'track_id' not in props:
        errors.append("Missing track_id in properties")

    # 幾何類型
    if geom.get('type') != 'LineString':
        errors.append(f"Expected LineString, got {geom.get('type')}")
        return errors

    # 座標檢查
    coords = geom.get('coordinates', [])
    if len(coords) < 2:
        errors.append("LineString must have >= 2 coordinates")

    # 座標範圍 (台灣)
    for i, coord in enumerate(coords):
        lng, lat = coord[0], coord[1]
        if not (119 <= lng <= 123):
            errors.append(f"Longitude {lng} at index {i} out of Taiwan range")
        if not (21 <= lat <= 26):
            errors.append(f"Latitude {lat} at index {i} out of Taiwan range")

    return errors
```

## 錯誤處理

### 錯誤等級

| 等級 | 說明 | 處理方式 |
|------|------|----------|
| ❌ Error | 嚴重錯誤 | 阻止 commit |
| ⚠️ Warning | 潛在問題 | 顯示警告但允許 commit |
| ℹ️ Info | 資訊提示 | 僅顯示 |

### 錯誤訊息範例

```
========================================
Pre-Commit 資料驗證
========================================

檢查: public/data/tra/schedules_od/PX-0.json
❌ Error: Duplicate train_id: PX-0-0600

檢查: public/data/tra/tracks_od/od_station_progress.json
⚠️ Warning: PX-SD-JT 只有 7 個車站，建議確認

檢查: public/data/tra/tracks_od/PX-SD-JT.geojson
✅ Pass

========================================
結果: 1 錯誤, 1 警告
Commit 已阻止，請修正錯誤後重試
========================================
```

## 跳過驗證

緊急情況下可跳過驗證：
```bash
git commit --no-verify -m "緊急修復"
```

**注意**：僅在緊急情況使用，應儘快補上正確驗證。

## 與 Claude Code 整合

當 Claude Code 準備執行 git commit 時，應：

1. 先執行此 hook 的驗證邏輯
2. 如有錯誤，顯示詳細訊息並建議修正
3. 如有警告，詢問用戶是否繼續
4. 驗證通過後才執行 commit
