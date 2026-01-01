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
