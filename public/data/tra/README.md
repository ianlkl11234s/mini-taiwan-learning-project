# TRA 台鐵資料目錄

## 目錄結構

```
tra/
├── README.md                 # 本文件
├── stations.geojson          # 原始車站座標
├── stations_snapped.geojson  # 對齊軌道後的車站座標（程式使用）
│
├── schedules_real/           # 時刻表
│   └── master_schedule.json  # 主時刻表（992 班）
│
├── tracks_golden/            # 顯示用精修軌道（優先載入）
├── tracks_official/          # 顯示用官方軌道（備用）
├── tracks_od/                # O-D 計算用軌道（列車位置計算）
│   ├── *.geojson             # 各 O-D 軌道
│   └── od_station_progress.json  # 站點進度映射
│
├── docs/                     # 文件
│   ├── TRACKS_STATUS.md      # 軌道處理狀態
│   ├── REAL_TIMETABLE_PLAN.md
│   ├── STANDARD_WORKFLOW.md
│   └── ...
│
└── tracks_archive/           # 歸檔（暫存，可能刪除）
    ├── data_backup/          # TDX 處理中間資料
    ├── schedules_od_backup/  # 舊格式時刻表
    ├── schedules_by_od_backup/  # 轉換中間檔
    ├── tracks_handdrawn_backup/ # 手繪軌道片段
    └── ...
```

## 程式碼使用的檔案

| 檔案 | 用途 | 載入位置 |
|------|------|----------|
| `stations_snapped.geojson` | 車站顯示 | `useTraData.ts` |
| `schedules_real/master_schedule.json` | 列車時刻表 | `useTraData.ts` |
| `tracks_golden/*.geojson` | 地圖軌道顯示 | `useTraData.ts` |
| `tracks_official/*.geojson` | 軌道顯示（備用） | `useTraData.ts` |
| `tracks_od/*.geojson` | 列車位置計算 | `useTraData.ts` |
| `tracks_od/od_station_progress.json` | 站點進度映射 | `useTraData.ts` |

## 軌道系統說明

詳見 [docs/TRACK_SYSTEM.md](docs/TRACK_SYSTEM.md)

## 更新時刻表

1. 執行 TDX 轉換腳本：
   ```bash
   cd scripts/tra/prepare_real_timetable
   python3 01_fetch_tdx_timetable.py
   python3 05_convert_tdx_timetable.py
   ```

2. 輸出位置：`schedules_real/master_schedule.json`

## 注意事項

- `tracks_archive/` 為暫存歸檔，確認不需要後可刪除
- 修改軌道後需重新計算 `od_station_progress.json`
- 新增路線需更新 `useTraData.ts` 的載入清單
