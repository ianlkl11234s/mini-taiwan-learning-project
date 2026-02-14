import type { VisualTheme } from './ThemeToggle';

interface ThemeColors {
  panelBg: string;
  panelText: string;
  panelTextSecondary: string;
  panelBorder: string;
}

interface DateSelectorProps {
  selectedDate: string | undefined; // undefined = 固定時刻表
  onDateChange: (date: string | undefined) => void;
  scheduleDate: string | null; // 實際載入的日期
  scheduleLoading: boolean;
  trainCount: number;
  availableDates: string[]; // 已下載的日期清單 (sorted)
  themeColors: ThemeColors;
  visualTheme?: VisualTheme;
  isMobile?: boolean;
}

/**
 * 日期選擇器 — 左上角面板，風格與圖例一致
 */
export function DateSelector({
  selectedDate,
  onDateChange,
  scheduleDate,
  scheduleLoading,
  trainCount,
  availableDates,
  themeColors,
  visualTheme = 'dark',
  isMobile = false,
}: DateSelectorProps) {
  const isDark = visualTheme === 'dark';

  const buttonBg = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)';
  const activeBg = '#d90023';

  const today = new Date().toISOString().split('T')[0];

  // 日期範圍
  const minDate = availableDates.length > 0 ? availableDates[0] : today;
  const maxDate = availableDates.length > 0 ? availableDates[availableDates.length - 1] : today;

  // 判斷是否能前後移動
  const canGoPrev = selectedDate ? selectedDate > minDate : true;
  const canGoNext = selectedDate ? selectedDate < maxDate : true;

  const shiftDate = (days: number) => {
    if (!selectedDate) {
      onDateChange(today);
      return;
    }
    const d = new Date(selectedDate + 'T00:00:00');
    d.setDate(d.getDate() + days);
    const newDate = d.toISOString().split('T')[0];
    // 限制在可用範圍內
    if (newDate < minDate || newDate > maxDate) return;
    onDateChange(newDate);
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr + 'T00:00:00');
    const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
    const month = d.getMonth() + 1;
    const day = d.getDate();
    const weekday = weekdays[d.getDay()];
    return `${month}/${day} (${weekday})`;
  };

  const buttonStyle = (active = false): React.CSSProperties => ({
    padding: '3px 8px',
    borderRadius: 4,
    border: 'none',
    background: active ? activeBg : buttonBg,
    color: active ? '#fff' : themeColors.panelText,
    fontSize: 11,
    cursor: 'pointer',
    transition: 'background 0.15s',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    lineHeight: '18px',
  });

  const navButtonStyle = (enabled: boolean): React.CSSProperties => ({
    ...buttonStyle(),
    padding: '3px 6px',
    fontSize: 10,
    opacity: enabled ? 1 : 0,
    pointerEvents: enabled ? 'auto' : 'none',
    transition: 'opacity 0.2s, background 0.15s',
  });

  return (
    <div
      style={{
        background: themeColors.panelBg,
        borderRadius: 8,
        padding: '8px 14px',
        color: themeColors.panelText,
        fontFamily: 'system-ui',
        fontSize: 11,
        backdropFilter: 'blur(8px)',
        border: `1px solid ${themeColors.panelBorder}`,
        transition: 'background 0.3s, color 0.3s, border-color 0.3s',
        minWidth: 140,
      }}
    >
      {/* 第一行：標題 + 狀態 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        marginBottom: 6,
      }}>
        <span style={{ fontWeight: 600, color: themeColors.panelTextSecondary }}>時刻表</span>
        <span style={{ color: themeColors.panelTextSecondary, fontSize: 10 }}>
          {scheduleLoading
            ? '載入中...'
            : scheduleDate
              ? `${formatDate(scheduleDate)} / ${trainCount} 班`
              : `定期 / ${trainCount} 班`
          }
        </span>
      </div>

      {/* 第二行：按鈕列 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 3,
      }}>
        <button onClick={() => onDateChange(undefined)} style={buttonStyle(!selectedDate)}>
          定期
        </button>

        <div style={{ width: 1, height: 14, background: themeColors.panelBorder, margin: '0 2px' }} />

        <button onClick={() => shiftDate(-1)} style={navButtonStyle(canGoPrev)}>◀</button>

        <button onClick={() => onDateChange(today)} style={buttonStyle(selectedDate === today)}>
          今天
        </button>

        <button onClick={() => shiftDate(1)} style={navButtonStyle(canGoNext)}>▶</button>

        {!isMobile && (
          <input
            type="date"
            value={selectedDate || ''}
            min={minDate}
            max={maxDate}
            onChange={(e) => onDateChange(e.target.value || undefined)}
            style={{
              padding: '2px 4px',
              borderRadius: 4,
              border: `1px solid ${themeColors.panelBorder}`,
              background: buttonBg,
              color: themeColors.panelText,
              fontSize: 11,
              fontFamily: 'system-ui',
              width: 115,
              cursor: 'pointer',
            }}
          />
        )}
      </div>
    </div>
  );
}
