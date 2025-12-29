# Mini Taipei 3D

台北捷運即時列車模擬系統 - 在 3D 地圖上視覺化呈現列車運行狀態

> 本專案啟發自 [Mini Tokyo 3D](https://github.com/nagix/mini-tokyo-3d)，一個超讚的的東京交通即時 3D 視覺化專案。感謝 [@nagix](https://github.com/nagix) 的開源貢獻，讓我能夠學習！

## 快速開始

```bash
# 安裝依賴
npm install

# 設定環境變數
cp .env.example .env
# 編輯 .env，填入你的 Mapbox Token

# 啟動開發伺服器
npm run dev
```

開啟 http://localhost:5173 即可看到列車模擬

## 功能特色

- 即時列車位置模擬
- Mapbox GL 3D 地圖
- 時間控制 (1x-60x 加速)
- 多路線支援 (淡水信義線)

## 專案結構

```
mini-taipei-3d/
├── src/                 # React 原始碼
│   ├── components/      # UI 元件
│   ├── engines/         # 時間與列車引擎
│   ├── hooks/           # React Hooks
│   └── types/           # TypeScript 型別
├── public/data/         # 靜態資料
│   ├── tracks/          # 軌道 GeoJSON
│   ├── schedules/       # 時刻表 JSON
│   └── *.geojson        # 車站資料
├── tools/               # 開發工具
│   └── data_collector/  # TDX 資料收集腳本
└── docs/                # 內部文件 (不含在 git)
```

## 環境變數

```env
VITE_MAPBOX_TOKEN=your_mapbox_token_here
```

取得 Mapbox Token: https://account.mapbox.com/access-tokens/

## 技術棧

| 層級 | 技術 |
|------|------|
| 前端 | React 19 + TypeScript + Vite |
| 地圖 | Mapbox GL JS |
| 資料 | TDX 運輸資料流通服務 |

## 建置與部署

```bash
# 建置生產版本
npm run build

# 預覽建置結果
npm run preview
```

## 資料收集工具

如需更新捷運資料，請參考 `tools/data_collector/`：

```bash
cd tools/data_collector
pip install -r requirements.txt
# 設定 TDX API 金鑰後執行腳本
```

## 授權

MIT License
