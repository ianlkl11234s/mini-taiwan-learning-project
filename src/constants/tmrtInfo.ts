/**
 * 台中捷運路線資訊對照表
 */

// 路線名稱
export const TMRT_LINE_NAMES: Record<string, string> = {
  G: '綠線',
};

// 方向名稱
export const TMRT_DIRECTION_NAMES: Record<string, Record<string, string>> = {
  G: {
    '0': '往高鐵台中站',
    '1': '往北屯總站',
  },
};

// 路線主色調
export const TMRT_LINE_COLORS: Record<string, string> = {
  G: '#0cab2c',  // 台中捷運綠
};

// 軌道顏色
export const TMRT_TRACK_COLORS: Record<string, string> = {
  G: '#0cab2c',  // 綠線
};

// 列車顏色（依路線與方向區分）
export const TMRT_TRAIN_COLORS: Record<string, string> = {
  G_0: '#0cab2c',  // 綠線 往高鐵台中站 - 深綠色
  G_1: '#4ddb75',  // 綠線 往北屯總站 - 淺綠色
};

// 3D 渲染用顏色
export const TMRT_LINE_COLORS_3D: Record<string, number> = {
  G: 0x0cab2c,  // 綠線
};

// 車站對照表（StationID -> 站名）
export const TMRT_STATION_NAMES: Record<string, string> = {
  G0: '北屯總站',
  G3: '舊社',
  G4: '松竹',
  G5: '四維國小',
  G6: '文心崇德',
  G7: '文心中清',
  G8: '文華高中',
  G8a: '文心櫻花',
  G9: '市政府',
  G10: '水安宮',
  G10a: '文心森林公園',
  G11: '南屯',
  G12: '豐樂公園',
  G13: '大慶',
  G14: '九張犁',
  G15: '九德',
  G16: '烏日',
  G17: '高鐵台中站',
};

/**
 * 從 trackId 取得線路 ID
 * 例如：TMRT-G-0 → G
 */
export function getTmrtLineId(trackId: string): string {
  const match = trackId.match(/TMRT-([A-Z])-/);
  return match ? match[1] : 'G';
}

/**
 * 從 trackId 取得方向
 * 例如：TMRT-G-0 → 0, TMRT-G-1 → 1
 */
export function getTmrtDirection(trackId: string): string {
  return trackId.endsWith('-0') ? '0' : '1';
}

/**
 * 取得線路名稱
 */
export function getTmrtLineName(trackId: string): string {
  const lineId = getTmrtLineId(trackId);
  const lineName = TMRT_LINE_NAMES[lineId] || '台中捷運';
  const direction = getTmrtDirection(trackId);
  const directionName = TMRT_DIRECTION_NAMES[lineId]?.[direction] || '';
  return `台中捷運${lineName}${directionName ? ` (${directionName})` : ''}`;
}

/**
 * 取得方向名稱
 */
export function getTmrtDirectionName(trackId: string): string {
  const lineId = getTmrtLineId(trackId);
  const direction = getTmrtDirection(trackId);
  return TMRT_DIRECTION_NAMES[lineId]?.[direction] || '未知方向';
}

/**
 * 取得線路顏色
 */
export function getTmrtLineColor(trackId: string): string {
  const lineId = getTmrtLineId(trackId);
  return TMRT_LINE_COLORS[lineId] || '#888888';
}

/**
 * 取得列車顏色（依方向區分）
 */
export function getTmrtTrainColor(trackId: string): string {
  const lineId = getTmrtLineId(trackId);
  const direction = getTmrtDirection(trackId);
  const key = `${lineId}_${direction}`;
  return TMRT_TRAIN_COLORS[key] || TMRT_LINE_COLORS[lineId] || '#888888';
}

/**
 * 取得車站名稱
 */
export function getTmrtStationName(stationId: string): string {
  return TMRT_STATION_NAMES[stationId] || stationId;
}

/**
 * 取得 3D 渲染用顏色
 */
export function getTmrtLineColor3D(trackId: string): number {
  const lineId = getTmrtLineId(trackId);
  return TMRT_LINE_COLORS_3D[lineId] || 0x888888;
}
