# Mini Taiwan 效能優化計畫

> 建立日期：2026-01-29
> 狀態：規劃中

## 問題描述

使用「跟隨模式」時會出現卡頓現象，需要進行效能分析與優化。

---

## 效能瓶頸分析

### 🔴 高優先度問題

#### 1. TrainEngine 每幀重建所有列車

**位置**：`src/engines/TrainEngine.ts:435-571`

**問題**：
```typescript
update(currentTimeSeconds: number): Train[] {
  this.activeTrains.clear();  // 每幀清空！

  for (const [trackId, schedule] of this.schedules) {
    for (const departure of schedule.departures) {
      // 重建所有列車...
    }
  }
  return Array.from(this.activeTrains.values());
}
```

**影響**：
- 即使只有少量列車位置改變，也要重建整個 Map
- 992 班列車 × 60 FPS = 每秒處理 59,520 次列車計算

**解決方案**：增量更新，只更新位置改變的列車

---

#### 2. 軌道距離重複計算

**位置**：`src/engines/TrainEngine.ts:119-165`

**問題**：
```typescript
function interpolateOnLineString(coords, progress) {
  const totalLength = calculateTotalLength(coords);  // 每幀重算！
  for (let i = 0; i < coords.length - 1; i++) {
    const segmentLength = distance(coords[i], coords[i + 1]);  // 重複計算！
  }
}
```

**影響**：
- 同一軌道的總長度被重複計算數百次
- 線段距離也重複計算

**解決方案**：
- 資料載入時預計算 `totalLength` 和 `cumulativeDistances[]`
- 存入軌道 metadata

---

#### 3. selectedTrain 搜尋效率低

**位置**：`src/App.tsx:500-521`

**問題**：
```typescript
const selectedTrain = useMemo(() => {
  const mrtTrain = filteredTrains.find(t => t.trainId === selectedTrainId);      // O(n)
  const thsrTrain = filteredThsrTrains.find(t => t.trainId === selectedTrainId); // O(n)
  const krtcTrain = filteredKrtcTrains.find(t => t.trainId === selectedTrainId); // O(n)
  const klrtTrain = filteredKlrtTrains.find(t => t.trainId === selectedTrainId); // O(n)
  const tmrtTrain = filteredTmrtTrains.find(t => t.trainId === selectedTrainId); // O(n)
  const traTrain = filteredTraTrains.find(t => t.trainId === selectedTrainId);   // O(n)
  // ...
}, [...]);
```

**影響**：
- 每次列車更新都執行 6 次 O(n) 搜尋
- 跟隨模式下每幀都要搜尋

**解決方案**：
- 使用 `Map<trainId, Train>` 快取
- O(1) 查找

---

#### 4. 3D 層 calculateBearing() 效能差

**位置**：`src/layers/Train3DLayer.ts:383-394`

**問題**：
```typescript
private calculateBearing(train: Train): number {
  const coords = track.geometry.coordinates;
  for (let i = 0; i < coords.length - 1; i++) {  // O(軌道點數)
    distSq = this.pointToSegmentDistSq(train.position, coords[i], coords[i+1]);
  }
}
```

**影響**：
- 每列車每幀執行 O(軌道點數) 搜尋
- 軌道平均 1000+ 點 × 60 列車 = 每幀 60,000+ 次距離計算

**解決方案**：
- 使用空間索引（四叉樹/BVH）
- 或根據 progress 值直接定位線段

---

### 🟠 中優先度問題

#### 5. 6 個獨立的時間訂閱

**位置**：`src/App.tsx:1984-2157`

**問題**：
```typescript
// 每個運輸系統獨立訂閱
useEffect(() => { timeEngine.onTick(...) }, [...]); // MRT
useEffect(() => { timeEngine.onTick(...) }, [...]); // THSR
useEffect(() => { timeEngine.onTick(...) }, [...]); // KRTC
useEffect(() => { timeEngine.onTick(...) }, [...]); // KLRT
useEffect(() => { timeEngine.onTick(...) }, [...]); // TMRT
useEffect(() => { timeEngine.onTick(...) }, [...]); // TRA
```

**影響**：
- 每次時間更新觸發 6 次 React 狀態更新
- 可能造成 6 次 re-render

**解決方案**：
- 合併為單一狀態物件 `{ mrt, thsr, krtc, klrt, tmrt, tra }`
- 使用 `useReducer` 批次更新

---

#### 6. GeoJSON Source 完全重設

**位置**：`src/layers/TrainSymbolLayer.ts:293-325`

**問題**：
```typescript
updateTrains(features: TrainFeature[]): void {
  source.setData(featureCollection);  // 每幀完全重設！
}

setSelectedTrainId(trainId: string | null): void {
  const updatedFeatures = this.currentFeatures.map(f => ({...})); // 複製所有
  this.updateTrains(updatedFeatures);  // 再次 setData
}
```

**影響**：
- 即使只有 1 列車移動，也重設整個 GeoJSON
- Mapbox 需要重新索引

**解決方案**：
- 使用 Mapbox 的 `updateImage` 或增量更新 API
- 或拆分為多個 Source

---

#### 7. Matrix4 每幀建立

**位置**：`src/layers/Train3DLayer.ts:200-246`

**問題**：
```typescript
render() {
  const rotationX = new THREE.Matrix4().makeRotationAxis(...);  // 每幀 new
  const rotationY = new THREE.Matrix4().makeRotationAxis(...);  // 每幀 new
  const rotationZ = new THREE.Matrix4().makeRotationAxis(...);  // 每幀 new
  const m = new THREE.Matrix4().fromArray(matrix);              // 每幀 new
  const l = new THREE.Matrix4()...;                             // 每幀 new
}
```

**影響**：
- 5 個 Matrix4 × 60 FPS = 每秒 300 個物件
- 增加 GC 壓力

**解決方案**：
- 在類別層級建立靜態矩陣物件
- 使用 `.copy()` 而非 `new`

---

### 🟡 低優先度問題

#### 8. filteredTrains 依賴過多

**位置**：`src/App.tsx:364-373`

**問題**：
- 依賴 `trains`, `visibleLines`, `mkState`
- 任何變動都重新過濾

**解決方案**：
- 分離過濾邏輯
- 使用更細粒度的 memo

---

## 優化方案與優先順序

### Phase 1: 立即可做（低風險，高回報）

| # | 優化項目 | 預期效果 | 工作量 |
|---|----------|----------|--------|
| 1 | selectedTrain 改用 Map 快取 | 跟隨模式搜尋 O(1) | 小 |
| 2 | 合併 6 個時間訂閱為 1 個 | 減少 React re-render | 中 |
| 3 | 重用 Matrix4 物件 | 減少 GC 壓力 | 小 |

**預估改善**：跟隨模式卡頓減少 30-50%

---

### Phase 2: 短期優化（中風險，高回報）

| # | 優化項目 | 預期效果 | 工作量 |
|---|----------|----------|--------|
| 4 | 預計算軌道 totalLength 和 cumulativeDistances | 列車計算效能 +50% | 中 |
| 5 | TrainEngine 增量更新 | 減少每幀物件建立 | 中 |
| 6 | calculateBearing 使用 progress 定位 | 3D 渲染效能 +30% | 中 |

**預估改善**：整體 FPS 提升 20-40%

---

### Phase 3: 中期優化（需謹慎測試）

| # | 優化項目 | 預期效果 | 工作量 |
|---|----------|----------|--------|
| 7 | TrainSymbolLayer 增量更新 | 2D 模式效能提升 | 大 |
| 8 | 空間索引（四叉樹）加速碰撞檢測 | 列車數量多時效能保持 | 大 |

---

### Phase 4: 長期優化（架構調整）

| # | 優化項目 | 預期效果 | 工作量 |
|---|----------|----------|--------|
| 9 | Web Worker 處理列車計算 | 主執行緒不阻塞 | 大 |
| 10 | 虛擬化列車（視野外不渲染） | 大幅減少渲染量 | 大 |

---

## 具體實作建議

### 1. selectedTrain Map 快取

```typescript
// 改前
const selectedTrain = useMemo(() => {
  const mrtTrain = filteredTrains.find(t => t.trainId === selectedTrainId);
  // ... 6 次 find
}, [selectedTrainId, ...]);

// 改後
const trainMap = useMemo(() => {
  const map = new Map<string, Train>();
  filteredTrains.forEach(t => map.set(t.trainId, t));
  filteredThsrTrains.forEach(t => map.set(t.trainId, t));
  // ... 其他系統
  return map;
}, [filteredTrains, filteredThsrTrains, ...]);

const selectedTrain = useMemo(() => {
  return selectedTrainId ? trainMap.get(selectedTrainId) : null;
}, [selectedTrainId, trainMap]);
```

---

### 2. 合併時間訂閱

```typescript
// 改前：6 個 useEffect

// 改後：1 個 useEffect + 批次狀態
interface AllTrains {
  mrt: Train[];
  thsr: Train[];
  krtc: Train[];
  klrt: Train[];
  tmrt: Train[];
  tra: Train[];
}

const [allTrains, setAllTrains] = useState<AllTrains>({...});

useEffect(() => {
  const unsubscribe = timeEngine.onTick((time) => {
    setAllTrains({
      mrt: trainEngine.update(time),
      thsr: thsrEngine.update(time),
      krtc: krtcEngine.update(time),
      klrt: klrtEngine.update(time),
      tmrt: tmrtEngine.update(time),
      tra: traEngine.update(time),
    });
  });
  return unsubscribe;
}, [/* 依賴項 */]);
```

---

### 3. 預計算軌道距離

```typescript
// 資料載入時
interface TrackWithCache {
  geometry: LineStringGeometry;
  totalLength: number;           // 預計算
  cumulativeDistances: number[]; // 預計算
}

// 載入後計算
function preprocessTrack(track: Track): TrackWithCache {
  const coords = track.geometry.coordinates;
  const distances = [0];
  for (let i = 1; i < coords.length; i++) {
    distances.push(distances[i-1] + euclideanDistance(coords[i-1], coords[i]));
  }
  return {
    ...track,
    totalLength: distances[distances.length - 1],
    cumulativeDistances: distances,
  };
}

// 使用時（二分搜尋）
function interpolateWithCache(track: TrackWithCache, progress: number) {
  const targetDist = track.totalLength * progress;
  const segmentIndex = binarySearch(track.cumulativeDistances, targetDist);
  // 直接定位到線段，無需遍歷
}
```

---

### 4. calculateBearing 使用 progress

```typescript
// 改前：遍歷所有線段找最近
private calculateBearing(train: Train): number {
  for (let i = 0; i < coords.length - 1; i++) { ... }
}

// 改後：利用 progress 定位
private calculateBearing(train: Train): number {
  const track = this.tracks.get(train.trackId);
  if (!track.cumulativeDistances) return 0;

  // 用 progress 直接找到線段 index
  const targetDist = track.totalLength * train.progress;
  const segmentIndex = binarySearch(track.cumulativeDistances, targetDist);

  // 只計算該線段的方向
  const p1 = coords[segmentIndex];
  const p2 = coords[segmentIndex + 1];
  return Math.atan2(p2[1] - p1[1], p2[0] - p1[0]) * 180 / Math.PI;
}
```

---

## 效能測量方法

### 開發時測量

```typescript
// 在 TimeEngine 加入 FPS 計數
private frameCount = 0;
private lastFpsTime = 0;

tick() {
  this.frameCount++;
  const now = performance.now();
  if (now - this.lastFpsTime > 1000) {
    console.log(`FPS: ${this.frameCount}`);
    this.frameCount = 0;
    this.lastFpsTime = now;
  }
}
```

### Chrome DevTools

1. **Performance Tab**：錄製跟隨模式操作
2. **Memory Tab**：檢查 GC 頻率
3. **Rendering Tab**：開啟 FPS meter

### 關鍵指標

| 指標 | 目標值 | 當前估計 |
|------|--------|----------|
| FPS (跟隨模式) | ≥55 | ~40-50 |
| JS Heap 增長 | <1MB/分鐘 | 未測量 |
| Long Task (>50ms) | 0 | 未測量 |

---

## 風險評估

| 優化項目 | 風險等級 | 潛在問題 |
|----------|----------|----------|
| Map 快取 | 低 | 無 |
| 合併時間訂閱 | 中 | 狀態更新時機變化 |
| 預計算距離 | 中 | 資料載入時間增加 |
| 增量更新 | 中 | 列車狀態同步問題 |
| 空間索引 | 高 | 複雜度增加，維護成本 |

---

## 下一步

1. **確認優化優先順序**
2. **建立效能基準測量**
3. **從 Phase 1 開始實作**
4. **每次優化後測量並比較**

---

## 附錄：關鍵檔案位置

| 檔案 | 說明 |
|------|------|
| `src/engines/TimeEngine.ts` | 時間迴圈 |
| `src/engines/TrainEngine.ts` | MRT 列車引擎 |
| `src/engines/TraTrainEngine.ts` | TRA 列車引擎 |
| `src/layers/Train3DLayer.ts` | 3D 渲染層 |
| `src/layers/TrainSymbolLayer.ts` | 2D 符號層 |
| `src/App.tsx` | 主應用整合 |
