# Mini Taipei 3D

台北捷運即時列車模擬系統 - 在 3D 地圖上視覺化呈現列車運行狀態

> 本專案啟發自 [Mini Tokyo 3D](https://github.com/nagix/mini-tokyo-3d)，一個超讚的的東京交通即時 3D 視覺化專案。感謝 [@nagix](https://github.com/nagix) 的開源貢獻，讓我能夠學習！

## 專案結構

```
mini-taipei-v3/
├── viewer/           # React 前端應用 (主要專案)
├── data_collector/   # 資料收集腳本 (TDX API)
└── docs/             # 內部開發文件 (不包含在 git 中)
```

## 快速開始

### 1. 啟動前端應用

```bash
cd viewer
npm install
cp .env.example .env   # 填入 Mapbox Token
npm run dev
```

開啟 http://localhost:5173 即可看到列車模擬

### 2. 取得 API Token

| 服務 | 用途 | 申請連結 |
|------|------|----------|
| Mapbox | 地圖渲染 | https://account.mapbox.com/access-tokens/ |
| TDX | 捷運資料 | https://tdx.transportdata.tw/ |

### 3. 環境變數設定

**viewer/.env** (前端)
```env
VITE_MAPBOX_TOKEN=your_mapbox_token
```

**.env** (資料收集，選用)
```env
TDX_APP_ID=your_tdx_app_id
TDX_APP_KEY=your_tdx_app_key
```

## 功能特色

- 即時列車位置模擬
- Mapbox GL 3D 地圖
- 時間控制 (1x-60x 加速)
- 多路線支援 (淡水信義線)

## 技術棧

| 層級 | 技術 |
|------|------|
| 前端 | React 19 + TypeScript + Vite |
| 地圖 | Mapbox GL JS |
| 資料 | TDX 運輸資料流通服務 |

## 開發指南

詳細的開發文件請參考 `viewer/README.md`

## 授權

MIT License
