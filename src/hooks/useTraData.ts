/**
 * useTraData - 台鐵資料載入 Hook
 *
 * 載入所有台鐵相關資料：
 * - 軌道顯示資料 (tracks_official)
 * - 車站資料 (stations_snapped)
 * - O-D 軌道 (tracks_od) - 用於列車位置計算
 * - 時刻表 (schedules_od)
 * - 車站進度 (od_station_progress)
 */

import { useState, useEffect } from 'react';
import type { TrackCollection, StationCollection, Track } from '../types/track';
import type { TraTrack, TraSchedule, TraStationProgressMap } from '../engines/TraTrainEngine';

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
 * O-D 軌道 ID 列表 (用於列車位置計算)
 */
const OD_TRACK_IDS = [
  'NW-HC-NB',  // 新竹→內灣
  'NW-NB-HC',  // 內灣→新竹
  'NW-JJ-NB',  // 竹中→內灣
  'NW-NB-JJ',  // 內灣→竹中
  'NW-HC-JD',  // 新竹→竹東
  'LJ-HC-LJ',  // 新竹→六家
  'LJ-LJ-HC',  // 六家→新竹
  'PX-SD-JT',  // 三貂嶺→菁桐
  'PX-JT-SD',  // 菁桐→三貂嶺
  'JJ-ES-CT',  // 二水→車埕
  'JJ-CT-ES',  // 車埕→二水
  'CZ-CG-ZF',  // 成功→追分
  'CZ-ZF-CG',  // 追分→成功
  'SH-TN-SL',  // 臺南→沙崙
  'SH-SL-TN',  // 沙崙→臺南
];

/**
 * 時刻表 ID 列表
 */
const SCHEDULE_IDS = [
  'NW-0', 'NW-1',
  'LJ-0', 'LJ-1',
  'PX-0', 'PX-1',
  'JJ-0', 'JJ-1',
  'CZ-0', 'CZ-1',
  'SH-0', 'SH-1',
];

/**
 * 台鐵資料狀態
 */
export interface TraDataState {
  // 顯示用資料
  tracks: TrackCollection | null;
  stations: StationCollection | null;
  trackMap: Map<string, Track>;
  // 列車引擎用資料
  odTracks: Map<string, TraTrack>;
  schedules: Map<string, TraSchedule>;
  stationProgress: TraStationProgressMap;
  // 狀態
  loading: boolean;
  error: string | null;
}

export function useTraData(): TraDataState {
  // 顯示用資料
  const [tracks, setTracks] = useState<TrackCollection | null>(null);
  const [stations, setStations] = useState<StationCollection | null>(null);
  const [trackMap, setTrackMap] = useState<Map<string, Track>>(new Map());
  // 列車引擎用資料
  const [odTracks, setOdTracks] = useState<Map<string, TraTrack>>(new Map());
  const [schedules, setSchedules] = useState<Map<string, TraSchedule>>(new Map());
  const [stationProgress, setStationProgress] = useState<TraStationProgressMap>({});
  // 狀態
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);

        // === 載入顯示用軌道 (官方資料) ===
        const trackFeatures: Track[] = [];
        for (const trackId of TRA_TRACK_IDS) {
          try {
            const res = await fetch(`/data/tra/tracks_official/${trackId}.geojson`);
            if (res.ok) {
              const data = await res.json();
              if (data.features?.[0]) {
                trackFeatures.push(data.features[0]);
              }
            }
          } catch (e) {
            console.warn(`無法載入軌道 ${trackId}:`, e);
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
        console.log(`載入 ${trackFeatures.length} 條顯示軌道`);

        // === 載入車站 ===
        try {
          const stationsRes = await fetch('/data/tra/stations_snapped.geojson');
          if (stationsRes.ok) {
            const stationsData = await stationsRes.json();
            setStations(stationsData);
            console.log('載入車站資料');
          }
        } catch (e) {
          console.warn('無法載入車站資料:', e);
        }

        // === 載入 O-D 軌道 (用於列車位置計算) ===
        const odTracksMap = new Map<string, TraTrack>();
        for (const trackId of OD_TRACK_IDS) {
          try {
            const res = await fetch(`/data/tra/tracks_od/${trackId}.geojson`);
            if (res.ok) {
              const data = await res.json();
              if (data.features?.[0]) {
                odTracksMap.set(trackId, data.features[0]);
              }
            }
          } catch (e) {
            console.warn(`無法載入 O-D 軌道 ${trackId}:`, e);
          }
        }
        setOdTracks(odTracksMap);
        console.log(`載入 ${odTracksMap.size} 條 O-D 軌道`);

        // === 載入車站進度 ===
        try {
          const progressRes = await fetch('/data/tra/tracks_od/od_station_progress.json');
          if (progressRes.ok) {
            const progressData = await progressRes.json();
            setStationProgress(progressData);
            console.log('載入車站進度');
          }
        } catch (e) {
          console.warn('無法載入車站進度:', e);
        }

        // === 載入時刻表 ===
        const scheduleMap = new Map<string, TraSchedule>();
        for (const scheduleId of SCHEDULE_IDS) {
          try {
            const res = await fetch(`/data/tra/schedules_od/${scheduleId}.json`);
            if (res.ok) {
              const data = await res.json();
              scheduleMap.set(scheduleId, data);
            }
          } catch (e) {
            console.warn(`無法載入時刻表 ${scheduleId}:`, e);
          }
        }
        setSchedules(scheduleMap);
        console.log(`載入 ${scheduleMap.size} 個時刻表`);

        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setLoading(false);
      }
    }

    loadData();
  }, []);

  return {
    tracks,
    stations,
    trackMap,
    odTracks,
    schedules,
    stationProgress,
    loading,
    error,
  };
}
