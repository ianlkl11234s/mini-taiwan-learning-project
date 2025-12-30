import { useState, useEffect } from 'react';
import type { TrackCollection, StationCollection, Track } from '../types/track';
import type { TrackSchedule } from '../types/schedule';

// 軌道 ID 列表
const TRACK_IDS = [
  // === 紅線 (R) ===
  'R-1-0', 'R-1-1',  // 全程車
  'R-2-0', 'R-2-1',  // 南段區間車
  'R-3-0', 'R-3-1',  // 新北投支線
  'R-4-0', 'R-4-1',  // 北段區間車
  // 首班車專用軌道 (北上)
  'R-5-0',           // 首班車：大安→淡水
  'R-6-0',           // 首班車：雙連→淡水
  'R-7-0',           // 首班車：圓山→淡水
  'R-8-0',           // 首班車：芝山→淡水
  // 首班車專用軌道 (南下)
  'R-9-1',           // 首班車：紅樹林→象山
  'R-10-1',          // 首班車：大安→象山
  'R-11-1',          // 首班車：雙連→象山
  'R-12-1',          // 首班車：民權西路→象山
  'R-13-1',          // 首班車：圓山→象山
  'R-14-1',          // 首班車：石牌→象山
  'R-15-1',          // 首班車：唭哩岸→象山
  // === 藍線 (BL) ===
  'BL-1-0', 'BL-1-1',  // 全程車（頂埔↔南港展覽館）
  'BL-2-0', 'BL-2-1',  // 區間車（亞東醫院↔南港展覽館）
];

// 車站在軌道上的實際進度 (0-1)
export type StationProgressMap = Record<string, Record<string, number>>;

export interface DataState {
  tracks: TrackCollection | null;
  stations: StationCollection | null;
  schedules: Map<string, TrackSchedule>;
  trackMap: Map<string, Track>;
  stationProgress: StationProgressMap | null;
  loading: boolean;
  error: string | null;
}

export function useData(): DataState {
  const [tracks, setTracks] = useState<TrackCollection | null>(null);
  const [stations, setStations] = useState<StationCollection | null>(null);
  const [schedules, setSchedules] = useState<Map<string, TrackSchedule>>(new Map());
  const [trackMap, setTrackMap] = useState<Map<string, Track>>(new Map());
  const [stationProgress, setStationProgress] = useState<StationProgressMap | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);

        // 載入所有軌道
        const trackFeatures: Track[] = [];
        for (const trackId of TRACK_IDS) {
          const res = await fetch(`/data/tracks/${trackId}.geojson`);
          if (!res.ok) throw new Error(`Failed to load track ${trackId}`);
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

        // 載入車站（紅線 + 藍線）
        const redStationsRes = await fetch('/data/red_line_stations.geojson');
        if (!redStationsRes.ok) throw new Error('Failed to load red line stations');
        const redStationsData = await redStationsRes.json();

        const blueStationsRes = await fetch('/data/blue_line_stations.geojson');
        if (!blueStationsRes.ok) throw new Error('Failed to load blue line stations');
        const blueStationsData = await blueStationsRes.json();

        // 合併車站資料
        const allStations: StationCollection = {
          type: 'FeatureCollection',
          features: [
            ...redStationsData.features,
            ...blueStationsData.features,
          ],
        };
        setStations(allStations);

        // 載入時刻表
        const scheduleMap = new Map<string, TrackSchedule>();
        for (const trackId of TRACK_IDS) {
          const res = await fetch(`/data/schedules/${trackId}.json`);
          if (!res.ok) throw new Error(`Failed to load schedule ${trackId}`);
          const data = await res.json();
          scheduleMap.set(trackId, data);
        }
        setSchedules(scheduleMap);

        // 載入車站進度映射
        const progressRes = await fetch('/data/station_progress.json');
        if (!progressRes.ok) throw new Error('Failed to load station progress');
        const progressData = await progressRes.json();
        setStationProgress(progressData);

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
