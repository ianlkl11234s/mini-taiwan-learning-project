/**
 * ODTrainEngine - O-D 專屬軌道列車引擎
 *
 * 使用預先建立的 O-D 專屬軌道來計算列車位置，
 * 避免軌道切換時的抖動問題。
 *
 * 特點：
 * - 每班車使用自己的專屬軌道
 * - 無需動態軌道切換
 * - 支援 NW (內灣線) 和 LJ (六家線)
 */

export interface ODTrain {
  trainId: string;
  trackId: string;         // 用於顏色顯示 (如 NW-1, LJ-0)
  odTrackId: string;       // O-D 軌道 ID (如 NW-HC-NB)
  departureTime: number;   // 當天秒數
  totalTravelTime: number; // 秒
  status: 'waiting' | 'running' | 'stopped' | 'arrived';
  progress: number;        // 0-1 (整體進度)
  position: [number, number]; // [lng, lat]
  currentStation?: string;
  nextStation?: string;
  segmentProgress?: number;

  // 列車資訊
  originStation: string;
  destinationStation: string;
  trainNo?: string;
  trainType?: string;
}

export interface StationTime {
  station_id: string;
  station_name: string;
  arrival: number;
  departure: number;
}

export interface ODDeparture {
  departure_time: string;
  train_id: string;
  train_no?: string;
  train_type?: string;
  origin_station: string;
  destination_station: string;
  od_track_id: string;
  stations: StationTime[];
  total_travel_time: number;
}

export interface ODSchedule {
  track_id: string;
  route_id: string;
  name: string;
  departure_count: number;
  departures: ODDeparture[];
}

export interface ODTrack {
  type: 'Feature';
  properties: {
    track_id: string;
    origin: string;
    destination: string;
    origin_station_id: string;
    destination_station_id: string;
    source_tracks: string[];
    stations: Array<{
      station_id: string;
      name: string;
      progress: number;
    }>;
  };
  geometry: {
    type: 'LineString';
    coordinates: [number, number][];
  };
}

// 車站進度映射 { od_track_id: { station_id: progress } }
export type ODStationProgressMap = Record<string, Record<string, number>>;

export interface ODTrainEngineOptions {
  schedules: Map<string, ODSchedule>;
  odTracks: Map<string, ODTrack>;
  stationProgress: ODStationProgressMap;
}

// 終站停留時間
const TERMINAL_DWELL_TIME = 60;
// 起站提前出現時間
const ORIGIN_EARLY_APPEAR_TIME = 120;

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
 * 從 O-D 軌道 ID 取得顯示用 trackId
 * NW-HC-NB (新竹→內灣) → NW-1
 * NW-NB-HC (內灣→新竹) → NW-0
 * LJ-HC-LJ (新竹→六家) → LJ-1
 * LJ-LJ-HC (六家→新竹) → LJ-0
 */
function getTrackIdFromOdTrackId(odTrackId: string): string {
  const [lineId, _origin, dest] = odTrackId.split('-');

  // 判斷方向：往新竹(HC)為 0，往其他站為 1
  const direction = dest === 'HC' ? '0' : '1';

  return `${lineId}-${direction}`;
}

export class ODTrainEngine {
  private schedules: Map<string, ODSchedule>;
  private odTracks: Map<string, ODTrack>;
  private stationProgress: ODStationProgressMap;
  private activeTrains: Map<string, ODTrain> = new Map();

  constructor(options: ODTrainEngineOptions) {
    this.schedules = options.schedules;
    this.odTracks = options.odTracks;
    this.stationProgress = options.stationProgress;
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
    if (elapsedTime < 0) {
      return {
        status: 'waiting',
        stationIndex: 0,
        nextStationIndex: 0,
        segmentProgress: 0,
        currentStation: stations[0]?.station_id,
      };
    }

    for (let i = 0; i < stations.length; i++) {
      const station = stations[i];
      const arrival = station.arrival;
      const departure = station.departure;

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

    return {
      status: 'arrived',
      stationIndex: stations.length - 1,
      nextStationIndex: stations.length - 1,
      segmentProgress: 1,
      currentStation: stations[stations.length - 1]?.station_id,
    };
  }

  /**
   * 更新所有列車狀態
   */
  update(currentTimeSeconds: number): ODTrain[] {
    this.activeTrains.clear();

    for (const [_scheduleId, schedule] of this.schedules) {
      for (const departure of schedule.departures) {
        const departureSeconds = timeToSeconds(departure.departure_time);
        const totalTravelTime = departure.total_travel_time;
        const elapsedTime = currentTimeSeconds - departureSeconds;

        // 跳過不在顯示範圍的列車
        if (elapsedTime < -ORIGIN_EARLY_APPEAR_TIME || elapsedTime > totalTravelTime + TERMINAL_DWELL_TIME + 60) {
          continue;
        }

        // 取得 O-D 軌道
        const odTrackId = departure.od_track_id;
        const odTrack = this.odTracks.get(odTrackId);
        if (!odTrack) {
          console.warn(`O-D 軌道不存在: ${odTrackId}`);
          continue;
        }

        const coords = odTrack.geometry.coordinates;
        if (coords.length === 0) continue;

        // 取得車站進度
        const trackProgress = this.stationProgress[odTrackId];
        if (!trackProgress) {
          console.warn(`車站進度不存在: ${odTrackId}`);
          continue;
        }

        // 找到當前狀態
        const segment = this.findCurrentSegment(departure.stations, elapsedTime);

        let displayStatus = segment.status;
        let isWaitingAtOrigin = false;
        if (segment.status === 'waiting') {
          displayStatus = 'stopped';
          isWaitingAtOrigin = true;
        }

        if (segment.status === 'arrived') {
          const timeAfterArrival = elapsedTime - totalTravelTime;
          if (timeAfterArrival > TERMINAL_DWELL_TIME) {
            continue;
          }
          displayStatus = 'stopped';
        }

        // 計算位置
        const stations = departure.stations;
        const fromStationId = stations[segment.stationIndex]?.station_id;
        const toStationId = stations[segment.nextStationIndex]?.station_id;

        const fromProgress = trackProgress[fromStationId] ?? 0;
        const toProgress = trackProgress[toStationId] ?? 1;

        let position: [number, number];

        if (isWaitingAtOrigin || displayStatus === 'stopped') {
          position = interpolateOnLineString(coords, fromProgress);
        } else {
          const actualProgress = fromProgress + (toProgress - fromProgress) * segment.segmentProgress;
          position = interpolateOnLineString(coords, actualProgress);
        }

        const overallProgress = totalTravelTime > 0
          ? Math.max(0, Math.min(1, elapsedTime / totalTravelTime))
          : 0;

        const train: ODTrain = {
          trainId: departure.train_id,
          trackId: getTrackIdFromOdTrackId(odTrackId),
          odTrackId,
          departureTime: departureSeconds,
          totalTravelTime,
          status: displayStatus,
          progress: overallProgress,
          position,
          currentStation: segment.currentStation,
          nextStation: segment.nextStation,
          segmentProgress: segment.segmentProgress,
          originStation: departure.origin_station,
          destinationStation: departure.destination_station,
          trainNo: departure.train_no,
          trainType: departure.train_type,
        };

        this.activeTrains.set(train.trainId, train);
      }
    }

    return Array.from(this.activeTrains.values());
  }

  /**
   * 取得所有活躍列車
   */
  getActiveTrains(): ODTrain[] {
    return Array.from(this.activeTrains.values());
  }

  /**
   * 取得列車數量統計
   */
  getStats(): {
    total: number;
    running: number;
    stopped: number;
  } {
    let running = 0;
    let stopped = 0;

    for (const train of this.activeTrains.values()) {
      if (train.status === 'running') running++;
      if (train.status === 'stopped') stopped++;
    }

    return {
      total: this.activeTrains.size,
      running,
      stopped,
    };
  }
}
