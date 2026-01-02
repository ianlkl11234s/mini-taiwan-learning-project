/**
 * KrtcTrainEngine - 高雄捷運列車引擎
 *
 * 簡化版列車引擎：
 * - 雙路線（橘線、紅線）
 * - 無碰撞檢測（KRTC 軌道獨立）
 * - 無延長日制（KRTC 06:00-24:00 運營）
 * - 使用累積距離計算車站進度
 */

import type { TrackSchedule, StationTime } from '../types/schedule';
import type { Track } from '../types/track';
import type { KrtcStationProgressMap } from '../hooks/useKrtcData';

export interface KrtcTrain {
  trainId: string;
  trackId: string;
  departureTime: number; // 當天秒數
  totalTravelTime: number; // 秒
  status: 'waiting' | 'running' | 'stopped' | 'arrived';
  progress: number; // 0-1 (整體進度)
  position: [number, number]; // [lng, lat]
  currentStation?: string; // 停靠中的車站 ID
  nextStation?: string; // 下一站 ID
  segmentProgress?: number; // 當前區段進度 0-1

  // 列車資訊面板用欄位
  originStation: string;
  destinationStation: string;
  previousStation?: string;
  previousDepartureTime?: string;
  nextArrivalTime?: string;
}

export interface KrtcTrainEngineOptions {
  schedules: Map<string, TrackSchedule>;
  tracks: Map<string, Track>;
}

// 終站停留時間（秒）
const TERMINAL_DWELL_TIME = 60;

/**
 * 計算線段總長度
 */
function calculateTotalLength(coords: [number, number][]): number {
  let total = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    const dx = coords[i + 1][0] - coords[i][0];
    const dy = coords[i + 1][1] - coords[i][1];
    total += Math.sqrt(dx * dx + dy * dy);
  }
  return total;
}

/**
 * 在線段上進行線性內插
 */
function interpolateOnLineString(
  coords: [number, number][],
  progress: number
): [number, number] {
  if (coords.length === 0) return [0, 0];
  if (coords.length === 1) return coords[0];
  if (progress <= 0) return coords[0];
  if (progress >= 1) return coords[coords.length - 1];

  const totalLength = calculateTotalLength(coords);
  const targetDistance = totalLength * progress;

  let accumulated = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    const dx = coords[i + 1][0] - coords[i][0];
    const dy = coords[i + 1][1] - coords[i][1];
    const segmentLength = Math.sqrt(dx * dx + dy * dy);

    if (accumulated + segmentLength >= targetDistance) {
      const segmentProgress = (targetDistance - accumulated) / segmentLength;
      return [
        coords[i][0] + dx * segmentProgress,
        coords[i][1] + dy * segmentProgress,
      ];
    }
    accumulated += segmentLength;
  }

  return coords[coords.length - 1];
}

/**
 * 時間字串轉秒數
 */
function timeToSeconds(timeStr: string): number {
  const parts = timeStr.split(':').map(Number);
  return parts[0] * 3600 + parts[1] * 60 + (parts[2] || 0);
}

/**
 * 秒數轉時間字串
 */
function secondsToTimeStr(seconds: number): string {
  const hours = Math.floor(seconds / 3600) % 24;
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
}

export class KrtcTrainEngine {
  private schedules: Map<string, TrackSchedule>;
  private tracks: Map<string, Track>;
  private activeTrains: Map<string, KrtcTrain> = new Map();
  private stationProgress: KrtcStationProgressMap = {};

  constructor(options: KrtcTrainEngineOptions) {
    this.schedules = options.schedules;
    this.tracks = options.tracks;
  }

  /**
   * 設置車站在軌道上的進度（由 station_progress.json 載入）
   */
  setStationProgress(progress: KrtcStationProgressMap): void {
    this.stationProgress = progress;
  }

  /**
   * 根據已過時間找到當前所在的區段
   */
  private findCurrentSegment(
    stations: StationTime[],
    elapsedTime: number
  ): {
    status: 'waiting' | 'running' | 'stopped' | 'arrived';
    stationIndex: number;
    nextStationIndex: number;
    segmentProgress: number;
    currentStation?: string;
    nextStation?: string;
  } {
    // 尚未發車
    if (elapsedTime < 0) {
      return {
        status: 'waiting',
        stationIndex: 0,
        nextStationIndex: 0,
        segmentProgress: 0,
        currentStation: stations[0]?.station_id,
      };
    }

    // 遍歷所有站點
    for (let i = 0; i < stations.length; i++) {
      const station = stations[i];
      const arrival = station.arrival;
      const departure = station.departure;

      // 檢查是否在這個站停靠
      if (elapsedTime >= arrival && elapsedTime < departure) {
        return {
          status: 'stopped',
          stationIndex: i,
          nextStationIndex: i < stations.length - 1 ? i + 1 : i,
          segmentProgress: 0,
          currentStation: station.station_id,
          nextStation: i < stations.length - 1 ? stations[i + 1].station_id : undefined,
        };
      }

      // 檢查是否在這個站和下一站之間行駛
      if (i < stations.length - 1) {
        const nextStation = stations[i + 1];
        const nextArrival = nextStation.arrival;

        if (elapsedTime >= departure && elapsedTime < nextArrival) {
          const travelTime = nextArrival - departure;
          const travelElapsed = elapsedTime - departure;
          const segmentProgress = travelTime > 0 ? travelElapsed / travelTime : 0;

          return {
            status: 'running',
            stationIndex: i,
            nextStationIndex: i + 1,
            segmentProgress: Math.min(1, Math.max(0, segmentProgress)),
            currentStation: undefined,
            nextStation: nextStation.station_id,
          };
        }
      }
    }

    // 已抵達終點
    return {
      status: 'arrived',
      stationIndex: stations.length - 1,
      nextStationIndex: stations.length - 1,
      segmentProgress: 1,
      currentStation: stations[stations.length - 1]?.station_id,
    };
  }

  /**
   * 計算車站在軌道上的進度 (0-1)
   * 使用均勻分布作為備用
   */
  private getStationProgressFallback(stationIndex: number, totalStations: number): number {
    if (totalStations <= 1) return 0;
    return stationIndex / (totalStations - 1);
  }

  /**
   * 更新所有列車狀態
   * @param currentTimeSeconds 當天秒數 (0-86399)
   */
  update(currentTimeSeconds: number): KrtcTrain[] {
    this.activeTrains.clear();

    // 遍歷所有軌道的時刻表
    for (const [trackId, schedule] of this.schedules) {
      const track = this.tracks.get(trackId);
      if (!track) continue;

      const coords = track.geometry.coordinates as [number, number][];
      const totalStations = schedule.stations.length;

      // 遍歷該軌道的所有發車班次
      for (const departure of schedule.departures) {
        const departureSeconds = timeToSeconds(departure.departure_time);
        const totalTravelTime = departure.total_travel_time;

        // 計算已過時間
        const elapsedTime = currentTimeSeconds - departureSeconds;

        // 快速檢查：跳過尚未發車或已完全離開的列車
        if (elapsedTime < -60 || elapsedTime > totalTravelTime + TERMINAL_DWELL_TIME + 60) {
          continue;
        }

        // 使用分段插值找到當前狀態
        const segment = this.findCurrentSegment(departure.stations, elapsedTime);

        // 跳過尚未發車的列車
        if (segment.status === 'waiting') {
          continue;
        }

        // 處理已抵達終點的列車
        let displayStatus = segment.status;
        if (segment.status === 'arrived') {
          const timeAfterArrival = elapsedTime - totalTravelTime;
          if (timeAfterArrival > TERMINAL_DWELL_TIME) {
            continue;
          }
          displayStatus = 'stopped';
        }

        // 計算位置：使用車站在軌道上的實際進度進行內插
        const stations = departure.stations;
        const fromStationId = stations[segment.stationIndex]?.station_id;
        const toStationId = stations[segment.nextStationIndex]?.station_id;

        // 取得車站在軌道上的進度
        const trackProgress = this.stationProgress[trackId];
        const fromProgress = fromStationId && trackProgress?.[fromStationId] !== undefined
          ? trackProgress[fromStationId]
          : this.getStationProgressFallback(segment.stationIndex, totalStations);
        const toProgress = toStationId && trackProgress?.[toStationId] !== undefined
          ? trackProgress[toStationId]
          : this.getStationProgressFallback(segment.nextStationIndex, totalStations);

        let position: [number, number];

        if (displayStatus === 'stopped') {
          // 停站中：使用該站的進度在軌道上定位
          position = interpolateOnLineString(coords, fromProgress);
        } else {
          // 行駛中：在兩站進度間內插，沿軌道移動
          const actualProgress = fromProgress + (toProgress - fromProgress) * segment.segmentProgress;
          position = interpolateOnLineString(coords, actualProgress);
        }

        // 計算整體進度
        const overallProgress = totalTravelTime > 0
          ? Math.max(0, Math.min(1, elapsedTime / totalTravelTime))
          : 0;

        // 計算列車資訊面板所需資料
        const stationList = departure.stations;
        const originStation = stationList[0]?.station_id || '';
        const destinationStation = stationList[stationList.length - 1]?.station_id || '';

        // 前一站資訊
        let previousStation: string | undefined;
        let previousDepartureTime: string | undefined;
        if (segment.stationIndex > 0) {
          const prevIdx = segment.stationIndex - 1;
          previousStation = stationList[prevIdx]?.station_id;
          const prevDepartureSeconds = stationList[prevIdx]?.departure;
          if (prevDepartureSeconds !== undefined) {
            previousDepartureTime = secondsToTimeStr(departureSeconds + prevDepartureSeconds);
          }
        }

        // 下一站到達時間
        let nextArrivalTime: string | undefined;
        if (segment.nextStation && segment.nextStationIndex < stationList.length) {
          const nextArrivalSeconds = stationList[segment.nextStationIndex]?.arrival;
          if (nextArrivalSeconds !== undefined) {
            nextArrivalTime = secondsToTimeStr(departureSeconds + nextArrivalSeconds);
          }
        }

        const train: KrtcTrain = {
          trainId: departure.train_id,
          trackId,
          departureTime: departureSeconds,
          totalTravelTime,
          status: displayStatus,
          progress: overallProgress,
          position,
          currentStation: segment.currentStation,
          nextStation: segment.nextStation,
          segmentProgress: segment.segmentProgress,
          originStation,
          destinationStation,
          previousStation,
          previousDepartureTime,
          nextArrivalTime,
        };

        this.activeTrains.set(train.trainId, train);
      }
    }

    return Array.from(this.activeTrains.values());
  }

  /**
   * 取得所有活躍列車
   */
  getActiveTrains(): KrtcTrain[] {
    return Array.from(this.activeTrains.values());
  }

  /**
   * 取得列車數量統計
   */
  getStats(): {
    total: number;
    running: number;
    stopped: number;
    byLine: Record<string, number>;
  } {
    let running = 0;
    let stopped = 0;
    const byLine: Record<string, number> = { O: 0, R: 0 };

    for (const train of this.activeTrains.values()) {
      if (train.status === 'running') running++;
      if (train.status === 'stopped') stopped++;

      // 統計各線路列車數
      if (train.trackId.includes('-O-')) {
        byLine.O++;
      } else if (train.trackId.includes('-R-')) {
        byLine.R++;
      }
    }

    return {
      total: this.activeTrains.size,
      running,
      stopped,
      byLine,
    };
  }
}
