/**
 * useTraData - 台鐵資料載入 Hook
 *
 * 載入所有台鐵相關資料：
 * - 軌道顯示資料 (優先使用 tracks_golden，fallback 到 tracks_official)
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
 *
 * === 漸進式實作中 ===
 * Step 1: WL-N-SL-BD (樹林→八堵) - 驗證中
 * Step 2: YL (八堵→蘇澳) - 待處理
 * Step 3: KL (八堵→基隆) - 待處理
 */
const TRA_TRACK_IDS = [
  // === Step 1: 樹林→八堵 ✅ ===
  'WL-N-SL-BD-0', 'WL-N-SL-BD-1',

  // === Step 2: 八堵→蘇澳 ✅ ===
  'YL-BD-SA-0', 'YL-SA-BD-1',

  // === Step 3: 八堵↔基隆 ✅ ===
  'KL-BD-KL-0', 'KL-KL-BD-1',

  // === Step 4: 蘇澳新↔花蓮 (驗證中) ===
  'BH-SX-HL-0', 'BH-HL-SX-1',

  // === Step 6: 花蓮↔臺東 ===
  'TL-0', 'TL-1',

  // === 支線 ===
  'NW-0', 'NW-1',         // 內灣線 (新竹-內灣)
  'LJ-0', 'LJ-1',         // 六家線 (新竹-六家)
  'SH-0', 'SH-1',         // 沙崙線 (臺南-沙崙)
  'JJ-0', 'JJ-1',         // 集集線 (二水-車埕)
  'CZ-0', 'CZ-1',         // 成追線 (成功-追分)
  'PX-0', 'PX-1',         // 平溪線 (三貂嶺-菁桐)

  // === 以下暫時註解，待各 Step 驗證完成後逐步開啟 ===
  // // 西部幹線
  // 'WL-N-0', 'WL-N-1',     // 縱貫線北段 (基隆-竹南)
  // 'WL-M-0', 'WL-M-1',     // 山線 (竹南-彰化)
  // 'WL-H-0', 'WL-H-1',     // 海線 (竹南-彰化)
  // 'WL-H2-0', 'WL-H2-1',   // 海岸線
  // 'WL-S1-0', 'WL-S1-1',   // 縱貫線南段 (彰化-高雄)
  // 'WL-S2-0', 'WL-S2-1',   // 縱貫線南段 (竹南-彰化)
  // // 東部幹線
  // 'YL-0', 'YL-1',         // 宜蘭線 (八堵-蘇澳)
  // 'BH-0', 'BH-1',         // 北迴線 (蘇澳新-花蓮)
  // 'TD-0', 'TD-1',         // 臺東線 (花蓮-臺東)
  // 'NH-0', 'NH-1',         // 南迴線 (臺東-枋寮)
  // // 屏東線
  // 'PT-0', 'PT-1',         // 屏東線 (高雄-枋寮)
  // // 支線
  // 'SH-0', 'SH-1',         // 沙崙線
  // 'CZ-0', 'CZ-1',         // 成追線
  // 'NW-0', 'NW-1',         // 內灣線
  // 'LJ-0', 'LJ-1',         // 六家線
  // 'JJ-0', 'JJ-1',         // 集集線
  // 'PX-0', 'PX-1',         // 平溪線
  // 'SA-0', 'SA-1',         // 深澳線
];

/**
 * O-D 軌道 ID 列表 (用於列車位置計算)
 *
 * === 漸進式實作中 ===
 * 待 WL-N-SL-BD + YL + KL 完成後，會建立以下 O-D 軌道：
 * - YL-SL-SA (樹林↔蘇澳)
 * - YL-SL-HL (樹林↔花蓮)
 * - KL-SL-KL (樹林↔基隆)
 */
const OD_TRACK_IDS = [
  // === Step 1: 樹林↔八堵 ✅ ===
  'WL-SL-BD-0',  // 樹林→八堵
  'WL-BD-SL-1',  // 八堵→樹林

  // === Step 2: 八堵↔蘇澳 ✅ ===
  'YL-BD-SA-0',  // 八堵→蘇澳
  'YL-SA-BD-1',  // 蘇澳→八堵

  // === 合併: 樹林↔蘇澳 ✅ ===
  'YL-SL-SA-0',  // 樹林→蘇澳 (WL-N + YL)
  'YL-SA-SL-1',  // 蘇澳→樹林 (YL + WL-N)

  // === Step 3: 八堵↔基隆 ✅ ===
  'KL-BD-KL-0',  // 八堵→基隆
  'KL-KL-BD-1',  // 基隆→八堵

  // === Step 4: 蘇澳新↔花蓮 ✅ ===
  'BH-SX-HL-0',  // 蘇澳新→花蓮
  'BH-HL-SX-1',  // 花蓮→蘇澳新

  // === Step 5: 樹林↔花蓮 (合併軌道) ===
  'YL-SL-HL-0',  // 樹林→花蓮 (WL+YL+BH 合併)
  'YL-HL-SL-1',  // 花蓮→樹林

  // === Step 6: 花蓮↔臺東 ===
  'TL-HL-TT',    // 花蓮→臺東
  'TL-TT-HL',    // 臺東→花蓮

  // === Step 7: 樹林↔臺東 (合併軌道) ===
  'YL-SL-TT-0',  // 樹林→臺東 (WL+YL+BH+TL 合併)
  'YL-TT-SL-1',  // 臺東→樹林

  // === 支線 O-D 軌道 ===
  // 內灣線
  'NW-HC-NB',  // 新竹→內灣
  'NW-NB-HC',  // 內灣→新竹
  'NW-JJ-NB',  // 竹中→內灣
  'NW-NB-JJ',  // 內灣→竹中
  // 六家線
  'LJ-HC-LJ',  // 新竹→六家
  'LJ-LJ-HC',  // 六家→新竹
  // 沙崙線
  'SH-TN-SL',  // 臺南→沙崙
  'SH-SL-TN',  // 沙崙→臺南
  // 集集線
  'JJ-ES-CT',  // 二水→車埕
  'JJ-CT-ES',  // 車埕→二水
  // 成追線
  'CZ-CG-ZF',  // 成功→追分
  'CZ-ZF-CG',  // 追分→成功
  // 平溪線
  'PX-SD-JT',  // 三貂嶺→菁桐
  'PX-JT-SD',  // 菁桐→三貂嶺
  // // 宜蘭線 + 北迴線 O-D 軌道
  // 'YL-TP-HL',  // 臺北→花蓮 (跨 WL-N + YL + BH)
  // 'YL-HL-TP',  // 花蓮→臺北
  // 'YL-TP-YL',  // 臺北→宜蘭
  // 'YL-YL-TP',  // 宜蘭→臺北
  // 'YL-TP-SA',  // 臺北→蘇澳
  // 'YL-SA-TP',  // 蘇澳→臺北
  // 'BH-SX-HL',  // 蘇澳新→花蓮
  // 'BH-HL-SX',  // 花蓮→蘇澳新
  // // 基隆支線 O-D 軌道
  // 'KL-TP-KL',  // 臺北→基隆
  // 'KL-KL-TP',  // 基隆→臺北
  // // 樹林起迄 O-D 軌道
  // 'YL-SL-YL',  // 樹林→宜蘭
  // 'YL-YL-SL',  // 宜蘭→樹林
  // 'KL-SL-KL',  // 樹林→基隆
  // 'KL-KL-SL',  // 基隆→樹林
];

/**
 * 時刻表 ID 列表
 */
const SCHEDULE_IDS = [
  // === Step 1: 樹林↔八堵 ✅ ===
  'WL-SL-BD-0',  // 樹林→八堵 測試時刻表
  'WL-BD-SL-1',  // 八堵→樹林 測試時刻表

  // === Step 2: 八堵↔蘇澳 ✅ ===
  'YL-BD-SA-0',  // 八堵→蘇澳 測試時刻表
  'YL-SA-BD-1',  // 蘇澳→八堵 測試時刻表

  // === 合併: 樹林↔蘇澳 ✅ ===
  'YL-SL-SA-0',  // 樹林→蘇澳 測試時刻表
  'YL-SA-SL-1',  // 蘇澳→樹林 測試時刻表

  // === Step 3: 八堵↔基隆 ✅ ===
  'KL-BD-KL-0',  // 八堵→基隆 測試時刻表
  'KL-KL-BD-1',  // 基隆→八堵 測試時刻表

  // === Step 4: 蘇澳新↔花蓮 ✅ ===
  'BH-SX-HL-0',  // 蘇澳新→花蓮 測試時刻表
  'BH-HL-SX-1',  // 花蓮→蘇澳新 測試時刻表

  // === Step 5: 樹林↔花蓮 (合併軌道) ===
  'YL-SL-HL-0',  // 樹林→花蓮 測試時刻表
  'YL-HL-SL-1',  // 花蓮→樹林 測試時刻表

  // === Step 6: 花蓮↔臺東 ===
  'TL-0',        // 花蓮→臺東 測試時刻表
  'TL-1',        // 臺東→花蓮 測試時刻表

  // === 以下暫時註解 ===
  // 'NW-0', 'NW-1',
  // 'LJ-0', 'LJ-1',
  // 'PX-0', 'PX-1',
  // 'JJ-0', 'JJ-1',
  // 'CZ-0', 'CZ-1',
  // 'SH-0', 'SH-1',
  // 'YL-0', 'YL-1',  // 宜蘭線
  // 'BH-0', 'BH-1',  // 北迴線
  // 'KL-0', 'KL-1',  // 基隆支線
  // 'YL-TEST',       // 測試時刻表 (板橋→宜蘭)
  // 'KL-TEST',       // 測試時刻表 (板橋→基隆)
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

        // === 載入顯示用軌道 (優先使用 Golden Track) ===
        const trackFeatures: Track[] = [];
        for (const trackId of TRA_TRACK_IDS) {
          try {
            // 優先嘗試 tracks_golden，fallback 到 tracks_official
            let res = await fetch(`/data/tra/tracks_golden/${trackId}.geojson`);
            if (!res.ok) {
              res = await fetch(`/data/tra/tracks_official/${trackId}.geojson`);
            }
            if (res.ok) {
              const data = await res.json();
              // 支援 Feature 和 FeatureCollection 兩種格式
              if (data.type === 'Feature') {
                trackFeatures.push(data);
              } else if (data.features?.[0]) {
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
