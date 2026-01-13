# TRA Golden Tracks

這是 TRA 軌道的「黃金版本」目錄，包含已驗證的正確軌道資料。

## 目的

- **單一來源真相 (Single Source of Truth)**：所有軌道顯示都從這裡載入
- **不可變手繪層**：手繪修正存放在 `tracks_handdrawn/`，永不被覆蓋
- **品質保證**：每條軌道都經過驗證，記錄在 `manifest.json`

## 目錄結構

```
tracks_golden/
├── README.md           # 本檔案
├── manifest.json       # 軌道狀態清單
├── YL-0.geojson       # 宜蘭線南下
├── YL-1.geojson       # 宜蘭線北上
├── BH-0.geojson       # 北迴線
├── KL-0.geojson       # 基隆支線
├── NW-0.geojson       # 內灣線
├── LJ-0.geojson       # 六家線
├── SH-0.geojson       # 沙崙線
└── ...
```

## manifest.json 說明

```json
{
  "tracks": {
    "YL-0": {
      "status": "golden" | "needs_review",
      "source": "tdx_with_handdrawn" | "handdrawn_only" | "tdx",
      "handdrawn_segments": ["tracks_handdrawn/YL/..."],
      "point_count": 2888,
      "validated_at": "2026-01-10T..."
    }
  }
}
```

## 使用方式

### 前端載入

`useTraData.ts` 會優先從 `tracks_golden/` 載入軌道，找不到時 fallback 到 `tracks_official/`。

### 重建軌道

```bash
source venv/bin/activate
python scripts/tra/build_golden_track.py YL
python scripts/tra/extract_golden_tracks.py
```

### 驗證軌道

```bash
python scripts/tra/extract_golden_tracks.py  # 會顯示驗證結果
```

## 相關目錄

| 目錄 | 用途 |
|------|------|
| `tracks_golden/` | 黃金版本軌道（本目錄） |
| `tracks_handdrawn/` | 手繪修正區段（永不覆蓋） |
| `tracks_official/` | TDX 原始資料（fallback 用） |
| `tracks_od/` | O-D 專屬軌道（列車位置計算） |

## 注意事項

1. **不要直接編輯** 這裡的檔案，請使用腳本重建
2. **手繪修正** 放在 `tracks_handdrawn/`，會被腳本自動整合
3. **驗證失敗** 的軌道標記為 `needs_review`，需要手動檢查
