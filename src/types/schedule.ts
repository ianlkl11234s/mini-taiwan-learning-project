/**
 * 時刻表資料類型定義
 */

export interface StationTime {
  station_id: string;
  arrival: number; // 相對秒數
  departure: number; // 相對秒數
}

export interface Departure {
  departure_time: string; // "HH:MM:SS"
  train_id: string;
  stations: StationTime[];
  total_travel_time: number; // 秒
}

export interface TrackSchedule {
  track_id: string;
  route_id: string;
  name: string;
  origin: string;
  destination: string;
  stations: string[];
  travel_time_minutes: number;
  dwell_time_seconds: number;
  is_weekday: boolean;
  departure_count: number;
  departures: Departure[];
}

export interface Schedule {
  [trackId: string]: TrackSchedule;
}
