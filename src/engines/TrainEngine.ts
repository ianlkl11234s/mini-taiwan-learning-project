/**
 * TrainEngine - 列車引擎 (精確版)
 *
 * 使用分段插值計算列車位置：
 * - 停站時列車靜止在車站
 * - 行駛時在兩站間平滑移動
 * - 使用時刻表中的精確站間時間
 */

import type { TrackSchedule, StationTime } from '../types/schedule';
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
  isColliding?: boolean; // 是否與其他列車碰撞
  collisionOffset?: [number, number]; // 碰撞時的視覺偏移
}

// 車站在軌道上的實際進度 (0-1)
export type StationProgressMap = Record<string, Record<string, number>>;

export interface TrainEngineOptions {
  schedules: Map<string, TrackSchedule>;
  tracks: Map<string, Track>;
  stationProgress?: StationProgressMap;
  enableCollisionDetection?: boolean; // 是否啟用碰撞檢測
}

// 共用軌道區段定義 (用於碰撞檢測)
const SHARED_TRACK_SEGMENTS: Record<string, string[]> = {
  // === 紅線 (R) ===
  // R-1-0 和 R-2-0 在 R05-R22 共用軌道 (北上方向)
  'R-1-0': ['R05', 'R06', 'R07', 'R08', 'R09', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17', 'R18', 'R19', 'R20', 'R21', 'R22'],
  'R-2-0': ['R05', 'R06', 'R07', 'R08', 'R09', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17', 'R18', 'R19', 'R20', 'R21', 'R22'],
  // R-1-1 和 R-2-1 在 R22-R05 共用軌道 (南下方向)
  'R-1-1': ['R22', 'R21', 'R20', 'R19', 'R18', 'R17', 'R16', 'R15', 'R14', 'R13', 'R12', 'R11', 'R10', 'R09', 'R08', 'R07', 'R06', 'R05'],
  'R-2-1': ['R22', 'R21', 'R20', 'R19', 'R18', 'R17', 'R16', 'R15', 'R14', 'R13', 'R12', 'R11', 'R10', 'R09', 'R08', 'R07', 'R06', 'R05'],
  // 北段區間車
  'R-4-0': ['R22', 'R23', 'R24', 'R25', 'R26', 'R27', 'R28'],
  'R-4-1': ['R28', 'R27', 'R26', 'R25', 'R24', 'R23', 'R22'],
  // 首班車專用軌道 - 北上 (往淡水方向)
  'R-5-0': ['R05', 'R06', 'R07', 'R08', 'R09', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17', 'R18', 'R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R25', 'R26', 'R27', 'R28'],
  'R-6-0': ['R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17', 'R18', 'R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R25', 'R26', 'R27', 'R28'],
  'R-7-0': ['R15', 'R16', 'R17', 'R18', 'R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R25', 'R26', 'R27', 'R28'],
  'R-8-0': ['R20', 'R21', 'R22', 'R23', 'R24', 'R25', 'R26', 'R27', 'R28'],
  // 首班車專用軌道 - 南下 (往象山方向)
  'R-9-1': ['R24', 'R23', 'R22', 'R21', 'R20', 'R19', 'R18', 'R17', 'R16', 'R15', 'R14', 'R13', 'R12', 'R11', 'R10', 'R09', 'R08', 'R07', 'R06', 'R05', 'R04', 'R03', 'R02'],
  'R-10-1': ['R05', 'R04', 'R03', 'R02'],  // 大安→象山
  'R-11-1': ['R10', 'R09', 'R08', 'R07', 'R06', 'R05', 'R04', 'R03', 'R02'],  // 雙連→象山
  'R-12-1': ['R13', 'R12', 'R11', 'R10', 'R09', 'R08', 'R07', 'R06', 'R05', 'R04', 'R03', 'R02'],  // 民權西路→象山
  'R-13-1': ['R15', 'R14', 'R13', 'R12', 'R11', 'R10', 'R09', 'R08', 'R07', 'R06', 'R05', 'R04', 'R03', 'R02'],  // 圓山→象山
  'R-14-1': ['R19', 'R18', 'R17', 'R16', 'R15', 'R14', 'R13', 'R12', 'R11', 'R10', 'R09', 'R08', 'R07', 'R06', 'R05', 'R04', 'R03', 'R02'],  // 石牌→象山
  'R-15-1': ['R20', 'R19', 'R18', 'R17', 'R16', 'R15', 'R14', 'R13', 'R12', 'R11', 'R10', 'R09', 'R08', 'R07', 'R06', 'R05', 'R04', 'R03', 'R02'],  // 唭哩岸→象山
  // === 藍線 (BL) ===
  // BL-1-0 和 BL-2-0 在 BL05-BL23 共用軌道 (往東/direction 0)
  'BL-1-0': ['BL05', 'BL06', 'BL07', 'BL08', 'BL09', 'BL10', 'BL11', 'BL12', 'BL13', 'BL14', 'BL15', 'BL16', 'BL17', 'BL18', 'BL19', 'BL20', 'BL21', 'BL22', 'BL23'],
  'BL-2-0': ['BL05', 'BL06', 'BL07', 'BL08', 'BL09', 'BL10', 'BL11', 'BL12', 'BL13', 'BL14', 'BL15', 'BL16', 'BL17', 'BL18', 'BL19', 'BL20', 'BL21', 'BL22', 'BL23'],
  // BL-1-1 和 BL-2-1 在 BL23-BL05 共用軌道 (往西/direction 1)
  'BL-1-1': ['BL23', 'BL22', 'BL21', 'BL20', 'BL19', 'BL18', 'BL17', 'BL16', 'BL15', 'BL14', 'BL13', 'BL12', 'BL11', 'BL10', 'BL09', 'BL08', 'BL07', 'BL06', 'BL05'],
  'BL-2-1': ['BL23', 'BL22', 'BL21', 'BL20', 'BL19', 'BL18', 'BL17', 'BL16', 'BL15', 'BL14', 'BL13', 'BL12', 'BL11', 'BL10', 'BL09', 'BL08', 'BL07', 'BL06', 'BL05'],
};

// 碰撞檢測閾值 (經緯度距離，約 50 公尺)
const COLLISION_THRESHOLD = 0.0005;
// 視覺偏移量 (經緯度，約 30 公尺垂直於軌道)
const COLLISION_OFFSET = 0.0003;

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
  private enableCollisionDetection: boolean;

  constructor(options: TrainEngineOptions) {
    this.schedules = options.schedules;
    this.tracks = options.tracks;
    this.stationProgress = options.stationProgress || {};
    this.enableCollisionDetection = options.enableCollisionDetection ?? true;
  }

  /**
   * 檢查列車是否在共用軌道區段
   */
  private isOnSharedSegment(trackId: string, currentStation?: string, nextStation?: string): boolean {
    const sharedStations = SHARED_TRACK_SEGMENTS[trackId];
    if (!sharedStations) return false;

    // 檢查當前站或下一站是否在共用區段
    if (currentStation && sharedStations.includes(currentStation)) return true;
    if (nextStation && sharedStations.includes(nextStation)) return true;
    return false;
  }

  /**
   * 計算兩列車的物理距離
   */
  private calculateDistance(pos1: [number, number], pos2: [number, number]): number {
    const dx = pos1[0] - pos2[0];
    const dy = pos1[1] - pos2[1];
    return Math.sqrt(dx * dx + dy * dy);
  }

  /**
   * 計算垂直於行進方向的偏移向量
   * @param position 當前位置
   * @param trackId 軌道 ID
   * @param progress 軌道進度
   */
  private calculatePerpendicularOffset(
    _position: [number, number],
    trackId: string,
    progress: number,
    offsetDirection: number
  ): [number, number] {
    const track = this.tracks.get(trackId);
    if (!track) return [0, 0];

    const coords = track.geometry.coordinates as [number, number][];
    if (coords.length < 2) return [0, 0];

    // 找到當前位置附近的軌道方向
    const totalLength = calculateTotalLength(coords);
    const targetDistance = totalLength * Math.min(0.99, Math.max(0.01, progress));

    let accumulated = 0;
    for (let i = 0; i < coords.length - 1; i++) {
      const segmentLength = distance(coords[i], coords[i + 1]);
      if (accumulated + segmentLength >= targetDistance) {
        // 計算此段的方向向量
        const dx = coords[i + 1][0] - coords[i][0];
        const dy = coords[i + 1][1] - coords[i][1];
        const length = Math.sqrt(dx * dx + dy * dy);

        if (length > 0) {
          // 垂直向量 (旋轉 90 度)
          const perpX = -dy / length;
          const perpY = dx / length;
          return [perpX * COLLISION_OFFSET * offsetDirection, perpY * COLLISION_OFFSET * offsetDirection];
        }
        break;
      }
      accumulated += segmentLength;
    }

    return [0, 0];
  }

  /**
   * 處理碰撞檢測和視覺分離
   */
  private handleCollisions(): void {
    if (!this.enableCollisionDetection) return;

    const trains = Array.from(this.activeTrains.values());

    // 將列車按共用軌道方向分組
    const direction0Trains: Train[] = []; // R-1-0, R-2-0
    const direction1Trains: Train[] = []; // R-1-1, R-2-1

    for (const train of trains) {
      if (train.trackId.endsWith('-0')) {
        if (this.isOnSharedSegment(train.trackId, train.currentStation, train.nextStation)) {
          direction0Trains.push(train);
        }
      } else if (train.trackId.endsWith('-1')) {
        if (this.isOnSharedSegment(train.trackId, train.currentStation, train.nextStation)) {
          direction1Trains.push(train);
        }
      }
    }

    // 檢測方向 0 的碰撞
    this.detectAndResolveCollisions(direction0Trains);
    // 檢測方向 1 的碰撞
    this.detectAndResolveCollisions(direction1Trains);
  }

  /**
   * 檢測並解決一組列車的碰撞
   * 注意：只檢測真正的軌道碰撞，排除車站同時停靠的情況
   * (現實中車站有多個月台，不同列車可同時停靠)
   */
  private detectAndResolveCollisions(trains: Train[]): void {
    // 按位置排序，使偏移一致
    trains.sort((a, b) => a.position[0] - b.position[0] || a.position[1] - b.position[1]);

    for (let i = 0; i < trains.length; i++) {
      for (let j = i + 1; j < trains.length; j++) {
        const trainA = trains[i];
        const trainB = trains[j];

        // 跳過雙方都在停站的情況 (車站有多月台，不算碰撞)
        if (trainA.status === 'stopped' && trainB.status === 'stopped') {
          continue;
        }

        const dist = this.calculateDistance(trainA.position, trainB.position);

        if (dist < COLLISION_THRESHOLD) {
          // 標記碰撞
          trainA.isColliding = true;
          trainB.isColliding = true;

          // 計算偏移 (A 向一側偏移，B 向另一側)
          const offsetA = this.calculatePerpendicularOffset(
            trainA.position,
            trainA.trackId,
            trainA.progress,
            1 // 正方向
          );
          const offsetB = this.calculatePerpendicularOffset(
            trainB.position,
            trainB.trackId,
            trainB.progress,
            -1 // 負方向
          );

          trainA.collisionOffset = offsetA;
          trainB.collisionOffset = offsetB;

          // 應用偏移到位置
          trainA.position = [
            trainA.position[0] + offsetA[0],
            trainA.position[1] + offsetA[1],
          ];
          trainB.position = [
            trainB.position[0] + offsetB[0],
            trainB.position[1] + offsetB[1],
          ];
        }
      }
    }
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

    // 處理碰撞檢測和視覺分離
    this.handleCollisions();

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
