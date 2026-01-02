/**
 * 路線資訊對照表
 * 用於列車資訊面板顯示
 */

// 路線 ID → 路線名稱
export const LINE_NAMES: Record<string, string> = {
  R: '淡水信義線',
  BL: '板南線',
  G: '松山新店線',
  O: '中和新蘆線',
  BR: '文湖線',
  K: '安坑輕軌',
  V: '淡海輕軌',
  A: '桃園機場捷運',
  Y: '環狀線',
  MK: '貓空纜車',
};

// 路線 ID + 方向 → 方向名稱
export const DIRECTION_NAMES: Record<string, Record<string, string>> = {
  R: {
    '0': '往淡水',
    '1': '往象山',
  },
  BL: {
    '0': '往南港展覽館',
    '1': '往頂埔',
  },
  G: {
    '0': '往松山',
    '1': '往新店',
  },
  O: {
    '0': '往南勢角',
    '1': '往迴龍/蘆洲',
  },
  BR: {
    '0': '往南港展覽館',
    '1': '往動物園',
  },
  K: {
    '0': '往十四張',
    '1': '往雙城',
  },
  V: {
    '0': '往崁頂/台北海洋大學',
    '1': '往紅樹林/淡水漁人碼頭',
  },
  A: {
    '0': '往機場/老街溪',
    '1': '往台北車站',
  },
  Y: {
    '0': '往新北產業園區',
    '1': '往大坪林',
  },
  MK: {
    '0': '往貓空',
    '1': '往動物園',
  },
};

// 路線顏色（用於資訊面板）
export const LINE_COLORS: Record<string, string> = {
  R: '#d90023',
  BL: '#0070c0',
  G: '#008659',
  O: '#f8b61c',
  BR: '#c48c31',
  K: '#8cc540',
  V: '#a4ce4e',
  A: '#8246af',
  Y: '#fedb00',
  MK: '#06b8e6',  // 貓空纜車藍
};

// 軌道顏色（用於地圖圖層，包含支線）
export const TRACK_COLORS: Record<string, string> = {
  R: '#d90023',   // 紅線
  BL: '#0070c0',  // 藍線
  G: '#008659',   // 綠線
  G3: '#66c4a0',  // 小碧潭支線（淺綠色）
  O: '#f8b61c',   // 橘線
  V: '#a4ce4e',   // 淡海輕軌
  BR: '#c48c31',  // 文湖線（棕色）
  K: '#8cc540',   // 安坑輕軌（草綠色）
  A: '#8246af',   // 機場捷運（紫色）
  Y: '#fedb00',   // 環狀線（黃色）
  MK: '#06b8e6',  // 貓空纜車（藍色）
};

// 列車顏色（依路線與方向區分，用於 2D markers）
export const TRAIN_COLORS: Record<string, string> = {
  // 紅線
  R_0: '#d90023',   // 往淡水（北上/direction 0）- 深紅色
  R_1: '#ff8a8a',   // 往象山（南下/direction 1）- 淡紅色
  // 藍線
  BL_0: '#0070c0',  // 往南港展覽館（往東/direction 0）- 深藍色
  BL_1: '#80bfff',  // 往頂埔（往西/direction 1）- 淡藍色
  // 綠線
  G_0: '#008659',   // 往新店（南下/direction 0）- 深綠色
  G_1: '#66c4a0',   // 往松山（北上/direction 1）- 淡綠色
  // 橘線
  O_0: '#f8b61c',   // 往南勢角（direction 0）- 深橘色
  O_1: '#ffd966',   // 往迴龍/蘆洲（direction 1）- 淡橘色
  // 文湖線
  BR_0: '#c48c31',  // 往南港展覽館（direction 0）- 深棕色
  BR_1: '#d4a65a',  // 往動物園（direction 1）- 淡棕色
  // 安坑輕軌
  K_0: '#8cc540',   // 往十四張（direction 0）- 深草綠色
  K_1: '#b8e080',   // 往雙城（direction 1）- 淡草綠色
  // 淡海輕軌
  V_0: '#a4ce4e',   // 綠山線/藍海線 往崁頂/台北海洋大學（direction 0）- 深黃綠色
  V_1: '#c8e588',   // 綠山線/藍海線 往紅樹林/淡水漁人碼頭（direction 1）- 淡黃綠色
  // 機場捷運
  A_0: '#67378b',   // 去程（往機場/老街溪）- 深紫色
  A_1: '#a778c9',   // 回程（往台北）- 淡紫色
  // 環狀線
  Y_0: '#fedb00',   // 去程（往新北產業園區）- 黃色
  Y_1: '#ffe566',   // 回程（往大坪林）- 淡黃色
  // 貓空纜車
  MK_0: '#06b8e6',  // 往貓空（direction 0）- 淡藍色
  MK_1: '#7dd4f0',  // 往動物園（direction 1）- 更淡藍色
};

// 3D 渲染用顏色（THREE.js 0x 格式）
export const LINE_COLORS_3D: Record<string, number> = {
  R: 0xd90023,   // 紅線
  BL: 0x0070c0,  // 藍線
  G: 0x008659,   // 綠線
  O: 0xf8b61c,   // 橘線
  BR: 0xc48c31,  // 文湖線
  K: 0x8cc540,   // 安坑輕軌
  V: 0xa4ce4e,   // 淡海輕軌
  A: 0x8246af,   // 機場捷運
  Y: 0xfedb00,   // 環狀線
  MK: 0x06b8e6,  // 貓空纜車
};

/**
 * 從 trackId 取得路線 ID
 * 例如：R-1-0 → R, BL-2-1 → BL
 */
export function getLineIdFromTrackId(trackId: string): string {
  if (trackId.startsWith('MK')) return 'MK';
  if (trackId.startsWith('K')) return 'K';
  if (trackId.startsWith('V')) return 'V';
  if (trackId.startsWith('BR')) return 'BR';
  if (trackId.startsWith('BL')) return 'BL';
  if (trackId.startsWith('G')) return 'G';
  if (trackId.startsWith('O')) return 'O';
  if (trackId.startsWith('A')) return 'A';
  if (trackId.startsWith('Y')) return 'Y';
  return 'R';
}

/**
 * 從 trackId 取得方向 (0 或 1)
 * 例如：R-1-0 → 0, BL-2-1 → 1
 */
export function getDirectionFromTrackId(trackId: string): string {
  return trackId.endsWith('-0') ? '0' : '1';
}

/**
 * 取得路線名稱
 */
export function getLineName(trackId: string): string {
  const lineId = getLineIdFromTrackId(trackId);
  return LINE_NAMES[lineId] || '未知路線';
}

/**
 * 取得方向名稱
 */
export function getDirectionName(trackId: string): string {
  const lineId = getLineIdFromTrackId(trackId);
  const direction = getDirectionFromTrackId(trackId);
  return DIRECTION_NAMES[lineId]?.[direction] || '未知方向';
}

/**
 * 取得路線顏色
 */
export function getLineColor(trackId: string): string {
  const lineId = getLineIdFromTrackId(trackId);
  return LINE_COLORS[lineId] || '#888888';
}

/**
 * 根據 trackId 取得列車顏色（依方向區分）
 */
export function getTrainColor(trackId: string): string {
  const lineId = getLineIdFromTrackId(trackId);
  const direction = getDirectionFromTrackId(trackId);
  const key = `${lineId}_${direction}`;
  return TRAIN_COLORS[key] || '#888888';
}

/**
 * 根據 lineId 取得 3D 渲染用顏色
 */
export function getLineColor3D(lineId: string): number {
  return LINE_COLORS_3D[lineId] || 0x888888;
}
