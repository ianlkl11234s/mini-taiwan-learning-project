import type { TrainCountData } from '../hooks/useTrainCountHistogram';
import { toExtendedSeconds } from '../utils/timeUtils';
import type { VisualTheme } from './ThemeToggle';

interface TrainHistogramProps {
  data: TrainCountData;
  currentTimeSeconds: number;  // 當前時間（秒，標準時間）
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
  width = 200,
  height = 50,
  visualTheme = 'dark',
}: TrainHistogramProps) {
  const { intervals, maxCount, startHour, endHour } = data;

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
    indicator: isDark ? '#fff' : '#333',
    indicatorShadow: isDark ? 'rgba(255, 255, 255, 0.8)' : 'rgba(0, 0, 0, 0.3)',
  };

  return (
    <div
      style={{
        width,
        height: height + 20, // 額外空間給時間標籤
        position: 'relative',
        background: colors.bg,
        borderRadius: 6,
        padding: '8px 10px',
        boxSizing: 'content-box',
        backdropFilter: 'blur(8px)',
        border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
        transition: 'background 0.3s, border-color 0.3s',
      }}
    >
      {/* 標題 */}
      <div
        style={{
          position: 'absolute',
          top: 4,
          left: 10,
          fontSize: 9,
          color: colors.text,
          fontWeight: 500,
        }}
      >
        列車數趨勢
      </div>

      {/* 線圖 SVG */}
      <svg
        width={width}
        height={height}
        style={{ marginTop: 12, overflow: 'visible' }}
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
          left: 10 + currentProgress * width,
          top: 20,
          width: 2,
          height: height,
          background: colors.indicator,
          borderRadius: 1,
          boxShadow: `0 0 4px ${colors.indicatorShadow}`,
          transition: 'left 0.3s ease',
        }}
      />

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
    </div>
  );
}
