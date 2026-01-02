/**
 * 高雄捷運路線資訊對照表
 */

// 路線名稱
export const KRTC_LINE_NAMES: Record<string, string> = {
  O: '橘線',
  R: '紅線',
};

// 方向名稱
export const KRTC_DIRECTION_NAMES: Record<string, Record<string, string>> = {
  O: {
    '0': '往大寮',
    '1': '往哈瑪星',
  },
  R: {
    '0': '往岡山車站',
    '1': '往小港',
  },
};

// 路線主色調
export const KRTC_LINE_COLORS: Record<string, string> = {
  O: '#f8981d',  // 橘線
  R: '#e2211c',  // 紅線
};

// 軌道顏色
export const KRTC_TRACK_COLORS: Record<string, string> = {
  O: '#f8981d',  // 橘線
  R: '#e2211c',  // 紅線
};

// 列車顏色（依路線與方向區分）
export const KRTC_TRAIN_COLORS: Record<string, string> = {
  O_0: '#f8981d',  // 橘線 往大寮 - 深橘色
  O_1: '#ffc266',  // 橘線 往哈瑪星 - 淺橘色
  R_0: '#e2211c',  // 紅線 往岡山 - 深紅色
  R_1: '#ff7a7a',  // 紅線 往小港 - 淺紅色
};

// 3D 渲染用顏色
export const KRTC_LINE_COLORS_3D: Record<string, number> = {
  O: 0xf8981d,  // 橘線
  R: 0xe2211c,  // 紅線
};

// 車站對照表（StationID -> 站名）
export const KRTC_STATION_NAMES: Record<string, string> = {
  // 橘線車站
  O1: '哈瑪星(西子灣)',
  O2: '鹽埕埔',
  O4: '美麗島',
  O5: '文化中心',
  O6: '五塊厝',
  O7: '技擊館',
  O8: '衛武營',
  O9: '鳳山西站',
  O10: '鳳山',
  O11: '大東',
  O12: '鳳山國中',
  O13: '大寮',
  O14: '林園',
  OT1: '大寮(終點)',
  // 紅線車站
  R3: '小港',
  R4: '高雄國際機場',
  R4A: '草衙',
  R5: '前鎮高中',
  R6: '凱旋',
  R7: '獅甲',
  R8: '三多商圈',
  R9: '中央公園',
  R10: '美麗島',
  R11: '高雄車站',
  R12: '後驛',
  R13: '凹子底',
  R14: '巨蛋',
  R15: '生態園區',
  R16: '左營',
  R17: '世運',
  R18: '油廠國小',
  R19: '楠梓加工區',
  R20: '後勁',
  R21: '都會公園',
  R22: '青埔',
  R22A: '橋頭糖廠',
  R23: '橋頭火車站',
  R24: '南岡山',
  RK1: '岡山車站',
};

/**
 * 從 trackId 取得線路 ID
 * 例如：KRTC-O-0 → O
 */
export function getKrtcLineId(trackId: string): string {
  const match = trackId.match(/KRTC-([OR])-/);
  return match ? match[1] : 'O';
}

/**
 * 從 trackId 取得方向
 * 例如：KRTC-O-0 → 0, KRTC-R-1 → 1
 */
export function getKrtcDirection(trackId: string): string {
  return trackId.endsWith('-0') ? '0' : '1';
}

/**
 * 取得線路名稱
 */
export function getKrtcLineName(trackId: string): string {
  const lineId = getKrtcLineId(trackId);
  const lineName = KRTC_LINE_NAMES[lineId] || '高雄捷運';
  const direction = getKrtcDirection(trackId);
  const directionName = KRTC_DIRECTION_NAMES[lineId]?.[direction] || '';
  return `高雄捷運${lineName}${directionName ? ` (${directionName})` : ''}`;
}

/**
 * 取得方向名稱
 */
export function getKrtcDirectionName(trackId: string): string {
  const lineId = getKrtcLineId(trackId);
  const direction = getKrtcDirection(trackId);
  return KRTC_DIRECTION_NAMES[lineId]?.[direction] || '未知方向';
}

/**
 * 取得線路顏色
 */
export function getKrtcLineColor(trackId: string): string {
  const lineId = getKrtcLineId(trackId);
  return KRTC_LINE_COLORS[lineId] || '#888888';
}

/**
 * 取得列車顏色（依方向區分）
 */
export function getKrtcTrainColor(trackId: string): string {
  const lineId = getKrtcLineId(trackId);
  const direction = getKrtcDirection(trackId);
  const key = `${lineId}_${direction}`;
  return KRTC_TRAIN_COLORS[key] || KRTC_LINE_COLORS[lineId] || '#888888';
}

/**
 * 取得車站名稱
 */
export function getKrtcStationName(stationId: string): string {
  return KRTC_STATION_NAMES[stationId] || stationId;
}

/**
 * 取得 3D 渲染用顏色
 */
export function getKrtcLineColor3D(trackId: string): number {
  const lineId = getKrtcLineId(trackId);
  return KRTC_LINE_COLORS_3D[lineId] || 0x888888;
}
