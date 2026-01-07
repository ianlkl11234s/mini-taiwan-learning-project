/**
 * useAllTrains - 整合所有運輸系統列車資料
 * 將各系統的 Train 物件轉換為統一的 TrainFeature 格式
 */

import { useMemo } from 'react';
import type { Train } from '../engines/TrainEngine';
import type { TraTrain } from '../engines/TraTrainEngine';
import type { TrainFeature, TransportSystem, TrainStatus } from '../types/trainFeature';

// MRT (TRTC) 顏色
import { getLineIdFromTrackId, getTrainColor, getDirectionFromTrackId } from '../constants/lineInfo';

// THSR 顏色
import { getThsrDirection, getThsrTrainColor } from '../constants/thsrInfo';

// KRTC 顏色
import { getKrtcLineId, getKrtcDirection, getKrtcTrainColor } from '../constants/krtcInfo';

// KLRT 顏色
import { getKlrtLineId, getKlrtDirection, getKlrtTrainColor } from '../constants/klrtInfo';

// TMRT 顏色
import { getTmrtLineId, getTmrtDirection, getTmrtTrainColor } from '../constants/tmrtInfo';

// TRA 顏色
import { getTraLineId, getTraDirection, getTraTrainColor } from '../constants/traInfo';

// 通用列車介面（各系統共用的欄位）
interface BaseTrain {
  trainId: string;
  trackId: string;
  position: [number, number];
  status: string;
}

// THSR 列車（使用與 Train 相同結構但來自不同引擎）
export type ThsrTrain = Train;

// KRTC 列車
export type KrtcTrain = Train;

// KLRT 列車
export type KlrtTrain = Train;

// TMRT 列車
export type TmrtTrain = Train;

export interface AllTrainsInput {
  filteredTrains: Train[];
  filteredThsrTrains: ThsrTrain[];
  filteredKrtcTrains: KrtcTrain[];
  filteredKlrtTrains: KlrtTrain[];
  filteredTmrtTrains: TmrtTrain[];
  filteredTraTrains: TraTrain[];
  selectedTrainId: string | null;
}

/**
 * 將所有運輸系統的列車轉換為 TrainFeature 陣列
 */
export function useAllTrains(input: AllTrainsInput): TrainFeature[] {
  const {
    filteredTrains,
    filteredThsrTrains,
    filteredKrtcTrains,
    filteredKlrtTrains,
    filteredTmrtTrains,
    filteredTraTrains,
    selectedTrainId,
  } = input;

  return useMemo(() => {
    const features: TrainFeature[] = [];

    // === MRT (TRTC) ===
    for (const train of filteredTrains) {
      const lineId = getLineIdFromTrackId(train.trackId);
      const direction = parseInt(getDirectionFromTrackId(train.trackId), 10);
      const isColliding = train.isColliding ?? false;
      const color = isColliding ? '#ffcc00' : getTrainColor(train.trackId);

      features.push(
        createFeature(train, 'trtc', selectedTrainId, {
          lineId,
          direction,
          color,
          isColliding,
        })
      );
    }

    // === THSR (高鐵) ===
    // 高鐵使用 DOM Markers 保持長方形外觀，不加入 WebGL Circle Layer
    void filteredThsrTrains;

    // === KRTC (高雄捷運) ===
    for (const train of filteredKrtcTrains) {
      const lineId = getKrtcLineId(train.trackId);
      const direction = parseInt(getKrtcDirection(train.trackId), 10);
      const color = getKrtcTrainColor(train.trackId);

      features.push(
        createFeature(train, 'krtc', selectedTrainId, {
          lineId,
          direction,
          color,
          isColliding: false,
        })
      );
    }

    // === KLRT (高雄輕軌) ===
    for (const train of filteredKlrtTrains) {
      const lineId = getKlrtLineId(train.trackId);
      const direction = parseInt(getKlrtDirection(train.trackId), 10);
      const color = getKlrtTrainColor(train.trackId);

      features.push(
        createFeature(train, 'klrt', selectedTrainId, {
          lineId,
          direction,
          color,
          isColliding: false,
        })
      );
    }

    // === TMRT (台中捷運) ===
    for (const train of filteredTmrtTrains) {
      const lineId = getTmrtLineId(train.trackId);
      const direction = parseInt(getTmrtDirection(train.trackId), 10);
      const color = getTmrtTrainColor(train.trackId);

      features.push(
        createFeature(train, 'tmrt', selectedTrainId, {
          lineId,
          direction,
          color,
          isColliding: false,
        })
      );
    }

    // === TRA (台鐵) ===
    for (const train of filteredTraTrains) {
      const lineId = getTraLineId(train.trackId);
      const direction = parseInt(getTraDirection(train.trackId), 10);
      const color = getTraTrainColor(train.trackId);

      features.push(
        createFeature(train, 'tra', selectedTrainId, {
          lineId,
          direction,
          color,
          isColliding: false,
        })
      );
    }

    return features;
  }, [
    filteredTrains,
    filteredThsrTrains,
    filteredKrtcTrains,
    filteredKlrtTrains,
    filteredTmrtTrains,
    filteredTraTrains,
    selectedTrainId,
  ]);
}

/**
 * 建立 TrainFeature 物件
 */
function createFeature(
  train: BaseTrain,
  system: TransportSystem,
  selectedTrainId: string | null,
  extra: {
    lineId: string;
    direction: number;
    color: string;
    isColliding: boolean;
  }
): TrainFeature {
  return {
    type: 'Feature',
    properties: {
      trainId: train.trainId,
      trackId: train.trackId,
      system,
      lineId: extra.lineId,
      direction: extra.direction,
      status: normalizeStatus(train.status),
      isSelected: train.trainId === selectedTrainId,
      isColliding: extra.isColliding,
      color: extra.color,
    },
    geometry: {
      type: 'Point',
      coordinates: train.position,
    },
  };
}

/**
 * 正規化列車狀態
 */
function normalizeStatus(status: string): TrainStatus {
  switch (status) {
    case 'waiting':
    case 'running':
    case 'stopped':
    case 'arrived':
      return status;
    default:
      return 'running';
  }
}
