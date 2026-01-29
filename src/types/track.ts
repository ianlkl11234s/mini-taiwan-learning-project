/**
 * 軌道資料類型定義
 */

export interface LineStringGeometry {
  type: 'LineString';
  coordinates: [number, number][];
}

export interface MultiLineStringGeometry {
  type: 'MultiLineString';
  coordinates: [number, number][][];
}

export type TrackGeometry = LineStringGeometry | MultiLineStringGeometry;

export interface TrackProperties {
  track_id: string;
  route_id: string;
  direction: number;
  name: string;
  start_station: string;
  end_station: string;
  travel_time: number;
  line_id: string;
  color: string;
}

/**
 * 效能優化：預計算的軌道距離資料
 * 用於加速 interpolateOnLineString 和 calculateBearing
 */
export interface TrackDistanceCache {
  totalLength: number;           // 軌道總長度
  cumulativeDistances: number[]; // 累積距離陣列 [0, d1, d1+d2, ...]
}

export interface Track {
  type: 'Feature';
  properties: TrackProperties;
  geometry: TrackGeometry;
  distanceCache?: TrackDistanceCache; // 效能優化：預計算的距離快取
}

export interface TrackCollection {
  type: 'FeatureCollection';
  features: Track[];
}

export interface Station {
  station_id: string;
  name_zh: string;
  name_en: string;
  coordinates: [number, number];
}

export interface StationCollection {
  type: 'FeatureCollection';
  features: {
    type: 'Feature';
    properties: {
      station_id: string;
      name_zh: string;
      name_en: string;
    };
    geometry: {
      type: 'Point';
      coordinates: [number, number];
    };
  }[];
}
