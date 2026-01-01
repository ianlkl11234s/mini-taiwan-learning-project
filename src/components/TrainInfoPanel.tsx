import type { Train } from '../engines/TrainEngine';
import {
  getLineName,
  getDirectionName,
  getLineColor,
} from '../constants/lineInfo';

interface TrainInfoPanelProps {
  train: Train;
  stationNames: Map<string, string>;
  onClose: () => void;
}

export function TrainInfoPanel({ train, stationNames, onClose }: TrainInfoPanelProps) {
  const lineColor = getLineColor(train.trackId);
  const lineName = getLineName(train.trackId);
  const directionName = getDirectionName(train.trackId);

  // 取得站名（如果找不到則顯示 ID）
  const getStationName = (stationId: string | undefined) => {
    if (!stationId) return '-';
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
        top: 60,
        right: 20,
        zIndex: 20,
        background: 'rgba(0, 0, 0, 0.85)',
        borderRadius: 10,
        padding: '16px 20px',
        color: 'white',
        fontFamily: 'system-ui',
        fontSize: 14,
        minWidth: 240,
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.5)',
        border: `2px solid ${lineColor}`,
      }}
    >
      {/* 關閉按鈕 */}
      <button
        onClick={onClose}
        style={{
          position: 'absolute',
          top: 10,
          right: 10,
          background: 'none',
          border: 'none',
          color: '#888',
          cursor: 'pointer',
          padding: 4,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'color 0.2s',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
        onMouseLeave={(e) => (e.currentTarget.style.color = '#888')}
        title="關閉"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
        </svg>
      </button>

      {/* 路線與方向 */}
      <div style={{ marginBottom: 12 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginBottom: 4,
          }}
        >
          <div
            style={{
              width: 14,
              height: 14,
              borderRadius: 3,
              background: lineColor,
            }}
          />
          <span style={{ fontWeight: 600, fontSize: 16 }}>{lineName}</span>
        </div>
        <div style={{ color: '#aaa', marginLeft: 22 }}>{directionName}</div>
      </div>

      {/* 起點 → 終點 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginBottom: 12,
          padding: '8px 12px',
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: 6,
        }}
      >
        <span style={{ fontWeight: 500 }}>{originName}</span>
        <span style={{ color: '#888' }}>→</span>
        <span style={{ fontWeight: 500 }}>{destinationName}</span>
      </div>

      {/* 前一站 */}
      <div style={{ marginBottom: 6 }}>
        <span style={{ color: '#888' }}>前一站：</span>
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
      <div style={{ marginBottom: 6 }}>
        <span style={{ color: '#888' }}>下一站：</span>
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
          marginTop: 12,
          paddingTop: 10,
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background:
              train.status === 'stopped'
                ? '#66c4a0'
                : train.status === 'running'
                ? '#80bfff'
                : '#888',
            boxShadow:
              train.status === 'stopped'
                ? '0 0 6px #66c4a0'
                : train.status === 'running'
                ? '0 0 6px #80bfff'
                : 'none',
          }}
        />
        <span style={{ color: '#aaa', fontSize: 12 }}>
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
  );
}
