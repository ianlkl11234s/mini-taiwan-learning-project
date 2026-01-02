import { useState, useEffect } from 'react';
import type { TrackCollection, StationCollection, Track } from '../types/track';
import type { TrackSchedule } from '../types/schedule';

/**
 * 高鐵軌道 ID 列表
 */
const THSR_TRACK_IDS = ['THSR-1-0', 'THSR-1-1'];

/**
 * 高鐵資料狀態
 */
export interface ThsrDataState {
  tracks: TrackCollection | null;
  stations: StationCollection | null;
  schedules: Map<string, TrackSchedule>;
  trackMap: Map<string, Track>;
  stationProgress: Map<string, number>; // 車站在軌道上的進度 (0-1)
  loading: boolean;
  error: string | null;
}

/**
 * 高鐵資料 Hook
 *
 * 獨立載入高鐵相關資料：
 * - 軌道 GeoJSON
 * - 車站 GeoJSON
 * - 時刻表
 */
export function useThsrData(): ThsrDataState {
  const [tracks, setTracks] = useState<TrackCollection | null>(null);
  const [stations, setStations] = useState<StationCollection | null>(null);
  const [schedules, setSchedules] = useState<Map<string, TrackSchedule>>(new Map());
  const [trackMap, setTrackMap] = useState<Map<string, Track>>(new Map());
  const [stationProgress, setStationProgress] = useState<Map<string, number>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);

        // 載入軌道
        const trackFeatures: Track[] = [];
        for (const trackId of THSR_TRACK_IDS) {
          const res = await fetch(`/data-thsr/tracks/${trackId}.geojson`);
          if (!res.ok) throw new Error(`Failed to load THSR track ${trackId}`);
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
        const stationsRes = await fetch('/data-thsr/stations/thsr_stations.geojson');
        if (!stationsRes.ok) throw new Error('Failed to load THSR stations');
        const stationsData = await stationsRes.json();
        setStations(stationsData);

        // 計算車站在軌道上的進度（基於累積距離）
        const progressMap = new Map<string, number>();
        const stationFeatures = stationsData.features || [];
        if (stationFeatures.length > 0) {
          // 找出最大累積距離（終點站）
          const maxDistance = Math.max(
            ...stationFeatures.map((f: { properties: { cumulative_distance?: number } }) =>
              f.properties.cumulative_distance || 0
            )
          );
          // 計算每站的進度 (0-1)
          for (const feature of stationFeatures) {
            const stationId = feature.properties.station_id;
            const distance = feature.properties.cumulative_distance || 0;
            const progress = maxDistance > 0 ? distance / maxDistance : 0;
            progressMap.set(stationId, progress);
          }
        }
        setStationProgress(progressMap);

        // 載入時刻表（單一合併檔案）
        const scheduleMap = new Map<string, TrackSchedule>();
        const schedulesRes = await fetch('/data-thsr/schedules/thsr_schedules.json');
        if (!schedulesRes.ok) throw new Error('Failed to load THSR schedules');
        const schedulesData = await schedulesRes.json();

        // 將 JSON 物件轉為 Map
        for (const trackId of THSR_TRACK_IDS) {
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
