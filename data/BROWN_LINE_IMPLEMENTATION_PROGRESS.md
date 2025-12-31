# 文湖線實作進度追蹤

> 最後更新: 2025-12-31
> 狀態: ✅ 完成

---

## 任務進度

| # | 任務 | 狀態 | 輸出檔案 |
|---|------|------|----------|
| 1 | 建立 brown_line_stations.geojson | ✅ 完成 | `public/data/brown_line_stations.geojson` |
| 2 | 轉換 WKT 軌道為 GeoJSON | ✅ 完成 | 暫存 (由 build_brown_line.py 處理) |
| 3 | 校準軌道座標 | ✅ 完成 | 內含於 build_brown_line.py |
| 4 | 建立雙向軌道檔案 | ✅ 完成 | `public/data/tracks/BR-1-0.geojson`, `BR-1-1.geojson` |
| 5 | 生成時刻表 JSON | ✅ 完成 | `public/data/schedules/BR-1-0.json`, `BR-1-1.json` |
| 6 | 更新 station_progress.json | ✅ 完成 | `public/data/station_progress.json` |
| 7 | 更新 useData.ts | ✅ 完成 | `src/hooks/useData.ts` |
| 8 | 更新 App.tsx | ✅ 完成 | `src/App.tsx` + `src/components/LineFilter.tsx` |
| 9 | 測試驗證 | ✅ 完成 | Build passed, Dev server tested |

---

## 資料來源

- `data/tdx_metro_test/metro_station_BR_20251231.json` - 車站座標
- `data/tdx_metro_test/metro_s2s_travel_time_BR_20251231.json` - 站間時間
- `data/tdx_metro_test/metro_frequency_BR_20251231.json` - 班距頻率
- `data/tdx_metro_test/metro_first_last_BR_20251231.json` - 首末班車
- `data/tdx_metro_test/metro_shape_BR_20251231.json` - 軌道幾何 (WKT)

---

## 關鍵參數

- 線路代碼: `BR`
- 軌道顏色: `#c48c31`
- 車站數: 24 站 (BR01-BR24)
- 終點站: 動物園 (BR01) ↔ 南港展覽館 (BR24)
- 營運時間: 06:00 - 24:00
- 班距: 尖峰 3 分鐘 / 離峰 7 分鐘 / 深夜 12 分鐘
- 全程時間: 44 分 40 秒
- 每方向班次: 201 班

---

## 執行記錄

### Task 1-3: 車站與軌道資料處理
- 完成時間: 2025-12-31
- 建立 `brown_line_stations.geojson` (24 站)
- 建立 `scripts/build_brown_line.py` 處理軌道轉換與校準
- 解決問題: WKT 軌道延伸至機廠，需截斷至車站範圍

### Task 4-6: 軌道與時刻表生成
- 完成時間: 2025-12-31
- BR-1-0.geojson: 動物園→南港展覽館 (505 座標點)
- BR-1-1.geojson: 南港展覽館→動物園 (505 座標點)
- 每方向 201 班次 (06:00-23:59)
- station_progress.json 正確映射 (BR01=0.0, BR24=1.0)

### Task 7-8: 前端整合
- 完成時間: 2025-12-31
- useData.ts: 新增 'BR-1-0', 'BR-1-1' 軌道 ID
- App.tsx: 新增 BR 顏色、圖例、篩選邏輯
- LineFilter.tsx: 新增 BR 按鈕

### Task 9: 測試驗證
- 完成時間: 2025-12-31
- TypeScript 編譯: 通過
- Vite Build: 成功 (dist/assets/index-*.js)
- Dev Server: 正常啟動 (http://localhost:5175/)

---

## 產出檔案清單

```
public/data/
├── brown_line_stations.geojson    # 24 站車站資料
├── station_progress.json          # 更新 BR-1-0, BR-1-1 進度
├── tracks/
│   ├── BR-1-0.geojson            # 動物園→南港展覽館
│   └── BR-1-1.geojson            # 南港展覽館→動物園
└── schedules/
    ├── BR-1-0.json               # 201 班次時刻表
    └── BR-1-1.json               # 201 班次時刻表

scripts/
└── build_brown_line.py           # 建置腳本 (可重複執行)

src/
├── hooks/useData.ts              # 新增 BR 軌道載入
├── App.tsx                       # 新增 BR 顏色、圖例
└── components/LineFilter.tsx     # 新增 BR 篩選按鈕
```
