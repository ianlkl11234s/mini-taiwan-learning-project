/**
 * TrainEngine - 列車引擎
 *
 * 根據時刻表管理列車：
 * - 產生列車實例
 * - 計算列車即時位置
 * - 管理列車生命週期（出發→行駛→抵達消失）
 */

import type { Schedule, TrackSchedule, Departure } from '../types/schedule';
import type { Track } from '../types/track';

export interface Train {
  trainId: string;
  trackId: string;
  departureTime: number; // 當天秒數
  totalTravelTime: number; // 秒
  status: 'waiting' | 'running' | 'arrived';
  progress: number; // 0-1
  position: [number, number]; // [lng, lat]
}

export interface TrainEngineOptions {
  schedules: Map<string, TrackSchedule>;
  tracks: Map<string, Track>;
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
 * 計算兩點間距離（使用 Haversine 公式簡化版）
 */
function distance(p1: [number, number], p2: [number, number]): number {
  const dx = p2[0] - p1[0];
  const dy = p2[1] - p1[1];
  // 簡化計算，對於短距離足夠精確
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

export class TrainEngine {
  private schedules: Map<string, TrackSchedule>;
  private tracks: Map<string, Track>;
  private activeTrains: Map<string, Train> = new Map();

  constructor(options: TrainEngineOptions) {
    this.schedules = options.schedules;
    this.tracks = options.tracks;
  }

  /**
   * 更新所有列車狀態
   * @param currentTimeSeconds 當天秒數 (0-86399)
   */
  update(currentTimeSeconds: number): Train[] {
    this.activeTrains.clear();

    // 遍歷所有軌道的時刻表
    for (const [trackId, schedule] of this.schedules) {
      const track = this.tracks.get(trackId);
      if (!track) continue;

      // 遍歷該軌道的所有發車班次
      for (const departure of schedule.departures) {
        const departureSeconds = timeToSeconds(departure.departure_time);
        const totalTravelTime = departure.total_travel_time;
        const arrivalSeconds = departureSeconds + totalTravelTime;

        // 判斷列車狀態
        let status: Train['status'];
        let progress: number;

        if (currentTimeSeconds < departureSeconds) {
          // 尚未發車
          status = 'waiting';
          progress = 0;
        } else if (currentTimeSeconds >= arrivalSeconds) {
          // 已抵達終點
          status = 'arrived';
          progress = 1;
        } else {
          // 行駛中
          status = 'running';
          progress = (currentTimeSeconds - departureSeconds) / totalTravelTime;
        }

        // 只顯示行駛中的列車
        if (status !== 'running') continue;

        // 計算位置
        const position = interpolateOnLineString(
          track.geometry.coordinates as [number, number][],
          progress
        );

        const train: Train = {
          trainId: departure.train_id,
          trackId,
          departureTime: departureSeconds,
          totalTravelTime,
          status,
          progress,
          position,
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
  getStats(): { total: number; byTrack: Record<string, number> } {
    const byTrack: Record<string, number> = {};
    for (const train of this.activeTrains.values()) {
      byTrack[train.trackId] = (byTrack[train.trackId] || 0) + 1;
    }
    return {
      total: this.activeTrains.size,
      byTrack,
    };
  }
}
