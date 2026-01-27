/**
 * 台鐵車種定義
 * 用於 3D 渲染時區分不同車種的顏色
 */

export interface TrainTypeInfo {
  name: string;
  color: string;
  color3D: number;
  priority: number; // 數字越小越優先（用於排序）
}

/**
 * 車種代碼對照表
 */
export const TRA_TRAIN_TYPES: Record<string, TrainTypeInfo> = {
  // 傾斜式列車 - 紅色系
  PP: {
    name: '普悠瑪',
    color: '#E53935',
    color3D: 0xe53935,
    priority: 1,
  },
  TZ: {
    name: '太魯閣',
    color: '#E53935',
    color3D: 0xe53935,
    priority: 1,
  },
  // EMU3000 - 橘色
  TC: {
    name: '自強(3000)',
    color: '#FF6B00',
    color3D: 0xff6b00,
    priority: 2,
  },
  // 推拉式自強 - 深橘色
  'TC-PP': {
    name: '自強(推拉式)',
    color: '#E65100',
    color3D: 0xe65100,
    priority: 3,
  },
  // DMU3100 柴聯自強 - 琥珀色
  'TC-DMU': {
    name: '自強(柴聯)',
    color: '#FF8F00',
    color3D: 0xff8f00,
    priority: 3,
  },
  // 莒光號 - 紫色
  CG: {
    name: '莒光',
    color: '#7B1FA2',
    color3D: 0x7b1fa2,
    priority: 4,
  },
  // 區間快 - 深藍
  CK: {
    name: '區間快',
    color: '#1976D2',
    color3D: 0x1976d2,
    priority: 5,
  },
  // 區間車 - 淺藍
  LC: {
    name: '區間',
    color: '#42A5F5',
    color3D: 0x42a5f5,
    priority: 6,
  },
  // 其他 - 灰色
  OTHER: {
    name: '其他',
    color: '#9E9E9E',
    color3D: 0x9e9e9e,
    priority: 99,
  },
};

/**
 * TDX 車種名稱 → 車種代碼對照表
 */
export const TDX_TRAIN_TYPE_MAPPING: Record<string, string> = {
  // 傾斜式
  '普悠瑪(普悠瑪)': 'PP',
  '太魯閣(太魯閣)': 'TZ',
  // EMU3000
  '自強(3000)(EMU3000 型電車)': 'TC',
  // 推拉式自強
  '自強(推拉式自強號且無自行車車廂)': 'TC-PP',
  '自強(推拉式自強號且有自行車車廂)': 'TC-PP',
  // DMU3100 柴聯
  '自強(DMU3100 型柴聯)': 'TC-DMU',
  // 莒光
  '莒光(有身障座位)': 'CG',
  '莒光(無身障座位)': 'CG',
  // 區間
  '區間快': 'CK',
  '區間': 'LC',
};

/**
 * 從 TDX 車種名稱取得車種代碼
 */
export function getTrainTypeCode(tdxTrainTypeName: string): string {
  return TDX_TRAIN_TYPE_MAPPING[tdxTrainTypeName] || 'OTHER';
}

/**
 * 從車種代碼取得車種資訊
 */
export function getTrainTypeInfo(typeCode: string): TrainTypeInfo {
  return TRA_TRAIN_TYPES[typeCode] || TRA_TRAIN_TYPES.OTHER;
}

/**
 * 從車種代碼取得顏色（hex string）
 */
export function getTrainTypeColor(typeCode: string): string {
  return getTrainTypeInfo(typeCode).color;
}

/**
 * 從車種代碼取得 3D 渲染用顏色
 */
export function getTrainType3DColor(typeCode: string): number {
  return getTrainTypeInfo(typeCode).color3D;
}
