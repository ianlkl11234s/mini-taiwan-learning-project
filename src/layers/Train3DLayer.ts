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

  constructor(tracks?: Map<string, Track>) {
    if (tracks) {
      this.tracks = tracks;
    }
  }

  setTracks(tracks: Map<string, Track>): void {
    this.tracks = tracks;
  }

  updateTrains(trains: Train[]): void {
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

    // 持續重繪
    this.map.triggerRepaint();
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

        // 建立列車本體
        const mesh = new THREE.Mesh(this.geometry, material.clone());
        mesh.name = 'body';
        group.add(mesh);

        this.trainMeshes.set(train.trainId, group);
        this.scene.add(group);
      }

      // 計算位置（相對於 MODEL_ORIGIN，單位為公尺）
      const position = this.lngLatToMeters(train.position[0], train.position[1]);
      // Three.js 座標系統（經過 transform 後）:
      // X = 東西向 (east-west)
      // Y = 南北向 (north-south, scale 會翻轉)
      // Z = 高度 (elevation)
      group.position.set(position.x, position.y, TRAIN_HEIGHT / 2);

      // 計算旋轉（繞 Z 軸，因為 Z 是高度/垂直方向）
      // 根據列車實際位置找到最近的軌道線段，使用該線段方向
      const bearing = this.calculateBearing(train);
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

  onRemove(): void {
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
    for (const material of this.materials.values()) {
      material.dispose();
    }
    this.materials.clear();

    if (this.renderer) this.renderer.dispose();

    this.map = null;
  }
}
