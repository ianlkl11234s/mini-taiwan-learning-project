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

// 雨區範圍（公尺），涵蓋相機可視區域
const RAIN_AREA = 6000;
const RAIN_HEIGHT = 1500;

// ============================================================
// 自訂 Shader：讓雨絲有漸層透明效果
// ============================================================

const rainVertexShader = /* glsl */ `
  attribute float alpha;
  varying float vAlpha;

  void main() {
    vAlpha = alpha;
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

// 雪花用 Points shader
const snowVertexShader = /* glsl */ `
  uniform float size;
  varying float vAlpha;

  void main() {
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    // 根據距離縮放粒子大小
    gl_PointSize = size * (800.0 / -mvPosition.z);
    gl_PointSize = clamp(gl_PointSize, 1.0, 12.0);
    gl_Position = projectionMatrix * mvPosition;
    // 根據高度做淡入淡出
    float heightRatio = position.z / ${RAIN_HEIGHT.toFixed(1)};
    vAlpha = smoothstep(0.0, 0.05, heightRatio) * (1.0 - smoothstep(0.85, 1.0, heightRatio));
  }
`;

const snowFragmentShader = /* glsl */ `
  uniform vec3 color;
  uniform float opacity;
  varying float vAlpha;

  void main() {
    // 圓形粒子
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

  // 粒子資料（雨用 LineSegments，每個粒子 2 頂點 × 3 分量 = 6 floats）
  private linePositions: Float32Array | null = null;
  private lineAlphas: Float32Array | null = null;
  // 雪用 Points，每個粒子 3 floats
  private snowPositions: Float32Array | null = null;

  // 每個粒子的速度（N × 3）
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

  // 可視範圍的世界座標邊界（公尺，相對 MODEL_ORIGIN）
  // 粒子在此範圍內生成與回收，確保覆蓋整個畫面
  private _visibleBounds = {
    minX: -RAIN_AREA / 2, maxX: RAIN_AREA / 2,
    minY: -RAIN_AREA / 2, maxY: RAIN_AREA / 2,
  };

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
    this.updateVisibleBounds(); // 先計算可視範圍，供 rebuildParticles 使用
    this.rebuildParticles();

    // 開發用 debug（可移除）
    if (import.meta.env.DEV) {
      (window as unknown as Record<string, unknown>).__weatherLayer = this;
    }
  }

  render(_gl: WebGLRenderingContext, matrix: number[]): void {
    if (!this.renderer || !this.modelTransform || !this.map) return;
    if (this.config.type === 'clear') return;

    // 計算 dt
    const now = performance.now();
    const dt = Math.min((now - this.lastRenderTime) / 1000, 0.1); // 限制最大 dt，避免切頁回來粒子飛走
    this.lastRenderTime = now;

    // 更新可視範圍（粒子回收/重生用）
    this.updateVisibleBounds();

    // 更新粒子位置
    if (this.config.type !== 'clear') {
      if (this.config.type === 'snow') {
        this.updateSnowParticles(dt);
      } else {
        this.updateRainParticles(dt);
      }
    }

    // 投影矩陣（與 Train3DLayer 相同邏輯）
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

    // 設定場景霧氣
    if (preset.fogDensity > 0) {
      this.scene.fog = new THREE.FogExp2(preset.color, preset.fogDensity);
    } else {
      this.scene.fog = null;
    }

    // 風的水平分量（公尺/秒）
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

    // 每個粒子 = 1 條線段 = 2 頂點
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
      },
      vertexShader: snowVertexShader,
      fragmentShader: snowFragmentShader,
    });

    this.snowMesh = new THREE.Points(this.snowGeometry, this.snowMaterial);
    this.scene.add(this.snowMesh);
  }

  /** 初始化單一雨滴粒子 */
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

    // 底部頂點（世界座標，公尺）
    const b = this._visibleBounds;
    const x = b.minX + Math.random() * (b.maxX - b.minX);
    const y = b.minY + Math.random() * (b.maxY - b.minY);
    const z = randomHeight ? Math.random() * RAIN_HEIGHT : RAIN_HEIGHT * (0.9 + Math.random() * 0.1);

    // 速度：水平風 + 垂直下墜 + 隨機擾動
    const speedVariation = 0.7 + Math.random() * 0.6;
    const vx = windX + (Math.random() - 0.5) * 2;
    const vy = windY + (Math.random() - 0.5) * 2;
    const vz = -(preset.fallSpeed * speedVariation);

    this.velocities[i3] = vx;
    this.velocities[i3 + 1] = vy;
    this.velocities[i3 + 2] = vz;

    // 計算拖尾方向（與速度反向）
    const speed = Math.sqrt(vx * vx + vy * vy + vz * vz);
    const streakX = (-vx / speed) * preset.streakLength;
    const streakY = (-vy / speed) * preset.streakLength;
    const streakZ = (-vz / speed) * preset.streakLength;

    // 底部頂點
    this.linePositions[i6] = x;
    this.linePositions[i6 + 1] = y;
    this.linePositions[i6 + 2] = z;

    // 頂部頂點（拖尾端）
    this.linePositions[i6 + 3] = x + streakX;
    this.linePositions[i6 + 4] = y + streakY;
    this.linePositions[i6 + 5] = z + streakZ;

    // Alpha：底部亮、頂部暗
    this.lineAlphas[i2] = 0.8 + Math.random() * 0.2;
    this.lineAlphas[i2 + 1] = 0.1 + Math.random() * 0.15;
  }

  /** 初始化單一雪花粒子 */
  private initSnowParticle(
    index: number,
    preset: WeatherPreset,
    windX: number,
    windY: number,
    randomHeight: boolean,
  ): void {
    if (!this.snowPositions || !this.velocities) return;

    const i3 = index * 3;
    const b = this._visibleBounds;
    this.snowPositions[i3] = b.minX + Math.random() * (b.maxX - b.minX);
    this.snowPositions[i3 + 1] = b.minY + Math.random() * (b.maxY - b.minY);
    this.snowPositions[i3 + 2] = randomHeight ? Math.random() * RAIN_HEIGHT : RAIN_HEIGHT * (0.9 + Math.random() * 0.1);

    // 雪花飄動：較大水平擾動 + 緩慢下墜
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

    for (let i = 0; i < this.particleCount; i++) {
      const i6 = i * 6;
      const i3 = i * 3;

      const vx = this.velocities[i3];
      const vy = this.velocities[i3 + 1];
      const vz = this.velocities[i3 + 2];

      // 移動底部頂點
      this.linePositions[i6] += vx * dt;
      this.linePositions[i6 + 1] += vy * dt;
      this.linePositions[i6 + 2] += vz * dt;

      // 移動頂部頂點（同步）
      this.linePositions[i6 + 3] += vx * dt;
      this.linePositions[i6 + 4] += vy * dt;
      this.linePositions[i6 + 5] += vz * dt;

      // 落到地面以下 → 重生
      if (this.linePositions[i6 + 2] < 0) {
        this.initRainParticle(i, preset, windX, windY, false);
      }

      // 超出可視範圍 → 重生
      const x = this.linePositions[i6];
      const y = this.linePositions[i6 + 1];
      const b = this._visibleBounds;
      if (x < b.minX || x > b.maxX || y < b.minY || y > b.maxY) {
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

    for (let i = 0; i < this.particleCount; i++) {
      const i3 = i * 3;

      // 加入正弦飄動效果
      const wobble = Math.sin(time * 2 + i * 0.1) * 1.5;

      this.snowPositions[i3] += (this.velocities[i3] + wobble) * dt;
      this.snowPositions[i3 + 1] += this.velocities[i3 + 1] * dt;
      this.snowPositions[i3 + 2] += this.velocities[i3 + 2] * dt;

      if (this.snowPositions[i3 + 2] < 0) {
        this.initSnowParticle(i, preset, windX, windY, false);
      }

      const x = this.snowPositions[i3];
      const y = this.snowPositions[i3 + 1];
      const b = this._visibleBounds;
      if (x < b.minX || x > b.maxX || y < b.minY || y > b.maxY) {
        this.initSnowParticle(i, preset, windX, windY, false);
      }
    }

    const posAttr = this.snowGeometry.getAttribute('position') as THREE.BufferAttribute;
    posAttr.needsUpdate = true;
  }

  /**
   * 計算目前地圖可視範圍的世界座標邊界。
   * 粒子在此範圍內生成，超出則回收重生。
   * Mesh 固定在原點不動 → 粒子座標即世界座標 → 跟隨模式下雨自然留在原地。
   */
  private updateVisibleBounds(): void {
    if (!this.map) return;

    const bounds = this.map.getBounds();
    const sw = this.lngLatToMeters(bounds.getWest(), bounds.getSouth());
    const ne = this.lngLatToMeters(bounds.getEast(), bounds.getNorth());

    // 含 40% 邊距，讓畫面邊緣不會看到粒子突然出現
    const marginX = Math.abs(ne.x - sw.x) * 0.2;
    const marginY = Math.abs(ne.y - sw.y) * 0.2;

    this._visibleBounds = {
      minX: Math.min(sw.x, ne.x) - marginX,
      maxX: Math.max(sw.x, ne.x) + marginX,
      minY: Math.min(sw.y, ne.y) - marginY,
      maxY: Math.max(sw.y, ne.y) + marginY,
    };
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
