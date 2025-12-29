/**
 * TrainEngine - 列車引擎 (精確版)
 *
 * 使用分段插值計算列車位置：
 * - 停站時列車靜止在車站
 * - 行駛時在兩站間平滑移動
 * - 使用時刻表中的精確站間時間
 */

import type { Schedule, TrackSchedule, Departure, StationTime } from '../types/schedule';
import type { Track } from '../types/track';

export interface Train {
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
}

// 車站在軌道上的實際進度 (0-1)
export type StationProgressMap = Record<string, Record<string, number>>;

export interface TrainEngineOptions {
  schedules: Map<string, TrackSchedule>;
  tracks: Map<string, Track>;
  stationProgress?: StationProgressMap;
}

/**
 * 將時間字串轉換為當天秒數
 */
function timeToSeconds(timeStr: string): number {
  const parts = timeStr.split(':').map(Number);
  return parts[0] * 3600 + parts[1] * 60 + (parts[2] || 0);
}

/**
 * 計算線段總長度
 */
function calculateTotalLength(coords: [number, number][]): number {
  let total = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    total += distance(coords[i], coords[i + 1]);
  }
  return total;
}

/**
 * 計算兩點間距離
 */
function distance(p1: [number, number], p2: [number, number]): number {
  const dx = p2[0] - p1[0];
  const dy = p2[1] - p1[1];
  return Math.sqrt(dx * dx + dy * dy);
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
    const segmentLength = distance(coords[i], coords[i + 1]);
    if (accumulated + segmentLength >= targetDistance) {
      const segmentProgress = (targetDistance - accumulated) / segmentLength;
      return [
        coords[i][0] + (coords[i + 1][0] - coords[i][0]) * segmentProgress,
        coords[i][1] + (coords[i + 1][1] - coords[i][1]) * segmentProgress,
      ];
    }
    accumulated += segmentLength;
  }

  return coords[coords.length - 1];
}

/**
 * 找到車站在軌道座標中的位置 (使用實際進度或均勻分布)
 */
function getStationProgressFallback(stationIndex: number, totalStations: number): number {
  if (totalStations <= 1) return 0;
  return stationIndex / (totalStations - 1);
}

/**
 * 在兩站之間進行插值 (使用實際進度)
 */
function interpolateBetweenStationsWithProgress(
  coords: [number, number][],
  fromProgress: number,
  toProgress: number,
  segmentProgress: number
): [number, number] {
  const actualProgress = fromProgress + (toProgress - fromProgress) * segmentProgress;
  return interpolateOnLineString(coords, actualProgress);
}

export class TrainEngine {
  private schedules: Map<string, TrackSchedule>;
  private tracks: Map<string, Track>;
  private stationProgress: StationProgressMap;
  private activeTrains: Map<string, Train> = new Map();

  constructor(options: TrainEngineOptions) {
    this.schedules = options.schedules;
    this.tracks = options.tracks;
    this.stationProgress = options.stationProgress || {};
  }

  /**
   * 取得車站在軌道上的實際進度
   */
  private getStationProgress(trackId: string, stationId: string, fallbackIndex: number, totalStations: number): number {
    const trackProgress = this.stationProgress[trackId];
    if (trackProgress && typeof trackProgress[stationId] === 'number') {
      return trackProgress[stationId];
    }
    // 回退到均勻分布
    return getStationProgressFallback(fallbackIndex, totalStations);
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
   * 更新所有列車狀態 (精確版)
   * @param currentTimeSeconds 當天秒數 (0-86399)
   */
  update(currentTimeSeconds: number): Train[] {
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
        const arrivalSeconds = departureSeconds + totalTravelTime;

        // 計算已過時間
        const elapsedTime = currentTimeSeconds - departureSeconds;

        // 快速檢查：跳過尚未發車或已抵達的列車
        if (elapsedTime < -60 || elapsedTime > totalTravelTime + 60) {
          continue;
        }

        // 使用分段插值找到當前狀態
        const segment = this.findCurrentSegment(departure.stations, elapsedTime);

        // 只顯示運行中或停站中的列車
        if (segment.status === 'waiting' || segment.status === 'arrived') {
          continue;
        }

        // 計算位置 (使用實際車站進度)
        let position: [number, number];
        const currentStationId = departure.stations[segment.stationIndex]?.station_id;
        const nextStationId = departure.stations[segment.nextStationIndex]?.station_id;

        if (segment.status === 'stopped') {
          // 停站中：位置固定在車站 (使用實際進度)
          const stationProg = currentStationId
            ? this.getStationProgress(trackId, currentStationId, segment.stationIndex, totalStations)
            : getStationProgressFallback(segment.stationIndex, totalStations);
          position = interpolateOnLineString(coords, stationProg);
        } else {
          // 行駛中：在兩站間插值 (使用實際進度)
          const fromProgress = currentStationId
            ? this.getStationProgress(trackId, currentStationId, segment.stationIndex, totalStations)
            : getStationProgressFallback(segment.stationIndex, totalStations);
          const toProgress = nextStationId
            ? this.getStationProgress(trackId, nextStationId, segment.nextStationIndex, totalStations)
            : getStationProgressFallback(segment.nextStationIndex, totalStations);
          position = interpolateBetweenStationsWithProgress(
            coords,
            fromProgress,
            toProgress,
            segment.segmentProgress
          );
        }

        // 計算整體進度
        const overallProgress = totalTravelTime > 0
          ? Math.max(0, Math.min(1, elapsedTime / totalTravelTime))
          : 0;

        const train: Train = {
          trainId: departure.train_id,
          trackId,
          departureTime: departureSeconds,
          totalTravelTime,
          status: segment.status,
          progress: overallProgress,
          position,
          currentStation: segment.currentStation,
          nextStation: segment.nextStation,
          segmentProgress: segment.segmentProgress,
        };

        this.activeTrains.set(train.trainId, train);
      }
    }

    return Array.from(this.activeTrains.values());
  }

  /**
   * 取得所有活躍列車
   */
  getActiveTrains(): Train[] {
    return Array.from(this.activeTrains.values());
  }

  /**
   * 取得特定軌道的活躍列車
   */
  getTrainsOnTrack(trackId: string): Train[] {
    return this.getActiveTrains().filter((t) => t.trackId === trackId);
  }

  /**
   * 取得列車數量統計
   */
  getStats(): {
    total: number;
    running: number;
    stopped: number;
    byTrack: Record<string, number>
  } {
    const byTrack: Record<string, number> = {};
    let running = 0;
    let stopped = 0;

    for (const train of this.activeTrains.values()) {
      byTrack[train.trackId] = (byTrack[train.trackId] || 0) + 1;
      if (train.status === 'running') running++;
      if (train.status === 'stopped') stopped++;
    }

    return {
      total: this.activeTrains.size,
      running,
      stopped,
      byTrack,
    };
  }
}
