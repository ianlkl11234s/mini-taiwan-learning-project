/**
 * useTraData - 台鐵資料載入 Hook
 *
 * 載入所有台鐵相關資料：
 * - 軌道顯示資料 (優先使用 tracks_golden，fallback 到 tracks_official)
 * - 車站資料 (stations_snapped)
 * - O-D 軌道 (tracks_od) - 用於列車位置計算
 * - 真實時刻表 (schedules_real/master_schedule.json)
 * - 車站進度 (od_station_progress)
 *
 * 支援每日時刻表切換（selectedDate 參數）
 */

import { useState, useEffect } from 'react';
import type { TrackCollection, StationCollection, Track } from '../types/track';
import type { TraTrack, TraSchedule, TraDeparture, TraStationProgressMap } from '../engines/TraTrainEngine';

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

  // === Step 13: 臺東↔新左營 ===
  'SK-0', 'SK-1',         // 南迴線 (臺東-新左營)

  // === Step 15: 屏東線 ===
  'PT-0', 'PT-1',         // 屏東線 (新左營-枋寮)

  // === Step 19: 西部幹線南段 ===
  'WL-S-CH-ZY-0', 'WL-S-CH-ZY-1',  // 縱貫線南段 (彰化-新左營)

  // === Step 18: 西部幹線海線 ===
  'WL-C-CH-ZN-0', 'WL-C-ZN-CH-1',  // 海線 (彰化-竹南)

  // === Step 20: 西部幹線山線 ===
  'WL-M-ZN-CH-0', 'WL-M-CH-ZN-1',  // 山線 (竹南-彰化)

  // === Step 21: 西部幹線北段 (竹南-樹林) ===
  'WL-N-ZN-SL-0', 'WL-N-ZN-SL-1',  // 北段 (竹南-樹林)

  // === 支線 ===
  'NW-0', 'NW-1',         // 內灣線 (新竹-內灣)
  'LJ-0', 'LJ-1',         // 六家線 (新竹-六家)
  'SH-0', 'SH-1',         // 沙崙線 (臺南-沙崙)
  'JJ-0', 'JJ-1',         // 集集線 (二水-車埕)
  'CZ-0', 'CZ-1',         // 成追線 (成功-追分)
  'PX-0', 'PX-1',         // 平溪線 (三貂嶺-菁桐)

  // === Step 22: 深澳線 ===
  'SA-RF-BD-0', 'SA-BD-RF-1',  // 深澳線 (瑞芳-八斗子)

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
 * O-D 軌道 ID 列表 (僅供參考，實際從 bundle 載入)
 *
 * 注意：目前改用 tracks_od_bundle.json 一次載入所有軌道，
 * 此列表僅保留作為文件參考用途。
 */
const _OD_TRACK_IDS_REFERENCE = [
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

  // === Step 13: 臺東↔新左營 ===
  'SK-TT-ZY-0',  // 臺東→新左營 (NH+PT+WL-S1 合併)
  'SK-ZY-TT-1',  // 新左營→臺東

  // === Step 14: 環島軌道 (樹林↔新左營，經東部) ===
  'YL-SL-ZY-0',  // 樹林→新左營 (YL+BH+TL+SK 合併)
  'YL-ZY-SL-1',  // 新左營→樹林

  // === Step 15: 屏東線 (新左營↔枋寮，經高雄) ===
  'PT-ZY-PL-0',  // 新左營→枋寮
  'PT-PL-ZY-1',  // 枋寮→新左營

  // === Step 19: 西部幹線南段 (彰化↔新左營) ===
  'WL-CH-ZY-0',  // 彰化→新左營
  'WL-ZY-CH-1',  // 新左營→彰化

  // === Step 18: 西部幹線海線 ===
  'WL-C-CH-ZN-0',  // 彰化→竹南
  'WL-C-ZN-CH-1',  // 竹南→彰化

  // === Step 20: 西部幹線山線 (竹南↔彰化) ===
  'WL-M-ZN-CH-0',  // 竹南→彰化
  'WL-M-CH-ZN-1',  // 彰化→竹南

  // === Step 21: 西部幹線北段 (竹南↔樹林) ===
  'WL-ZN-SL-0',    // 竹南→樹林
  'WL-SL-ZN-1',    // 樹林→竹南

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
  // 深澳線
  'SA-RF-BD-0',  // 瑞芳→八斗子
  'SA-BD-RF-1',  // 八斗子→瑞芳
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
void _OD_TRACK_IDS_REFERENCE; // 抑制未使用變數警告

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
  scheduleLoading: boolean;
  error: string | null;
  // 每日時刻表
  scheduleDate: string | null;
  scheduleTrainCount: number;
  availableDates: string[];
}

/**
 * 將 master_schedule 格式的 JSON 轉為 schedules Map
 */
function parseTraSchedule(data: { schedules?: TraDeparture[] }): {
  scheduleMap: Map<string, TraSchedule>;
  trainCount: number;
} {
  const scheduleMap = new Map<string, TraSchedule>();
  const schedulesList: TraDeparture[] = data.schedules || [];

  const byOd = new Map<string, TraDeparture[]>();
  for (const s of schedulesList) {
    const trackId = s.od_track_id;
    if (!byOd.has(trackId)) byOd.set(trackId, []);
    byOd.get(trackId)!.push(s);
  }

  for (const [trackId, departures] of byOd) {
    scheduleMap.set(trackId, {
      track_id: trackId,
      departures,
    });
  }

  return { scheduleMap, trainCount: schedulesList.length };
}

export function useTraData(selectedDate?: string): TraDataState {
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
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 每日時刻表
  const [scheduleDate, setScheduleDate] = useState<string | null>(null);
  const [scheduleTrainCount, setScheduleTrainCount] = useState(0);
  const [availableDates, setAvailableDates] = useState<string[]>([]);

  // 初始載入：軌道、車站、車站進度、預設時刻表、可用日期清單
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

        // === 載入真實時刻表（預設 master_schedule） ===
        try {
          const masterRes = await fetch('/data/tra/schedules_real/master_schedule.json');
          if (masterRes.ok) {
            const masterData = await masterRes.json();
            const { scheduleMap, trainCount } = parseTraSchedule(masterData);
            setSchedules(scheduleMap);
            setScheduleTrainCount(trainCount);
            setScheduleDate(null);
            console.log(`載入真實時刻表: ${trainCount} 班, ${scheduleMap.size} 條軌道`);
          }
        } catch (e) {
          console.warn('無法載入真實時刻表:', e);
        }

        // === 載入 O-D 軌道 (用於列車位置計算) ===
        // 使用 bundle 檔案一次載入所有軌道（優化：263 個請求 → 1 個請求）
        const odTracksMap = new Map<string, TraTrack>();
        try {
          const bundleRes = await fetch('/data/tra/tracks_od/tracks_od_bundle.json');
          if (bundleRes.ok) {
            const bundleData: Record<string, GeoJSON.LineString> = await bundleRes.json();
            for (const [trackId, geometry] of Object.entries(bundleData)) {
              // 建立符合 TraTrack 格式的物件
              odTracksMap.set(trackId, {
                type: 'Feature',
                properties: { track_id: trackId },
                geometry,
              } as TraTrack);
            }
          }
        } catch (e) {
          console.warn('無法載入 O-D 軌道 bundle:', e);
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

        // === 載入可用日期清單 ===
        try {
          const indexRes = await fetch('/data/tra/schedules_real/daily/index.json');
          if (indexRes.ok) {
            const indexData = await indexRes.json();
            setAvailableDates(indexData.dates || []);
          }
        } catch {
          // index.json 不存在沒關係
        }

        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setLoading(false);
      }
    }

    loadData();
  }, []);

  // 日期切換：只重載時刻表
  useEffect(() => {
    // 初始載入時跳過（由上方 useEffect 處理）
    if (loading) return;

    async function loadDailySchedule() {
      if (!selectedDate) {
        // 切回固定時刻表
        setScheduleLoading(true);
        try {
          const masterRes = await fetch('/data/tra/schedules_real/master_schedule.json');
          if (masterRes.ok) {
            const masterData = await masterRes.json();
            const { scheduleMap, trainCount } = parseTraSchedule(masterData);
            setSchedules(scheduleMap);
            setScheduleTrainCount(trainCount);
            setScheduleDate(null);
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
        setScheduleLoading(false);
        return;
      }

      // 載入指定日期時刻表
      setScheduleLoading(true);
      try {
        const dailyRes = await fetch(`/data/tra/schedules_real/daily/${selectedDate}.json`);
        if (!dailyRes.ok) throw new Error('not found');
        const dailyData = await dailyRes.json();
        const { scheduleMap, trainCount } = parseTraSchedule(dailyData);
        setSchedules(scheduleMap);
        setScheduleTrainCount(trainCount);
        setScheduleDate(selectedDate);
        setError(null);
      } catch {
        // 該日期時刻表不存在，fallback 到固定時刻表
        console.warn(`TRA daily schedule for ${selectedDate} not found, using default`);
        try {
          const masterRes = await fetch('/data/tra/schedules_real/master_schedule.json');
          if (masterRes.ok) {
            const masterData = await masterRes.json();
            const { scheduleMap, trainCount } = parseTraSchedule(masterData);
            setSchedules(scheduleMap);
            setScheduleTrainCount(trainCount);
            setScheduleDate(null);
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
      }
      setScheduleLoading(false);
    }

    loadDailySchedule();
  }, [selectedDate, loading]);

  return {
    tracks,
    stations,
    trackMap,
    odTracks,
    schedules,
    stationProgress,
    loading,
    scheduleLoading,
    error,
    scheduleDate,
    scheduleTrainCount,
    availableDates,
  };
}
