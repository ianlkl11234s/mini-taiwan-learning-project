/**
 * 高雄輕軌路線資訊對照表
 */

// 路線名稱
export const KLRT_LINE_NAMES: Record<string, string> = {
  C: '環狀線',
};

// 方向名稱
export const KLRT_DIRECTION_NAMES: Record<string, Record<string, string>> = {
  C: {
    '0': '順時針',
    '1': '逆時針',
  },
};

// 路線主色調
export const KLRT_LINE_COLORS: Record<string, string> = {
  C: '#99cc00',  // 輕軌綠色
};

// 軌道顏色
export const KLRT_TRACK_COLORS: Record<string, string> = {
  C: '#99cc00',  // 輕軌綠色
};

// 列車顏色（依路線與方向區分）
export const KLRT_TRAIN_COLORS: Record<string, string> = {
  C_0: '#99cc00',  // 環狀線 順時針 - 標準綠色
  C_1: '#ccff66',  // 環狀線 逆時針 - 淺綠色
};

// 3D 渲染用顏色
export const KLRT_LINE_COLORS_3D: Record<string, number> = {
  C: 0x99cc00,  // 輕軌綠色
};

// 車站對照表（StationID -> 站名）
export const KLRT_STATION_NAMES: Record<string, string> = {
  C1: '籬仔內',
  C2: '凱旋瑞田',
  C3: '前鎮之星',
  C4: '凱旋中華',
  C5: '夢時代',
  C6: '經貿園區',
  C7: '軟體園區',
  C8: '高雄展覽館',
  C9: '旅運中心',
  C10: '光榮碼頭',
  C11: '真愛碼頭',
  C12: '駁二大義',
  C13: '駁二蓬萊',
  C14: '哈瑪星',
  C15: '壽山公園',
  C16: '文武聖殿',
  C17: '鼓山區公所',
  C18: '鼓山',
  C19: '馬卡道',
  C20: '臺鐵美術館',
  C21A: '內惟藝術中心',
  C21: '美術館',
  C22: '聯合醫院',
  C23: '龍華國小',
  C24: '愛河之心',
  C25: '新上國小',
  C26: '大順民族',
  C27: '灣仔內',
  C28: '高雄高工',
  C29: '樹德家商',
  C30: '科工館',
  C31: '聖功醫院',
  C32: '凱旋公園',
  C33: '衛生局',
  C34: '五權國小',
  C35: '凱旋武昌',
  C36: '凱旋二聖',
  C37: '輕軌機廠',
};

/**
 * 從 trackId 取得線路 ID
 * 例如：KLRT-C-0 → C
 */
export function getKlrtLineId(trackId: string): string {
  const match = trackId.match(/KLRT-([C])-/);
  return match ? match[1] : 'C';
}

/**
 * 從 trackId 取得方向
 * 例如：KLRT-C-0 → 0, KLRT-C-1 → 1
 */
export function getKlrtDirection(trackId: string): string {
  return trackId.endsWith('-0') ? '0' : '1';
}

/**
 * 取得線路名稱
 */
export function getKlrtLineName(trackId: string): string {
  const lineId = getKlrtLineId(trackId);
  const lineName = KLRT_LINE_NAMES[lineId] || '高雄輕軌';
  const direction = getKlrtDirection(trackId);
  const directionName = KLRT_DIRECTION_NAMES[lineId]?.[direction] || '';
  return `高雄輕軌${lineName}${directionName ? ` (${directionName})` : ''}`;
}

/**
 * 取得方向名稱
 */
export function getKlrtDirectionName(trackId: string): string {
  const lineId = getKlrtLineId(trackId);
  const direction = getKlrtDirection(trackId);
  return KLRT_DIRECTION_NAMES[lineId]?.[direction] || '未知方向';
}

/**
 * 取得線路顏色
 */
export function getKlrtLineColor(trackId: string): string {
  const lineId = getKlrtLineId(trackId);
  return KLRT_LINE_COLORS[lineId] || '#99cc00';
}

/**
 * 取得列車顏色（依方向區分）
 */
export function getKlrtTrainColor(trackId: string): string {
  const lineId = getKlrtLineId(trackId);
  const direction = getKlrtDirection(trackId);
  const key = `${lineId}_${direction}`;
  return KLRT_TRAIN_COLORS[key] || KLRT_LINE_COLORS[lineId] || '#99cc00';
}

/**
 * 取得車站名稱
 */
export function getKlrtStationName(stationId: string): string {
  return KLRT_STATION_NAMES[stationId] || stationId;
}

/**
 * 取得 3D 渲染用顏色
 */
export function getKlrtLineColor3D(trackId: string): number {
  const lineId = getKlrtLineId(trackId);
  return KLRT_LINE_COLORS_3D[lineId] || 0x99cc00;
}
