import * as THREE from 'three';
import mapboxgl from 'mapbox-gl';
import type { Train } from '../engines/TrainEngine';
import type { Track } from '../types/track';

// 列車顏色（依路線區分）
const LINE_COLORS: Record<string, number> = {
  R: 0xd90023,   // 紅線
  BL: 0x0070c0,  // 藍線
  G: 0x008659,   // 綠線
  O: 0xf8b61c,   // 橘線
  BR: 0xc48c31,  // 文湖線
  K: 0x8cc540,   // 安坑輕軌
  V: 0xa4ce4e,   // 淡海輕軌
  A: 0x8246af,   // 機場捷運
  Y: 0xfedb00,   // 環狀線
};

// 從 trackId 取得路線 ID
function getLineId(trackId: string): string {
  if (trackId.startsWith('K')) return 'K';
  if (trackId.startsWith('V')) return 'V';
  if (trackId.startsWith('BR')) return 'BR';
  if (trackId.startsWith('BL')) return 'BL';
  if (trackId.startsWith('G')) return 'G';
  if (trackId.startsWith('O')) return 'O';
  if (trackId.startsWith('A')) return 'A';
  if (trackId.startsWith('Y')) return 'Y';
  return 'R';
}

// 參考點：台北市中心
const MODEL_ORIGIN: [number, number] = [121.52, 25.02];

// 列車尺寸（公尺）- 放大以便在地圖上清楚可見
const TRAIN_LENGTH = 160;  // 長度 (前後方向)
const TRAIN_WIDTH = 90;    // 寬度 (左右方向)
const TRAIN_HEIGHT = 90;   // 高度 (垂直方向)

/**
 * Train3DLayer - Mapbox Custom Layer for 3D train rendering
 * 參考 Mapbox 官方 Custom Layer 範例實作
 */
export class Train3DLayer implements mapboxgl.CustomLayerInterface {
  id = 'train-3d-layer';
  type: 'custom' = 'custom';
  renderingMode: '3d' = '3d';

  private map: mapboxgl.Map | null = null;
  private camera: THREE.Camera = new THREE.Camera();
  private scene: THREE.Scene = new THREE.Scene();
  private renderer: THREE.WebGLRenderer | null = null;

  // 列車 mesh 物件池（每個列車是一個 Group，包含本體和邊框）
  private trainMeshes: Map<string, THREE.Group> = new Map();

  // 目前顯示的列車資料
  private trains: Train[] = [];

  // 軌道資料（用於計算行進方向）
  private tracks: Map<string, Track> = new Map();

  // 車站座標（用於停站時精確定位）
  private stationCoordinates: Map<string, [number, number]> = new Map();

  // 模型轉換參數
  private modelTransform: {
    translateX: number;
    translateY: number;
    translateZ: number;
    rotateX: number;
    rotateY: number;
    rotateZ: number;
    scale: number;
  } | null = null;

  // 幾何體與材質快取
  private geometry: THREE.BoxGeometry | null = null;
  private materials: Map<string, THREE.MeshStandardMaterial> = new Map();

  // 選中的列車 ID
  private selectedTrainId: string | null = null;

  // 選中回呼函數
  private onSelectCallback: ((trainId: string) => void) | null = null;

  // 選中邊框材質
  private outlineMaterial: THREE.LineBasicMaterial | null = null;
  private outlineGeometry: THREE.EdgesGeometry | null = null;

  // 效能優化：追蹤資料變化，避免不必要的重繪
  private lastTrainCount = 0;
  private lastUpdateTime = 0;
  private needsRepaint = true;

  constructor(tracks?: Map<string, Track>) {
    if (tracks) {
      this.tracks = tracks;
    }
  }

  // 設定選中回呼
  setOnSelect(callback: (trainId: string) => void): void {
    this.onSelectCallback = callback;
  }

  // 設定選中的列車
  setSelectedTrainId(trainId: string | null): void {
    this.selectedTrainId = trainId;
  }

  setTracks(tracks: Map<string, Track>): void {
    this.tracks = tracks;
  }

  setStations(stationCoordinates: Map<string, [number, number]>): void {
    this.stationCoordinates = stationCoordinates;
  }

  updateTrains(trains: Train[]): void {
    // 效能優化：只在列車數量變化時標記需要重繪
    if (trains.length !== this.lastTrainCount) {
      this.needsRepaint = true;
      this.lastTrainCount = trains.length;
    }
    this.trains = trains;
  }

  onAdd(map: mapboxgl.Map, gl: WebGLRenderingContext): void {
    this.map = map;

    // 計算模型原點的 Mercator 座標
    const modelAsMercatorCoordinate = mapboxgl.MercatorCoordinate.fromLngLat(
      MODEL_ORIGIN,
      0
    );

    // 設定轉換參數（參考 Mapbox 官方範例）
    this.modelTransform = {
      translateX: modelAsMercatorCoordinate.x,
      translateY: modelAsMercatorCoordinate.y,
      translateZ: modelAsMercatorCoordinate.z || 0,
      rotateX: 0,
      rotateY: 0,
      rotateZ: 0,
      scale: modelAsMercatorCoordinate.meterInMercatorCoordinateUnits()
    };

    // 建立共用幾何體
    this.geometry = new THREE.BoxGeometry(TRAIN_LENGTH, TRAIN_WIDTH, TRAIN_HEIGHT);

    // 建立選中邊框的幾何體和材質
    this.outlineGeometry = new THREE.EdgesGeometry(this.geometry);
    this.outlineMaterial = new THREE.LineBasicMaterial({
      color: 0xffffff,
      linewidth: 2,  // 注意：WebGL 只支援 linewidth=1，但保留設定
    });

    // 建立各路線的材質（使用 Standard 材質，支援發光效果）
    for (const [lineId, color] of Object.entries(LINE_COLORS)) {
      const material = new THREE.MeshStandardMaterial({
        color: color,
        transparent: true,
        opacity: 0.9,
        emissive: color,
        emissiveIntensity: 0,  // 預設不發光，進站時增加
      });
      this.materials.set(lineId, material);
    }

    // 點擊事件處理 - 使用 Mapbox unproject 找最近列車
    const handleClick = (event: MouseEvent) => {
      if (!this.map || !this.onSelectCallback) return;
      if (this.trains.length === 0) return;

      const canvas = this.map.getCanvas();
      const rect = canvas.getBoundingClientRect();

      // 取得點擊位置的螢幕座標
      const point = new mapboxgl.Point(
        event.clientX - rect.left,
        event.clientY - rect.top
      );

      // 找最近的列車（以螢幕像素距離計算）
      let closestTrain: Train | null = null;
      let minDistSq = Infinity;
      const clickThreshold = 30; // 點擊容差（像素）

      for (const train of this.trains) {
        // 將列車位置投影到螢幕座標
        const trainPoint = this.map.project(train.position);
        const dx = trainPoint.x - point.x;
        const dy = trainPoint.y - point.y;
        const distSq = dx * dx + dy * dy;

        if (distSq < minDistSq && distSq < clickThreshold * clickThreshold) {
          minDistSq = distSq;
          closestTrain = train;
        }
      }

      if (closestTrain) {
        this.onSelectCallback(closestTrain.trainId);
      }
    };

    map.getCanvas().addEventListener('click', handleClick);

    // 儲存 handler 以便移除
    (this as unknown as { _clickHandler: (e: MouseEvent) => void })._clickHandler = handleClick;

    // 加入光源
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    this.scene.add(ambientLight);

    const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.6);
    directionalLight1.position.set(0, 70, 100);
    this.scene.add(directionalLight1);

    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
    directionalLight2.position.set(0, -70, 100);
    this.scene.add(directionalLight2);

    // 建立 renderer
    this.renderer = new THREE.WebGLRenderer({
      canvas: map.getCanvas(),
      context: gl,
      antialias: true,
    });
    this.renderer.autoClear = false;
  }

  render(_gl: WebGLRenderingContext, matrix: number[]): void {
    if (!this.renderer || !this.modelTransform || !this.map) return;

    // 更新列車 mesh
    this.updateTrainMeshes();

    // 建立旋轉矩陣
    const rotationX = new THREE.Matrix4().makeRotationAxis(
      new THREE.Vector3(1, 0, 0),
      this.modelTransform.rotateX
    );
    const rotationY = new THREE.Matrix4().makeRotationAxis(
      new THREE.Vector3(0, 1, 0),
      this.modelTransform.rotateY
    );
    const rotationZ = new THREE.Matrix4().makeRotationAxis(
      new THREE.Vector3(0, 0, 1),
      this.modelTransform.rotateZ
    );

    // 建立完整的轉換矩陣
    const m = new THREE.Matrix4().fromArray(matrix);
    const l = new THREE.Matrix4()
      .makeTranslation(
        this.modelTransform.translateX,
        this.modelTransform.translateY,
        this.modelTransform.translateZ
      )
      .scale(new THREE.Vector3(
        this.modelTransform.scale,
        -this.modelTransform.scale,  // Y 軸翻轉
        this.modelTransform.scale
      ))
      .multiply(rotationX)
      .multiply(rotationY)
      .multiply(rotationZ);

    // 設定相機投影矩陣
    this.camera.projectionMatrix = m.multiply(l);

    // 渲染
    this.renderer.resetState();
    this.renderer.render(this.scene, this.camera);

    // 效能優化：使用節流的重繪機制
    // 列車持續移動，需要持續重繪，但使用 requestAnimationFrame 節奏
    const now = performance.now();
    if (this.needsRepaint || now - this.lastUpdateTime > 16) { // 約 60fps
      this.lastUpdateTime = now;
      this.needsRepaint = false;
      this.map.triggerRepaint();
    }
  }

  private updateTrainMeshes(): void {
    if (!this.geometry || !this.modelTransform) return;

    const activeTrainIds = new Set(this.trains.map(t => t.trainId));

    // 移除不存在的列車
    for (const [trainId, group] of this.trainMeshes) {
      if (!activeTrainIds.has(trainId)) {
        this.scene.remove(group);
        this.trainMeshes.delete(trainId);
      }
    }

    // 更新或建立列車 mesh
    for (const train of this.trains) {
      let group = this.trainMeshes.get(train.trainId);
      const lineId = getLineId(train.trackId);
      const material = this.materials.get(lineId) || this.materials.get('R')!;

      if (!group) {
        // 建立新的列車群組
        group = new THREE.Group();
        group.userData.trainId = train.trainId;

        // 建立列車本體
        const mesh = new THREE.Mesh(this.geometry, material.clone());
        mesh.name = 'body';
        group.add(mesh);

        this.trainMeshes.set(train.trainId, group);
        this.scene.add(group);
      }

      // 處理選中狀態的邊框
      const isSelected = train.trainId === this.selectedTrainId;
      let outline = group.getObjectByName('outline') as THREE.LineSegments | undefined;

      if (isSelected && !outline && this.outlineGeometry && this.outlineMaterial) {
        // 新增白色邊框
        outline = new THREE.LineSegments(this.outlineGeometry, this.outlineMaterial);
        outline.name = 'outline';
        outline.scale.set(1.1, 1.1, 1.1);  // 稍微放大以包覆本體
        group.add(outline);
      } else if (!isSelected && outline) {
        // 移除邊框
        group.remove(outline);
      }

      // 計算位置（相對於 MODEL_ORIGIN，單位為公尺）
      // 停站時使用車站座標，讓同站列車完全重疊
      let displayPosition = train.position;
      if (train.status === 'stopped' && train.currentStation) {
        const stationCoord = this.stationCoordinates.get(train.currentStation);
        if (stationCoord) {
          displayPosition = stationCoord;
        }
      }
      const position = this.lngLatToMeters(displayPosition[0], displayPosition[1]);
      // Three.js 座標系統（經過 transform 後）:
      // X = 東西向 (east-west)
      // Y = 南北向 (north-south, scale 會翻轉)
      // Z = 高度 (elevation)
      group.position.set(position.x, position.y, TRAIN_HEIGHT / 2);

      // 計算旋轉（繞 Z 軸，因為 Z 是高度/垂直方向）
      let bearing: number;
      if (train.status === 'stopped' && train.currentStation) {
        // 停站時使用統一朝向：根據軌道方向計算但不區分正反向
        // 這樣同站不同方向的列車會完美重疊
        bearing = this.calculateStationBearing(train.currentStation, train.trackId);
      } else {
        // 行駛中：根據列車實際位置找到最近的軌道線段，使用該線段方向
        bearing = this.calculateBearing(train);
      }
      group.rotation.z = THREE.MathUtils.degToRad(bearing);
    }
  }

  /**
   * 將經緯度轉換為相對於原點的公尺座標
   * 注意：因為 transform matrix 中 Y 軸有 -scale，所以 Y 需要取負值
   */
  private lngLatToMeters(lng: number, lat: number): { x: number; y: number } {
    if (!this.modelTransform) return { x: 0, y: 0 };

    const mercator = mapboxgl.MercatorCoordinate.fromLngLat([lng, lat], 0);

    // 計算相對於原點的偏移（Mercator 單位），再轉換為公尺
    // X: 正常計算
    // Y: 因為 scale matrix 有 -scale，需要取負值才能得到正確的 Mercator Y
    const x = (mercator.x - this.modelTransform.translateX) / this.modelTransform.scale;
    const y = (this.modelTransform.translateY - mercator.y) / this.modelTransform.scale;

    return { x, y };
  }

  /**
   * 計算點到線段的最短距離平方（用於找最近線段）
   */
  private pointToSegmentDistSq(
    p: [number, number],
    a: [number, number],
    b: [number, number]
  ): number {
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const lengthSq = dx * dx + dy * dy;

    if (lengthSq === 0) {
      // a 和 b 是同一點
      const pdx = p[0] - a[0];
      const pdy = p[1] - a[1];
      return pdx * pdx + pdy * pdy;
    }

    // 計算投影參數 t
    let t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / lengthSq;
    t = Math.max(0, Math.min(1, t));

    // 最近點
    const nearestX = a[0] + t * dx;
    const nearestY = a[1] + t * dy;

    const distX = p[0] - nearestX;
    const distY = p[1] - nearestY;
    return distX * distX + distY * distY;
  }

  /**
   * 根據列車實際位置計算行進方向
   *
   * 核心想法：找到列車位置最接近的軌道線段，用該線段的方向
   * 這樣避免 progress 和實際位置不一致的問題
   */
  private calculateBearing(train: Train): number {
    const track = this.tracks.get(train.trackId);
    if (!track) return 0;

    const coords = track.geometry.coordinates as [number, number][];
    if (coords.length < 2) return 0;

    const trainPos = train.position;

    // 找到最接近的軌道線段
    let minDistSq = Infinity;
    let closestSegment = 0;

    for (let i = 0; i < coords.length - 1; i++) {
      const distSq = this.pointToSegmentDistSq(trainPos, coords[i], coords[i + 1]);
      if (distSq < minDistSq) {
        minDistSq = distSq;
        closestSegment = i;
      }
    }

    // 取得該線段的兩端點，轉換到 mesh 座標
    const p1 = this.lngLatToMeters(coords[closestSegment][0], coords[closestSegment][1]);
    const p2 = this.lngLatToMeters(coords[closestSegment + 1][0], coords[closestSegment + 1][1]);

    // 計算線段方向
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;

    // 如果線段太短，返回 0
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 0.001) {
      return 0;
    }

    // 計算角度：列車前方是 +X 方向
    const angle = Math.atan2(dy, dx);
    return THREE.MathUtils.radToDeg(angle);
  }

  /**
   * 計算車站的統一朝向
   *
   * 停站時使用統一朝向，讓同站不同方向的列車完美重疊
   * 策略：使用 direction-0 軌道在該站附近的方向
   */
  private calculateStationBearing(stationId: string, trackId: string): number {
    // 嘗試取得該站的座標
    const stationCoord = this.stationCoordinates.get(stationId);
    if (!stationCoord) return 0;

    // 取得基準軌道 ID（使用 direction-0 的軌道作為統一方向）
    // 例如：R-1-0, R-1-1 都使用 R-1-0 的方向
    const baseTrackId = trackId.replace(/-1$/, '-0');
    const track = this.tracks.get(baseTrackId) || this.tracks.get(trackId);
    if (!track) return 0;

    const coords = track.geometry.coordinates as [number, number][];
    if (coords.length < 2) return 0;

    // 找到最接近車站的軌道線段
    let minDistSq = Infinity;
    let closestSegment = 0;

    for (let i = 0; i < coords.length - 1; i++) {
      const distSq = this.pointToSegmentDistSq(stationCoord, coords[i], coords[i + 1]);
      if (distSq < minDistSq) {
        minDistSq = distSq;
        closestSegment = i;
      }
    }

    // 取得該線段的兩端點，轉換到 mesh 座標
    const p1 = this.lngLatToMeters(coords[closestSegment][0], coords[closestSegment][1]);
    const p2 = this.lngLatToMeters(coords[closestSegment + 1][0], coords[closestSegment + 1][1]);

    // 計算線段方向
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;

    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 0.001) return 0;

    const angle = Math.atan2(dy, dx);
    return THREE.MathUtils.radToDeg(angle);
  }

  onRemove(): void {
    // 移除點擊事件監聽
    if (this.map) {
      const handler = (this as unknown as { _clickHandler: (e: MouseEvent) => void })._clickHandler;
      if (handler) {
        this.map.getCanvas().removeEventListener('click', handler);
      }
    }

    for (const group of this.trainMeshes.values()) {
      // 清理群組內的子材質
      group.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          (child.material as THREE.Material).dispose();
        }
      });
      this.scene.remove(group);
    }
    this.trainMeshes.clear();

    if (this.geometry) this.geometry.dispose();
    if (this.outlineGeometry) this.outlineGeometry.dispose();
    if (this.outlineMaterial) this.outlineMaterial.dispose();

    for (const material of this.materials.values()) {
      material.dispose();
    }
    this.materials.clear();

    if (this.renderer) this.renderer.dispose();

    this.map = null;
  }
}
