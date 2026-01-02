import * as THREE from 'three';
import mapboxgl from 'mapbox-gl';
import type { ThsrTrain } from '../engines/ThsrTrainEngine';
import type { Track } from '../types/track';
import { THSR_COLOR_3D, getThsrDirection } from '../constants/thsrInfo';

// 參考點：台北市中心
const MODEL_ORIGIN: [number, number] = [121.52, 25.02];

// 高鐵列車尺寸（公尺）- 高鐵列車比捷運更長
const TRAIN_LENGTH = 250;  // 長度 (前後方向)
const TRAIN_WIDTH = 80;    // 寬度 (左右方向)
const TRAIN_HEIGHT = 70;   // 高度 (垂直方向)

/**
 * Thsr3DLayer - Mapbox Custom Layer for 3D THSR train rendering
 */
export class Thsr3DLayer implements mapboxgl.CustomLayerInterface {
  id = 'thsr-3d-layer';
  type: 'custom' = 'custom';
  renderingMode: '3d' = '3d';

  private map: mapboxgl.Map | null = null;
  private camera: THREE.Camera = new THREE.Camera();
  private scene: THREE.Scene = new THREE.Scene();
  private renderer: THREE.WebGLRenderer | null = null;

  // 列車 mesh 物件池
  private trainMeshes: Map<string, THREE.Group> = new Map();

  // 目前顯示的列車資料
  private trains: ThsrTrain[] = [];

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

  constructor(tracks?: Map<string, Track>) {
    if (tracks) {
      this.tracks = tracks;
    }
  }

  setOnSelect(callback: (trainId: string) => void): void {
    this.onSelectCallback = callback;
  }

  setSelectedTrainId(trainId: string | null): void {
    this.selectedTrainId = trainId;
  }

  setTracks(tracks: Map<string, Track>): void {
    this.tracks = tracks;
  }

  setStations(stationCoordinates: Map<string, [number, number]>): void {
    this.stationCoordinates = stationCoordinates;
  }

  updateTrains(trains: ThsrTrain[]): void {
    this.trains = trains;
  }

  onAdd(map: mapboxgl.Map, gl: WebGLRenderingContext): void {
    this.map = map;

    const modelAsMercatorCoordinate = mapboxgl.MercatorCoordinate.fromLngLat(
      MODEL_ORIGIN,
      0
    );

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
      linewidth: 2,
    });

    // 建立高鐵方向材質（南下/北上略有不同）
    const material0 = new THREE.MeshStandardMaterial({
      color: THSR_COLOR_3D,
      transparent: true,
      opacity: 0.9,
      emissive: THSR_COLOR_3D,
      emissiveIntensity: 0,
    });
    const material1 = new THREE.MeshStandardMaterial({
      color: 0xff9a4d,  // 北上略淺
      transparent: true,
      opacity: 0.9,
      emissive: 0xff9a4d,
      emissiveIntensity: 0,
    });
    this.materials.set('0', material0);
    this.materials.set('1', material1);

    // 點擊事件處理
    const handleClick = (event: MouseEvent) => {
      if (!this.map || !this.onSelectCallback) return;
      if (this.trains.length === 0) return;

      const canvas = this.map.getCanvas();
      const rect = canvas.getBoundingClientRect();

      const point = new mapboxgl.Point(
        event.clientX - rect.left,
        event.clientY - rect.top
      );

      let closestTrain: ThsrTrain | null = null;
      let minDistSq = Infinity;
      const clickThreshold = 40; // 高鐵較大，點擊容差也較大

      for (const train of this.trains) {
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
    (this as unknown as { _clickHandler: (e: MouseEvent) => void })._clickHandler = handleClick;

    // 光源
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

    this.updateTrainMeshes();

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

    const m = new THREE.Matrix4().fromArray(matrix);
    const l = new THREE.Matrix4()
      .makeTranslation(
        this.modelTransform.translateX,
        this.modelTransform.translateY,
        this.modelTransform.translateZ
      )
      .scale(new THREE.Vector3(
        this.modelTransform.scale,
        -this.modelTransform.scale,
        this.modelTransform.scale
      ))
      .multiply(rotationX)
      .multiply(rotationY)
      .multiply(rotationZ);

    this.camera.projectionMatrix = m.multiply(l);

    this.renderer.resetState();
    this.renderer.render(this.scene, this.camera);

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
      const direction = getThsrDirection(train.trackId);
      const material = this.materials.get(direction) || this.materials.get('0')!;

      if (!group) {
        group = new THREE.Group();
        group.userData.trainId = train.trainId;

        const mesh = new THREE.Mesh(this.geometry, material);
        mesh.name = 'body';
        group.add(mesh);

        this.trainMeshes.set(train.trainId, group);
        this.scene.add(group);
      }

      // 處理選中狀態的邊框
      const isSelected = train.trainId === this.selectedTrainId;
      let outline = group.getObjectByName('outline') as THREE.LineSegments | undefined;

      if (isSelected && !outline && this.outlineGeometry && this.outlineMaterial) {
        outline = new THREE.LineSegments(this.outlineGeometry, this.outlineMaterial);
        outline.name = 'outline';
        outline.scale.set(1.1, 1.1, 1.1);
        group.add(outline);
      } else if (!isSelected && outline) {
        group.remove(outline);
      }

      // 計算位置
      let displayPosition = train.position;
      if (train.status === 'stopped' && train.currentStation) {
        const stationCoord = this.stationCoordinates.get(train.currentStation);
        if (stationCoord) {
          displayPosition = stationCoord;
        }
      }
      const position = this.lngLatToMeters(displayPosition[0], displayPosition[1]);
      group.position.set(position.x, position.y, TRAIN_HEIGHT / 2);

      // 計算旋轉
      let bearing: number;
      if (train.status === 'stopped' && train.currentStation) {
        bearing = this.calculateStationBearing(train.currentStation, train.trackId);
      } else {
        bearing = this.calculateBearing(train);
      }
      group.rotation.z = THREE.MathUtils.degToRad(bearing);
    }
  }

  private lngLatToMeters(lng: number, lat: number): { x: number; y: number } {
    if (!this.modelTransform) return { x: 0, y: 0 };

    const mercator = mapboxgl.MercatorCoordinate.fromLngLat([lng, lat], 0);

    const x = (mercator.x - this.modelTransform.translateX) / this.modelTransform.scale;
    const y = (this.modelTransform.translateY - mercator.y) / this.modelTransform.scale;

    return { x, y };
  }

  private pointToSegmentDistSq(
    p: [number, number],
    a: [number, number],
    b: [number, number]
  ): number {
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const lengthSq = dx * dx + dy * dy;

    if (lengthSq === 0) {
      const pdx = p[0] - a[0];
      const pdy = p[1] - a[1];
      return pdx * pdx + pdy * pdy;
    }

    let t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / lengthSq;
    t = Math.max(0, Math.min(1, t));

    const nearestX = a[0] + t * dx;
    const nearestY = a[1] + t * dy;

    const distX = p[0] - nearestX;
    const distY = p[1] - nearestY;
    return distX * distX + distY * distY;
  }

  private calculateBearing(train: ThsrTrain): number {
    const track = this.tracks.get(train.trackId);
    if (!track) return 0;

    const coords = track.geometry.coordinates as [number, number][];
    if (coords.length < 2) return 0;

    const trainPos = train.position;

    let minDistSq = Infinity;
    let closestSegment = 0;

    for (let i = 0; i < coords.length - 1; i++) {
      const distSq = this.pointToSegmentDistSq(trainPos, coords[i], coords[i + 1]);
      if (distSq < minDistSq) {
        minDistSq = distSq;
        closestSegment = i;
      }
    }

    const p1 = this.lngLatToMeters(coords[closestSegment][0], coords[closestSegment][1]);
    const p2 = this.lngLatToMeters(coords[closestSegment + 1][0], coords[closestSegment + 1][1]);

    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;

    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 0.001) return 0;

    const angle = Math.atan2(dy, dx);
    return THREE.MathUtils.radToDeg(angle);
  }

  private calculateStationBearing(stationId: string, trackId: string): number {
    const stationCoord = this.stationCoordinates.get(stationId);
    if (!stationCoord) return 0;

    // 高鐵只有一條路線，使用 THSR-1-0 作為基準方向
    const baseTrackId = 'THSR-1-0';
    const track = this.tracks.get(baseTrackId) || this.tracks.get(trackId);
    if (!track) return 0;

    const coords = track.geometry.coordinates as [number, number][];
    if (coords.length < 2) return 0;

    let minDistSq = Infinity;
    let closestSegment = 0;

    for (let i = 0; i < coords.length - 1; i++) {
      const distSq = this.pointToSegmentDistSq(stationCoord, coords[i], coords[i + 1]);
      if (distSq < minDistSq) {
        minDistSq = distSq;
        closestSegment = i;
      }
    }

    const p1 = this.lngLatToMeters(coords[closestSegment][0], coords[closestSegment][1]);
    const p2 = this.lngLatToMeters(coords[closestSegment + 1][0], coords[closestSegment + 1][1]);

    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;

    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 0.001) return 0;

    const angle = Math.atan2(dy, dx);
    return THREE.MathUtils.radToDeg(angle);
  }

  onRemove(): void {
    if (this.map) {
      const handler = (this as unknown as { _clickHandler: (e: MouseEvent) => void })._clickHandler;
      if (handler) {
        this.map.getCanvas().removeEventListener('click', handler);
      }
    }

    for (const group of this.trainMeshes.values()) {
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
