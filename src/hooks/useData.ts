import { useState, useEffect } from 'react';
import type { TrackCollection, StationCollection, Track } from '../types/track';
import type { TrackSchedule } from '../types/schedule';

// 軌道 ID 列表
const TRACK_IDS = ['R-1-0', 'R-1-1', 'R-2-0', 'R-2-1', 'R-3-0', 'R-3-1'];

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

        // 載入車站
        const stationsRes = await fetch('/data/red_line_stations.geojson');
        if (!stationsRes.ok) throw new Error('Failed to load stations');
        const stationsData = await stationsRes.json();
        setStations(stationsData);

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
