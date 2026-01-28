import { useState } from 'react';
import type { Train } from '../engines/TrainEngine';
import type { ThsrTrain } from '../engines/ThsrTrainEngine';
import type { KrtcTrain } from '../engines/KrtcTrainEngine';
import type { TmrtTrain } from '../engines/TmrtTrainEngine';
import { getLineName, getLineColor } from '../constants/lineInfo';
import { getThsrLineName, getThsrLineColor } from '../constants/thsrInfo';
import { getKrtcLineName, getKrtcLineColor } from '../constants/krtcInfo';
import { getKlrtLineName, getKlrtLineColor } from '../constants/klrtInfo';
import { getTmrtLineName, getTmrtLineColor } from '../constants/tmrtInfo';
import { getTraLineName, TRA_PRIMARY_COLOR, TRA_STATION_NAMES } from '../constants/traInfo';
import type { TraTrain } from '../engines/TraTrainEngine';
import type { VisualTheme } from './ThemeToggle';

interface TrainInfoPanelProps {
  train: Train | ThsrTrain | KrtcTrain | TmrtTrain | TraTrain;
  stationNames: Map<string, string>;
  onClose: () => void;
  visualTheme?: VisualTheme;
}

export function TrainInfoPanel({ train, stationNames, onClose, visualTheme = 'dark' }: TrainInfoPanelProps) {
  const [collapsed, setCollapsed] = useState(false);

  // 判斷列車類型
  const isThsr = train.trackId.startsWith('THSR');
  const isKrtc = train.trackId.startsWith('KRTC');
  const isKlrt = train.trackId.startsWith('KLRT');
  const isTmrt = train.trackId.startsWith('TMRT');
  // TRA 路線判斷（包含所有可能的 trackId 前綴）
  const isTra = train.trackId.startsWith('NW') ||   // 內灣線
                train.trackId.startsWith('LJ') ||   // 六家線
                train.trackId.startsWith('SH') ||   // 沙崙線
                train.trackId.startsWith('WL') ||   // 西部幹線
                train.trackId.startsWith('PX') ||   // 平溪線
                train.trackId.startsWith('JJ') ||   // 集集線
                train.trackId.startsWith('CZ') ||   // 成追線
                train.trackId.startsWith('YL') ||   // 宜蘭線
                train.trackId.startsWith('BH') ||   // 北迴線
                train.trackId.startsWith('TL') ||   // 臺東線
                train.trackId.startsWith('SK') ||   // 南迴線
                train.trackId.startsWith('PT') ||   // 屏東線
                train.trackId.startsWith('SA') ||   // 深澳線
                train.trackId.startsWith('OD') ||   // O-D 軌道
                train.trackId.startsWith('BB') ||   // 合併軌道
                train.trackId.startsWith('SP');

  // 根據類型取得線路資訊
  const lineColor = isThsr
    ? getThsrLineColor(train.trackId)
    : isKrtc
    ? getKrtcLineColor(train.trackId)
    : isKlrt
    ? getKlrtLineColor(train.trackId)
    : isTmrt
    ? getTmrtLineColor(train.trackId)
    : isTra
    ? TRA_PRIMARY_COLOR
    : getLineColor(train.trackId);
  const lineName = isThsr
    ? getThsrLineName(train.trackId)
    : isKrtc
    ? getKrtcLineName(train.trackId)
    : isKlrt
    ? getKlrtLineName(train.trackId)
    : isTmrt
    ? getTmrtLineName(train.trackId)
    : isTra
    ? getTraLineName(train.trackId)
    : getLineName(train.trackId);

  // 主題顏色
  const isDark = visualTheme === 'dark';
  const colors = {
    bg: isDark ? 'rgba(0, 0, 0, 0.85)' : 'rgba(255, 255, 255, 0.95)',
    text: isDark ? '#fff' : '#333',
    textSecondary: isDark ? '#888' : '#666',
    textMuted: isDark ? '#aaa' : '#777',
    bgHighlight: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)',
    border: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
    shadow: isDark ? '0 4px 16px rgba(0, 0, 0, 0.5)' : '0 4px 16px rgba(0, 0, 0, 0.15)',
  };

  // 取得站名（如果找不到則顯示 ID）
  // TRA 使用獨立的站名查找表，避免與 THSR 的 station_id 衝突
  const getStationName = (stationId: string | undefined) => {
    if (!stationId) return '-';
    if (isTra) {
      return TRA_STATION_NAMES[stationId] || stationId;
    }
    return stationNames.get(stationId) || stationId;
  };

  // 起點站名稱
  const originName = getStationName(train.originStation);
  // 終點站名稱
  const destinationName = getStationName(train.destinationStation);
  // 前一站名稱
  const prevStationName = getStationName(train.previousStation);
  // 下一站名稱
  const nextStationName = getStationName(train.nextStation);

  return (
    <div
      style={{
        position: 'absolute',
        top: 75,
        right: 60,
        zIndex: 20,
        background: colors.bg,
        borderRadius: 10,
        padding: collapsed ? '10px 16px' : '16px 20px',
        color: colors.text,
        fontFamily: 'system-ui',
        fontSize: 14,
        minWidth: collapsed ? 160 : 220,
        boxShadow: colors.shadow,
        border: `2px solid ${lineColor}`,
        transition: 'all 0.2s ease',
        backdropFilter: 'blur(8px)',
      }}
    >
      {/* 標題列：可點擊收合 */}
      <div
        onClick={() => setCollapsed(!collapsed)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <div
          style={{
            width: 12,
            height: 12,
            borderRadius: 3,
            background: lineColor,
            flexShrink: 0,
          }}
        />
        <span style={{ fontWeight: 600, fontSize: 15 }}>{lineName}</span>
        <span
          style={{
            fontSize: 10,
            color: colors.textSecondary,
            marginLeft: 'auto',
            transition: 'transform 0.2s ease',
            transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
          }}
        >
          ▼
        </span>
        {/* 關閉按鈕 */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
          style={{
            background: 'none',
            border: 'none',
            color: colors.textSecondary,
            cursor: 'pointer',
            padding: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'color 0.2s',
            marginLeft: 4,
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = colors.text)}
          onMouseLeave={(e) => (e.currentTarget.style.color = colors.textSecondary)}
          title="關閉"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
          </svg>
        </button>
      </div>

      {/* 可收合的詳細資訊 */}
      <div
        style={{
          maxHeight: collapsed ? 0 : 250,
          overflow: 'hidden',
          transition: 'max-height 0.2s ease, opacity 0.2s ease, margin 0.2s ease',
          opacity: collapsed ? 0 : 1,
          marginTop: collapsed ? 0 : 12,
        }}
      >
        {/* 車種（僅 TRA） */}
        {isTra && 'trainType' in train && train.trainType && (
          <div
            style={{
              marginBottom: 8,
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span
              style={{
                background: colors.bgHighlight,
                padding: '2px 8px',
                borderRadius: 4,
                fontWeight: 500,
              }}
            >
              {train.trainType}
            </span>
            {'trainNo' in train && train.trainNo && (
              <span style={{ color: colors.textSecondary, fontFamily: 'monospace' }}>
                #{train.trainNo}
              </span>
            )}
          </div>
        )}

        {/* 起點 → 終點 */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginBottom: 10,
            padding: '6px 10px',
            background: colors.bgHighlight,
            borderRadius: 6,
            fontSize: 13,
          }}
        >
          <span style={{ fontWeight: 500 }}>{originName}</span>
          <span style={{ color: colors.textSecondary }}>→</span>
          <span style={{ fontWeight: 500 }}>{destinationName}</span>
        </div>

        {/* 前一站 */}
        <div style={{ marginBottom: 4, fontSize: 13 }}>
          <span style={{ color: colors.textSecondary }}>前一站：</span>
          <span>{prevStationName}</span>
          {train.previousDepartureTime && (
            <span
              style={{
                marginLeft: 8,
                color: '#66c4a0',
                fontFamily: 'monospace',
              }}
            >
              {train.previousDepartureTime}
            </span>
          )}
        </div>

        {/* 下一站 */}
        <div style={{ marginBottom: 4, fontSize: 13 }}>
          <span style={{ color: colors.textSecondary }}>下一站：</span>
          <span>{nextStationName}</span>
          {train.nextArrivalTime && (
            <span
              style={{
                marginLeft: 8,
                color: '#80bfff',
                fontFamily: 'monospace',
              }}
            >
              {train.nextArrivalTime}
            </span>
          )}
        </div>

        {/* 列車狀態 */}
        <div
          style={{
            marginTop: 8,
            paddingTop: 8,
            borderTop: `1px solid ${colors.border}`,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background:
                train.status === 'stopped'
                  ? '#66c4a0'
                  : train.status === 'running'
                  ? '#80bfff'
                  : colors.textSecondary,
              boxShadow:
                train.status === 'stopped'
                  ? '0 0 6px #66c4a0'
                  : train.status === 'running'
                  ? '0 0 6px #80bfff'
                  : 'none',
            }}
          />
          <span style={{ color: colors.textMuted, fontSize: 11 }}>
            {train.status === 'stopped'
              ? '停站中'
              : train.status === 'running'
              ? '行駛中'
              : train.status === 'waiting'
              ? '等待發車'
              : '已到站'}
          </span>
        </div>
      </div>
    </div>
  );
}
