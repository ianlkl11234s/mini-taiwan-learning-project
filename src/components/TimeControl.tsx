import { TimeEngine } from '../engines/TimeEngine';
import { toExtendedSeconds, toStandardSeconds } from '../utils/timeUtils';
import type { VisualTheme } from './ThemeToggle';

export interface TransportCounts {
  trtc: number;   // TPE MRT (台北捷運，不含貓纜)
  krtc: number;   // KHH MRT (高雄捷運)
  klrt: number;   // KHH LRT (高雄輕軌)
  thsr: number;   // THSR (高鐵)
  tmrt: number;   // TXG MRT (台中捷運)
  tra: number;    // TRA (台鐵)
}

interface TimeControlProps {
  timeEngine: TimeEngine;
  currentTime: string;
  transportCounts: TransportCounts;
  isPlaying: boolean;
  speed: number;
  onTogglePlay: () => void;
  onSpeedChange: (speed: number) => void;
  onTimeChange: (seconds: number) => void;
  visualTheme?: VisualTheme;
  isMobile?: boolean;
}

export function TimeControl({
  timeEngine,
  currentTime,
  transportCounts,
  isPlaying,
  speed,
  onTogglePlay,
  onSpeedChange,
  onTimeChange,
  visualTheme = 'dark',
  isMobile = false,
}: TimeControlProps) {
  const standardSeconds = timeEngine.getTimeOfDaySeconds();
  const timeSeconds = toExtendedSeconds(standardSeconds);

  // 時間滑桿: 5:50 - 01:30 (延長日: 21000 - 91800 秒)
  const minTime = 5 * 3600 + 50 * 60; // 05:50
  const maxTime = 25.5 * 3600; // 01:30 (延長日表示為 25:30)

  // 主題顏色
  const isDark = visualTheme === 'dark';
  const colors = {
    bg: isDark ? 'rgba(0, 0, 0, 0.85)' : 'rgba(255, 255, 255, 0.95)',
    text: isDark ? '#fff' : '#333',
    textSecondary: isDark ? '#aaa' : '#666',
    textMuted: isDark ? '#888' : '#999',
    textDim: isDark ? '#666' : '#aaa',
    border: isDark ? '#444' : '#ccc',
    sliderTrack: isDark ? '#333' : '#ddd',
    shadow: isDark ? '0 4px 20px rgba(0,0,0,0.3)' : '0 4px 20px rgba(0,0,0,0.15)',
    thumbShadow: isDark ? '0 2px 4px rgba(0,0,0,0.3)' : '0 2px 4px rgba(0,0,0,0.2)',
  };

  // 計算總列車數（手機版用）
  const totalTrains = transportCounts.trtc + transportCounts.krtc + transportCounts.klrt +
                      transportCounts.tmrt + transportCounts.thsr + transportCounts.tra;

  return (
    <div
      style={{
        position: 'absolute',
        bottom: isMobile ? 0 : 16,
        left: isMobile ? 0 : 60,
        right: isMobile ? 0 : 60,
        background: colors.bg,
        borderRadius: isMobile ? '16px 16px 0 0' : 10,
        padding: isMobile ? '12px 16px 20px' : '10px 16px',
        // Safe Area: 避免被手機底部 Home Indicator + 瀏覽器工具列遮擋
        // env(safe-area-inset-bottom) 只處理 Home Indicator (~34px)
        // 額外加 50px 補償瀏覽器底部工具列
        paddingBottom: isMobile ? 'calc(70px + env(safe-area-inset-bottom))' : '10px',
        color: colors.text,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        boxShadow: colors.shadow,
        backdropFilter: 'blur(8px)',
        border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
        transition: 'background 0.3s, color 0.3s, border-color 0.3s',
      }}
    >
      {/* 上方資訊列 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: isMobile ? 8 : 6,
        }}
      >
        {/* 時間顯示 */}
        <div style={{
          fontSize: isMobile ? 20 : 24,
          fontWeight: 600,
          fontVariantNumeric: 'tabular-nums'
        }}>
          {currentTime}
        </div>

        {/* 右側：列車數量（手機版顯示總數，桌面版簡化顯示）*/}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: isMobile ? 12 : 13,
            color: colors.textSecondary,
          }}
        >
          <span
            style={{
              display: 'inline-block',
              width: isMobile ? 6 : 8,
              height: isMobile ? 6 : 8,
              background: '#d90023',
              borderRadius: '50%',
            }}
          />
          <span>{totalTrains} 列車運行中</span>
        </div>
      </div>

      {/* 時間滑桿 */}
      <div style={{ marginBottom: isMobile ? 8 : 6 }}>
        <style>
          {`
            .time-slider::-webkit-slider-thumb {
              -webkit-appearance: none;
              appearance: none;
              width: ${isMobile ? '12px' : '14px'};
              height: ${isMobile ? '12px' : '14px'};
              border-radius: 50%;
              background: ${isDark ? 'white' : '#333'};
              cursor: pointer;
              box-shadow: ${colors.thumbShadow};
            }
            .time-slider::-moz-range-thumb {
              width: ${isMobile ? '12px' : '14px'};
              height: ${isMobile ? '12px' : '14px'};
              border-radius: 50%;
              background: ${isDark ? 'white' : '#333'};
              cursor: pointer;
              border: none;
              box-shadow: ${colors.thumbShadow};
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
            height: isMobile ? 4 : 6,
            appearance: 'none',
            background: `linear-gradient(to right, ${colors.sliderTrack} 0%, #d90023 50%, ${colors.sliderTrack} 100%)`,
            borderRadius: 3,
            cursor: 'pointer',
          }}
        />
        {/* 時間標籤 - 按照實際時間比例定位 */}
        <div
          style={{
            position: 'relative',
            height: 16,
            fontSize: isMobile ? 9 : 11,
            color: colors.textDim,
            marginTop: 4,
          }}
        >
          {/*
            時間範圍: 05:50 (21000s) - 01:30 (91800s) = 70800s
            各時間點位置:
            - 05:50 = 0%
            - 06:00 = (21600-21000)/70800 = 0.85%
            - 12:00 = (43200-21000)/70800 = 31.36%
            - 18:00 = (64800-21000)/70800 = 61.86%
            - 24:00 = (86400-21000)/70800 = 92.37%
            - 01:30 = 100%
          */}
          {isMobile ? (
            // 手機版：簡化標籤
            <>
              <span style={{ position: 'absolute', left: '0%', transform: 'translateX(0)' }}>6AM</span>
              <span style={{ position: 'absolute', left: '31.36%', transform: 'translateX(-50%)' }}>12PM</span>
              <span style={{ position: 'absolute', left: '61.86%', transform: 'translateX(-50%)' }}>6PM</span>
              <span style={{ position: 'absolute', right: '0%', transform: 'translateX(0)' }}>1AM</span>
            </>
          ) : (
            // 桌面版：完整標籤
            <>
              <span style={{ position: 'absolute', left: '0%', transform: 'translateX(0)' }}>05:50</span>
              <span style={{ position: 'absolute', left: '31.36%', transform: 'translateX(-50%)' }}>12:00</span>
              <span style={{ position: 'absolute', left: '61.86%', transform: 'translateX(-50%)' }}>18:00</span>
              <span style={{ position: 'absolute', left: '92.37%', transform: 'translateX(-50%)' }}>24:00</span>
              <span style={{ position: 'absolute', right: '0%', transform: 'translateX(0)' }}>01:30</span>
            </>
          )}
        </div>
      </div>

      {/* 控制按鈕列 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: isMobile ? 12 : 0,
        }}
      >
        {/* 播放/暫停按鈕 */}
        <button
          onClick={onTogglePlay}
          style={{
            width: isMobile ? 40 : 40,
            height: isMobile ? 40 : 40,
            borderRadius: '50%',
            border: 'none',
            background: '#d90023',
            color: 'white',
            fontSize: isMobile ? 16 : 16,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'transform 0.1s',
            flexShrink: 0,
          }}
          onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(0.95)')}
          onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
          onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
        >
          {isPlaying ? '⏸' : '▶'}
        </button>

        {/* 速度滑桿 (線性刻度) */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: isMobile ? 8 : 12,
          flex: 1,
          maxWidth: isMobile ? undefined : 320
        }}>
          {!isMobile && <span style={{ fontSize: 12, color: colors.textMuted, minWidth: 24 }}>1x</span>}
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
              height: isMobile ? 4 : 6,
              appearance: 'none',
              background: `linear-gradient(to right, #d90023 0%, #d90023 ${(speed - 1) / 299 * 100}%, ${colors.sliderTrack} ${(speed - 1) / 299 * 100}%, ${colors.sliderTrack} 100%)`,
              borderRadius: 3,
              cursor: 'pointer',
            }}
          />
          {!isMobile && <span style={{ fontSize: 12, color: colors.textMuted, minWidth: 32 }}>300x</span>}
          <span
            style={{
              fontSize: isMobile ? 14 : 16,
              fontWeight: 600,
              color: '#d90023',
              minWidth: isMobile ? 40 : 50,
              textAlign: 'right',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {speed}x
          </span>
        </div>

      </div>
    </div>
  );
}
