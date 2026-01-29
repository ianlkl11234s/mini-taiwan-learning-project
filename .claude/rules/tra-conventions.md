# TRA 台鐵開發規範

處理台鐵相關功能時必須遵守的規範。

## O-D 專屬軌道系統

TRA 使用 Origin-Destination 專屬軌道，避免動態切換造成的抖動。

### 檔案結構
```
public/data/tra/
├── tracks_golden/       # 精修軌道（優先載入）
├── tracks_official/     # 官方軌道（備用）
├── tracks_od/           # O-D 專屬軌道（列車計算用）
│   └── od_station_progress.json
├── schedules_real/      # 真實時刻表
│   └── master_schedule.json  # 992 班 TDX 資料
└── docs/
    └── TRACKS_STATUS.md # 軌道狀態追蹤（必讀！）
```

### 路線代碼
| 代碼 | 路線 | 狀態 |
|------|------|------|
| NW | 內灣線 | ✅ |
| LJ | 六家線 | ✅ |
| SH | 沙崙線 | ✅ |
| PX | 平溪線 | ✅ |
| JJ | 集集線 | ✅ |
| CZ | 成追線 | ✅ |
| SA | 深澳線 | ✅ |
| KL | 基隆支線 | ✅ |
| WL-N | 西部幹線北段 | ✅ |
| WL-S | 西部幹線南段 | ✅ |
| WL-M | 西部幹線山線 | ✅ |
| WL-C | 西部幹線海線 | ✅ |
| YL | 宜蘭線 | ✅ |
| BH | 北迴線 | ✅ |
| TL | 臺東線 | ✅ |
| SK | 南迴線 | ✅ |
| PT | 屏東線 | ✅ |

## 關鍵規則

### 1. 距離計算必須使用歐幾里得距離

**Python 和 TypeScript 都必須一致！**

```python
# ✅ 正確 - 歐幾里得距離
def calculate_distance(coord1, coord2):
    dx = coord2[0] - coord1[0]
    dy = coord2[1] - coord1[1]
    return math.sqrt(dx * dx + dy * dy)

# ❌ 錯誤 - 不要用 Haversine
from geopy.distance import geodesic  # 禁用！
```

### 2. station_progress 規範

- 起點站 progress = 0.0
- 終點站 progress = 1.0
- 數值必須單調遞增
- 使用歐幾里得距離計算

### 3. TRA station_id 衝突

TRA 和 THSR 使用相同的 station_id 編號（如 0990, 1000）。

- TRA 車站**不加入**共用 `stationNames` Map
- 使用 `TRA_STATION_NAMES` 獨立查找
- 在 `TrainInfoPanel.tsx` 中特別處理

### 4. O-D 軌道方向對映

`TraTrainEngine.ts` 的 `getTrackIdFromOdTrackId()` 函數規則：

```typescript
// mainStations 定義每條線的「起點站」
// 起點站 = 方向 0 的終點（通常是連接幹線的車站）
const mainStations: Record<string, string> = {
  'NW': 'CC',  // 內灣線起點 = 竹中
  'SH': 'TN',  // 沙崙線起點 = 臺南
  // 新增路線時必須加入對應條目
};
```

### 5. 軌道狀態追蹤

**開始任何 TRA 工作前，必須先讀取 `TRACKS_STATUS.md`！**

狀態標記：
- ✅ 完成 - 軌道與時刻表皆完成
- 🔧 手繪補充 - 軌道部分區段使用手繪修正

> 截至 2026-01-29，所有路線皆已完成 ✅

## 新增路線檢查清單

- [ ] 讀取 `TRACKS_STATUS.md` 確認狀態
- [ ] 軌道座標點數量 > 100
- [ ] station_progress 使用歐幾里得距離
- [ ] 起點 = 0.0, 終點 = 1.0
- [ ] 時刻表站數正確
- [ ] `traInfo.ts` 新增路線資訊
- [ ] `useTraData.ts` 新增路線到載入清單
- [ ] `TraTrainEngine.ts` 新增 mainStations 條目
- [ ] 測試列車沿軌道移動
- [ ] 更新 `TRACKS_STATUS.md`
