import { useState, useEffect } from 'react';
import type { TrackCollection, StationCollection, Track } from '../types/track';
import type { TrackSchedule } from '../types/schedule';

/**
 * Supabase 直連 — 從 reference.daily_schedules 取時刻表
 * S3 Base URL (備援) — fallback 到 S3 靜態檔案
 */
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
const DAILY_SCHEDULE_BASE_URL = import.meta.env.VITE_DAILY_SCHEDULE_BASE_URL || '';

/**
 * 從 Supabase 查詢 daily_schedules
 */
async function fetchSupabaseSchedule(system: string, date: string): Promise<unknown | null> {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) return null;
  // 優先查 _daily，失敗則查 _fixed
  for (const suffix of ['_daily', '_fixed']) {
    const params = new URLSearchParams({
      system: `eq.${system}${suffix}`,
      select: 'data',
      ...(suffix === '_daily' ? { schedule_date: `eq.${date}` } : {}),
    });
    const res = await fetch(`${SUPABASE_URL}/rest/v1/daily_schedules?${params}`, {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        'Accept-Profile': 'reference',
      },
    });
    if (res.ok) {
      const rows = await res.json();
      if (rows.length > 0) return rows[0].data;
    }
  }
  return null;
}

/**
 * 從 Supabase 查詢可用日期清單
 */
async function fetchSupabaseDates(system: string, days: number = 30): Promise<string[]> {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) return [];
  const params = new URLSearchParams({
    system: `eq.${system}_daily`,
    select: 'schedule_date',
    order: 'schedule_date.desc',
    limit: String(days),
  });
  const res = await fetch(`${SUPABASE_URL}/rest/v1/daily_schedules?${params}`, {
    headers: {
      apikey: SUPABASE_ANON_KEY,
      'Accept-Profile': 'reference',
    },
  });
  if (res.ok) {
    const rows = await res.json();
    return rows.map((r: { schedule_date: string }) => r.schedule_date);
  }
  return [];
}

/**
 * 高鐵軌道 ID 列表
 */
const THSR_TRACK_IDS = ['THSR-1-0', 'THSR-1-1'];

/**
 * 車站進度映射表類型
 * 外層 key: track_id (THSR-1-0, THSR-1-1)
 * 內層 key: station_id
 * value: 0-1 之間的進度值
 */
export type StationProgressMap = Record<string, Record<string, number>>;

/**
 * 高鐵資料狀態
 */
export interface ThsrDataState {
  tracks: TrackCollection | null;
  stations: StationCollection | null;
  schedules: Map<string, TrackSchedule>;
  trackMap: Map<string, Track>;
  stationProgress: StationProgressMap; // 車站在軌道上的進度 (0-1)
  loading: boolean;
  scheduleLoading: boolean; // 時刻表切換中（軌道/車站不需重載）
  error: string | null;
  scheduleDate: string | null; // 目前載入的時刻表日期（null = 固定時刻表）
  scheduleTrainCount: number; // 目前載入的班次數
  availableDates: string[]; // 已下載的每日時刻表日期清單
}

/**
 * 從 data 物件解析 THSR 時刻表
 */
function parseThsrSchedule(data: Record<string, TrackSchedule>): {
  scheduleMap: Map<string, TrackSchedule>;
  trainCount: number;
} {
  const scheduleMap = new Map<string, TrackSchedule>();
  let trainCount = 0;
  for (const trackId of THSR_TRACK_IDS) {
    if (data[trackId]) {
      scheduleMap.set(trackId, data[trackId]);
      trainCount += data[trackId].departure_count || data[trackId].departures?.length || 0;
    }
  }
  return { scheduleMap, trainCount };
}

/**
 * 從 URL 載入時刻表 JSON 並轉為 Map
 */
async function loadScheduleFromUrl(url: string): Promise<{
  scheduleMap: Map<string, TrackSchedule>;
  trainCount: number;
}> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load schedule: ${url}`);
  const data = await res.json();
  return parseThsrSchedule(data);
}

/**
 * 高鐵資料 Hook
 *
 * 獨立載入高鐵相關資料：
 * - 軌道 GeoJSON
 * - 車站 GeoJSON
 * - 時刻表（支援日期切換）
 *
 * @param selectedDate 可選的日期字串 (YYYY-MM-DD)，undefined 時使用固定時刻表
 */
export function useThsrData(selectedDate?: string): ThsrDataState {
  const [tracks, setTracks] = useState<TrackCollection | null>(null);
  const [stations, setStations] = useState<StationCollection | null>(null);
  const [schedules, setSchedules] = useState<Map<string, TrackSchedule>>(new Map());
  const [trackMap, setTrackMap] = useState<Map<string, Track>>(new Map());
  const [stationProgress, setStationProgress] = useState<StationProgressMap>({});
  const [loading, setLoading] = useState(true);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scheduleDate, setScheduleDate] = useState<string | null>(null);
  const [scheduleTrainCount, setScheduleTrainCount] = useState(0);
  const [availableDates, setAvailableDates] = useState<string[]>([]);

  // 初始載入：軌道、車站、車站進度、預設時刻表、可用日期清單
  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);

        // 載入軌道
        const trackFeatures: Track[] = [];
        for (const trackId of THSR_TRACK_IDS) {
          const res = await fetch(`/data/thsr/tracks/${trackId}.geojson`);
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
        const stationsRes = await fetch('/data/thsr/stations/thsr_stations.geojson');
        if (!stationsRes.ok) throw new Error('Failed to load THSR stations');
        const stationsData = await stationsRes.json();
        setStations(stationsData);

        // 載入車站進度映射表
        const progressRes = await fetch('/data/thsr/station_progress.json');
        if (!progressRes.ok) throw new Error('Failed to load THSR station progress');
        const progressData = await progressRes.json();
        setStationProgress(progressData);

        // 載入預設時刻表（固定時刻表）
        const { scheduleMap, trainCount } = await loadScheduleFromUrl(
          '/data/thsr/schedules/thsr_schedules.json'
        );
        setSchedules(scheduleMap);
        setScheduleTrainCount(trainCount);
        setScheduleDate(null);

        // 載入可用日期清單 (優先 Supabase → S3 → 本地)
        try {
          let indexDates = await fetchSupabaseDates('thsr', 30);
          if (!indexDates.length) {
            const fallbackUrl = DAILY_SCHEDULE_BASE_URL
              ? `${DAILY_SCHEDULE_BASE_URL}/thsr/index.json`
              : '/data/thsr/schedules/daily/index.json';
            const res = await fetch(fallbackUrl);
            if (res.ok) {
              const data = await res.json();
              indexDates = data.dates || [];
            }
          }
          setAvailableDates(indexDates);
        } catch {
          // 日期清單不存在沒關係，日期選擇器會沒有限制
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
          const { scheduleMap, trainCount } = await loadScheduleFromUrl(
            '/data/thsr/schedules/thsr_schedules.json'
          );
          setSchedules(scheduleMap);
          setScheduleTrainCount(trainCount);
          setScheduleDate(null);
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
        setScheduleLoading(false);
        return;
      }

      // 載入指定日期時刻表 (優先 Supabase → S3 → 本地)
      setScheduleLoading(true);
      try {
        // 先嘗試 Supabase
        const supaData = await fetchSupabaseSchedule('thsr', selectedDate);
        let scheduleMap: Map<string, TrackSchedule>;
        let trainCount: number;
        if (supaData && typeof supaData === 'object') {
          const result = parseThsrSchedule(supaData as Record<string, TrackSchedule>);
          scheduleMap = result.scheduleMap;
          trainCount = result.trainCount;
        } else {
          // Fallback 到 S3 或本地
          const dailyUrl = DAILY_SCHEDULE_BASE_URL
            ? `${DAILY_SCHEDULE_BASE_URL}/thsr/daily/${selectedDate}.json`
            : `/data/thsr/schedules/daily/${selectedDate}.json`;
          const result = await loadScheduleFromUrl(dailyUrl);
          scheduleMap = result.scheduleMap;
          trainCount = result.trainCount;
        }
        setSchedules(scheduleMap);
        setScheduleTrainCount(trainCount);
        setScheduleDate(selectedDate);
        setError(null);
      } catch {
        // 該日期時刻表不存在，fallback 到固定時刻表
        console.warn(`THSR daily schedule for ${selectedDate} not found, using default`);
        try {
          const { scheduleMap, trainCount } = await loadScheduleFromUrl(
            '/data/thsr/schedules/thsr_schedules.json'
          );
          setSchedules(scheduleMap);
          setScheduleTrainCount(trainCount);
          setScheduleDate(null);
          setError(`${selectedDate} 的高鐵時刻表不存在，已切回固定時刻表`);
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
      }
      setScheduleLoading(false);
    }

    loadDailySchedule();
  }, [selectedDate, loading]);

  return {
    tracks, stations, schedules, trackMap, stationProgress,
    loading, scheduleLoading, error,
    scheduleDate, scheduleTrainCount, availableDates,
  };
}
