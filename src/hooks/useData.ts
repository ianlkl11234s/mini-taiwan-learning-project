import { useState, useEffect } from 'react';
import type { TrackCollection, StationCollection, Track } from '../types/track';
import type { TrackSchedule } from '../types/schedule';

// 軌道 ID 列表
const TRACK_IDS = [
  // === 文湖線 (BR) ===
  'BR-1-0', 'BR-1-1',  // 全程車（動物園↔南港展覽館）
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
  // 首班車往南港展覽館
  'BL-3-0',            // 新埔→南港展覽館
  'BL-4-0',            // 台北車站→南港展覽館
  'BL-5-0',            // 忠孝復興→南港展覽館
  'BL-6-0',            // 市政府→南港展覽館
  'BL-7-0',            // 南港→南港展覽館
  // 首班車往頂埔
  'BL-8-1',            // 永寧→頂埔
  'BL-9-1',            // 亞東醫院→頂埔
  'BL-10-1',           // 江子翠→頂埔
  'BL-11-1',           // 台北車站→頂埔
  'BL-12-1',           // 國父紀念館→頂埔
  'BL-13-1',           // 後山埤→頂埔
  // === 綠線 (G) ===
  'G-1-0', 'G-1-1',    // 全程車（新店↔松山）
  'G-2-0', 'G-2-1',    // 區間車（台電大樓↔松山）
  'G-3-0', 'G-3-1',    // 小碧潭支線（七張↔小碧潭）
  // 首班車往新店
  'G-4-0',             // 七張→新店
  'G-5-0',             // 台電大樓→新店
  'G-6-0',             // 西門→新店
  'G-7-0',             // 中山→新店
  // 首班車往松山
  'G-8-1',             // 大坪林→松山
  'G-9-1',             // 公館→松山
  'G-10-1',            // 中正紀念堂→松山
  'G-11-1',            // 北門→松山
  'G-12-1',            // 南京復興→松山
  // === 橘線 (O) ===
  'O-1-0', 'O-1-1',    // 新莊線（迴龍↔南勢角）
  'O-2-0', 'O-2-1',    // 蘆洲線（蘆洲↔南勢角）
  // 首班車往南勢角
  'O-3-0',             // 輔大→南勢角
  'O-4-0',             // 頭前庄→南勢角
  'O-5-0',             // 先嗇宮→南勢角
  'O-6-0',             // 大橋頭→南勢角
  'O-7-0',             // 民權西路→南勢角
  'O-8-0',             // 中山國小→南勢角
  'O-9-0',             // 忠孝新生→南勢角
  'O-10-0',            // 古亭→南勢角
  'O-11-0',            // 永安市場→南勢角
  'O-12-0',            // 三和國中→南勢角
  // 首班車往迴龍
  'O-13-1',            // 景安→迴龍
  'O-14-1',            // 古亭→迴龍
  'O-15-1',            // 行天宮→迴龍
  'O-16-1',            // 菜寮→迴龍
  'O-17-1',            // 新莊→迴龍
  'O-18-1',            // 丹鳳→迴龍
  // 首班車往蘆洲
  'O-19-1',            // 永安市場→蘆洲
  'O-20-1',            // 古亭→蘆洲
  'O-21-1',            // 忠孝新生→蘆洲
  'O-22-1',            // 民權西路→蘆洲
  'O-23-1',            // 徐匯中學→蘆洲
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

        // 載入車站（紅線 + 藍線 + 綠線）
        const redStationsRes = await fetch('/data/red_line_stations.geojson');
        if (!redStationsRes.ok) throw new Error('Failed to load red line stations');
        const redStationsData = await redStationsRes.json();

        const blueStationsRes = await fetch('/data/blue_line_stations.geojson');
        if (!blueStationsRes.ok) throw new Error('Failed to load blue line stations');
        const blueStationsData = await blueStationsRes.json();

        const greenStationsRes = await fetch('/data/green_line_stations.geojson');
        if (!greenStationsRes.ok) throw new Error('Failed to load green line stations');
        const greenStationsData = await greenStationsRes.json();

        const orangeStationsRes = await fetch('/data/orange_line_stations.geojson');
        if (!orangeStationsRes.ok) throw new Error('Failed to load orange line stations');
        const orangeStationsData = await orangeStationsRes.json();

        const brownStationsRes = await fetch('/data/brown_line_stations.geojson');
        if (!brownStationsRes.ok) throw new Error('Failed to load brown line stations');
        const brownStationsData = await brownStationsRes.json();

        // 合併車站資料
        const allStations: StationCollection = {
          type: 'FeatureCollection',
          features: [
            ...redStationsData.features,
            ...blueStationsData.features,
            ...greenStationsData.features,
            ...orangeStationsData.features,
            ...brownStationsData.features,
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
