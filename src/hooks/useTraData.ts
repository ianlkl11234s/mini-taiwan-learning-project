import { useState, useEffect } from 'react';
import type { TrackCollection, StationCollection, Track } from '../types/track';
import type { TrackSchedule } from '../types/schedule';

/**
 * 台鐵軌道 ID 列表 (用於顯示軌道)
 * 使用官方 SHP 資料 (國土測繪中心)
 */
const TRA_TRACK_IDS = [
  // 西部幹線
  'WL-N-0', 'WL-N-1',     // 縱貫線北段 (基隆-竹南)
  'WL-M-0', 'WL-M-1',     // 山線 (竹南-彰化)
  'WL-H-0', 'WL-H-1',     // 海線 (竹南-彰化)
  'WL-H2-0', 'WL-H2-1',   // 海岸線
  'WL-S1-0', 'WL-S1-1',   // 縱貫線南段 (彰化-高雄)
  'WL-S2-0', 'WL-S2-1',   // 縱貫線南段 (竹南-彰化)
  // 東部幹線
  'YL-0', 'YL-1',         // 宜蘭線 (八堵-蘇澳)
  'BH-0', 'BH-1',         // 北迴線 (蘇澳新-花蓮)
  'TD-0', 'TD-1',         // 臺東線 (花蓮-臺東)
  'NH-0', 'NH-1',         // 南迴線 (臺東-枋寮)
  // 屏東線
  'PT-0', 'PT-1',         // 屏東線 (高雄-枋寮)
  // 支線
  'SH-0', 'SH-1',         // 沙崙線
  'CZ-0', 'CZ-1',         // 成追線
  'NW-0', 'NW-1',         // 內灣線
  'LJ-0', 'LJ-1',         // 六家線
  'JJ-0', 'JJ-1',         // 集集線
  'PX-0', 'PX-1',         // 平溪線
  'SA-0', 'SA-1',         // 深澳線
];

/**
 * 有完整時刻表的軌道 ID (用於列車動畫)
 * 注意：所有支線 (NW, LJ, SH, PX, JJ, CZ) 都已移至 ODTrainEngine 處理
 * 此列表應為空，以避免重複渲染列車
 */
const TRA_SCHEDULE_IDS: string[] = [];

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

        // 載入軌道 (使用官方資料)
        const trackFeatures: Track[] = [];
        for (const trackId of TRA_TRACK_IDS) {
          const res = await fetch(`/data/tra/tracks_official/${trackId}.geojson`);
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

        // 載入車站 (使用對齊到軌道的版本)
        const stationsRes = await fetch('/data/tra/stations_snapped.geojson');
        if (!stationsRes.ok) throw new Error('Failed to load TRA stations');
        const stationsData = await stationsRes.json();
        setStations(stationsData);

        // 載入車站進度映射表
        const progressRes = await fetch('/data/tra/station_progress.json');
        if (!progressRes.ok) throw new Error('Failed to load TRA station progress');
        const progressData = await progressRes.json();
        setStationProgress(progressData);

        // 載入時刻表（只載入有完整時刻表的軌道）
        const scheduleMap = new Map<string, TrackSchedule>();
        for (const trackId of TRA_SCHEDULE_IDS) {
          const scheduleRes = await fetch(`/data/tra/schedules/${trackId}.json`);
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
