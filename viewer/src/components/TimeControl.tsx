import { TimeEngine } from '../engines/TimeEngine';

interface TimeControlProps {
  timeEngine: TimeEngine;
  currentTime: string;
  trainCount: number;
  isPlaying: boolean;
  speed: number;
  onTogglePlay: () => void;
  onSpeedChange: (speed: number) => void;
  onTimeChange: (seconds: number) => void;
}

export function TimeControl({
  timeEngine,
  currentTime,
  trainCount,
  isPlaying,
  speed,
  onTogglePlay,
  onSpeedChange,
  onTimeChange,
}: TimeControlProps) {
  const timeSeconds = timeEngine.getTimeOfDaySeconds();

  // 時間滑桿: 6:00 - 24:00 (21600 - 86400 秒)
  const minTime = 6 * 3600; // 06:00
  const maxTime = 24 * 3600; // 24:00

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 20,
        left: 20,
        right: 20,
        background: 'rgba(0, 0, 0, 0.85)',
        borderRadius: 12,
        padding: '16px 20px',
        color: 'white',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
      }}
    >
      {/* 上方資訊列 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 12,
        }}
      >
        {/* 時間顯示 */}
        <div style={{ fontSize: 32, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
          {currentTime}
        </div>

        {/* 列車數量 */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 14,
            color: '#aaa',
          }}
        >
          <span
            style={{
              display: 'inline-block',
              width: 10,
              height: 10,
              background: '#d90023',
              borderRadius: '50%',
            }}
          />
          <span>運行中列車: {trainCount}</span>
        </div>
      </div>

      {/* 時間滑桿 */}
      <div style={{ marginBottom: 12 }}>
        <input
          type="range"
          min={minTime}
          max={maxTime}
          value={Math.max(minTime, Math.min(maxTime, timeSeconds))}
          onChange={(e) => onTimeChange(Number(e.target.value))}
          style={{
            width: '100%',
            height: 6,
            appearance: 'none',
            background: 'linear-gradient(to right, #333 0%, #d90023 50%, #333 100%)',
            borderRadius: 3,
            cursor: 'pointer',
          }}
        />
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: 11,
            color: '#666',
            marginTop: 4,
          }}
        >
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>24:00</span>
        </div>
      </div>

      {/* 控制按鈕列 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        {/* 播放/暫停按鈕 */}
        <button
          onClick={onTogglePlay}
          style={{
            width: 48,
            height: 48,
            borderRadius: '50%',
            border: 'none',
            background: '#d90023',
            color: 'white',
            fontSize: 20,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'transform 0.1s',
          }}
          onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(0.95)')}
          onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
          onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
        >
          {isPlaying ? '⏸' : '▶'}
        </button>

        {/* 速度滑桿 (對數刻度) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, maxWidth: 320 }}>
          <span style={{ fontSize: 12, color: '#888', minWidth: 24 }}>1x</span>
          <input
            type="range"
            min={0}
            max={100}
            value={Math.log(speed) / Math.log(300) * 100}
            onChange={(e) => {
              // 對數刻度: 0-100 → 1-300x
              const logValue = Number(e.target.value) / 100;
              const newSpeed = Math.round(Math.pow(300, logValue));
              onSpeedChange(Math.max(1, newSpeed));
            }}
            style={{
              flex: 1,
              height: 6,
              appearance: 'none',
              background: `linear-gradient(to right, #d90023 0%, #d90023 ${Math.log(speed) / Math.log(300) * 100}%, #333 ${Math.log(speed) / Math.log(300) * 100}%, #333 100%)`,
              borderRadius: 3,
              cursor: 'pointer',
            }}
          />
          <span style={{ fontSize: 12, color: '#888', minWidth: 32 }}>300x</span>
          <span
            style={{
              fontSize: 16,
              fontWeight: 600,
              color: '#d90023',
              minWidth: 50,
              textAlign: 'right',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {speed}x
          </span>
        </div>

        {/* 快速跳轉按鈕 */}
        <div style={{ display: 'flex', gap: 8 }}>
          {['06:00', '08:00', '12:00', '18:00', '22:00'].map((time) => (
            <button
              key={time}
              onClick={() => timeEngine.jumpTo(time)}
              style={{
                padding: '6px 10px',
                borderRadius: 4,
                border: '1px solid #444',
                background: 'transparent',
                color: '#888',
                fontSize: 12,
                cursor: 'pointer',
              }}
            >
              {time}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
