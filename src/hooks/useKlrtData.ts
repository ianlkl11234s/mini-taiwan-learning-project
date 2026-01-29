import { useState, useEffect } from 'react';
import type { TrackCollection, StationCollection, Track } from '../types/track';
import type { TrackSchedule } from '../types/schedule';

/**
 * 高雄輕軌軌道 ID 列表
 */
const KLRT_TRACK_IDS = [
  'KLRT-C-0',  // 環狀線 順時針
  'KLRT-C-1',  // 環狀線 逆時針
];

/**
 * 車站進度映射表類型
 * 外層 key: track_id (KLRT-C-0, KLRT-C-1)
 * 內層 key: station_id
 * value: 0-1 之間的進度值
 */
export type KlrtStationProgressMap = Record<string, Record<string, number>>;

/**
 * 高雄輕軌資料狀態
 */
export interface KlrtDataState {
  tracks: TrackCollection | null;
  stations: StationCollection | null;
  schedules: Map<string, TrackSchedule>;
  trackMap: Map<string, Track>;
  stationProgress: KlrtStationProgressMap;
  loading: boolean;
  error: string | null;
}

/**
 * 高雄輕軌資料 Hook
 *
 * 獨立載入高雄輕軌相關資料：
 * - 軌道 GeoJSON
 * - 車站 GeoJSON
 * - 時刻表
 * - 車站進度映射
 */
export function useKlrtData(): KlrtDataState {
  const [tracks, setTracks] = useState<TrackCollection | null>(null);
  const [stations, setStations] = useState<StationCollection | null>(null);
  const [schedules, setSchedules] = useState<Map<string, TrackSchedule>>(new Map());
  const [trackMap, setTrackMap] = useState<Map<string, Track>>(new Map());
  const [stationProgress, setStationProgress] = useState<KlrtStationProgressMap>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);

        // 快取破壞參數
        const cacheBuster = `?v=${Date.now()}`;

        // 載入軌道
        const trackFeatures: Track[] = [];
        for (const trackId of KLRT_TRACK_IDS) {
          const res = await fetch(`/data/klrt/tracks/${trackId}.geojson${cacheBuster}`);
          if (!res.ok) throw new Error(`Failed to load KLRT track ${trackId}`);
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
        const stationsRes = await fetch(`/data/klrt/stations/klrt_stations.geojson${cacheBuster}`);
        if (!stationsRes.ok) throw new Error('Failed to load KLRT stations');
        const stationsData = await stationsRes.json();
        setStations(stationsData);

        // 載入車站進度映射表
        const progressRes = await fetch(`/data/klrt/station_progress.json${cacheBuster}`);
        if (!progressRes.ok) throw new Error('Failed to load KLRT station progress');
        const progressData = await progressRes.json();
        setStationProgress(progressData);

        // 載入時刻表（單一合併檔案）
        const scheduleMap = new Map<string, TrackSchedule>();
        const schedulesRes = await fetch(`/data/klrt/schedules/klrt_schedules.json${cacheBuster}`);
        if (!schedulesRes.ok) throw new Error('Failed to load KLRT schedules');
        const schedulesData = await schedulesRes.json();

        // 將 JSON 物件轉為 Map
        for (const trackId of KLRT_TRACK_IDS) {
          if (schedulesData[trackId]) {
            scheduleMap.set(trackId, schedulesData[trackId]);
          }
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
