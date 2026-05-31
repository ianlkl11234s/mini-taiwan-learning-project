/**
 * TrainSymbolLayer - WebGL Circle Layer 列車渲染
 * 使用 Mapbox GeoJSON Source + Circle Layer 取代 DOM Markers
 */

import type { Map as MapboxMap, GeoJSONSource, MapLayerMouseEvent } from 'mapbox-gl';
import type { TrainFeature, TrainFeatureCollection } from '../types/trainFeature';

/**
 * 建立圓角正方形圖標（用於 TRA 列車）
 * 使用 Canvas 繪製，返回 ImageData
 */
function createRoundedSquareIcon(size: number, radius: number): ImageData {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;

  // 繪製圓角正方形路徑
  const padding = 2;
  const x = padding;
  const y = padding;
  const width = size - padding * 2;
  const height = size - padding * 2;
  const r = Math.min(radius, width / 2, height / 2);

  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + width - r, y);
  ctx.arcTo(x + width, y, x + width, y + r, r);
  ctx.lineTo(x + width, y + height - r);
  ctx.arcTo(x + width, y + height, x + width - r, y + height, r);
  ctx.lineTo(x + r, y + height);
  ctx.arcTo(x, y + height, x, y + height - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();

  // 填滿白色（實際顏色由 icon-color 控制）
  ctx.fillStyle = '#ffffff';
  ctx.fill();

  return ctx.getImageData(0, 0, size, size);
}

export interface TrainSymbolLayerOptions {
  map: MapboxMap;
  onTrainClick?: (trainUid: string, system: string) => void;
  onReady?: () => void;  // 初始化完成後的回調
}

export class TrainSymbolLayer {
  private map: MapboxMap;
  private onTrainClickCallback: ((trainUid: string, system: string) => void) | null = null;
  private onReadyCallback: (() => void) | null = null;
  private selectedTrainId: string | null = null;
  private currentFeatures: TrainFeature[] = [];
  private initialized = false;

  // Source 和 Layer ID 常數
  static readonly SOURCE_ID = 'all-trains';
  static readonly LAYER_BASE = 'trains-circle-base';
  static readonly LAYER_GLOW = 'trains-circle-glow';
  static readonly LAYER_STOPPED_GLOW = 'trains-circle-stopped-glow';
  static readonly LAYER_COLLISION = 'trains-circle-collision';
  // TRA 專用圖層（圓角正方形）
  static readonly LAYER_TRA_BASE = 'trains-tra-base';
  static readonly LAYER_TRA_GLOW = 'trains-tra-glow';
  static readonly LAYER_TRA_STOPPED_GLOW = 'trains-tra-stopped-glow';
  static readonly TRA_ICON_ID = 'tra-rounded-square';

  constructor(options: TrainSymbolLayerOptions) {
    this.map = options.map;
    if (options.onTrainClick) {
      this.onTrainClickCallback = options.onTrainClick;
    }
    if (options.onReady) {
      this.onReadyCallback = options.onReady;
    }
  }

  /**
   * 初始化 GeoJSON source 和 circle layers
   * 應在 map.on('load') 或 map.isStyleLoaded() 之後呼叫
   */
  initialize(): void {
    if (this.initialized) return;

    // 確認 map style 已載入
    if (!this.map.isStyleLoaded()) {
      // 使用輪詢重試，避免 style.load 事件不觸發的問題
      setTimeout(() => this.initialize(), 50);
      return;
    }

    // 建立空的 GeoJSON source
    this.map.addSource(TrainSymbolLayer.SOURCE_ID, {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: [],
      },
    });

    // === TRA 圓角正方形圖標 ===
    // 建立並註冊圓角正方形圖標（sdf 模式允許動態著色）
    const iconSize = 32;
    const cornerRadius = 8;
    const iconData = createRoundedSquareIcon(iconSize, cornerRadius);
    this.map.addImage(TrainSymbolLayer.TRA_ICON_ID, iconData, { sdf: true });

    // === 非 TRA 的圓形圖層 ===
    // 建立選中光暈圖層 (最底層) - 排除 TRA
    // 尺寸約為選中圓點的 1.5 倍
    this.map.addLayer({
      id: TrainSymbolLayer.LAYER_GLOW,
      type: 'circle',
      source: TrainSymbolLayer.SOURCE_ID,
      minzoom: 10, // 縮放 >= 10 才顯示
      filter: ['all', ['==', ['get', 'isSelected'], true], ['!=', ['get', 'system'], 'tra']],
      paint: {
        'circle-radius': 12,
        'circle-color': ['get', 'color'],
        'circle-opacity': 0.3,
        'circle-blur': 1,
        'circle-emissive-strength': 1.0,
      },
    });

    // 建立停站發光圖層（僅 stopped 且非 selected 時顯示）- 排除 TRA
    // 尺寸約為停站圓點的 1.5 倍
    this.map.addLayer({
      id: TrainSymbolLayer.LAYER_STOPPED_GLOW,
      type: 'circle',
      source: TrainSymbolLayer.SOURCE_ID,
      minzoom: 10, // 縮放 >= 10 才顯示
      filter: [
        'all',
        ['==', ['get', 'status'], 'stopped'],
        ['!=', ['get', 'isSelected'], true],
        ['!=', ['get', 'system'], 'tra'],
      ],
      paint: {
        'circle-radius': 9,
        'circle-color': ['get', 'color'],
        'circle-opacity': 0.25,
        'circle-blur': 0.8,
        'circle-emissive-strength': 1.0,
      },
    });

    // 建立碰撞警示圖層 - 排除 TRA
    this.map.addLayer({
      id: TrainSymbolLayer.LAYER_COLLISION,
      type: 'circle',
      source: TrainSymbolLayer.SOURCE_ID,
      minzoom: 10, // 縮放 >= 10 才顯示
      filter: ['all', ['==', ['get', 'isColliding'], true], ['!=', ['get', 'system'], 'tra']],
      paint: {
        'circle-radius': 8,
        'circle-color': '#ffcc00',
        'circle-stroke-color': '#ff6600',
        'circle-stroke-width': 2,
        'circle-opacity': 0.6,
        'circle-blur': 0.5,
        'circle-emissive-strength': 1.0,
      },
    });

    // 建立基礎圓點圖層 - 排除 TRA
    // 尺寸匹配參考專案 DOM Markers: running 12px, stopped 14px, selected 18px
    // 公式: total_size = 2 * radius + 2 * stroke_width (stroke 在外圈)
    this.map.addLayer({
      id: TrainSymbolLayer.LAYER_BASE,
      type: 'circle',
      source: TrainSymbolLayer.SOURCE_ID,
      minzoom: 10, // 縮放 >= 10 才顯示
      filter: ['!=', ['get', 'system'], 'tra'],
      paint: {
        'circle-radius': [
          'case',
          ['get', 'isSelected'], 6,    // 6*2 + 3*2 = 18px
          ['==', ['get', 'status'], 'stopped'], 5, // 5*2 + 2*2 = 14px
          4,                            // 4*2 + 2*2 = 12px
        ],
        'circle-color': ['get', 'color'],
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': [
          'case',
          ['get', 'isSelected'], 3,
          2,
        ],
        'circle-opacity': 0.95,
        'circle-emissive-strength': 1.0,
      },
    });

    // === TRA 專用圓角正方形圖層 ===
    // TRA 選中光暈
    this.map.addLayer({
      id: TrainSymbolLayer.LAYER_TRA_GLOW,
      type: 'symbol',
      source: TrainSymbolLayer.SOURCE_ID,
      minzoom: 10, // 縮放 >= 10 才顯示
      filter: ['all', ['==', ['get', 'system'], 'tra'], ['==', ['get', 'isSelected'], true]],
      layout: {
        'icon-image': TrainSymbolLayer.TRA_ICON_ID,
        'icon-size': 0.9,
        'icon-allow-overlap': true,
      },
      paint: {
        'icon-color': ['get', 'color'],
        'icon-opacity': 0.3,
        'icon-emissive-strength': 1.0,
      },
    });

    // TRA 停站光暈
    this.map.addLayer({
      id: TrainSymbolLayer.LAYER_TRA_STOPPED_GLOW,
      type: 'symbol',
      source: TrainSymbolLayer.SOURCE_ID,
      minzoom: 10, // 縮放 >= 10 才顯示
      filter: [
        'all',
        ['==', ['get', 'system'], 'tra'],
        ['==', ['get', 'status'], 'stopped'],
        ['!=', ['get', 'isSelected'], true],
      ],
      layout: {
        'icon-image': TrainSymbolLayer.TRA_ICON_ID,
        'icon-size': 0.6,
        'icon-allow-overlap': true,
      },
      paint: {
        'icon-color': ['get', 'color'],
        'icon-opacity': 0.25,
        'icon-emissive-strength': 1.0,
      },
    });

    // TRA 基礎圖層（圓角正方形）
    this.map.addLayer({
      id: TrainSymbolLayer.LAYER_TRA_BASE,
      type: 'symbol',
      source: TrainSymbolLayer.SOURCE_ID,
      minzoom: 10, // 縮放 >= 10 才顯示
      filter: ['==', ['get', 'system'], 'tra'],
      layout: {
        'icon-image': TrainSymbolLayer.TRA_ICON_ID,
        'icon-size': [
          'case',
          ['get', 'isSelected'], 0.6,     // 選中時較大
          ['==', ['get', 'status'], 'stopped'], 0.5, // 停站時中等
          0.42,                            // 行駛中較小
        ],
        'icon-allow-overlap': true,
      },
      paint: {
        'icon-color': ['get', 'color'],
        'icon-opacity': 0.95,
        'icon-halo-color': '#ffffff',
        'icon-halo-width': [
          'case',
          ['get', 'isSelected'], 4,
          3,
        ],
        'icon-emissive-strength': 1.0,
      },
    });

    // 綁定點擊事件（包含 TRA 圖層）
    this.map.on('click', TrainSymbolLayer.LAYER_BASE, this.handleClick);
    this.map.on('click', TrainSymbolLayer.LAYER_TRA_BASE, this.handleClick);

    // 設定游標樣式（包含 TRA 圖層）
    this.map.on('mouseenter', TrainSymbolLayer.LAYER_BASE, this.handleMouseEnter);
    this.map.on('mouseleave', TrainSymbolLayer.LAYER_BASE, this.handleMouseLeave);
    this.map.on('mouseenter', TrainSymbolLayer.LAYER_TRA_BASE, this.handleMouseEnter);
    this.map.on('mouseleave', TrainSymbolLayer.LAYER_TRA_BASE, this.handleMouseLeave);

    this.initialized = true;

    // 通知初始化完成
    if (this.onReadyCallback) {
      this.onReadyCallback();
    }
  }

  /**
   * 批次更新所有列車
   */
  updateTrains(features: TrainFeature[]): void {
    if (!this.initialized) return;

    this.currentFeatures = features;

    const source = this.map.getSource(TrainSymbolLayer.SOURCE_ID) as GeoJSONSource;
    if (source) {
      const featureCollection: TrainFeatureCollection = {
        type: 'FeatureCollection',
        features: features,
      };
      source.setData(featureCollection as GeoJSON.FeatureCollection);
    }
  }

  /**
   * 設定選中的列車 ID
   */
  setSelectedTrainId(trainUid: string | null): void {
    if (this.selectedTrainId === trainUid) return;
    this.selectedTrainId = trainUid;

    // 更新 features 的 isSelected 屬性並重新渲染
    const updatedFeatures = this.currentFeatures.map(f => ({
      ...f,
      properties: {
        ...f.properties,
        isSelected: f.properties.trainUid === trainUid,
      },
    }));

    this.updateTrains(updatedFeatures);
  }

  /**
   * 取得目前選中的列車 ID
   */
  getSelectedTrainId(): string | null {
    return this.selectedTrainId;
  }

  /**
   * 檢查是否已初始化
   */
  isInitialized(): boolean {
    return this.initialized;
  }

  /**
   * 設定圖層可見性
   */
  setVisibility(visible: boolean): void {
    if (!this.initialized) return;

    const visibility = visible ? 'visible' : 'none';

    // 非 TRA 圓形圖層
    if (this.map.getLayer(TrainSymbolLayer.LAYER_BASE)) {
      this.map.setLayoutProperty(TrainSymbolLayer.LAYER_BASE, 'visibility', visibility);
    }
    if (this.map.getLayer(TrainSymbolLayer.LAYER_GLOW)) {
      this.map.setLayoutProperty(TrainSymbolLayer.LAYER_GLOW, 'visibility', visibility);
    }
    if (this.map.getLayer(TrainSymbolLayer.LAYER_STOPPED_GLOW)) {
      this.map.setLayoutProperty(TrainSymbolLayer.LAYER_STOPPED_GLOW, 'visibility', visibility);
    }
    if (this.map.getLayer(TrainSymbolLayer.LAYER_COLLISION)) {
      this.map.setLayoutProperty(TrainSymbolLayer.LAYER_COLLISION, 'visibility', visibility);
    }
    // TRA 圓角正方形圖層
    if (this.map.getLayer(TrainSymbolLayer.LAYER_TRA_BASE)) {
      this.map.setLayoutProperty(TrainSymbolLayer.LAYER_TRA_BASE, 'visibility', visibility);
    }
    if (this.map.getLayer(TrainSymbolLayer.LAYER_TRA_GLOW)) {
      this.map.setLayoutProperty(TrainSymbolLayer.LAYER_TRA_GLOW, 'visibility', visibility);
    }
    if (this.map.getLayer(TrainSymbolLayer.LAYER_TRA_STOPPED_GLOW)) {
      this.map.setLayoutProperty(TrainSymbolLayer.LAYER_TRA_STOPPED_GLOW, 'visibility', visibility);
    }
  }

  /**
   * 點擊事件處理
   */
  private handleClick = (e: MapLayerMouseEvent): void => {
    if (!this.onTrainClickCallback) return;
    if (!e.features || e.features.length === 0) return;

    let closestFeature = e.features[0];
    let minDistSq = Infinity;

    for (const feature of e.features) {
      if (feature.geometry?.type !== 'Point') continue;

      const coordinates = feature.geometry.coordinates as [number, number];
      const point = this.map.project(coordinates);
      const dx = point.x - e.point.x;
      const dy = point.y - e.point.y;
      const distSq = dx * dx + dy * dy;

      if (distSq < minDistSq) {
        minDistSq = distSq;
        closestFeature = feature;
      }
    }

    const trainUid = closestFeature.properties?.trainUid;
    const system = closestFeature.properties?.system;

    if (trainUid && system) {
      this.onTrainClickCallback(trainUid, system);
    }
  };

  /**
   * 滑鼠進入處理
   */
  private handleMouseEnter = (): void => {
    this.map.getCanvas().style.cursor = 'pointer';
  };

  /**
   * 滑鼠離開處理
   */
  private handleMouseLeave = (): void => {
    this.map.getCanvas().style.cursor = '';
  };

  /**
   * 設定點擊回調
   */
  onTrainClick(callback: (trainUid: string, system: string) => void): void {
    this.onTrainClickCallback = callback;
  }

  /**
   * 清理資源
   */
  destroy(): void {
    if (!this.initialized) return;

    // 移除事件監聽（包含 TRA 圖層）
    this.map.off('click', TrainSymbolLayer.LAYER_BASE, this.handleClick);
    this.map.off('click', TrainSymbolLayer.LAYER_TRA_BASE, this.handleClick);
    this.map.off('mouseenter', TrainSymbolLayer.LAYER_BASE, this.handleMouseEnter);
    this.map.off('mouseleave', TrainSymbolLayer.LAYER_BASE, this.handleMouseLeave);
    this.map.off('mouseenter', TrainSymbolLayer.LAYER_TRA_BASE, this.handleMouseEnter);
    this.map.off('mouseleave', TrainSymbolLayer.LAYER_TRA_BASE, this.handleMouseLeave);

    // 移除圖層 (順序重要，從上到下)
    // TRA 圖層
    if (this.map.getLayer(TrainSymbolLayer.LAYER_TRA_BASE)) {
      this.map.removeLayer(TrainSymbolLayer.LAYER_TRA_BASE);
    }
    if (this.map.getLayer(TrainSymbolLayer.LAYER_TRA_STOPPED_GLOW)) {
      this.map.removeLayer(TrainSymbolLayer.LAYER_TRA_STOPPED_GLOW);
    }
    if (this.map.getLayer(TrainSymbolLayer.LAYER_TRA_GLOW)) {
      this.map.removeLayer(TrainSymbolLayer.LAYER_TRA_GLOW);
    }
    // 非 TRA 圖層
    if (this.map.getLayer(TrainSymbolLayer.LAYER_BASE)) {
      this.map.removeLayer(TrainSymbolLayer.LAYER_BASE);
    }
    if (this.map.getLayer(TrainSymbolLayer.LAYER_COLLISION)) {
      this.map.removeLayer(TrainSymbolLayer.LAYER_COLLISION);
    }
    if (this.map.getLayer(TrainSymbolLayer.LAYER_STOPPED_GLOW)) {
      this.map.removeLayer(TrainSymbolLayer.LAYER_STOPPED_GLOW);
    }
    if (this.map.getLayer(TrainSymbolLayer.LAYER_GLOW)) {
      this.map.removeLayer(TrainSymbolLayer.LAYER_GLOW);
    }

    // 移除 source
    if (this.map.getSource(TrainSymbolLayer.SOURCE_ID)) {
      this.map.removeSource(TrainSymbolLayer.SOURCE_ID);
    }

    // 移除圖標
    if (this.map.hasImage(TrainSymbolLayer.TRA_ICON_ID)) {
      this.map.removeImage(TrainSymbolLayer.TRA_ICON_ID);
    }

    this.onTrainClickCallback = null;
    this.currentFeatures = [];
    this.selectedTrainId = null;
    this.initialized = false;
  }
}
