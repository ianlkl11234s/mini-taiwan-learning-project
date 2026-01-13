根據先前的分析，我來深度思考這個軌道資料管理問題，並提出完整的解決方案。

  問題診斷

  核心問題：資料一致性斷裂

  目前的問題流程：

  TDX/SHP 原始資料 → 有座標跳躍問題
         ↓
  手繪修正 → gaps_to_fill.geojson / yl_gaps_to_fill.geojson
         ↓
  rebuild_*.py → 只更新 all_tracks.geojson ❌
         ↓
  useTraData.ts → 載入個別檔案 (YL-0.geojson) ← 從未被更新！

  根本原因：
  1. 兩套來源不同步：all_tracks.geojson 是正確的，但前端載入的是個別檔案
  2. 手繪資料分散：手繪檔案分散在 gaps_to_fill.geojson 和 yl_gaps_to_fill.geojson
  3. 腳本更新不完整：rebuild_yl_from_gaps.py 只更新合併檔，不更新個別檔
  4. 無版本控制概念：沒有「黃金版本」的概念，每次重跑腳本可能覆蓋修正

  當前資料結構問題

  public/data/tra/
  ├── tracks_official/          # 顯示用軌道（問題所在）
  │   ├── all_tracks.geojson   # ✅ 有正確的 YL（rebuilt_from_gaps=True）
  │   ├── YL-0.geojson         # ❌ 舊的 MultiLineString，有跳躍
  │   ├── YL-1.geojson         # ❌ 舊的 MultiLineString，有跳躍
  │   ├── BH-0.geojson         # 狀態不明
  │   └── ...
  ├── tracks_od/               # O-D 專屬軌道（相對正確）
  │   └── od_station_progress.json
  ├── gaps_to_fill.geojson     # 手繪資料（BH + KL 區段）
  └── yl_gaps_to_fill.geojson  # 手繪資料（YL 區段）

  ---
  解決方案：Golden Track 架構

  設計原則

  1. 單一來源真相 (Single Source of Truth)：所有軌道都從「黃金版本」產生
  2. 不可變手繪層 (Immutable Hand-drawn Layer)：手繪修正永遠保留，永不覆蓋
  3. 自動化一致性：腳本確保所有輸出檔案同步
  4. 明確狀態追蹤：每個軌道都有明確的處理狀態標記

  新的目錄結構

  public/data/tra/
  ├── tracks_golden/            # 🏆 黃金版本 - 最終正確的軌道
  │   ├── YL-0.geojson         # LineString, 已整合手繪
  │   ├── YL-1.geojson
  │   ├── BH-0.geojson
  │   ├── KL-0.geojson
  │   └── manifest.json        # 每條軌道的來源和狀態
  │
  ├── tracks_raw/              # 📦 TDX 原始資料 - 參考用，不直接使用
  │   ├── YL-0-raw.geojson
  │   └── ...
  │
  ├── tracks_handdrawn/        # ✏️ 手繪修正 - 永不覆蓋
  │   ├── YL/
  │   │   ├── 7290-7300-福隆貢寮.geojson
  │   │   ├── 7300-7310-貢寮雙溪.geojson
  │   │   ├── 7310-7320-雙溪牡丹.geojson
  │   │   └── 7350-7360-猴硐瑞芳.geojson
  │   ├── BH/
  │   │   └── ...
  │   └── KL/
  │       ├── 0920-0910-八堵三坑.geojson
  │       └── 0910-0900-三坑基隆.geojson
  │
  ├── tracks_od/               # 🚂 O-D 專屬軌道 - 從 golden 產生
  │   ├── YL-TP-HL.geojson
  │   └── od_station_progress.json
  │
  └── schedules_od/            # 📅 時刻表
      └── ...

  manifest.json 結構

  {
    "version": "1.0.0",
    "generated_at": "2026-01-10T12:00:00Z",
    "tracks": {
      "YL-0": {
        "status": "golden",
        "source": "tdx_with_handdrawn",
        "handdrawn_segments": [
          "tracks_handdrawn/YL/7290-7300-福隆貢寮.geojson",
          "tracks_handdrawn/YL/7300-7310-貢寮雙溪.geojson",
          "tracks_handdrawn/YL/7310-7320-雙溪牡丹.geojson",
          "tracks_handdrawn/YL/7350-7360-猴硐瑞芳.geojson"
        ],
        "point_count": 2888,
        "geometry_type": "LineString",
        "validated_at": "2026-01-10T12:00:00Z"
      },
      "KL-0": {
        "status": "golden",
        "source": "handdrawn_only",
        "handdrawn_segments": [
          "tracks_handdrawn/KL/0920-0910-八堵三坑.geojson",
          "tracks_handdrawn/KL/0910-0900-三坑基隆.geojson"
        ],
        "point_count": 33,
        "geometry_type": "LineString",
        "validated_at": "2026-01-10T12:00:00Z"
      }
    }
  }

  工作流程

                  新增/修正軌道流程
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
     TDX 原始資料   手繪修正      既有黃金版本
          │             │             │
          ▼             ▼             │
     tracks_raw/   tracks_handdrawn/  │
          │             │             │
          └──────┬──────┘             │
                 ▼                    │
      build_golden_track.py ←─────────┘
                 │
                 ▼
        tracks_golden/ (黃金版本)
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
  build_od_tracks.py   useTraData.ts
       │                   │
       ▼                   ▼
  tracks_od/          前端顯示

  關鍵腳本設計

  1. build_golden_track.py - 黃金軌道建構器

  """
  黃金軌道建構器
  - 從 TDX 原始資料 + 手繪修正 → 產生黃金版本
  - 或直接使用手繪資料（如 KL）
  - 永遠不覆蓋 tracks_handdrawn/
  """

  def build_golden_track(route_id: str):
      """
      1. 檢查 tracks_handdrawn/{route_id}/ 是否有手繪資料
      2. 如有 TDX 原始資料，載入並識別問題區段
      3. 用手繪資料替換問題區段
      4. 驗證座標連續性（無 >500m 跳躍）
      5. 輸出到 tracks_golden/
      6. 更新 manifest.json
      """
      pass

  def validate_track(coords: List) -> List[str]:
      """驗證軌道品質，回傳問題列表"""
      issues = []
      for i in range(len(coords) - 1):
          dist = euclidean_distance(coords[i], coords[i+1])
          if dist > 0.005:  # ~500m
              issues.append(f"Jump at index {i}: {dist*111:.1f}km")
      return issues

  2. sync_all_tracks.py - 同步腳本

  """
  同步所有軌道檔案
  - 確保 tracks_golden/ 的內容同步到所有需要的地方
  - 產生 all_tracks.geojson
  - 產生 O-D 軌道
  """

  def sync_all():
      """
      1. 從 tracks_golden/ 讀取所有黃金軌道
      2. 合併成 all_tracks.geojson（如仍需要）
      3. 呼叫 build_od_tracks.py 產生 O-D 軌道
      4. 驗證所有輸出一致性
      """
      pass

  前端調整

  修改 useTraData.ts 改為從 tracks_golden/ 載入：

  // 修改前
  const trackUrl = `/data/tra/tracks_official/${trackId}.geojson`;

  // 修改後
  const trackUrl = `/data/tra/tracks_golden/${trackId}.geojson`;

  ---
  立即行動計畫

  Phase 1: 建立黃金版本目錄結構

  # 1. 建立新目錄
  mkdir -p public/data/tra/tracks_golden
  mkdir -p public/data/tra/tracks_raw
  mkdir -p public/data/tra/tracks_handdrawn/{YL,BH,KL,NW,LJ,SH,PX,JJ,CZ}

  # 2. 搬移現有手繪資料
  # - yl_gaps_to_fill.geojson → tracks_handdrawn/YL/ (拆分)
  # - gaps_to_fill.geojson 中的 KL 區段 → tracks_handdrawn/KL/

  Phase 2: 遷移現有正確資料

  1. 從 all_tracks.geojson 提取 YL-0, YL-1, BH-0, BH-1（有 rebuilt_from_gaps=True）
  2. 從最新 KL 軌道提取 KL-0, KL-1
  3. 建立 manifest.json

  Phase 3: 建立自動化腳本

  1. build_golden_track.py - 單一軌道建構
  2. sync_all_tracks.py - 全部同步
  3. validate_tracks.py - 驗證所有軌道品質

  Phase 4: 前端調整

  1. 修改 useTraData.ts 使用 tracks_golden/
  2. 測試所有路線顯示正確

  ---
  防呆機制

  1. 手繪資料保護

  # 在任何修改腳本中加入
  def ensure_handdrawn_safe():
      """確保不會覆蓋手繪資料"""
      handdrawn_path = Path("public/data/tra/tracks_handdrawn")
      if handdrawn_path.exists():
          # 檢查 git status，如果 handdrawn 有變更則中止
          result = subprocess.run(
              ["git", "status", "--porcelain", str(handdrawn_path)],
              capture_output=True
          )
          if result.stdout:
              raise RuntimeError("手繪資料有未提交變更，請先處理")

  2. 軌道品質驗證

  def validate_before_save(track_data):
      """儲存前驗證"""
      coords = track_data["geometry"]["coordinates"]

      # 1. 檢查座標跳躍
      for i in range(len(coords) - 1):
          dist = euclidean_distance(coords[i], coords[i+1])
          if dist > 0.005:  # ~500m
              raise ValueError(f"Coordinate jump at {i}: {dist*111:.1f}km")

      # 2. 檢查 geometry type
      if track_data["geometry"]["type"] != "LineString":
          raise ValueError(f"Must be LineString, got {track_data['geometry']['type']}")

      # 3. 檢查最小點數
      if len(coords) < 10:
          raise ValueError(f"Too few points: {len(coords)}")

  3. 變更前後對比

  def compare_before_after(old_file, new_data):
      """比較變更前後，顯示差異摘要"""
      old_data = json.load(open(old_file))

      old_coords = old_data["features"][0]["geometry"]["coordinates"]
      new_coords = new_data["features"][0]["geometry"]["coordinates"]

      print(f"點數變化: {len(old_coords)} → {len(new_coords)}")
      print(f"起點: {old_coords[0]} → {new_coords[0]}")
      print(f"終點: {old_coords[-1]} → {new_coords[-1]}")

      # 計算總長度變化
      old_len = sum(euclidean_distance(old_coords[i], old_coords[i+1])
                    for i in range(len(old_coords)-1))
      new_len = sum(euclidean_distance(new_coords[i], new_coords[i+1])
                    for i in range(len(new_coords)-1))
      print(f"總長度變化: {old_len*111:.2f}km → {new_len*111:.2f}km")

  ---
  總結
  ┌────────────────────────┬────────────────────────────────────────────┐
  │          問題          │                  解決方案                  │
  ├────────────────────────┼────────────────────────────────────────────┤
  │ 手繪修正被覆蓋         │ tracks_handdrawn/ 獨立目錄，永不自動修改   │
  ├────────────────────────┼────────────────────────────────────────────┤
  │ 個別檔案與合併檔不同步 │ 改用 tracks_golden/，單一來源產生所有輸出  │
  ├────────────────────────┼────────────────────────────────────────────┤
  │ 無法追蹤軌道狀態       │ manifest.json 記錄每條軌道的來源和驗證時間 │
  ├────────────────────────┼────────────────────────────────────────────┤
  │ 腳本互相干擾           │ 明確的流程：raw + handdrawn → golden → od  │
  ├────────────────────────┼────────────────────────────────────────────┤
  │ 座標跳躍問題           │ 儲存前強制驗證，超過 500m 跳躍則拒絕       │
  └────────────────────────┴────────────────────────────────────────────┘
  這個架構確保：
  1. ✅ 手繪修正永久保留
  2. ✅ 有明確的「黃金版本」
  3. ✅ 所有輸出檔案自動同步
  4. ✅ 新增路線時不會破壞既有軌道
  5. ✅ 每次變更都可追溯

  是否要我開始實作 Phase 1，建立新的目錄結構並遷移現有資料？