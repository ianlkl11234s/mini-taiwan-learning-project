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
  YL: '宜蘭線',
  BH: '北迴線',
  TL: '臺東線',
  SK: '南迴線',
  PT: '屏東線',
  SA: '深澳線',
  OD: '台鐵',      // O-D 軌道
  BB: '台鐵',      // 合併軌道
  SP: '台鐵',      // 跨線軌道
};

// 方向名稱（依線路區分）
export const TRA_DIRECTION_NAMES: Record<string, Record<string, string>> = {
  SH: {
    '0': '往沙崙',
    '1': '往臺南',
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
  YL: {
    '0': '往蘇澳',
    '1': '往臺北',
  },
  BH: {
    '0': '往花蓮',
    '1': '往蘇澳新',
  },
  TL: {
    '0': '往臺東',
    '1': '往花蓮',
  },
  SK: {
    '0': '往新左營',
    '1': '往臺東',
  },
  PT: {
    '0': '往枋寮',
    '1': '往新左營',
  },
  SA: {
    '0': '往八斗子',
    '1': '往瑞芳',
  },
  // O-D/BB/SP 軌道不顯示方向
  OD: {},
  BB: {},
  SP: {},
};

// 台鐵主色調（統一灰色）
export const TRA_PRIMARY_COLOR = '#7B7B7B';
export const TRA_SECONDARY_COLOR = '#7B7B7B';

// 軌道顏色（統一灰色）
export const TRA_TRACK_COLORS: Record<string, string> = {
  SH: '#7B7B7B', // 沙崙線
  WL: '#7B7B7B', // 西部幹線
  NW: '#7B7B7B', // 內灣線
  LJ: '#7B7B7B', // 六家線
  PX: '#7B7B7B', // 平溪線
  JJ: '#7B7B7B', // 集集線
  CZ: '#7B7B7B', // 成追線
  YL: '#7B7B7B', // 宜蘭線
  BH: '#7B7B7B', // 北迴線
  TL: '#7B7B7B', // 臺東線
  SK: '#7B7B7B', // 南迴線
  PT: '#7B7B7B', // 屏東線
  SA: '#7B7B7B', // 深澳線
  OD: '#7B7B7B', // O-D 軌道
  BB: '#7B7B7B', // 合併軌道
  SP: '#7B7B7B', // 跨線軌道
};

// 列車顏色（統一灰色）
export const TRA_TRAIN_COLORS: Record<string, string> = {
  'SH-0': '#7B7B7B',
  'SH-1': '#7B7B7B',
  'WL-0': '#7B7B7B',
  'WL-1': '#7B7B7B',
  'NW-0': '#7B7B7B',
  'NW-1': '#7B7B7B',
  'LJ-0': '#7B7B7B',
  'LJ-1': '#7B7B7B',
  'PX-0': '#7B7B7B',
  'PX-1': '#7B7B7B',
  'JJ-0': '#7B7B7B',
  'JJ-1': '#7B7B7B',
  'CZ-0': '#7B7B7B',
  'CZ-1': '#7B7B7B',
  'YL-0': '#7B7B7B',
  'YL-1': '#7B7B7B',
  'BH-0': '#7B7B7B',
  'BH-1': '#7B7B7B',
  'TL-0': '#7B7B7B',
  'TL-1': '#7B7B7B',
};

// 3D 渲染用顏色
export const TRA_COLOR_3D = 0x7B7B7B;

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
  // 宜蘭線 (八堵→蘇澳)
  '7390': '暖暖',
  '7380': '四腳亭',
  '7360': '瑞芳',
  '7350': '猴硐',
  '7330': '三貂嶺',  // 平溪線分岔點
  '7320': '牡丹',
  '7310': '雙溪',
  '7300': '貢寮',
  '7290': '福隆',
  '7280': '石城',
  '7270': '大里',
  '7260': '大溪',
  '7250': '龜山',
  '7240': '外澳',
  '7230': '頭城',
  '7220': '頂埔',
  '7210': '礁溪',
  '7200': '四城',
  '7190': '宜蘭',
  '7180': '二結',
  '7170': '中里',
  '7160': '羅東',
  '7150': '冬山',
  '7140': '新馬',
  '7130': '蘇澳新',  // 北迴線分岔點
  '7120': '蘇澳',
  // 北迴線 (蘇澳新→花蓮)
  '7110': '永樂',
  '7100': '東澳',
  '7090': '南澳',
  '7080': '武塔',
  '7070': '漢本',
  '7060': '和平',
  '7050': '和仁',
  '7040': '崇德',
  '7030': '新城',
  '7020': '景美',
  '7010': '北埔',
  '7000': '花蓮',
  // 臺東線 (花蓮→臺東)
  '6250': '吉安',
  '6240': '志學',
  '6230': '平和',
  '6220': '壽豐',
  '6210': '豐田',
  '6200': '林榮新光',
  '6190': '南平',
  '6180': '鳳林',
  '6170': '萬榮',
  '6160': '光復',
  '6150': '大富',
  '6140': '富源',
  '6130': '瑞穗',
  '6120': '三民',
  '6110': '玉里',
  '6100': '東里',
  '6090': '東竹',
  '6080': '富里',
  '6070': '池上',
  '6060': '海端',
  '6050': '關山',
  '6040': '瑞和',
  '6030': '瑞源',
  '6020': '鹿野',
  '6010': '山里',
  '6000': '臺東',
  // 平溪線
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
  '3325': '新烏日',
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
  // 屏東線 (屏東→枋寮)
  '5010': '歸來',
  '5020': '麟洛',
  '5030': '西勢',
  '5040': '竹田',
  '5050': '潮州',
  '5060': '崁頂',
  '5070': '南州',
  '5080': '鎮安',
  '5090': '林邊',
  '5100': '佳冬',
  '5110': '東海',
  '5120': '枋寮',
  // 南迴線 (枋寮→臺東)
  '5130': '加祿',
  '5140': '內獅',
  '5160': '枋山',
  '5170': '枋野',
  '5190': '大武',
  '5200': '瀧溪',
  '5210': '金崙',
  '5220': '太麻里',
  '5230': '知本',
  '5240': '康樂',
  // 海線 (竹南→彰化)
  '2110': '談文',
  '2120': '大山',
  '2130': '後龍',
  '2140': '龍港',
  '2150': '白沙屯',
  '2160': '新埔',
  '2170': '通霄',
  '2180': '苑裡',
  '2190': '日南',
  '2200': '大甲',
  '2210': '臺中港',
  '2220': '清水',
  '2230': '沙鹿',
  '2240': '龍井',
  '2250': '大肚',
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
 * @example "BH-SX-HL-0" -> "0"
 * @example "WL-M-ZN-CH-0" -> "0"
 * @example "PX-SD-JT" -> "1" (往菁桐)
 * @example "PX-JT-SD" -> "0" (往三貂嶺)
 */
export function getTraDirection(trackId: string): string {
  const parts = trackId.split('-');
  // 複雜格式：最後一個數字是方向
  const lastPart = parts[parts.length - 1];
  if (lastPart === '0' || lastPart === '1') {
    return lastPart;
  }

  // 平溪線特殊格式：PX-SD-JT / PX-JT-SD
  // SD = 三貂嶺, JT = 菁桐
  if (trackId.startsWith('PX-')) {
    if (trackId.endsWith('-JT')) return '1';  // 往菁桐
    if (trackId.endsWith('-SD')) return '0';  // 往三貂嶺
  }

  // 簡單格式：第二個部分是方向
  return parts[1] || '0';
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
/**
 * 根據起終站推斷路線名稱
 */
export function inferLineNameFromStations(originId: string, destId: string): string {
  const originNum = parseInt(originId, 10);
  const destNum = parseInt(destId, 10);

  // 花蓮/臺東線 (6000-7100)
  if ((originNum >= 6000 && originNum <= 7100) || (destNum >= 6000 && destNum <= 7100)) {
    // 只有起終點都在東部才顯示臺東/北迴線
    if (originNum >= 6000 && originNum <= 7130 && destNum >= 6000 && destNum <= 7130) {
      if (originNum >= 6000 && originNum < 7000) {
        return '臺東線';
      }
      return '北迴線';
    }
  }

  // 宜蘭線 (7130-7390)
  if ((originNum >= 7130 && originNum <= 7390) || (destNum >= 7130 && destNum <= 7390)) {
    // 只有起終點都在宜蘭線範圍才顯示宜蘭線
    if (originNum >= 7130 && originNum <= 7390 && destNum >= 7130 && destNum <= 7390) {
      return '宜蘭線';
    }
  }

  // 屏東線 (4340-5000+)
  if ((originNum >= 4340 && originNum <= 5100) || (destNum >= 4340 && destNum <= 5100)) {
    if (originNum >= 4340 && destNum >= 4340) {
      return '屏東線';
    }
  }

  // 預設西部幹線
  return '西部幹線';
}

export function getTraLineName(trackId: string): string {
  const lineId = getTraLineId(trackId);
  const lineName = TRA_LINE_NAMES[lineId] || '台鐵';
  // OD/BB/SP 軌道不顯示方向（方向已包含在 trackId 中）
  if (lineId === 'OD' || lineId === 'BB' || lineId === 'SP') {
    return lineName;
  }
  const directionName = getTraDirectionName(trackId);
  return `${lineName} (${directionName})`;
}

/**
 * 取得線路名稱（用於顯示）
 *
 * 由於台鐵跨線列車的路線判斷非常複雜（同一車次可能經過多條路線），
 * 且軌道分配也可能有誤，為避免顯示錯誤資訊，
 * 所有 O-D/BB/SP 軌道統一顯示為「台鐵」。
 */
export function getTraLineNameFromStations(trackId: string, _originId?: string, _destId?: string): string {
  const lineId = getTraLineId(trackId);

  // O-D/BB/SP 軌道：統一顯示「台鐵」
  // 原因：跨線列車無法準確判斷屬於哪條路線
  if (lineId === 'OD' || lineId === 'BB' || lineId === 'SP') {
    return '台鐵';
  }

  return getTraLineName(trackId);
}

/**
 * 取得軌道顏色
 */
export function getTraTrackColor(trackId: string): string {
  const lineId = getTraLineId(trackId);
  return TRA_TRACK_COLORS[lineId] || TRA_PRIMARY_COLOR;
}

/**
 * 根據車站 ID 判斷所屬路線名稱
 * 用於跨線列車動態顯示當前路線
 *
 * @added 2026-01-31 動態路線名稱功能
 */
export function getLineNameFromStationId(stationId: string): string {
  const id = parseInt(stationId, 10);
  if (isNaN(id)) return '台鐵';

  // 支線優先判斷（避免被幹線覆蓋）
  // 平溪線 (7331-7336)
  if (id >= 7331 && id <= 7336) return '平溪線';
  // 內灣線 (1197-1208)
  if (id >= 1197 && id <= 1208) return '內灣線';
  // 六家線 (1193-1194)
  if (id >= 1193 && id <= 1194) return '六家線';
  // 沙崙線 (4271-4272)
  if (id >= 4271 && id <= 4272) return '沙崙線';
  // 集集線 (3431-3436)
  if (id >= 3431 && id <= 3436) return '集集線';
  // 成追線 (2260 追分)
  if (id === 2260) return '成追線';
  // 深澳線 (略，目前無營運)

  // 幹線判斷
  // 南迴線 (5130-5240: 加祿→康樂)
  if (id >= 5130 && id <= 5240) return '南迴線';
  // 屏東線 (5000-5120: 屏東→枋寮)
  if (id >= 5000 && id <= 5120) return '屏東線';
  // 臺東線 (6000-6250: 臺東→吉安)
  if (id >= 6000 && id <= 6250) return '臺東線';
  // 北迴線 (7000-7110: 花蓮→永樂)
  if (id >= 7000 && id <= 7110) return '北迴線';
  // 宜蘭線 (7120-7390: 蘇澳→暖暖)
  if (id >= 7120 && id <= 7390) return '宜蘭線';
  // 海線 (2110-2250: 談文→大肚)
  if (id >= 2110 && id <= 2250) return '海線';
  // 山線 (3140-3220: 造橋→后里)
  if (id >= 3140 && id <= 3220) return '山線';

  // 西部幹線（預設）
  return '西部幹線';
}

/**
 * 判斷列車行進方向（北上/南下）
 *
 * 車站 ID 編號規則：
 * - 西部幹線、屏東線、南迴線、海線、山線：ID 遞增 = 南下
 *   (0900 基隆 → 5240 康樂)
 * - 宜蘭線、北迴線、臺東線：ID 遞減 = 南下
 *   (7390 暖暖 → 7120 蘇澳 → 7000 花蓮 → 6000 臺東)
 * - 東西向路線（成追線、集集線、內灣/六家線、沙崙線、平溪線）：不顯示方向
 *
 * @added 2026-01-31 動態路線名稱功能
 * @returns "北上" | "南下" | ""
 */
export function getTraDirectionFromStations(
  prevStationId: string | undefined,
  nextStationId: string | undefined,
  currentLineName: string
): string {
  // 東西向路線不顯示方向
  const eastWestLines = ['成追線', '集集線', '內灣線', '六家線', '沙崙線', '平溪線'];
  if (eastWestLines.includes(currentLineName)) {
    return '';
  }

  // 需要兩個站點才能判斷方向
  if (!prevStationId || !nextStationId) return '';

  const prevId = parseInt(prevStationId, 10);
  const nextId = parseInt(nextStationId, 10);
  if (isNaN(prevId) || isNaN(nextId)) return '';

  // 東部路線（宜蘭線、北迴線、臺東線）：ID 遞減 = 南下，ID 遞增 = 北上
  // 7390(暖暖) → 7120(蘇澳) → 7000(花蓮) → 6000(臺東)
  const eastLines = ['宜蘭線', '北迴線', '臺東線'];
  if (eastLines.includes(currentLineName)) {
    return nextId > prevId ? '北上' : '南下';
  }

  // 西部路線（西部幹線、屏東線、南迴線、海線、山線）：ID 遞增 = 南下，ID 遞減 = 北上
  // 0900(基隆) → 4220(臺南) → 5000(屏東) → 5240(康樂)
  return nextId > prevId ? '南下' : '北上';
}

/**
 * 取得動態路線名稱（根據當前車站位置）
 *
 * 用於跨線列車，根據當前所在位置顯示對應路線名稱
 * 例如：臺中→臺東 的列車在屏東線站點時顯示「屏東線 (南下)」
 *
 * @added 2026-01-31 動態路線名稱功能
 */
export function getTraDynamicLineName(
  prevStationId: string | undefined,
  nextStationId: string | undefined
): string {
  // 優先使用下一站判斷路線（更能反映列車即將到達的位置）
  const referenceStation = nextStationId || prevStationId;
  if (!referenceStation) return '台鐵';

  const lineName = getLineNameFromStationId(referenceStation);
  const direction = getTraDirectionFromStations(prevStationId, nextStationId, lineName);

  if (direction) {
    return `${lineName} (${direction})`;
  }
  return lineName;
}
