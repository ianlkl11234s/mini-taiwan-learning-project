import { useState, useEffect } from 'react';
import type { TrackCollection, StationCollection, Track } from '../types/track';
import type { TrackSchedule } from '../types/schedule';

/**
 * GIS Platform API URL (優先) — 從 Supabase 取時刻表
 * S3 Base URL (備援) — fallback 到 S3 靜態檔案
 */
const GIS_API_URL = import.meta.env.VITE_GIS_API_URL || '';
const DAILY_SCHEDULE_BASE_URL = import.meta.env.VITE_DAILY_SCHEDULE_BASE_URL || '';

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
 * 載入時刻表 JSON 並轉為 Map
 */
async function loadScheduleFromUrl(url: string): Promise<{
  scheduleMap: Map<string, TrackSchedule>;
  trainCount: number;
}> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load schedule: ${url}`);
  const data = await res.json();

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

        // 載入可用日期清單 (優先 GIS API → S3 → 本地)
        try {
          let indexDates: string[] = [];
          if (GIS_API_URL) {
            const res = await fetch(`${GIS_API_URL}/api/schedules/dates?system=thsr&days=30`);
            if (res.ok) {
              const data = await res.json();
              indexDates = data.dates || [];
            }
          }
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

      // 載入指定日期時刻表 (優先 GIS API → S3 → 本地)
      setScheduleLoading(true);
      try {
        let dailyUrl: string;
        if (GIS_API_URL) {
          dailyUrl = `${GIS_API_URL}/api/schedules?system=thsr&date=${selectedDate}`;
        } else if (DAILY_SCHEDULE_BASE_URL) {
          dailyUrl = `${DAILY_SCHEDULE_BASE_URL}/thsr/daily/${selectedDate}.json`;
        } else {
          dailyUrl = `/data/thsr/schedules/daily/${selectedDate}.json`;
        }
        const { scheduleMap, trainCount } = await loadScheduleFromUrl(dailyUrl);
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
