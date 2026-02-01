import { useState } from 'react';
import type { TrainCountData } from '../hooks/useTrainCountHistogram';
import { toExtendedSeconds } from '../utils/timeUtils';
import type { VisualTheme } from './ThemeToggle';
import type { TransportCounts } from './TimeControl';

interface TrainHistogramProps {
  data: TrainCountData;
  currentTimeSeconds: number;  // 當前時間（秒，標準時間）
  transportCounts: TransportCounts;  // 各系統運行中列車數
  width?: number;
  height?: number;
  visualTheme?: VisualTheme;
}

/**
 * 生成平滑曲線的 SVG path
 * 使用 Catmull-Rom spline 轉換為 Bezier curves
 */
function generateSmoothPath(points: { x: number; y: number }[]): string {
  if (points.length < 2) return '';

  const tension = 0.3; // 曲線張力，越小越平滑
  let path = `M ${points[0].x} ${points[0].y}`;

  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(points.length - 1, i + 2)];

    // 計算控制點
    const cp1x = p1.x + (p2.x - p0.x) * tension;
    const cp1y = p1.y + (p2.y - p0.y) * tension;
    const cp2x = p2.x - (p3.x - p1.x) * tension;
    const cp2y = p2.y - (p3.y - p1.y) * tension;

    path += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
  }

  return path;
}

export function TrainHistogram({
  data,
  currentTimeSeconds,
  transportCounts,
  width = 200,
  height = 50,
  visualTheme = 'dark',
}: TrainHistogramProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { intervals, maxCount, startHour, endHour } = data;

  // 計算總列車數
  const totalTrains = transportCounts.trtc + transportCounts.krtc + transportCounts.klrt +
                      transportCounts.tmrt + transportCounts.thsr + transportCounts.tra;

  // 計算當前時間指示線位置
  const extendedSeconds = toExtendedSeconds(currentTimeSeconds);
  const startSeconds = startHour * 3600;
  const endSeconds = endHour * 3600;
  const totalSeconds = endSeconds - startSeconds;
  const currentProgress = Math.max(0, Math.min(1,
    (extendedSeconds - startSeconds) / totalSeconds
  ));

  // 生成線圖的點座標
  const points = intervals.map((count, i) => ({
    x: (i / (intervals.length - 1)) * width,
    y: height - (count / maxCount) * height * 0.85,
  }));

  // 生成平滑曲線路徑
  const linePath = generateSmoothPath(points);

  // 生成填充區域路徑（閉合曲線）
  const areaPath = `${linePath} L ${width} ${height} L 0 ${height} Z`;

  // 主題顏色
  const isDark = visualTheme === 'dark';
  const colors = {
    bg: isDark ? 'rgba(40, 40, 40, 0.6)' : 'rgba(255, 255, 255, 0.85)',
    text: isDark ? '#888' : '#666',
    textDim: isDark ? '#666' : '#999',
    textBright: isDark ? '#ccc' : '#444',
    indicator: isDark ? '#fff' : '#333',
    indicatorShadow: isDark ? 'rgba(255, 255, 255, 0.8)' : 'rgba(0, 0, 0, 0.3)',
  };

  return (
    <div
      style={{
        width: collapsed ? 'auto' : width,
        minWidth: collapsed ? 140 : width,
        position: 'relative',
        background: colors.bg,
        borderRadius: 6,
        padding: collapsed ? '6px 10px' : '8px 10px',
        boxSizing: 'content-box',
        backdropFilter: 'blur(8px)',
        border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
        transition: 'all 0.2s ease',
      }}
    >
      {/* 標題列：可點擊收合 */}
      <div
        onClick={() => setCollapsed(!collapsed)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          userSelect: 'none',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            style={{
              fontSize: 9,
              color: colors.text,
              fontWeight: 500,
            }}
          >
            列車數趨勢
          </span>
          <span
            style={{
              fontSize: 10,
              transition: 'transform 0.2s ease',
              transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
              color: colors.textDim,
            }}
          >
            ▼
          </span>
        </div>
        {/* 收合時顯示總數 */}
        {collapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span
              style={{
                display: 'inline-block',
                width: 6,
                height: 6,
                background: '#d90023',
                borderRadius: '50%',
              }}
            />
            <span style={{ fontSize: 11, color: colors.textBright, fontWeight: 500 }}>
              {totalTrains}
            </span>
          </div>
        )}
      </div>

      {/* 可收合的內容 */}
      <div
        style={{
          maxHeight: collapsed ? 0 : 200,
          overflow: 'hidden',
          opacity: collapsed ? 0 : 1,
          transition: 'all 0.2s ease',
          marginTop: collapsed ? 0 : 8,
        }}
      >
        {/* 線圖 SVG */}
        <div style={{ position: 'relative' }}>
          <svg
            width={width}
            height={height}
            style={{ overflow: 'visible' }}
          >
            {/* 漸層定義 */}
            <defs>
              <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="rgba(217, 0, 35, 0.4)" />
                <stop offset="100%" stopColor="rgba(217, 0, 35, 0.05)" />
              </linearGradient>
            </defs>

            {/* 填充區域 */}
            <path
              d={areaPath}
              fill="url(#areaGradient)"
            />

            {/* 線條 */}
            <path
              d={linePath}
              fill="none"
              stroke="#d90023"
              strokeWidth={1.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>

          {/* 當前時間指示線 */}
          <div
            style={{
              position: 'absolute',
              left: currentProgress * width,
              top: 0,
              width: 2,
              height: height,
              background: colors.indicator,
              borderRadius: 1,
              boxShadow: `0 0 4px ${colors.indicatorShadow}`,
              transition: 'left 0.3s ease',
            }}
          />
        </div>

        {/* 時間標籤 */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginTop: 4,
            fontSize: 8,
            color: colors.textDim,
          }}
        >
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>24:00</span>
        </div>

        {/* 各系統運行中列車數 */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '4px 8px',
            marginTop: 8,
            paddingTop: 8,
            borderTop: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
            fontSize: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ color: '#d90023', fontWeight: 500 }}>TPE</span>
            <span style={{ color: colors.textBright, fontVariantNumeric: 'tabular-nums' }}>{transportCounts.trtc}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ color: '#e2211c', fontWeight: 500 }}>KHH</span>
            <span style={{ color: colors.textBright, fontVariantNumeric: 'tabular-nums' }}>{transportCounts.krtc}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ color: '#00ab4e', fontWeight: 500 }}>LRT</span>
            <span style={{ color: colors.textBright, fontVariantNumeric: 'tabular-nums' }}>{transportCounts.klrt}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ color: '#0cab2c', fontWeight: 500 }}>TXG</span>
            <span style={{ color: colors.textBright, fontVariantNumeric: 'tabular-nums' }}>{transportCounts.tmrt}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ color: '#f37421', fontWeight: 500 }}>HSR</span>
            <span style={{ color: colors.textBright, fontVariantNumeric: 'tabular-nums' }}>{transportCounts.thsr}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ color: '#0072bc', fontWeight: 500 }}>TRA</span>
            <span style={{ color: colors.textBright, fontVariantNumeric: 'tabular-nums' }}>{transportCounts.tra}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
