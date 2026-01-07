/**
 * TrainSymbolLayer - WebGL Circle Layer 列車渲染
 * 使用 Mapbox GeoJSON Source + Circle Layer 取代 DOM Markers
 */

import type { Map as MapboxMap, GeoJSONSource, MapLayerMouseEvent } from 'mapbox-gl';
import type { TrainFeature, TrainFeatureCollection } from '../types/trainFeature';

export interface TrainSymbolLayerOptions {
  map: MapboxMap;
  onTrainClick?: (trainId: string, system: string) => void;
  onReady?: () => void;  // 初始化完成後的回調
}

export class TrainSymbolLayer {
  private map: MapboxMap;
  private onTrainClickCallback: ((trainId: string, system: string) => void) | null = null;
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

    // 建立選中光暈圖層 (最底層)
    this.map.addLayer({
      id: TrainSymbolLayer.LAYER_GLOW,
      type: 'circle',
      source: TrainSymbolLayer.SOURCE_ID,
      filter: ['==', ['get', 'isSelected'], true],
      paint: {
        'circle-radius': 16,
        'circle-color': ['get', 'color'],
        'circle-opacity': 0.3,
        'circle-blur': 1,
      },
    });

    // 建立停站發光圖層（僅 stopped 且非 selected 時顯示）
    this.map.addLayer({
      id: TrainSymbolLayer.LAYER_STOPPED_GLOW,
      type: 'circle',
      source: TrainSymbolLayer.SOURCE_ID,
      filter: [
        'all',
        ['==', ['get', 'status'], 'stopped'],
        ['!=', ['get', 'isSelected'], true],
      ],
      paint: {
        'circle-radius': 12,
        'circle-color': ['get', 'color'],
        'circle-opacity': 0.25,
        'circle-blur': 0.8,
      },
    });

    // 建立碰撞警示圖層
    this.map.addLayer({
      id: TrainSymbolLayer.LAYER_COLLISION,
      type: 'circle',
      source: TrainSymbolLayer.SOURCE_ID,
      filter: ['==', ['get', 'isColliding'], true],
      paint: {
        'circle-radius': 12,
        'circle-color': '#ffcc00',
        'circle-stroke-color': '#ff6600',
        'circle-stroke-width': 2,
        'circle-opacity': 0.6,
        'circle-blur': 0.5,
      },
    });

    // 建立基礎圓點圖層 (最上層)
    this.map.addLayer({
      id: TrainSymbolLayer.LAYER_BASE,
      type: 'circle',
      source: TrainSymbolLayer.SOURCE_ID,
      paint: {
        'circle-radius': [
          'case',
          ['get', 'isSelected'], 9,
          ['==', ['get', 'status'], 'stopped'], 7,
          6,
        ],
        'circle-color': ['get', 'color'],
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': [
          'case',
          ['get', 'isSelected'], 3,
          2,
        ],
        'circle-opacity': 0.95,
      },
    });

    // 綁定點擊事件
    this.map.on('click', TrainSymbolLayer.LAYER_BASE, this.handleClick);

    // 設定游標樣式
    this.map.on('mouseenter', TrainSymbolLayer.LAYER_BASE, this.handleMouseEnter);
    this.map.on('mouseleave', TrainSymbolLayer.LAYER_BASE, this.handleMouseLeave);

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
  setSelectedTrainId(trainId: string | null): void {
    if (this.selectedTrainId === trainId) return;
    this.selectedTrainId = trainId;

    // 更新 features 的 isSelected 屬性並重新渲染
    const updatedFeatures = this.currentFeatures.map(f => ({
      ...f,
      properties: {
        ...f.properties,
        isSelected: f.properties.trainId === trainId,
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
  }

  /**
   * 點擊事件處理
   */
  private handleClick = (e: MapLayerMouseEvent): void => {
    if (!this.onTrainClickCallback) return;
    if (!e.features || e.features.length === 0) return;

    const feature = e.features[0];
    const trainId = feature.properties?.trainId;
    const system = feature.properties?.system;

    if (trainId && system) {
      this.onTrainClickCallback(trainId, system);
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
  onTrainClick(callback: (trainId: string, system: string) => void): void {
    this.onTrainClickCallback = callback;
  }

  /**
   * 清理資源
   */
  destroy(): void {
    if (!this.initialized) return;

    // 移除事件監聽
    this.map.off('click', TrainSymbolLayer.LAYER_BASE, this.handleClick);
    this.map.off('mouseenter', TrainSymbolLayer.LAYER_BASE, this.handleMouseEnter);
    this.map.off('mouseleave', TrainSymbolLayer.LAYER_BASE, this.handleMouseLeave);

    // 移除圖層 (順序重要，從上到下)
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

    this.onTrainClickCallback = null;
    this.currentFeatures = [];
    this.selectedTrainId = null;
    this.initialized = false;
  }
}
