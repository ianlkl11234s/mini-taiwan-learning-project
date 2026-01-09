/**
 * useODTraData - 載入 O-D 專屬軌道資料
 *
 * 載入 NW/LJ 線的 O-D 軌道和時刻表資料
 */

import { useState, useEffect } from 'react';
import type { ODTrack, ODSchedule, ODStationProgressMap } from '../engines/ODTrainEngine';

// O-D 軌道 ID 列表
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

// 時刻表 ID 列表
const SCHEDULE_IDS = [
  'NW-0', 'NW-1',
  'LJ-0', 'LJ-1',
  'PX-0', 'PX-1',
  'JJ-0', 'JJ-1',
  'CZ-0', 'CZ-1',
  'SH-0', 'SH-1',
];

export interface ODTraDataState {
  odTracks: Map<string, ODTrack>;
  schedules: Map<string, ODSchedule>;
  stationProgress: ODStationProgressMap;
  loading: boolean;
  error: string | null;
}

export function useODTraData(): ODTraDataState {
  const [odTracks, setOdTracks] = useState<Map<string, ODTrack>>(new Map());
  const [schedules, setSchedules] = useState<Map<string, ODSchedule>>(new Map());
  const [stationProgress, setStationProgress] = useState<ODStationProgressMap>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);

        // 載入 O-D 軌道
        const tracksMap = new Map<string, ODTrack>();
        for (const trackId of OD_TRACK_IDS) {
          try {
            const res = await fetch(`/data/tra/tracks_od/${trackId}.geojson`);
            if (res.ok) {
              const data = await res.json();
              if (data.features?.[0]) {
                tracksMap.set(trackId, data.features[0]);
              }
            }
          } catch (e) {
            console.warn(`無法載入 O-D 軌道 ${trackId}:`, e);
          }
        }
        setOdTracks(tracksMap);
        console.log(`載入 ${tracksMap.size} 條 O-D 軌道`);

        // 載入車站進度
        try {
          const progressRes = await fetch('/data/tra/tracks_od/od_station_progress.json');
          if (progressRes.ok) {
            const progressData = await progressRes.json();
            setStationProgress(progressData);
            console.log('載入 O-D 車站進度');
          }
        } catch (e) {
          console.warn('無法載入 O-D 車站進度:', e);
        }

        // 載入時刻表
        const scheduleMap = new Map<string, ODSchedule>();
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

  return { odTracks, schedules, stationProgress, loading, error };
}
