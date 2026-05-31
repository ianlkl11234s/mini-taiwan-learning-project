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

// KRTC 顏色
import { getKrtcLineId, getKrtcDirection, getKrtcTrainColor } from '../constants/krtcInfo';

// KLRT 顏色
import { getKlrtLineId, getKlrtDirection, getKlrtTrainColor } from '../constants/klrtInfo';

// TMRT 顏色
import { getTmrtLineId, getTmrtDirection, getTmrtTrainColor } from '../constants/tmrtInfo';

// TRA 使用 DOM Markers，不需要在這裡匯入顏色函數

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
  selectedTrainUid: string | null;
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
    selectedTrainUid,
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
        createFeature(train, 'trtc', selectedTrainUid, {
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
        createFeature(train, 'krtc', selectedTrainUid, {
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
        createFeature(train, 'klrt', selectedTrainUid, {
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
        createFeature(train, 'tmrt', selectedTrainUid, {
          lineId,
          direction,
          color,
          isColliding: false,
        })
      );
    }

    // === TRA (台鐵) ===
    // 台鐵使用 DOM Markers 保持圓角正方形外觀，不加入 WebGL Circle Layer
    void filteredTraTrains;

    return features;
  }, [
    filteredTrains,
    filteredThsrTrains,
    filteredKrtcTrains,
    filteredKlrtTrains,
    filteredTmrtTrains,
    filteredTraTrains,
    selectedTrainUid,
  ]);
}

function getTrainUid(train: BaseTrain): string {
  return `${train.trackId}::${train.trainId}`;
}

/**
 * 建立 TrainFeature 物件
 */
function createFeature(
  train: BaseTrain,
  system: TransportSystem,
  selectedTrainUid: string | null,
  extra: {
    lineId: string;
    direction: number;
    color: string;
    isColliding: boolean;
  }
): TrainFeature {
  const trainUid = getTrainUid(train);
  return {
    type: 'Feature',
    properties: {
      trainId: train.trainId,
      trainUid,
      trackId: train.trackId,
      system,
      lineId: extra.lineId,
      direction: extra.direction,
      status: normalizeStatus(train.status),
      isSelected: trainUid === selectedTrainUid,
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
