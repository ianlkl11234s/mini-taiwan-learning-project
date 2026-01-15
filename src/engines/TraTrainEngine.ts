/**
 * TraTrainEngine - 台鐵列車引擎
 *
 * 使用 O-D 專屬軌道來計算列車位置，
 * 避免軌道切換時的抖動問題。
 *
 * 支援路線：
 * - NW (內灣線)
 * - LJ (六家線)
 * - SH (沙崙線)
 * - PX (平溪線)
 * - JJ (集集線)
 * - CZ (成追線)
 * - YL (宜蘭線)
 * - BH (北迴線)
 * - KL (基隆支線)
 * - TL (臺東線)
 *
 * 合併軌道：
 * - YL-SL-SA (樹林↔蘇澳)
 * - YL-SL-HL (樹林↔花蓮)
 * - YL-SL-TT (樹林↔臺東)
 */

export interface TraTrain {
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

export interface TraDeparture {
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

export interface TraSchedule {
  track_id: string;
  route_id: string;
  name: string;
  departure_count: number;
  departures: TraDeparture[];
}

export interface TraTrack {
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
export type TraStationProgressMap = Record<string, Record<string, number>>;

export interface TraTrainEngineOptions {
  schedules: Map<string, TraSchedule>;
  odTracks: Map<string, TraTrack>;
  stationProgress: TraStationProgressMap;
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
 *
 * 支線方向：
 * - 方向 0 = 返回主線/起點站
 * - 方向 1 = 前往支線終點
 *
 * NW: HC=新竹(0), NB=內灣(1), JJ=竹中(中間站), JD=竹東(中間站)
 * LJ: HC=新竹(0), LJ=六家(1)
 * SH: TN=臺南(0), SL=沙崙(1)
 * PX: SD=三貂嶺(0), JT=菁桐(1)
 * JJ: ES=二水(0), CT=車埕(1)
 * CZ: CG=成功(0), ZF=追分(1)
 *
 * 幹線方向：
 * YL: 0=往蘇澳(南下), 1=往臺北(北上)
 * BH: 0=往花蓮(南下), 1=往蘇澳新(北上)
 */
function getTrackIdFromOdTrackId(odTrackId: string): string {
  const parts = odTrackId.split('-');
  const lineId = parts[0];

  // WL 西部幹線：WL-SL-BD-0 → WL-N-SL-BD-0
  if (lineId === 'WL') {
    // odTrackId 格式: WL-SL-BD-0 或 WL-BD-SL-1
    const direction = parts[parts.length - 1];  // 取最後一個數字
    return `WL-N-SL-BD-${direction}`;
  }

  const [, _origin, dest] = parts;

  // YL 宜蘭線
  if (lineId === 'YL') {
    // 樹林↔臺東 合併軌道：YL-SL-TT-0 / YL-TT-SL-1 → 使用 YL golden track
    if (odTrackId === 'YL-SL-TT-0') {
      return 'YL-BD-SA-0';  // 南下使用 YL 方向 0
    }
    if (odTrackId === 'YL-TT-SL-1') {
      return 'YL-SA-BD-1';  // 北上使用 YL 方向 1
    }
    // 樹林↔花蓮 合併軌道：YL-SL-HL-0 / YL-HL-SL-1 → 使用 YL golden track
    if (odTrackId === 'YL-SL-HL-0') {
      return 'YL-BD-SA-0';  // 南下使用 YL 方向 0
    }
    if (odTrackId === 'YL-HL-SL-1') {
      return 'YL-SA-BD-1';  // 北上使用 YL 方向 1
    }
    // 樹林↔蘇澳 合併軌道：YL-SL-SA-0 / YL-SA-SL-1 → 使用 YL golden track
    if (odTrackId === 'YL-SL-SA-0') {
      return 'YL-BD-SA-0';
    }
    if (odTrackId === 'YL-SA-SL-1') {
      return 'YL-SA-BD-1';
    }
    // 區段軌道：YL-BD-SA-0 / YL-SA-BD-1 → 直接對應 golden track
    if (odTrackId.startsWith('YL-BD-SA') || odTrackId.startsWith('YL-SA-BD')) {
      return odTrackId;
    }
    // 舊格式：終點是 TP (臺北) 則為北上 (方向 1)
    const direction = dest === 'TP' ? '1' : '0';
    return `YL-${direction}`;
  }

  // BH 北迴線
  if (lineId === 'BH') {
    // 區段軌道：BH-SX-HL-0 / BH-HL-SX-1 → 直接對應 golden track
    if (odTrackId.startsWith('BH-SX-HL') || odTrackId.startsWith('BH-HL-SX')) {
      return odTrackId;
    }
    // 舊格式：終點是 SX (蘇澳新) 則為北上 (方向 1)
    const direction = dest === 'SX' ? '1' : '0';
    return `BH-${direction}`;
  }

  // KL 基隆支線
  if (lineId === 'KL') {
    // 區段軌道：KL-BD-KL-0 / KL-KL-BD-1 → 直接對應 golden track
    if (odTrackId.startsWith('KL-BD-KL') || odTrackId.startsWith('KL-KL-BD')) {
      return odTrackId;
    }
    // 舊格式：終點是 TP (臺北) 則為北上 (方向 1)
    const direction = dest === 'TP' ? '1' : '0';
    return `KL-${direction}`;
  }

  // TL 臺東線
  if (lineId === 'TL') {
    // O-D 軌道：TL-HL-TT / TL-TT-HL → 對應 TL golden track
    if (odTrackId === 'TL-HL-TT') {
      return 'TL-0';  // 花蓮→臺東 (南下)
    }
    if (odTrackId === 'TL-TT-HL') {
      return 'TL-1';  // 臺東→花蓮 (北上)
    }
    // 終點是 HL (花蓮) 則為北上 (方向 1)
    const direction = dest === 'HL' ? '1' : '0';
    return `TL-${direction}`;
  }

  // NW 內灣線 (新竹↔內灣, 竹中↔內灣)
  if (lineId === 'NW') {
    // NW-HC-NB / NW-NB-HC: 新竹↔內灣
    if (odTrackId === 'NW-HC-NB' || odTrackId === 'NW-JJ-NB') {
      return 'NW-0';  // 往內灣方向
    }
    if (odTrackId === 'NW-NB-HC' || odTrackId === 'NW-NB-JJ') {
      return 'NW-1';  // 往新竹方向
    }
    return 'NW-0';
  }

  // LJ 六家線 (新竹↔六家)
  if (lineId === 'LJ') {
    if (odTrackId === 'LJ-HC-LJ') {
      return 'LJ-0';  // 新竹→六家
    }
    if (odTrackId === 'LJ-LJ-HC') {
      return 'LJ-1';  // 六家→新竹
    }
    return 'LJ-0';
  }

  // SH 沙崙線 (臺南↔沙崙)
  if (lineId === 'SH') {
    if (odTrackId === 'SH-TN-SL') {
      return 'SH-0';  // 臺南→沙崙
    }
    if (odTrackId === 'SH-SL-TN') {
      return 'SH-1';  // 沙崙→臺南
    }
    return 'SH-0';
  }

  // JJ 集集線 (二水↔車埕)
  if (lineId === 'JJ') {
    if (odTrackId === 'JJ-ES-CT') {
      return 'JJ-0';  // 二水→車埕
    }
    if (odTrackId === 'JJ-CT-ES') {
      return 'JJ-1';  // 車埕→二水
    }
    return 'JJ-0';
  }

  // CZ 成追線 (成功↔追分)
  if (lineId === 'CZ') {
    if (odTrackId === 'CZ-CG-ZF') {
      return 'CZ-0';  // 成功→追分
    }
    if (odTrackId === 'CZ-ZF-CG') {
      return 'CZ-1';  // 追分→成功
    }
    return 'CZ-0';
  }

  // PX 平溪線 (三貂嶺↔菁桐)
  if (lineId === 'PX') {
    if (odTrackId === 'PX-SD-JT') {
      return 'PX-0';  // 三貂嶺→菁桐
    }
    if (odTrackId === 'PX-JT-SD') {
      return 'PX-1';  // 菁桐→三貂嶺
    }
    return 'PX-0';
  }

  // 預設：使用舊邏輯
  const mainStations: Record<string, string> = {
    'NW': 'HC',  // 新竹
    'LJ': 'HC',  // 新竹
    'SH': 'TN',  // 臺南
    'PX': 'SD',  // 三貂嶺
    'JJ': 'ES',  // 二水
    'CZ': 'CG',  // 成功
  };

  const mainStation = mainStations[lineId] || 'HC';
  const direction = dest === mainStation ? '0' : '1';

  return `${lineId}-${direction}`;
}

export class TraTrainEngine {
  private schedules: Map<string, TraSchedule>;
  private odTracks: Map<string, TraTrack>;
  private stationProgress: TraStationProgressMap;
  private activeTrains: Map<string, TraTrain> = new Map();

  constructor(options: TraTrainEngineOptions) {
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
  update(currentTimeSeconds: number): TraTrain[] {
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

        const train: TraTrain = {
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
  getActiveTrains(): TraTrain[] {
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
