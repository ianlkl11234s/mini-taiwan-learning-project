import type { VisualTheme } from './ThemeToggle';

interface ThemeColors {
  panelBg: string;
  panelText: string;
  panelTextSecondary: string;
  panelBorder: string;
}

interface DateSelectorProps {
  selectedDate: string | undefined; // undefined = 定期時刻表
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
 * 日期選擇器 — 定期/每日模式切換 + 日期導航
 *
 * 定期模式：使用固定時刻表，日期控制 disabled
 * 每日模式：使用當日時刻表，可用 ◀ ▶ 切換日期
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

  // 使用本地時間格式化日期（避免 UTC 時區偏移問題）
  const toLocalDateStr = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

  const today = toLocalDateStr(new Date());
  const isDailyMode = selectedDate !== undefined;

  // 日期範圍
  const minDate = availableDates.length > 0 ? availableDates[0] : today;
  const maxDate = availableDates.length > 0 ? availableDates[availableDates.length - 1] : today;

  // 箭頭可用性（每日模式 + 未到邊界）
  const canGoPrev = isDailyMode && !!selectedDate && selectedDate > minDate;
  const canGoNext = isDailyMode && !!selectedDate && selectedDate < maxDate;

  const shiftDate = (days: number) => {
    if (!selectedDate) return;
    const d = new Date(selectedDate + 'T00:00:00');
    d.setDate(d.getDate() + days);
    const newDate = toLocalDateStr(d);
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

  // 中間標籤：今日 or 日期
  const centerLabel = (() => {
    if (!isDailyMode) return '今日'; // 定期模式顯示但 disabled
    if (selectedDate === today) return '今日';
    return formatDate(selectedDate!);
  })();

  // 第一行狀態文字
  const statusText = (() => {
    if (scheduleLoading) return '載入中...';
    if (scheduleDate) return `${formatDate(scheduleDate)} / ${trainCount} 班`;
    return `定期 / ${trainCount} 班`;
  })();

  // --- Styles ---

  const modeButtonStyle = (active: boolean): React.CSSProperties => ({
    padding: '3px 10px',
    borderRadius: 4,
    border: 'none',
    background: active ? activeBg : buttonBg,
    color: active ? '#fff' : themeColors.panelText,
    fontSize: 11,
    cursor: 'pointer',
    transition: 'background 0.15s',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    lineHeight: '18px',
    fontWeight: active ? 600 : 400,
  });

  const navButtonStyle = (enabled: boolean): React.CSSProperties => ({
    padding: '3px 6px',
    borderRadius: 4,
    border: 'none',
    background: buttonBg,
    color: themeColors.panelText,
    fontSize: 10,
    cursor: enabled ? 'pointer' : 'default',
    opacity: enabled ? 1 : 0.3,
    pointerEvents: enabled ? 'auto' : 'none',
    transition: 'opacity 0.2s, background 0.15s',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    lineHeight: '18px',
  });

  const dateControlOpacity = isDailyMode ? 1 : 0.3;

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
          {statusText}
        </span>
      </div>

      {/* 第二行：模式切換 + 日期導航 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 3,
      }}>
        {/* 模式按鈕 */}
        <button onClick={() => onDateChange(undefined)} style={modeButtonStyle(!isDailyMode)}>
          定期
        </button>
        <button onClick={() => onDateChange(selectedDate || today)} style={modeButtonStyle(isDailyMode)}>
          每日
        </button>

        <div style={{ width: 1, height: 14, background: themeColors.panelBorder, margin: '0 4px' }} />

        {/* 日期導航：◀ [日期] ▶ */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 3,
          opacity: dateControlOpacity,
          transition: 'opacity 0.2s',
        }}>
          <button onClick={() => shiftDate(-1)} style={navButtonStyle(canGoPrev)}>
            ◀
          </button>

          <span style={{
            padding: '3px 8px',
            fontSize: 11,
            fontFamily: 'system-ui, -apple-system, sans-serif',
            minWidth: 56,
            textAlign: 'center',
            color: themeColors.panelText,
            userSelect: 'none',
          }}>
            {centerLabel}
          </span>

          <button onClick={() => shiftDate(1)} style={navButtonStyle(canGoNext)}>
            ▶
          </button>
        </div>

        {/* 日期選擇器 */}
        {!isMobile && (
          <input
            type="date"
            value={selectedDate || ''}
            min={minDate}
            max={maxDate}
            disabled={!isDailyMode}
            onChange={(e) => onDateChange(e.target.value || today)}
            style={{
              padding: '2px 4px',
              borderRadius: 4,
              border: `1px solid ${themeColors.panelBorder}`,
              background: buttonBg,
              color: themeColors.panelText,
              fontSize: 11,
              fontFamily: 'system-ui',
              width: 115,
              cursor: isDailyMode ? 'pointer' : 'default',
              opacity: dateControlOpacity,
              transition: 'opacity 0.2s',
            }}
          />
        )}
      </div>
    </div>
  );
}
