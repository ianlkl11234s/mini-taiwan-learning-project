import * as THREE from 'three';
import mapboxgl from 'mapbox-gl';

// 與其他 3D 圖層共用同一個參考原點
const MODEL_ORIGIN: [number, number] = [121.52, 25.02];

// ============================================================
// 天氣類型與設定
// ============================================================

export type WeatherType = 'clear' | 'drizzle' | 'rain' | 'heavy-rain' | 'thunderstorm' | 'snow';

export interface WeatherConfig {
  type: WeatherType;
  intensity: number;         // 0.0 - 1.0
  precipitationRate: number; // mm/h（來自 API）
  windSpeed: number;         // m/s
  windDirection: number;     // degrees（0=北, 90=東）
}

export const CLEAR_WEATHER: WeatherConfig = {
  type: 'clear',
  intensity: 0,
  precipitationRate: 0,
  windSpeed: 0,
  windDirection: 0,
};

/** 不同天氣類型的視覺參數 */
interface WeatherPreset {
  particles: number;
  fallSpeed: number;     // 基礎下墜速度 (m/s)
  streakLength: number;  // 雨滴拖尾長度 (m)
  opacity: number;       // 基礎透明度
  color: number;         // 雨滴顏色
  size: number;          // 粒子大小 (snow 用)
  fogDensity: number;    // 場景霧氣濃度
}

const WEATHER_PRESETS: Record<WeatherType, WeatherPreset> = {
  'clear':        { particles: 0,     fallSpeed: 0,   streakLength: 0,   opacity: 0,   color: 0xffffff, size: 0,  fogDensity: 0 },
  'drizzle':      { particles: 5000,  fallSpeed: 60,  streakLength: 80,  opacity: 0.2, color: 0xc0d8f0, size: 3,  fogDensity: 0.00003 },
  'rain':         { particles: 15000, fallSpeed: 100, streakLength: 120, opacity: 0.4, color: 0xa0c0e0, size: 4,  fogDensity: 0.0001 },
  'heavy-rain':   { particles: 25000, fallSpeed: 150, streakLength: 180, opacity: 0.6, color: 0x90b0d0, size: 5,  fogDensity: 0.00025 },
  'thunderstorm': { particles: 35000, fallSpeed: 200, streakLength: 220, opacity: 0.7, color: 0x80a0c0, size: 6,  fogDensity: 0.0004 },
  'snow':         { particles: 8000,  fallSpeed: 15,  streakLength: 20,  opacity: 0.7, color: 0xeef4ff, size: 10, fogDensity: 0.00008 },
};

const RAIN_HEIGHT = 1500;
// 預設半徑（onAdd 時 map.getBounds 尚未可用的 fallback）
const DEFAULT_RADIUS = 5000;

// ============================================================
// 自訂 Shader：圓形漸淡 + 雨絲漸層透明
// ============================================================

const rainVertexShader = /* glsl */ `
  attribute float alpha;
  uniform vec2 viewCenter;
  uniform float viewRadius;
  varying float vAlpha;

  void main() {
    // 距離可視中心的比例（0=中心, 1=邊緣）
    float dist = length(position.xy - viewCenter);
    // 從 60% 半徑開始漸淡，到 100% 完全透明
    float edgeFade = 1.0 - smoothstep(viewRadius * 0.6, viewRadius, dist);
    vAlpha = alpha * edgeFade;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const rainFragmentShader = /* glsl */ `
  uniform vec3 color;
  uniform float opacity;
  varying float vAlpha;

  void main() {
    gl_FragColor = vec4(color, opacity * vAlpha);
  }
`;

// 雪花用 Points shader（同樣加入圓形漸淡）
const snowVertexShader = /* glsl */ `
  uniform float size;
  uniform vec2 viewCenter;
  uniform float viewRadius;
  varying float vAlpha;

  void main() {
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = size * (800.0 / -mvPosition.z);
    gl_PointSize = clamp(gl_PointSize, 1.0, 12.0);
    gl_Position = projectionMatrix * mvPosition;

    // 高度淡入淡出
    float heightRatio = position.z / ${RAIN_HEIGHT.toFixed(1)};
    float heightFade = smoothstep(0.0, 0.05, heightRatio) * (1.0 - smoothstep(0.85, 1.0, heightRatio));

    // 圓形邊緣漸淡
    float dist = length(position.xy - viewCenter);
    float edgeFade = 1.0 - smoothstep(viewRadius * 0.6, viewRadius, dist);

    vAlpha = heightFade * edgeFade;
  }
`;

const snowFragmentShader = /* glsl */ `
  uniform vec3 color;
  uniform float opacity;
  varying float vAlpha;

  void main() {
    float dist = length(gl_PointCoord - vec2(0.5));
    if (dist > 0.5) discard;
    float edge = smoothstep(0.5, 0.3, dist);
    gl_FragColor = vec4(color, opacity * vAlpha * edge);
  }
`;

// ============================================================
// Weather3DLayer
// ============================================================

export class Weather3DLayer implements mapboxgl.CustomLayerInterface {
  id = 'weather-3d-layer';
  type: 'custom' = 'custom';
  renderingMode: '3d' = '3d';

  private map: mapboxgl.Map | null = null;
  private camera: THREE.Camera = new THREE.Camera();
  private scene: THREE.Scene = new THREE.Scene();
  private renderer: THREE.WebGLRenderer | null = null;

  // 雨 - LineSegments
  private rainGeometry: THREE.BufferGeometry | null = null;
  private rainMaterial: THREE.ShaderMaterial | null = null;
  private rainMesh: THREE.LineSegments | null = null;

  // 雪 - Points
  private snowGeometry: THREE.BufferGeometry | null = null;
  private snowMaterial: THREE.ShaderMaterial | null = null;
  private snowMesh: THREE.Points | null = null;

  // 粒子資料
  private linePositions: Float32Array | null = null;
  private lineAlphas: Float32Array | null = null;
  private snowPositions: Float32Array | null = null;
  private velocities: Float32Array | null = null;

  private config: WeatherConfig = { ...CLEAR_WEATHER };
  private particleCount = 0;
  private lastRenderTime = 0;

  // 座標轉換
  private modelTransform: {
    translateX: number;
    translateY: number;
    translateZ: number;
    rotateX: number;
    rotateY: number;
    rotateZ: number;
    scale: number;
  } | null = null;

  // 效能優化：重用矩陣
  private readonly _matrixM = new THREE.Matrix4();
  private readonly _matrixL = new THREE.Matrix4();
  private readonly _scaleVector = new THREE.Vector3();

  // 圓形可視範圍（世界座標，公尺）
  // 粒子在此範圍內生成，超出則回收重生
  private _viewCenter = { x: 0, y: 0 };
  private _viewRadius = DEFAULT_RADIUS;

  // ============================
  // 公開 API
  // ============================

  setWeather(config: WeatherConfig): void {
    const typeChanged = config.type !== this.config.type;
    this.config = { ...config };
    if (typeChanged) {
      this.rebuildParticles();
    } else {
      this.updateMaterialUniforms();
    }
  }

  getWeather(): WeatherConfig {
    return { ...this.config };
  }

  // ============================
  // CustomLayerInterface
  // ============================

  onAdd(map: mapboxgl.Map, gl: WebGLRenderingContext): void {
    this.map = map;

    const modelAsMercator = mapboxgl.MercatorCoordinate.fromLngLat(MODEL_ORIGIN, 0);
    this.modelTransform = {
      translateX: modelAsMercator.x,
      translateY: modelAsMercator.y,
      translateZ: modelAsMercator.z || 0,
      rotateX: 0,
      rotateY: 0,
      rotateZ: 0,
      scale: modelAsMercator.meterInMercatorCoordinateUnits(),
    };

    this.renderer = new THREE.WebGLRenderer({
      canvas: map.getCanvas(),
      context: gl,
      antialias: true,
    });
    this.renderer.autoClear = false;

    this.lastRenderTime = performance.now();
    this.updateViewArea();
    this.rebuildParticles();

    if (import.meta.env.DEV) {
      (window as unknown as Record<string, unknown>).__weatherLayer = this;
    }
  }

  render(_gl: WebGLRenderingContext, matrix: number[]): void {
    if (!this.renderer || !this.modelTransform || !this.map) return;
    if (this.config.type === 'clear') return;

    const now = performance.now();
    const dt = Math.min((now - this.lastRenderTime) / 1000, 0.1);
    this.lastRenderTime = now;

    // 更新圓形可視範圍
    this.updateViewArea();

    // 同步 shader uniforms（center / radius 每幀變動）
    this.syncViewUniforms();

    // 更新粒子位置
    if (this.config.type === 'snow') {
      this.updateSnowParticles(dt);
    } else {
      this.updateRainParticles(dt);
    }

    // 投影矩陣
    this._matrixM.fromArray(matrix);
    this._scaleVector.set(
      this.modelTransform.scale,
      -this.modelTransform.scale,
      this.modelTransform.scale
    );
    this._matrixL
      .makeTranslation(
        this.modelTransform.translateX,
        this.modelTransform.translateY,
        this.modelTransform.translateZ
      )
      .scale(this._scaleVector);

    this.camera.projectionMatrix = this._matrixM.multiply(this._matrixL);

    this.renderer.resetState();
    this.renderer.render(this.scene, this.camera);
    this.map.triggerRepaint();
  }

  onRemove(): void {
    this.clearParticles();
    if (this.renderer) this.renderer.dispose();
    this.map = null;
  }

  // ============================
  // 粒子系統管理
  // ============================

  private rebuildParticles(): void {
    this.clearParticles();

    const preset = WEATHER_PRESETS[this.config.type];
    this.particleCount = preset.particles;
    if (this.particleCount === 0) return;

    if (preset.fogDensity > 0) {
      this.scene.fog = new THREE.FogExp2(preset.color, preset.fogDensity);
    } else {
      this.scene.fog = null;
    }

    const windRad = (this.config.windDirection || 30) * Math.PI / 180;
    const windX = (this.config.windSpeed || 1.5) * Math.sin(windRad);
    const windY = (this.config.windSpeed || 1.5) * Math.cos(windRad);

    if (this.config.type === 'snow') {
      this.buildSnowParticles(preset, windX, windY);
    } else {
      this.buildRainParticles(preset, windX, windY);
    }
  }

  private buildRainParticles(preset: WeatherPreset, windX: number, windY: number): void {
    const N = this.particleCount;

    this.linePositions = new Float32Array(N * 6);
    this.lineAlphas = new Float32Array(N * 2);
    this.velocities = new Float32Array(N * 3);

    for (let i = 0; i < N; i++) {
      this.initRainParticle(i, preset, windX, windY, true);
    }

    this.rainGeometry = new THREE.BufferGeometry();
    this.rainGeometry.setAttribute('position', new THREE.BufferAttribute(this.linePositions, 3));
    this.rainGeometry.setAttribute('alpha', new THREE.BufferAttribute(this.lineAlphas, 1));

    this.rainMaterial = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      depthTest: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        color: { value: new THREE.Color(preset.color) },
        opacity: { value: preset.opacity },
        viewCenter: { value: new THREE.Vector2(this._viewCenter.x, this._viewCenter.y) },
        viewRadius: { value: this._viewRadius },
      },
      vertexShader: rainVertexShader,
      fragmentShader: rainFragmentShader,
    });

    this.rainMesh = new THREE.LineSegments(this.rainGeometry, this.rainMaterial);
    this.scene.add(this.rainMesh);
  }

  private buildSnowParticles(preset: WeatherPreset, windX: number, windY: number): void {
    const N = this.particleCount;

    this.snowPositions = new Float32Array(N * 3);
    this.velocities = new Float32Array(N * 3);

    for (let i = 0; i < N; i++) {
      this.initSnowParticle(i, preset, windX, windY, true);
    }

    this.snowGeometry = new THREE.BufferGeometry();
    this.snowGeometry.setAttribute('position', new THREE.BufferAttribute(this.snowPositions, 3));

    this.snowMaterial = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      depthTest: false,
      uniforms: {
        color: { value: new THREE.Color(preset.color) },
        opacity: { value: preset.opacity },
        size: { value: preset.size },
        viewCenter: { value: new THREE.Vector2(this._viewCenter.x, this._viewCenter.y) },
        viewRadius: { value: this._viewRadius },
      },
      vertexShader: snowVertexShader,
      fragmentShader: snowFragmentShader,
    });

    this.snowMesh = new THREE.Points(this.snowGeometry, this.snowMaterial);
    this.scene.add(this.snowMesh);
  }

  /** 在圓形區域內隨機生成一個位置 */
  private randomPointInCircle(): { x: number; y: number } {
    const angle = Math.random() * Math.PI * 2;
    const r = Math.sqrt(Math.random()) * this._viewRadius; // sqrt 確保面積均勻分佈
    return {
      x: this._viewCenter.x + r * Math.cos(angle),
      y: this._viewCenter.y + r * Math.sin(angle),
    };
  }

  /** 初始化單一雨滴粒子（世界座標，圓形分佈） */
  private initRainParticle(
    index: number,
    preset: WeatherPreset,
    windX: number,
    windY: number,
    randomHeight: boolean,
  ): void {
    if (!this.linePositions || !this.lineAlphas || !this.velocities) return;

    const i6 = index * 6;
    const i3 = index * 3;
    const i2 = index * 2;

    const { x, y } = this.randomPointInCircle();
    const z = randomHeight ? Math.random() * RAIN_HEIGHT : RAIN_HEIGHT * (0.9 + Math.random() * 0.1);

    const speedVariation = 0.7 + Math.random() * 0.6;
    const vx = windX + (Math.random() - 0.5) * 2;
    const vy = windY + (Math.random() - 0.5) * 2;
    const vz = -(preset.fallSpeed * speedVariation);

    this.velocities[i3] = vx;
    this.velocities[i3 + 1] = vy;
    this.velocities[i3 + 2] = vz;

    const speed = Math.sqrt(vx * vx + vy * vy + vz * vz);
    const streakX = (-vx / speed) * preset.streakLength;
    const streakY = (-vy / speed) * preset.streakLength;
    const streakZ = (-vz / speed) * preset.streakLength;

    this.linePositions[i6] = x;
    this.linePositions[i6 + 1] = y;
    this.linePositions[i6 + 2] = z;

    this.linePositions[i6 + 3] = x + streakX;
    this.linePositions[i6 + 4] = y + streakY;
    this.linePositions[i6 + 5] = z + streakZ;

    this.lineAlphas[i2] = 0.8 + Math.random() * 0.2;
    this.lineAlphas[i2 + 1] = 0.1 + Math.random() * 0.15;
  }

  /** 初始化單一雪花粒子（世界座標，圓形分佈） */
  private initSnowParticle(
    index: number,
    preset: WeatherPreset,
    windX: number,
    windY: number,
    randomHeight: boolean,
  ): void {
    if (!this.snowPositions || !this.velocities) return;

    const i3 = index * 3;
    const { x, y } = this.randomPointInCircle();
    this.snowPositions[i3] = x;
    this.snowPositions[i3 + 1] = y;
    this.snowPositions[i3 + 2] = randomHeight ? Math.random() * RAIN_HEIGHT : RAIN_HEIGHT * (0.9 + Math.random() * 0.1);

    this.velocities[i3] = windX + (Math.random() - 0.5) * 3;
    this.velocities[i3 + 1] = windY + (Math.random() - 0.5) * 3;
    this.velocities[i3 + 2] = -(preset.fallSpeed * (0.5 + Math.random() * 0.5));
  }

  // ============================
  // 每幀更新
  // ============================

  private updateRainParticles(dt: number): void {
    if (!this.linePositions || !this.velocities || !this.rainGeometry) return;

    const preset = WEATHER_PRESETS[this.config.type];
    const windRad = (this.config.windDirection || 30) * Math.PI / 180;
    const windX = (this.config.windSpeed || 1.5) * Math.sin(windRad);
    const windY = (this.config.windSpeed || 1.5) * Math.cos(windRad);
    const cx = this._viewCenter.x;
    const cy = this._viewCenter.y;
    const r2 = this._viewRadius * this._viewRadius;

    for (let i = 0; i < this.particleCount; i++) {
      const i6 = i * 6;
      const i3 = i * 3;

      const vx = this.velocities[i3];
      const vy = this.velocities[i3 + 1];
      const vz = this.velocities[i3 + 2];

      this.linePositions[i6] += vx * dt;
      this.linePositions[i6 + 1] += vy * dt;
      this.linePositions[i6 + 2] += vz * dt;

      this.linePositions[i6 + 3] += vx * dt;
      this.linePositions[i6 + 4] += vy * dt;
      this.linePositions[i6 + 5] += vz * dt;

      // 落到地面 或 超出圓形範圍 → 重生
      const x = this.linePositions[i6];
      const y = this.linePositions[i6 + 1];
      const dx = x - cx;
      const dy = y - cy;
      if (this.linePositions[i6 + 2] < 0 || dx * dx + dy * dy > r2) {
        this.initRainParticle(i, preset, windX, windY, false);
      }
    }

    const posAttr = this.rainGeometry.getAttribute('position') as THREE.BufferAttribute;
    posAttr.needsUpdate = true;
  }

  private updateSnowParticles(dt: number): void {
    if (!this.snowPositions || !this.velocities || !this.snowGeometry) return;

    const preset = WEATHER_PRESETS[this.config.type];
    const windRad = (this.config.windDirection || 30) * Math.PI / 180;
    const windX = (this.config.windSpeed || 1.5) * Math.sin(windRad);
    const windY = (this.config.windSpeed || 1.5) * Math.cos(windRad);
    const time = performance.now() / 1000;
    const cx = this._viewCenter.x;
    const cy = this._viewCenter.y;
    const r2 = this._viewRadius * this._viewRadius;

    for (let i = 0; i < this.particleCount; i++) {
      const i3 = i * 3;
      const wobble = Math.sin(time * 2 + i * 0.1) * 1.5;

      this.snowPositions[i3] += (this.velocities[i3] + wobble) * dt;
      this.snowPositions[i3 + 1] += this.velocities[i3 + 1] * dt;
      this.snowPositions[i3 + 2] += this.velocities[i3 + 2] * dt;

      const x = this.snowPositions[i3];
      const y = this.snowPositions[i3 + 1];
      const dx = x - cx;
      const dy = y - cy;
      if (this.snowPositions[i3 + 2] < 0 || dx * dx + dy * dy > r2) {
        this.initSnowParticle(i, preset, windX, windY, false);
      }
    }

    const posAttr = this.snowGeometry.getAttribute('position') as THREE.BufferAttribute;
    posAttr.needsUpdate = true;
  }

  /**
   * 計算圓形可視範圍。
   * 用 map.getBounds() 的對角線長度作為直徑，確保覆蓋整個可視區域（含傾斜視角）。
   */
  private updateViewArea(): void {
    if (!this.map) return;

    const center = this.map.getCenter();
    this._viewCenter = this.lngLatToMeters(center.lng, center.lat);

    const bounds = this.map.getBounds();
    const sw = this.lngLatToMeters(bounds.getWest(), bounds.getSouth());
    const ne = this.lngLatToMeters(bounds.getEast(), bounds.getNorth());

    // 對角線長度的一半 + 30% 邊距 = 圓形半徑
    const diagX = ne.x - sw.x;
    const diagY = ne.y - sw.y;
    const halfDiag = Math.sqrt(diagX * diagX + diagY * diagY) / 2;
    this._viewRadius = halfDiag * 1.3;
  }

  /** 每幀同步 shader 的 viewCenter / viewRadius uniform */
  private syncViewUniforms(): void {
    if (this.rainMaterial) {
      (this.rainMaterial.uniforms.viewCenter.value as THREE.Vector2).set(
        this._viewCenter.x, this._viewCenter.y
      );
      this.rainMaterial.uniforms.viewRadius.value = this._viewRadius;
    }
    if (this.snowMaterial) {
      (this.snowMaterial.uniforms.viewCenter.value as THREE.Vector2).set(
        this._viewCenter.x, this._viewCenter.y
      );
      this.snowMaterial.uniforms.viewRadius.value = this._viewRadius;
    }
  }

  // ============================
  // 輔助方法
  // ============================

  private updateMaterialUniforms(): void {
    const preset = WEATHER_PRESETS[this.config.type];
    if (this.rainMaterial) {
      this.rainMaterial.uniforms.opacity.value = preset.opacity;
      this.rainMaterial.uniforms.color.value.set(preset.color);
    }
    if (this.snowMaterial) {
      this.snowMaterial.uniforms.opacity.value = preset.opacity;
      this.snowMaterial.uniforms.color.value.set(preset.color);
      this.snowMaterial.uniforms.size.value = preset.size;
    }
    if (preset.fogDensity > 0) {
      this.scene.fog = new THREE.FogExp2(preset.color, preset.fogDensity);
    } else {
      this.scene.fog = null;
    }
  }

  private clearParticles(): void {
    if (this.rainMesh) {
      this.scene.remove(this.rainMesh);
      this.rainGeometry?.dispose();
      this.rainMaterial?.dispose();
      this.rainMesh = null;
      this.rainGeometry = null;
      this.rainMaterial = null;
    }
    if (this.snowMesh) {
      this.scene.remove(this.snowMesh);
      this.snowGeometry?.dispose();
      this.snowMaterial?.dispose();
      this.snowMesh = null;
      this.snowGeometry = null;
      this.snowMaterial = null;
    }
    this.linePositions = null;
    this.lineAlphas = null;
    this.snowPositions = null;
    this.velocities = null;
    this.scene.fog = null;
  }

  private lngLatToMeters(lng: number, lat: number): { x: number; y: number } {
    if (!this.modelTransform) return { x: 0, y: 0 };
    const mercator = mapboxgl.MercatorCoordinate.fromLngLat([lng, lat], 0);
    const x = (mercator.x - this.modelTransform.translateX) / this.modelTransform.scale;
    const y = (this.modelTransform.translateY - mercator.y) / this.modelTransform.scale;
    return { x, y };
  }
}
