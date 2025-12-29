/**
 * 軌道資料類型定義
 */

export interface TrackGeometry {
  type: 'LineString';
  coordinates: [number, number][];
}

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

export interface Track {
  type: 'Feature';
  properties: TrackProperties;
  geometry: TrackGeometry;
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
