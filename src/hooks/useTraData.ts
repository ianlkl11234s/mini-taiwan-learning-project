import { useState, useEffect } from 'react';
import type { TrackCollection, StationCollection, Track } from '../types/track';
import type { TrackSchedule } from '../types/schedule';

/**
 * 台鐵軌道 ID 列表 (用於顯示軌道)
 * SH: 沙崙線
 * CZ: 成追線
 * WL-TN-KH: 西部幹線 臺南-高雄段
 */
const TRA_TRACK_IDS = [
  'SH-0', 'SH-1',             // 沙崙線
  'CZ-0', 'CZ-1',             // 成追線
  'WL-TN-KH-0', 'WL-TN-KH-1', // 西部幹線 臺南-高雄段
  'WL-TN-ES-0', 'WL-TN-ES-1', // 西部幹線 臺南-二水段 (含嘉義、雲林)
  'PT-0', 'PT-1',             // 屏東線 (左營-屏東)
];
// 完整 WL 軌道太長，改用分段：'WL-0', 'WL-1'

/**
 * 有完整時刻表的軌道 ID (用於列車動畫)
 * 只有這些軌道會有列車運行
 */
const TRA_SCHEDULE_IDS = ['SH-0', 'SH-1'];

/**
 * 車站進度映射表類型
 * 外層 key: track_id (SH-0, SH-1)
 * 內層 key: station_id
 * value: 0-1 之間的進度值
 */
export type TraStationProgressMap = Record<string, Record<string, number>>;

/**
 * 台鐵資料狀態
 */
export interface TraDataState {
  tracks: TrackCollection | null;
  stations: StationCollection | null;
  schedules: Map<string, TrackSchedule>;
  trackMap: Map<string, Track>;
  stationProgress: TraStationProgressMap;
  loading: boolean;
  error: string | null;
}

/**
 * 台鐵資料 Hook
 *
 * 獨立載入台鐵相關資料：
 * - 軌道 GeoJSON
 * - 車站 GeoJSON
 * - 時刻表
 * - 車站進度映射
 */
export function useTraData(): TraDataState {
  const [tracks, setTracks] = useState<TrackCollection | null>(null);
  const [stations, setStations] = useState<StationCollection | null>(null);
  const [schedules, setSchedules] = useState<Map<string, TrackSchedule>>(new Map());
  const [trackMap, setTrackMap] = useState<Map<string, Track>>(new Map());
  const [stationProgress, setStationProgress] = useState<TraStationProgressMap>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);

        // 載入軌道
        const trackFeatures: Track[] = [];
        for (const trackId of TRA_TRACK_IDS) {
          const res = await fetch(`/data-tra/tracks/${trackId}.geojson`);
          if (!res.ok) throw new Error(`Failed to load TRA track ${trackId}`);
          const data = await res.json();
          if (data.features?.[0]) {
            trackFeatures.push(data.features[0]);
          }
        }

        const trackCollection: TrackCollection = {
          type: 'FeatureCollection',
          features: trackFeatures,
        };
        setTracks(trackCollection);

        // 建立軌道索引
        const tMap = new Map<string, Track>();
        for (const track of trackFeatures) {
          tMap.set(track.properties.track_id, track);
        }
        setTrackMap(tMap);

        // 載入車站
        const stationsRes = await fetch('/data-tra/stations.geojson');
        if (!stationsRes.ok) throw new Error('Failed to load TRA stations');
        const stationsData = await stationsRes.json();
        setStations(stationsData);

        // 載入車站進度映射表
        const progressRes = await fetch('/data-tra/station_progress.json');
        if (!progressRes.ok) throw new Error('Failed to load TRA station progress');
        const progressData = await progressRes.json();
        setStationProgress(progressData);

        // 載入時刻表（只載入有完整時刻表的軌道）
        const scheduleMap = new Map<string, TrackSchedule>();
        for (const trackId of TRA_SCHEDULE_IDS) {
          const scheduleRes = await fetch(`/data-tra/schedules/${trackId}.json`);
          if (!scheduleRes.ok) throw new Error(`Failed to load TRA schedule ${trackId}`);
          const scheduleData = await scheduleRes.json();
          scheduleMap.set(trackId, scheduleData);
        }
        setSchedules(scheduleMap);

        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setLoading(false);
      }
    }

    loadData();
  }, []);

  return { tracks, stations, schedules, trackMap, stationProgress, loading, error };
}
