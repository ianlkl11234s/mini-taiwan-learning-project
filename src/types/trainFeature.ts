/**
 * TrainFeature 型別定義
 * 用於 WebGL Circle Layer 的 GeoJSON Feature 結構
 */

/** 運輸系統類型 */
export type TransportSystem = 'trtc' | 'thsr' | 'krtc' | 'klrt' | 'tmrt' | 'tra';

/** 列車狀態 */
export type TrainStatus = 'waiting' | 'running' | 'stopped' | 'arrived';

/** TrainFeature 的 properties 結構 */
export interface TrainFeatureProperties {
  /** 班次識別碼（不同軌道可能重複） */
  trainId: string;
  /** 地圖列車唯一識別碼：trackId::trainId */
  trainUid: string;
  /** 軌道 ID */
  trackId: string;
  /** 所屬運輸系統 */
  system: TransportSystem;
  /** 路線 ID (如 BR, R, G, BL 等) */
  lineId: string;
  /** 行駛方向 (0 或 1) */
  direction: number;
  /** 列車狀態 */
  status: TrainStatus;
  /** 是否被選中 */
  isSelected: boolean;
  /** 是否碰撞中 */
  isColliding: boolean;
  /** 顯示顏色 (hex) */
  color: string;
}

/** GeoJSON Feature 結構，用於 Mapbox GeoJSON Source */
export interface TrainFeature {
  type: 'Feature';
  properties: TrainFeatureProperties;
  geometry: {
    type: 'Point';
    coordinates: [number, number]; // [lng, lat]
  };
}

/** GeoJSON FeatureCollection，用於批次更新 */
export interface TrainFeatureCollection {
  type: 'FeatureCollection';
  features: TrainFeature[];
}
