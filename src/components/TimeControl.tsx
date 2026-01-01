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

/**
 * 將標準時間秒數 (0-86399) 轉換為延長日秒數
 * 延長日：06:00 開始，凌晨 00:00-05:59 被視為前一天的延續 (86400-108000)
 */
function toExtendedSeconds(standardSeconds: number): number {
  // 凌晨 00:00-05:59 (0-21599) → 視為 24:00-29:59 (86400-108000)
  if (standardSeconds < 6 * 3600) {
    return standardSeconds + 24 * 3600;
  }
  return standardSeconds;
}

/**
 * 將延長日秒數轉換為標準時間秒數 (0-86399)
 */
function toStandardSeconds(extendedSeconds: number): number {
  // 24:00+ (86400+) → 轉回 00:00+ (0+)
  if (extendedSeconds >= 24 * 3600) {
    return extendedSeconds - 24 * 3600;
  }
  return extendedSeconds;
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
  const standardSeconds = timeEngine.getTimeOfDaySeconds();
  const timeSeconds = toExtendedSeconds(standardSeconds);

  // 時間滑桿: 6:00 - 01:30 (延長日: 21600 - 91800 秒)
  const minTime = 6 * 3600; // 06:00
  const maxTime = 25.5 * 3600; // 01:30 (延長日表示為 25:30)

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

        {/* 右側：列車數量 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
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
      </div>

      {/* 時間滑桿 */}
      <div style={{ marginBottom: 12 }}>
        <style>
          {`
            .time-slider::-webkit-slider-thumb {
              -webkit-appearance: none;
              appearance: none;
              width: 14px;
              height: 14px;
              border-radius: 50%;
              background: white;
              cursor: pointer;
              box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
            .time-slider::-moz-range-thumb {
              width: 14px;
              height: 14px;
              border-radius: 50%;
              background: white;
              cursor: pointer;
              border: none;
              box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
          `}
        </style>
        <input
          type="range"
          className="time-slider"
          min={minTime}
          max={maxTime}
          value={Math.max(minTime, Math.min(maxTime, timeSeconds))}
          onChange={(e) => {
            const extendedValue = Number(e.target.value);
            // 轉換為標準秒數後傳給 TimeEngine
            onTimeChange(toStandardSeconds(extendedValue));
          }}
          style={{
            width: '100%',
            height: 6,
            appearance: 'none',
            background: 'linear-gradient(to right, #333 0%, #d90023 50%, #333 100%)',
            borderRadius: 3,
            cursor: 'pointer',
          }}
        />
        {/* 時間標籤 - 按照實際時間比例定位 */}
        <div
          style={{
            position: 'relative',
            height: 16,
            fontSize: 11,
            color: '#666',
            marginTop: 4,
          }}
        >
          {/*
            時間範圍: 06:00 (21600s) - 01:30 (91800s) = 70200s
            各時間點位置:
            - 06:00 = 0%
            - 12:00 = (43200-21600)/70200 = 30.77%
            - 18:00 = (64800-21600)/70200 = 61.54%
            - 24:00 = (86400-21600)/70200 = 92.31%
            - 01:30 = 100%
          */}
          <span style={{ position: 'absolute', left: '0%', transform: 'translateX(0)' }}>06:00</span>
          <span style={{ position: 'absolute', left: '30.77%', transform: 'translateX(-50%)' }}>12:00</span>
          <span style={{ position: 'absolute', left: '61.54%', transform: 'translateX(-50%)' }}>18:00</span>
          <span style={{ position: 'absolute', left: '92.31%', transform: 'translateX(-50%)' }}>24:00</span>
          <span style={{ position: 'absolute', right: '0%', transform: 'translateX(0)' }}>01:30</span>
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

        {/* 速度滑桿 (線性刻度) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, maxWidth: 320 }}>
          <span style={{ fontSize: 12, color: '#888', minWidth: 24 }}>1x</span>
          <input
            type="range"
            min={1}
            max={300}
            value={speed}
            onChange={(e) => {
              onSpeedChange(Number(e.target.value));
            }}
            style={{
              flex: 1,
              height: 6,
              appearance: 'none',
              background: `linear-gradient(to right, #d90023 0%, #d90023 ${(speed - 1) / 299 * 100}%, #333 ${(speed - 1) / 299 * 100}%, #333 100%)`,
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
          {['06:00', '08:00', '12:00', '18:00', '22:00', '00:00'].map((time) => (
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
