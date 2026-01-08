/**
 * 台灣鐵路路線資訊對照表
 */

// 路線名稱
export const TRA_LINE_NAMES: Record<string, string> = {
  SH: '沙崙線',
  WL: '西部幹線',
  NW: '內灣線',
  LJ: '六家線',
  PX: '平溪線',
  JJ: '集集線',
  CZ: '成追線',
};

// 方向名稱（依線路區分）
export const TRA_DIRECTION_NAMES: Record<string, Record<string, string>> = {
  SH: {
    '0': '往臺南',
    '1': '往沙崙',
  },
  WL: {
    '0': '北上',
    '1': '南下',
  },
  NW: {
    '0': '往新竹',
    '1': '往內灣',
  },
  LJ: {
    '0': '往新竹',
    '1': '往六家',
  },
  PX: {
    '0': '往三貂嶺',
    '1': '往菁桐',
  },
  JJ: {
    '0': '往二水',
    '1': '往車埕',
  },
  CZ: {
    '0': '往追分',
    '1': '往成功',
  },
};

// 台鐵主色調（藍色系）
export const TRA_PRIMARY_COLOR = '#0066b3';
export const TRA_SECONDARY_COLOR = '#4d9ed6';

// 軌道顏色（依線路區分）
export const TRA_TRACK_COLORS: Record<string, string> = {
  SH: '#0066b3', // 沙崙線 - 藍色
  WL: '#1e90ff', // 西部幹線 - 道奇藍
  NW: '#8b4513', // 內灣線 - 褐色
  LJ: '#228b22', // 六家線 - 森林綠
  PX: '#ff6347', // 平溪線 - 番茄紅
  JJ: '#9932cc', // 集集線 - 深蘭花紫
  CZ: '#ffa500', // 成追線 - 橙色
};

// 列車顏色（依線路和方向區分）
export const TRA_TRAIN_COLORS: Record<string, string> = {
  'SH-0': '#0066b3', // 沙崙 → 臺南 - 深藍
  'SH-1': '#4d9ed6', // 臺南 → 沙崙 - 淺藍
  'WL-0': '#1e90ff', // 北上 - 道奇藍
  'WL-1': '#00bfff', // 南下 - 天藍
  'NW-0': '#8b4513', // 往新竹 - 褐色
  'NW-1': '#cd853f', // 往內灣 - 祕魯褐
  'LJ-0': '#228b22', // 往新竹 - 森林綠
  'LJ-1': '#32cd32', // 往六家 - 萊姆綠
  'PX-0': '#ff6347', // 往三貂嶺 - 番茄紅
  'PX-1': '#ff7f50', // 往菁桐 - 珊瑚色
  'JJ-0': '#9932cc', // 往二水 - 深蘭花紫
  'JJ-1': '#ba55d3', // 往車埕 - 中蘭花紫
  'CZ-0': '#ffa500', // 往追分 - 橙色
  'CZ-1': '#ff8c00', // 往成功 - 深橙色
};

// 3D 渲染用顏色
export const TRA_COLOR_3D = 0x0066b3;

// 車站對照表（StationID -> 站名）
export const TRA_STATION_NAMES: Record<string, string> = {
  // 沙崙線
  '4271': '長榮大學',
  '4272': '沙崙',
  // 西部幹線 (基隆-屏東)
  '0900': '基隆',
  '0910': '三坑',
  '0920': '八堵',
  '0930': '七堵',
  '0940': '百福',
  '0950': '五堵',
  '0960': '汐止',
  '0970': '汐科',
  '0980': '南港',
  '0990': '松山',
  '1000': '臺北',
  '1001': '臺北-環島',
  '1010': '萬華',
  '1020': '板橋',
  '1030': '浮洲',
  '1040': '樹林',
  '1050': '南樹林',
  '1060': '山佳',
  '1070': '鶯歌',
  '1075': '鳳鳴',
  '1080': '桃園',
  '1090': '內壢',
  '1100': '中壢',
  '1110': '埔心',
  '1120': '楊梅',
  '1130': '富岡',
  '1140': '新富',
  '1150': '北湖',
  '1160': '湖口',
  '1170': '新豐',
  '1180': '竹北',
  '1190': '北新竹',
  '1191': '千甲',
  '1192': '新莊',
  '1193': '竹中',
  '1194': '六家',
  '1197': '上員',
  '1198': '榮華',
  '1199': '橫山',
  '1200': '九讚頭',
  '1201': '合興',
  '1202': '富貴',
  '1203': '竹東',
  '1208': '內灣',
  '1210': '新竹',
  // 平溪線
  '7330': '三貂嶺',
  '7331': '大華',
  '7332': '十分',
  '7333': '望古',
  '7334': '嶺腳',
  '7335': '平溪',
  '7336': '菁桐',
  // 集集線 (3430 二水已在西部幹線定義)
  '3431': '源泉',
  // 成追線 (3350 成功已在西部幹線定義)
  '2260': '追分',
  '3432': '濁水',
  '3433': '龍泉',
  '3434': '集集',
  '3435': '水里',
  '3436': '車埕',
  '1220': '三姓橋',
  '1230': '香山',
  '1240': '崎頂',
  '1250': '竹南',
  '3140': '造橋',
  '3150': '豐富',
  '3160': '苗栗',
  '3170': '南勢',
  '3180': '銅鑼',
  '3190': '三義',
  '3210': '泰安',
  '3220': '后里',
  '3230': '豐原',
  '3240': '栗林',
  '3250': '潭子',
  '3260': '頭家厝',
  '3270': '松竹',
  '3280': '太原',
  '3290': '精武',
  '3300': '臺中',
  '3310': '五權',
  '3320': '大慶',
  '3330': '烏日',
  '3340': '新烏日',
  '3350': '成功',
  '3360': '彰化',
  '3370': '花壇',
  '3380': '大村',
  '3390': '員林',
  '3400': '永靖',
  '3410': '社頭',
  '3420': '田中',
  '3430': '二水',
  '3450': '林內',
  '3460': '石榴',
  '3470': '斗六',
  '3480': '斗南',
  '3490': '石龜',
  '4050': '大林',
  '4060': '民雄',
  '4070': '嘉北',
  '4080': '嘉義',
  '4090': '水上',
  '4100': '南靖',
  '4110': '後壁',
  '4120': '新營',
  '4130': '柳營',
  '4140': '林鳳營',
  '4150': '隆田',
  '4160': '拔林',
  '4170': '善化',
  '4180': '南科',
  '4190': '新市',
  '4200': '永康',
  '4210': '大橋',
  '4220': '臺南',
  '4250': '保安',
  '4260': '仁德',
  '4270': '中洲',
  '4290': '大湖',
  '4300': '路竹',
  '4310': '岡山',
  '4320': '橋頭',
  '4330': '楠梓',
  '4340': '新左營',
  '4350': '左營',
  '4360': '內惟',
  '4370': '美術館',
  '4380': '鼓山',
  '4390': '三塊厝',
  '4400': '高雄',
  '4410': '民族',
  '4420': '科工館',
  '4430': '正義',
  '4440': '鳳山',
  '4450': '後庄',
  '4460': '九曲堂',
  '4470': '六塊厝',
  '5000': '屏東',
};

/**
 * 從 trackId 取得線路 ID
 * @example "SH-0" -> "SH"
 */
export function getTraLineId(trackId: string): string {
  return trackId.split('-')[0];
}

/**
 * 從 trackId 取得方向
 * @example "SH-0" -> "0"
 */
export function getTraDirection(trackId: string): string {
  return trackId.split('-')[1] || '0';
}

/**
 * 取得方向名稱
 */
export function getTraDirectionName(trackId: string): string {
  const lineId = getTraLineId(trackId);
  const direction = getTraDirection(trackId);
  return TRA_DIRECTION_NAMES[lineId]?.[direction] || '未知方向';
}

/**
 * 取得列車顏色
 */
export function getTraTrainColor(trackId: string): string {
  return TRA_TRAIN_COLORS[trackId] || TRA_PRIMARY_COLOR;
}

/**
 * 取得車站名稱
 */
export function getTraStationName(stationId: string): string {
  return TRA_STATION_NAMES[stationId] || stationId;
}

/**
 * 取得線路名稱（含方向）
 */
export function getTraLineName(trackId: string): string {
  const lineId = getTraLineId(trackId);
  const lineName = TRA_LINE_NAMES[lineId] || '台鐵';
  const directionName = getTraDirectionName(trackId);
  return `${lineName} (${directionName})`;
}

/**
 * 取得軌道顏色
 */
export function getTraTrackColor(trackId: string): string {
  const lineId = getTraLineId(trackId);
  return TRA_TRACK_COLORS[lineId] || TRA_PRIMARY_COLOR;
}
