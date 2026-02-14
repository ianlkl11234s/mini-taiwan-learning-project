import type { VisualTheme } from './ThemeToggle';

interface DateSelectorProps {
  selectedDate: string | undefined; // undefined = 固定時刻表
  onDateChange: (date: string | undefined) => void;
  scheduleDate: string | null; // 實際載入的日期
  scheduleLoading: boolean;
  trainCount: number;
  visualTheme?: VisualTheme;
  isMobile?: boolean;
}

/**
 * 日期選擇器
 *
 * 切換每日時刻表或固定時刻表。
 * 設計風格與 TimeControl 一致。
 */
export function DateSelector({
  selectedDate,
  onDateChange,
  scheduleDate,
  scheduleLoading,
  trainCount,
  visualTheme = 'dark',
  isMobile = false,
}: DateSelectorProps) {
  const isDark = visualTheme === 'dark';

  const colors = {
    bg: isDark ? 'rgba(0, 0, 0, 0.85)' : 'rgba(255, 255, 255, 0.95)',
    text: isDark ? '#fff' : '#333',
    textSecondary: isDark ? '#aaa' : '#666',
    textMuted: isDark ? '#888' : '#999',
    border: isDark ? '#444' : '#ccc',
    shadow: isDark ? '0 4px 20px rgba(0,0,0,0.3)' : '0 4px 20px rgba(0,0,0,0.15)',
    buttonBg: isDark ? '#333' : '#eee',
    buttonHover: isDark ? '#444' : '#ddd',
    activeBg: '#d90023',
  };

  const today = new Date().toISOString().split('T')[0];

  // 日期前後移動
  const shiftDate = (days: number) => {
    if (!selectedDate) {
      onDateChange(today);
      return;
    }
    const d = new Date(selectedDate + 'T00:00:00');
    d.setDate(d.getDate() + days);
    onDateChange(d.toISOString().split('T')[0]);
  };

  // 格式化日期顯示
  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr + 'T00:00:00');
    const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
    const month = d.getMonth() + 1;
    const day = d.getDate();
    const weekday = weekdays[d.getDay()];
    return `${month}/${day} (${weekday})`;
  };

  const buttonStyle = (active = false): React.CSSProperties => ({
    padding: isMobile ? '4px 8px' : '4px 10px',
    borderRadius: 6,
    border: 'none',
    background: active ? colors.activeBg : colors.buttonBg,
    color: active ? '#fff' : colors.text,
    fontSize: isMobile ? 11 : 12,
    cursor: 'pointer',
    transition: 'background 0.15s',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  });

  const navButtonStyle: React.CSSProperties = {
    ...buttonStyle(),
    padding: isMobile ? '4px 6px' : '4px 8px',
    fontSize: isMobile ? 10 : 12,
    minWidth: isMobile ? 28 : 32,
  };

  return (
    <div
      style={{
        position: 'absolute',
        bottom: isMobile ? 'calc(170px + env(safe-area-inset-bottom))' : 130,
        left: isMobile ? 8 : 60,
        background: colors.bg,
        borderRadius: 10,
        padding: isMobile ? '8px 12px' : '8px 14px',
        color: colors.text,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        boxShadow: colors.shadow,
        backdropFilter: 'blur(8px)',
        border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
        transition: 'background 0.3s, color 0.3s',
        zIndex: 10,
      }}
    >
      {/* 第一行：標題 + 狀態 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        marginBottom: 6,
        fontSize: isMobile ? 11 : 12,
      }}>
        <span style={{ fontWeight: 600 }}>時刻表</span>
        <span style={{ color: colors.textMuted, fontSize: isMobile ? 10 : 11 }}>
          {scheduleLoading
            ? '載入中...'
            : scheduleDate
              ? `${formatDate(scheduleDate)} / ${trainCount} 班`
              : `定期時刻表 / ${trainCount} 班`
          }
        </span>
      </div>

      {/* 第二行：按鈕列 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
      }}>
        {/* 固定時刻表按鈕 */}
        <button
          onClick={() => onDateChange(undefined)}
          style={buttonStyle(!selectedDate)}
        >
          定期
        </button>

        {/* 分隔線 */}
        <div style={{
          width: 1,
          height: 16,
          background: colors.border,
          margin: '0 2px',
        }} />

        {/* 前一天 */}
        <button
          onClick={() => shiftDate(-1)}
          style={navButtonStyle}
        >
          ◀
        </button>

        {/* 今天按鈕 */}
        <button
          onClick={() => onDateChange(today)}
          style={buttonStyle(selectedDate === today)}
        >
          今天
        </button>

        {/* 後一天 */}
        <button
          onClick={() => shiftDate(1)}
          style={navButtonStyle}
        >
          ▶
        </button>

        {/* 日期 input */}
        <input
          type="date"
          value={selectedDate || ''}
          onChange={(e) => {
            const val = e.target.value;
            onDateChange(val || undefined);
          }}
          style={{
            padding: '3px 6px',
            borderRadius: 6,
            border: `1px solid ${colors.border}`,
            background: colors.buttonBg,
            color: colors.text,
            fontSize: isMobile ? 11 : 12,
            fontFamily: 'system-ui',
            width: isMobile ? 110 : 120,
            cursor: 'pointer',
          }}
        />
      </div>
    </div>
  );
}
