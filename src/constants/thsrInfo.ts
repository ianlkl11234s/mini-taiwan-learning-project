/**
 * 台灣高鐵路線資訊對照表
 */

// 路線名稱
export const THSR_LINE_NAME = '台灣高鐵';

// 方向名稱
export const THSR_DIRECTION_NAMES: Record<string, string> = {
  '0': '往左營',
  '1': '往南港',
};

// 高鐵主色調（橘色系）
export const THSR_PRIMARY_COLOR = '#f47920';
export const THSR_SECONDARY_COLOR = '#ff9a4d';

// 軌道顏色
export const THSR_TRACK_COLOR = '#f47920';

// 列車顏色（依方向區分）
export const THSR_TRAIN_COLORS: Record<string, string> = {
  THSR_0: '#f47920', // 南下（往左營）- 深橘色
  THSR_1: '#ff9a4d', // 北上（往南港）- 淺橘色
};

// 3D 渲染用顏色
export const THSR_COLOR_3D = 0xf47920;

// 車站對照表（StationID -> 站名）
export const THSR_STATION_NAMES: Record<string, string> = {
  '0990': '南港',
  '1000': '台北',
  '1010': '板橋',
  '1020': '桃園',
  '1030': '新竹',
  '1035': '苗栗',
  '1040': '台中',
  '1043': '彰化',
  '1047': '雲林',
  '1050': '嘉義',
  '1060': '台南',
  '1070': '左營',
};

/**
 * 從 trackId 取得方向
 */
export function getThsrDirection(trackId: string): string {
  return trackId.endsWith('-0') ? '0' : '1';
}

/**
 * 取得方向名稱
 */
export function getThsrDirectionName(trackId: string): string {
  const direction = getThsrDirection(trackId);
  return THSR_DIRECTION_NAMES[direction] || '未知方向';
}

/**
 * 取得列車顏色
 */
export function getThsrTrainColor(trackId: string): string {
  const direction = getThsrDirection(trackId);
  return THSR_TRAIN_COLORS[`THSR_${direction}`] || THSR_PRIMARY_COLOR;
}

/**
 * 取得車站名稱
 */
export function getThsrStationName(stationId: string): string {
  return THSR_STATION_NAMES[stationId] || stationId;
}

/**
 * 取得線路名稱（含方向）
 */
export function getThsrLineName(trackId: string): string {
  const direction = getThsrDirection(trackId);
  const directionName = THSR_DIRECTION_NAMES[direction] || '';
  return `${THSR_LINE_NAME}${directionName ? ` (${directionName})` : ''}`;
}

/**
 * 取得線路顏色
 */
export function getThsrLineColor(trackId: string): string {
  return getThsrTrainColor(trackId);
}
