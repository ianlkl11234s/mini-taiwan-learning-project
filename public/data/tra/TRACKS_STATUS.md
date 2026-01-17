# TRA 軌道資料狀態追蹤

> 最後更新：2026-01-17

## Golden Track 架構

自 2026-01-10 起，採用 Golden Track 架構管理軌道資料：

```
tracks_golden/      ← 黃金版本（前端載入來源）
tracks_handdrawn/   ← 手繪修正（永不覆蓋）
tracks_official/    ← TDX 原始資料（fallback）
tracks_od/          ← O-D 專屬軌道（列車位置計算）
```

**工作流程**：
1. 手繪修正存放在 `tracks_handdrawn/{路線}/` 目錄
2. 使用 `build_golden_track.py` 合併 TDX + 手繪產生黃金版本
3. 使用 `extract_golden_tracks.py` 驗證並產生 `manifest.json`
4. 前端 `useTraData.ts` 優先載入 `tracks_golden/`

**目錄結構**：
- `tracks_golden/manifest.json` - 軌道狀態清單
- `tracks_handdrawn/YL/` - 宜蘭線手繪區段 (4 檔案)
- `tracks_handdrawn/KL/` - 基隆支線手繪區段 (2 檔案)
- `tracks_handdrawn/BH/` - 北迴線手繪區段 (2 檔案)
- `tracks_handdrawn/WL-S-handraw-template.geojson` - 西部幹線南段手繪區段 (林內、斗南、大湖、岡山)

---

## 狀態說明

| 狀態 | 說明 |
|------|------|
| ✅ 完成 | 軌道資料正確，列車行駛正常 |
| 🔧 手繪補充 | 原始資料有問題，部分區段已改為手繪 |
| ⏸️ 直線替代 | 問題區段暫以站點直線連接，待手繪 |
| 📋 待處理 | 尚未開始處理 |
| ❌ 有問題 | 已知問題，尚未修正 |

---

## 支線軌道 (Branch Lines)

### NW 內灣線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | ✅ 完成 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | ✅ TDX 真實資料 |
| 備註 | 新竹-竹中-內灣 |

### LJ 六家線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | ✅ 完成 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | ✅ TDX 真實資料 |
| 備註 | 竹中-六家，與內灣線共用竹中站 |

### SH 沙崙線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | ✅ 完成 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | ✅ TDX 真實資料 |
| 備註 | 中洲-沙崙 |

### PX 平溪線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | 📋 待處理 |
| O-D 軌道 | 📋 待處理 |
| 時刻表 | 📋 待處理 |
| 備註 | 三貂嶺-菁桐 |

### JJ 集集線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | 📋 待處理 |
| O-D 軌道 | 📋 待處理 |
| 時刻表 | 📋 待處理 |
| 備註 | 二水-車埕 |

### CZ 成追線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | 📋 待處理 |
| O-D 軌道 | 📋 待處理 |
| 時刻表 | 📋 待處理 |
| 備註 | 追分-成功 |

### KL 基隆支線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | 🔧 使用 WL-N |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | ✅ TDX 真實資料 |
| 備註 | 八堵-基隆，從 WL-N 擷取軌道 |

**已知問題**：
- [x] 三坑站 (0910) 座標誤差約 1km → 已 snap 到軌道端點，待 WL-N 軌道修正後更新

---

## 幹線軌道 (Main Lines)

### YL 宜蘭線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | 🔧 手繪補充 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | ✅ TDX 真實資料 |
| 備註 | 八堵-蘇澳，目前僅包含臺北起迄列車 |

**已知問題與修正**：
- [x] MultiLineString 段落順序錯亂 → 已用 `fix_yl_track_segments.py` 修正
- [x] 福隆-貢寮 座標跳動 → 已手繪並整合
- [x] 貢寮-雙溪 座標跳動 → 已手繪並整合
- [x] 雙溪-牡丹 座標跳動 → 已手繪並整合
- [x] 猴硐-瑞芳 座標跳動 → 已手繪並整合

**手繪檔案**：`tracks_official/yl_gaps_to_fill.geojson` (已整合)

### BH 北迴線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | 🔧 手繪補充 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | 🔧 模擬資料 (TDX 維護中) |
| 備註 | 蘇澳新-花蓮 |

**已知問題與修正**：
- [x] 原始資料顯示兩條軌道 → 已用 `rebuild_bh_from_gaps.py` 從手繪重建

**手繪檔案**：`tracks_official/gaps_to_fill.geojson` (BH 相關部分)

### WL-N 西部幹線北段
| 項目 | 狀態 |
|------|------|
| 軌道資料 | ❌ 有問題 |
| O-D 軌道 | ⚠️ 部分使用 |
| 時刻表 | - |
| 備註 | 竹南-基隆 (含基隆支線) |

**已知問題**：
- [ ] 包含基隆支線，列車會繞道基隆 → 待真實時刻表後處理
- [ ] 需要建立臺北-八堵專用軌道，排除基隆支線

### WL-S 西部幹線南段
| 項目 | 狀態 |
|------|------|
| 軌道資料 | 🔧 手繪補充 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | 🔧 測試資料 |
| 備註 | 彰化-新左營 (39站) |

**已知問題與修正**：
- [x] 合併 WL-S1 (新左營→石龜) + WL-S2 (石龜→彰化) 軌道
- [x] 計算完整 station_progress：39 個車站 (3360 彰化 ~ 4340 新左營)
- [x] O-D 軌道與 Golden Track 完全一致
- [x] 林內附近軌道迴圈 → 手繪修正
- [x] 斗南附近軌道迴圈 → 手繪修正
- [x] 大湖附近軌道分岔 → 手繪修正
- [x] 岡山附近軌道分岔 → 手繪修正
- [x] 全部 39 站投影到軌道上，停車點與站點標示一致 (距離 < 1m)

**手繪檔案**：`tracks_handdrawn/WL-S-handraw-template.geojson`
**O-D 軌道**：`tracks_od/WL-CH-ZY-0.geojson`, `WL-ZY-CH-1.geojson`
**Golden Track**：`tracks_golden/WL-S-CH-ZY-0.geojson`, `WL-S-CH-ZY-1.geojson`

### TL 臺東線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | ✅ 完成 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | 🔧 模擬資料 |
| 備註 | 花蓮-臺東 (27站) |

**已知問題與修正**：
- [x] TDX 軌道 (TD-0/TD-1) MultiLineString 段落亂序 → 已用 `build_tl_od_tracks.py` 重新排序
- [x] 軌道覆蓋所有 27 站，平均誤差 28.6m，最大誤差 174.2m (瑞源站)

**Golden Track**：`tracks_golden/TL-0.geojson`, `TL-1.geojson`
**O-D 軌道**：`tracks_od/TL-HL-TT.geojson`, `TL-TT-HL.geojson`

### SK 南迴線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | ✅ 完成 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | 📋 待處理 |
| 備註 | 臺東-新左營 (合併 NH+PT+WL-S1) |

**已知問題與修正**：
- [x] NH/PT MultiLineString 段落亂序 → 使用 `reorder_multilinestring_by_geography()` 按地理位置排序
- [x] 軌道覆蓋 30 站 (臺東→新左營)
- [ ] 臺東站誤差 661m (軌道未完全延伸至車站) → 可接受

**O-D 軌道**：`tracks_od/SK-TT-ZY-0.geojson`, `SK-ZY-TT-1.geojson`
**合併來源**：NH (南迴線) + PT (屏東線) + WL-S1 (縱貫線南段)

### PT 屏東線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | ✅ 完成 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | 🔧 測試資料 |
| 備註 | 新左營-枋寮 (27 站)，從 SK 軌道擷取 |

**已知問題與修正**：
- [x] 原始 TDX 軌道是 MultiLineString，新左營→高雄段有缺口 → 從 SK O-D 軌道擷取座標解決
- [x] O-D 軌道與 SK 軌道座標完全一致，避免重疊段顯示多條線

**O-D 軌道**：`tracks_od/PT-ZY-PL-0.geojson`, `PT-PL-ZY-1.geojson`
**擷取來源**：從 `SK-ZY-TT-1` 和 `SK-TT-ZY-0` 擷取新左營↔枋寮段

---

## 處理腳本

### Golden Track 相關 (建議使用)

| 腳本 | 用途 |
|------|------|
| `split_handdrawn_segments.py` | 拆分手繪區段到 tracks_handdrawn/ 目錄 |
| `extract_golden_tracks.py` | 從 all_tracks.geojson 提取黃金軌道 + 驗證 |
| `build_golden_track.py` | 重建軌道：TDX + 手繪 → 黃金版本 |

### 路線建立相關

| 腳本 | 用途 |
|------|------|
| `build_yl_bh_od_tracks.py` | 建立 YL/BH O-D 專屬軌道 |
| `build_kl_od_tracks.py` | 從 WL-N 建立 KL 基隆支線 O-D 軌道 |
| `build_tl_od_tracks.py` | 建立 TL 臺東線 O-D 專屬軌道 |
| `build_sk_od_tracks.py` | 建立 SK 南迴線 O-D 專屬軌道 (合併 NH+PT+WL-S1) |
| `fetch_yl_kl_timetable.py` | 從 TDX API 取得 YL/KL 真實時刻表 |

### 舊版腳本 (已整合或棄用)

| 腳本 | 用途 |
|------|------|
| `fix_yl_track_segments.py` | 修正 YL MultiLineString 段落順序 |
| `fix_yl_problem_segments.py` | 產生 YL 手繪填補檔案 |
| `smooth_yl_track.py` | YL 軌道平滑化 (已棄用) |
| `rebuild_bh_from_gaps.py` | 從手繪資料重建 BH 軌道 |
| `rebuild_yl_from_gaps.py` | 從手繪資料重建 YL 軌道 |
| `generate_yl_bh_schedules.py` | 產生 YL/BH 模擬時刻表 (已棄用) |

---

## 資料來源

- **TDX Shape API**: 原始軌道資料
- **TDX Schedule API**: 真實時刻表 (部分路線維護中)
- **手繪補充**: geojson.io / QGIS 手動繪製

---

## 更新紀錄

### 2026-01-17 (WL-S 西部幹線南段)
- 新增 WL-S 西部幹線南段 O-D 軌道資料 (彰化-新左營)
- 合併 WL-S1 (新左營→石龜) + WL-S2 (石龜→彰化) TDX 軌道
- 建立 Golden Track：`WL-S-CH-ZY-0.geojson`, `WL-S-CH-ZY-1.geojson`
- 建立 O-D 軌道：`WL-CH-ZY-0.geojson` (彰化→新左營), `WL-ZY-CH-1.geojson` (新左營→彰化)
- 計算完整 station_progress：39 個車站 (3360 彰化 ~ 4340 新左營)
- 建立測試時刻表：`WL-CH-ZY-0.json`, `WL-ZY-CH-1.json` (每小時一班，06:00-22:00)
- 新增腳本：`build_wl_south_od_tracks.py`, `build_wl_south_schedules.py`
- 更新 `useTraData.ts`、`TraTrainEngine.ts` 支援 WL-S 路線
- **手繪修正**：林內、斗南、大湖、岡山附近軌道迴圈/分岔問題
- **車站投影**：全部 39 站投影到軌道上，確保停車點與站點標示一致
- 新增手繪模板：`tracks_handdrawn/WL-S-handraw-template.geojson`

### 2026-01-16 (PT 屏東線)
- 新增 PT 屏東線 O-D 軌道資料 (新左營-枋寮)
- **關鍵修正**：從 SK O-D 軌道擷取座標，確保 PT 和 SK 在重疊段（新左營↔枋寮）座標完全一致
- 解決原始 TDX 軌道的 MultiLineString 缺口問題（新左營→高雄段）
- 建立 O-D 軌道：`PT-ZY-PL-0.geojson` (新左營→枋寮), `PT-PL-ZY-1.geojson` (枋寮→新左營)
- 計算完整 station_progress：27 個車站 (4340 新左營 ~ 5120 枋寮)
- 建立測試時刻表：`PT-ZY-PL-0.json`, `PT-PL-ZY-1.json`
- 更新 Golden Tracks：`PT-0.geojson`, `PT-1.geojson`, `SK-0.geojson`, `SK-1.geojson`
- 更新 `useTraData.ts`、`TraTrainEngine.ts` 支援 PT 路線

### 2026-01-15 (SK 南迴線)
- 新增 SK 南迴線 O-D 軌道資料 (臺東-新左營)
- 合併三條路線軌道：NH (南迴線) + PT (屏東線) + WL-S1 (縱貫線南段)
- 開發 `reorder_multilinestring_by_geography()` 函數處理亂序的 MultiLineString 段落
- 建立 O-D 軌道：`SK-TT-ZY-0.geojson` (臺東→新左營), `SK-ZY-TT-1.geojson` (新左營→臺東)
- 共計 30 個車站，1946 個座標點
- 臺東站誤差 661m (軌道未完全延伸至車站)，其餘車站誤差均在 200m 以內
- 新增腳本：`build_sk_od_tracks.py`

### 2026-01-15 (TL 臺東線)
- 新增 TL 臺東線軌道資料
- 處理 TDX TD-0/TD-1 的 MultiLineString 段落亂序問題
- 建立 Golden Track：`TL-0.geojson`, `TL-1.geojson`
- 建立 O-D 軌道：`TL-HL-TT.geojson`, `TL-TT-HL.geojson`
- 建立測試時刻表：`TL-0.json`, `TL-1.json` (各 6 班次)
- 更新 `useTraData.ts`、`TraTrainEngine.ts`、`traInfo.ts`
- 新增腳本：`build_tl_od_tracks.py`

### 2026-01-10 (Golden Track 架構)
- 新增 `tracks_golden/` 目錄作為黃金版本來源
- 新增 `tracks_handdrawn/` 目錄，手繪區段永不覆蓋
- 拆分手繪區段：YL (4檔案)、KL (2檔案)、BH (2檔案)
- 新增腳本：`split_handdrawn_segments.py`、`extract_golden_tracks.py`、`build_golden_track.py`
- 更新 `useTraData.ts`：優先載入 `tracks_golden/`，fallback 到 `tracks_official/`
- 產生 `manifest.json` 追蹤軌道驗證狀態
- 驗證結果：8 條通過 (NW, LJ, CZ, PX)，10 條需檢查 (YL, BH, KL, JJ, SH 有座標跳躍)

### 2026-01-10 (TDX 真實時刻表整合)
- KL 基隆支線：新增 O-D 軌道 (KL-TP-KL, KL-KL-TP)
- KL 基隆支線：TDX 真實時刻表 (61 班次)
- YL 宜蘭線：TDX 真實時刻表 (33 班次，臺北起迄)
- 新增 `fetch_yl_kl_timetable.py` TDX 時刻表轉換腳本
- 新增 `build_kl_od_tracks.py` 基隆支線軌道建立腳本
- 更新 `useTraData.ts` 和 `TraTrainEngine.ts` 支援 KL 路線

### 2026-01-10
- YL 宜蘭線：手繪區段整合完成（福隆-貢寮、貢寮-雙溪、雙溪-牡丹、猴硐-瑞芳）
- 新增 `rebuild_yl_from_gaps.py` 腳本
- 新增 `fix_yl_problem_segments.py` 腳本（產生手繪填補檔案）
- 更新 tra-route-builder agent 加入軌道狀態確認流程

### 2025-01-10
- 建立此追蹤檔案
- YL 宜蘭線：修正 MultiLineString 段落順序
- YL 宜蘭線：貢寮-雙溪、雙溪-牡丹、猴硐-瑞芳 改為直線替代
- BH 北迴線：從手繪資料重建完成
- 時刻表時間修正：站間時間累加邏輯修正

### 2025-01-09
- NW 內灣線、LJ 六家線、SH 沙崙線 完成
