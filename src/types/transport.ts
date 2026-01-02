/**
 * 運具類型抽象定義
 *
 * 支援多種運具模式的統一介面
 * - MRT: 台北捷運系統
 * - THSR: 台灣高鐵
 * - TRA: 台鐵（未來擴充）
 * - LRT: 輕軌系統（安坑、淡海）
 * - KRTC: 高雄捷運
 * - TMRT: 台中捷運
 */

/**
 * 運具模式
 */
export type TransportMode = 'MRT' | 'THSR' | 'TRA' | 'LRT' | 'KRTC' | 'TMRT';

/**
 * 運具設定
 */
export interface TransportConfig {
  /** 運具識別碼 */
  id: TransportMode;
  /** 顯示名稱 */
  name: string;
  /** 資料目錄路徑 */
  dataPath: string;
  /** 是否啟用 3D 圖層 */
  enable3D: boolean;
  /** 是否支援跟隨模式 */
  enableFollow: boolean;
  /** 預設可見性 */
  defaultVisible: boolean;
}

/**
 * 運具狀態
 */
export interface TransportState {
  /** 是否可見 */
  visible: boolean;
  /** 是否載入中 */
  loading: boolean;
  /** 錯誤訊息 */
  error: string | null;
  /** 列車數量 */
  trainCount: number;
}

/**
 * 運具設定對照表
 */
export const TRANSPORT_CONFIGS: Record<TransportMode, TransportConfig> = {
  MRT: {
    id: 'MRT',
    name: '台北捷運',
    dataPath: '/data/trtc',
    enable3D: true,
    enableFollow: true,
    defaultVisible: true,
  },
  THSR: {
    id: 'THSR',
    name: '台灣高鐵',
    dataPath: '/data/thsr',
    enable3D: true,
    enableFollow: true,
    defaultVisible: true,
  },
  TRA: {
    id: 'TRA',
    name: '台灣鐵路',
    dataPath: '/data/tra',
    enable3D: true,
    enableFollow: true,
    defaultVisible: false,
  },
  LRT: {
    id: 'LRT',
    name: '輕軌系統',
    dataPath: '/data/trtc',
    enable3D: true,
    enableFollow: true,
    defaultVisible: true,
  },
  KRTC: {
    id: 'KRTC',
    name: '高雄捷運',
    dataPath: '/data-krtc',
    enable3D: true,
    enableFollow: true,
    defaultVisible: true,
  },
  TMRT: {
    id: 'TMRT',
    name: '台中捷運',
    dataPath: '/data-tmrt',
    enable3D: true,
    enableFollow: true,
    defaultVisible: true,
  },
};

/**
 * 判斷 trackId 屬於哪種運具
 */
export function getTransportMode(trackId: string): TransportMode {
  if (trackId.startsWith('THSR')) return 'THSR';
  if (trackId.startsWith('TRA')) return 'TRA';
  if (trackId.startsWith('KRTC')) return 'KRTC';
  if (trackId.startsWith('KLRT')) return 'KRTC'; // 高雄輕軌歸屬於 KRTC
  if (trackId.startsWith('TMRT')) return 'TMRT';
  if (trackId.startsWith('K') || trackId.startsWith('V')) return 'LRT';
  return 'MRT';
}

/**
 * 取得運具設定
 */
export function getTransportConfig(mode: TransportMode): TransportConfig {
  return TRANSPORT_CONFIGS[mode];
}
