# TRA 軌道資料狀態追蹤

> 最後更新：2026-01-25

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
- `tracks_handdrawn/WL-C-changhua-gap-template.geojson` - 西部幹線海線手繪區段 (彰化→追分)
- `tracks_handdrawn/WL-C-taichungport-gap-template.geojson` - 西部幹線海線手繪區段 (台中港附近)

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
| 軌道資料 | ✅ 完成 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | ✅ 完成 |
| 備註 | 三貂嶺-菁桐 |

### SA 深澳線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | ✅ 完成 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | 🔧 測試資料 |
| 備註 | 瑞芳-八斗子 (3站) |

**已知問題與修正**：
- [x] TDX 軌道不包含瑞芳站 (距離 828m) → 線性插值延伸
- [x] 軌道覆蓋所有 3 站，車站誤差 < 10m

**Golden Track**：`tracks_golden/SA-RF-BD-0.geojson`, `SA-BD-RF-1.geojson`
**O-D 軌道**：`tracks_od/SA-RF-BD-0.geojson`, `SA-BD-RF-1.geojson`

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
| 軌道資料 | ✅ 完成 |
| O-D 軌道 | ✅ 完成 (兩段) |
| 時刻表 | 🔧 測試資料 |
| 備註 | 分為兩段：竹南-樹林 (22站) + 樹林-八堵 (已完成) |

**WL-N-ZN-SL (竹南↔樹林)**：
- [x] 從 TDX WL-N-0 軌道提取竹南→樹林區間 (2318 pts)
- [x] 計算完整 station_progress：22 個車站 (1250 竹南 ~ 1040 樹林)
- [x] 建立測試時刻表：34 班次 (每小時一班，06:00-22:00)
- [x] 更新 useTraData.ts、TraTrainEngine.ts 支援 WL-N 路線
- [x] 小跳躍點 6 處 (500-760m) → 可接受，不影響行駛

**WL-N-SL-BD (樹林↔八堵)**：
- [x] 已完成 (Step 1)

**O-D 軌道檔案**：
- `tracks_od/WL-ZN-SL-0.geojson` (竹南→樹林)
- `tracks_od/WL-SL-ZN-1.geojson` (樹林→竹南)
- `tracks_od/WL-SL-BD-0.geojson` (樹林→八堵) - 已存在
- `tracks_od/WL-BD-SL-1.geojson` (八堵→樹林) - 已存在

**Golden Track**：
- `tracks_golden/WL-N-ZN-SL-0.geojson` (竹南→樹林)
- `tracks_golden/WL-N-ZN-SL-1.geojson` (樹林→竹南)

**腳本**：`build_wl_north_od_tracks.py`、`build_wl_north_schedules.py`

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

### WL-C 西部幹線海線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | 🔧 手繪補充 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | 🔧 測試資料 |
| 備註 | 彰化-竹南 (18 站)，合併 WL-H + WL-H2 軌道 + 手繪修正 |

**已知問題與修正**：
- [x] 合併 WL-H (追分→白沙屯) + WL-H2 (龍港→談文) 軌道
- [x] 軌道覆蓋所有 18 站，車站誤差均 < 50m
- [x] 延伸軌道到彰化站 (起點) 和竹南站 (終點)
- [x] 彰化→追分 軌道跳躍 (5.5km) → 手繪修正 (100 座標)
- [x] 清水→台中港 軌道跳躍 (1.5km) → 手繪修正
- [x] 台中港附近 軌道跳躍 (743m) → 手繪修正
- [x] 其餘 4 處小跳躍 (<600m) → 線性插值修正
- [x] 時刻表格式修正 (arrival/departure 改用秒數格式)

**手繪檔案**：
- `tracks_handdrawn/WL-C-changhua-gap-template.geojson` (彰化→追分)
- `tracks_handdrawn/WL-C-taichungport-gap-template.geojson` (台中港附近)

**Golden Track**：`tracks_golden/WL-C-CH-ZN-0.geojson`, `WL-C-ZN-CH-1.geojson`
**O-D 軌道**：`tracks_od/WL-C-CH-ZN-0.geojson`, `WL-C-ZN-CH-1.geojson`
**合併來源**：WL-H (追分→白沙屯) + WL-H2 (龍港→談文) + 手繪修正

### WL-M 西部幹線山線
| 項目 | 狀態 |
|------|------|
| 軌道資料 | 🔧 手繪補充 |
| O-D 軌道 | ✅ 完成 |
| 時刻表 | 🔧 測試資料 |
| 備註 | 竹南-彰化 (23 站)，使用 TDX WL-M 軌道 + 手繪修正 |

**已知問題與修正**：
- [x] 從備份檔案讀取 WL-M-0/WL-M-1 軌道 (2592 pts)
- [x] 延伸軌道到竹南站和彰化站
- [x] 計算完整 station_progress：23 個車站
- [x] 移除 7 個舊編號車站 (3250, 3260, 3270, 3280, 3290, 3340, 3350)，僅保留新編號
- [x] 修正 4 個車站名稱錯誤 (潭子、大慶、烏日、成功)
- [x] 后里-泰安 軌道繞路 → 手繪修正
- [x] 烏日-新烏日 軌道偏離 → 手繪修正
- [x] 6 站座標投影到軌道 (松竹、精武、五權、大慶、烏日、成功)
- [x] 與成追線共用成功站 (3330)

**手繪檔案**：`tracks_handdrawn/WL-M-handraw-template.geojson`
**Golden Track**：`tracks_golden/WL-M-ZN-CH-0.geojson`, `WL-M-CH-ZN-1.geojson`
**O-D 軌道**：`tracks_od/WL-M-ZN-CH-0.geojson`, `WL-M-CH-ZN-1.geojson`
**腳本**：`build_wl_mountain_od_tracks.py`, `build_wl_mountain_schedules.py`
**問題報告**：`WL-M_ISSUE_REPORT.md`

---

## 處理腳本

### 驗證工具 (建議使用)

| 腳本 | 用途 |
|------|------|
| `validate_stations.py` | 車站驗證 (重複 ID、舊編號、名稱錯誤、距離過近) |
| `validate_tracks.py` | 軌道驗證 (大跳躍、急轉彎、回頭路段) |
| `snap_stations.py` | 車站投影 (將車站座標投影到軌道上) |
| `calc_progress.py` | 進度值計算 (計算車站在軌道上的 progress) |
| `sync_shared_stations.py` | 共用車站同步 (確保跨路線車站一致性) |

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
| `build_wl_south_od_tracks.py` | 建立 WL-S 西部幹線南段 O-D 專屬軌道 |
| `build_wl_south_schedules.py` | 建立 WL-S 西部幹線南段測試時刻表 |
| `build_wl_coast_od_tracks.py` | 建立 WL-C 西部幹線海線 O-D 專屬軌道 |
| `build_wl_coast_schedules.py` | 建立 WL-C 西部幹線海線測試時刻表 |
| `build_wl_mountain_od_tracks.py` | 建立 WL-M 西部幹線山線 O-D 專屬軌道 |
| `build_wl_mountain_schedules.py` | 建立 WL-M 西部幹線山線測試時刻表 |
| `build_wl_north_od_tracks.py` | 建立 WL-N 西部幹線北段 O-D 專屬軌道 |
| `build_wl_north_schedules.py` | 建立 WL-N 西部幹線北段測試時刻表 |
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

### 2026-01-25 (SA 深澳線完成)
- **SA 深澳線完成** (瑞芳-八斗子，3 站)
- TDX 軌道不包含瑞芳站，線性插值延伸 828m
- 建立 Golden Track 和 O-D 軌道：`SA-RF-BD-0`, `SA-BD-RF-1`
- 建立測試時刻表：34 班次 (每小時一班，06:00-22:00)
- 更新 `useTraData.ts`、`TraTrainEngine.ts` 支援 SA 路線
- **TRA 軌道建置基本完成**

### 2026-01-25 (WL-C 海線手繪完成)
- **WL-C 西部幹線海線完成** (彰化-竹南，18 站)
- 手繪修正彰化→追分段 (5.5km 跳躍，100 座標點)
- 手繪修正清水→台中港段 (1.5km + 743m 跳躍)
- 線性插值修正其餘 4 處小跳躍 (<600m)
- 軌道座標點從原本約 900 點增加到 1959 點
- 修正時刻表格式：arrival/departure 改用秒數格式 (原為字串格式)
- O-D 軌道命名標準化：`WL-C-CH-ZN-0`, `WL-C-ZN-CH-1`
- 啟用海線載入：更新 `useTraData.ts` 取消註解
- 更新 `TraTrainEngine.ts` 軌道對映
- 海線列車現已正常運行

### 2026-01-24 (WL-N 竹南↔樹林完成)
- **WL-N 西部幹線北段完成** (竹南-樹林，22 站)
- 從 TDX WL-N-0 軌道擷取竹南→樹林區間 (2324 pts)
- 計算完整 station_progress：22 個車站
- 建立測試時刻表：34 班次 (每小時一班，06:00-22:00)
- 更新 useTraData.ts、TraTrainEngine.ts 支援 WL-N 路線
- **待處理**：竹南附近有 1.1km 軌道缺口，北新竹附近有小跳躍點

### 2026-01-24 (WL-M 完成 + 驗證工具)
- **WL-M 西部幹線山線完成** (竹南-彰化，23 站)
- 手繪修正兩段問題軌道：后里-泰安、烏日-新烏日
- 移除 7 個舊編號車站，修正 4 個名稱錯誤
- 投影 6 個車站座標到軌道上
- 與成追線統一共用成功站 (3330)
- Golden Track 與 O-D 軌道同步
- 建立 `WL-M_ISSUE_REPORT.md` 記錄問題處理經驗
- **新增驗證工具**：
  - `validate_stations.py` - 車站資料驗證
  - `validate_tracks.py` - 軌道資料驗證
  - `snap_stations.py` - 車站投影工具
  - `calc_progress.py` - 進度值計算工具
  - `sync_shared_stations.py` - 共用車站同步工具
- **更新 Agent**：
  - `tra-route-builder.md` - 新增 Optra 備份優先、驗證流程
  - `tra-validator.md` - 新增專用驗證 Agent

### 2026-01-24 (WL-M 初步建立)
- 新增 WL-M 西部幹線山線 O-D 軌道資料 (竹南-彰化)
- 從備份檔案讀取 TDX WL-M-0/WL-M-1 軌道 (2592 pts)
- 延伸軌道到竹南站 (北端) 和彰化站 (南端)
- 建立 Golden Track：`WL-M-ZN-CH-0.geojson`, `WL-M-CH-ZN-1.geojson`
- 建立 O-D 軌道：`WL-M-ZN-CH-0.geojson` (竹南→彰化), `WL-M-CH-ZN-1.geojson` (彰化→竹南)
- 計算完整 station_progress：23 個車站 (1250 竹南 ~ 3360 彰化)
- 建立測試時刻表：`WL-M-ZN-CH-0.json`, `WL-M-CH-ZN-1.json` (每小時一班，06:00-22:00)
- 新增腳本：`build_wl_mountain_od_tracks.py`, `build_wl_mountain_schedules.py`
- 更新 `useTraData.ts`、`TraTrainEngine.ts` 支援 WL-M 路線

### 2026-01-17 (WL-C 西部幹線海線)
- 新增 WL-C 西部幹線海線 O-D 軌道資料 (彰化-竹南)
- 合併 WL-H (追分→白沙屯) + WL-H2 (龍港→談文) TDX 軌道
- 建立 Golden Track：`WL-C-CH-ZN-0.geojson`, `WL-C-ZN-CH-1.geojson`
- 建立 O-D 軌道：`WL-CH-ZN-0.geojson` (彰化→竹南), `WL-ZN-CH-1.geojson` (竹南→彰化)
- 計算完整 station_progress：18 個車站 (3360 彰化 ~ 1250 竹南)
- 建立測試時刻表：`WL-CH-ZN-0.json`, `WL-ZN-CH-1.json` (每小時一班，06:00-22:00)
- 新增腳本：`build_wl_coast_od_tracks.py`, `build_wl_coast_schedules.py`
- 更新 `useTraData.ts`、`TraTrainEngine.ts`、`traInfo.ts` 支援 WL-C 路線
- **待修正**：7 處跳躍點 (最大 5.5km 在彰化附近)，需要手繪補充

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
