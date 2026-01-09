# Auto Update Docs Hook

## 描述

在特定程式碼檔案被修改後，自動更新相關文件以保持同步。確保文件與實作狀態一致。

## 觸發條件

當以下檔案被修改時自動執行：

| 觸發檔案 | 更新目標 |
|----------|----------|
| `src/constants/traInfo.ts` | `docs/TRA_IMPLEMENTATION_ROADMAP.md` |
| `src/engines/*TrainEngine.ts` | `README.md` 支援路線列表 |
| `src/layers/*3DLayer.ts` | `README.md` 核心模組表 |
| `public/data/*/schedules/*.json` | 對應系統的班次統計 |

## 更新規則

### 1. TRA 實作進度更新

**觸發**: `src/constants/traInfo.ts` 被修改

**動作**: 更新 `docs/TRA_IMPLEMENTATION_ROADMAP.md` 的實作狀態

```markdown
<!-- 自動更新區塊 -->
### 已完成實作
| 路線 | 代碼 | 狀態 | 實作內容 |
|------|------|------|----------|
| 沙崙線 | SH | ✅ 完成 | ... |
| 內灣線 | NW | ✅ 完成 | ... |
| 六家線 | LJ | ✅ 完成 | ... |
| 平溪線 | PX | ✅ 完成 | ... |  <!-- 新增 -->
<!-- /自動更新區塊 -->
```

**更新邏輯**:
```python
def update_tra_roadmap():
    # 讀取 traInfo.ts 中的 TRA_LINES
    tra_lines = parse_tra_lines('src/constants/traInfo.ts')

    # 讀取現有文件
    roadmap = read_file('docs/TRA_IMPLEMENTATION_ROADMAP.md')

    # 更新狀態表格
    for line_id, info in tra_lines.items():
        # 檢查是否有對應時刻表
        has_schedule = check_schedule_exists(line_id)

        # 更新狀態
        status = '✅ 完成' if has_schedule else '⚠️ 軌道已備齊'
        update_table_row(roadmap, line_id, status)

    # 寫回文件
    write_file('docs/TRA_IMPLEMENTATION_ROADMAP.md', roadmap)
```

### 2. README 支援路線更新

**觸發**: 新增 `*TrainEngine.ts` 或修改路線資訊

**動作**: 更新 `README.md` 的支援路線表格

```markdown
<!-- 自動更新區塊: 支援路線 -->
## 支援路線

### 台北都會區 (TPE)
| 路線 | 代碼 | 車站數 | 營運模式 |
|------|------|--------|----------|
| 🔴 淡水信義線 | R | 28 站 | ... |
...
<!-- /自動更新區塊 -->
```

**更新邏輯**:
```python
def update_readme_routes():
    # 掃描所有 lineInfo/xxxInfo.ts
    all_lines = []
    for info_file in glob('src/constants/*Info.ts'):
        lines = parse_line_info(info_file)
        all_lines.extend(lines)

    # 按城市分組
    grouped = group_by_city(all_lines)

    # 生成 Markdown 表格
    tables = generate_route_tables(grouped)

    # 更新 README
    update_readme_section('支援路線', tables)
```

### 3. 核心模組表更新

**觸發**: 新增 `*3DLayer.ts` 或 `use*Data.ts`

**動作**: 更新 `README.md` 的核心模組表格

```markdown
<!-- 自動更新區塊: 核心模組 -->
### 核心模組
| 模組 | 檔案 | 說明 |
|------|------|------|
| TrainEngine | `src/engines/TrainEngine.ts` | 台北捷運列車狀態管理 |
| Tra3DLayer | `src/layers/Tra3DLayer.ts` | 台鐵 3D 圖層 |  <!-- 新增 -->
...
<!-- /自動更新區塊 -->
```

### 4. 班次統計更新

**觸發**: `schedules/*.json` 被修改

**動作**: 更新對應系統的班次統計

```python
def update_schedule_stats(system):
    # 計算總班次
    total = 0
    for schedule_file in glob(f'public/data/{system}/schedules/*.json'):
        data = json.load(schedule_file)
        total += len(data.get('departures', []))

    # 更新對應文件中的統計
    # 例如: README.md 或系統專屬文件
    update_stat_in_docs(system, 'departure_count', total)
```

## 執行時機

### Claude Code 整合

當 Claude Code 完成以下操作後，應檢查並執行此 hook：

1. **編輯 traInfo.ts 後**
   ```
   [Edit traInfo.ts 完成]
   → 檢測到 TRA 路線資訊變更
   → 更新 TRA_IMPLEMENTATION_ROADMAP.md 狀態
   → 顯示: "已更新 TRA 實作進度文件"
   ```

2. **新增 Engine/Layer 後**
   ```
   [Write new System3DLayer.ts 完成]
   → 檢測到新增 3D 圖層
   → 更新 README.md 核心模組表
   → 顯示: "已更新 README 模組列表"
   ```

3. **修改時刻表後**
   ```
   [Edit schedules/XX-0.json 完成]
   → 重新計算班次統計
   → 更新相關文件
   → 顯示: "已更新班次統計: 總計 XXX 班"
   ```

## 更新標記格式

使用 HTML 註解標記自動更新區塊：

```markdown
<!-- AUTO-UPDATE:section-name START -->
這裡的內容會被自動更新
<!-- AUTO-UPDATE:section-name END -->
```

Claude Code 應只修改標記區塊內的內容，保留其他手動編輯的部分。

## 衝突處理

如果自動更新與手動修改衝突：

1. 優先保留手動修改
2. 將自動更新建議顯示給用戶
3. 詢問是否覆蓋或合併

```
⚠️ 偵測到文件衝突

docs/TRA_IMPLEMENTATION_ROADMAP.md 有手動修改，
自動更新建議：
- 將「平溪線」狀態從「⚠️ 軌道已備齊」改為「✅ 完成」

選項：
1. 套用自動更新 (覆蓋手動修改)
2. 保留手動修改 (跳過自動更新)
3. 顯示差異比較
```

## 停用自動更新

在特定 commit 中停用：
```bash
SKIP_AUTO_DOCS=1 git commit -m "..."
```

或在檔案中加入標記：
```markdown
<!-- SKIP-AUTO-UPDATE -->
此文件已停用自動更新
```
