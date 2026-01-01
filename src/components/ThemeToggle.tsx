import { useState } from 'react';

// 地圖主題模式
// standard 樣式的 lightPreset: dawn, day, dusk, night
// 獨立樣式: dark (dark-v11)
export type MapTheme = 'dawn' | 'day' | 'dusk' | 'night' | 'dark' | 'auto';

// 視覺主題（用於面板顏色）
export type VisualTheme = 'light' | 'dark';

// 根據 MapTheme 取得視覺主題
export const getVisualTheme = (theme: MapTheme, currentHour?: number): VisualTheme => {
  if (theme === 'auto' && currentHour !== undefined) {
    // 自動模式：根據時間判斷
    if (currentHour >= 5 && currentHour < 7) return 'light';   // dawn
    if (currentHour >= 7 && currentHour < 17) return 'light';  // day
    if (currentHour >= 17 && currentHour < 19) return 'dark';  // dusk
    return 'dark'; // night
  }
  // 手動模式
  if (theme === 'dawn' || theme === 'day') return 'light';
  return 'dark'; // dusk, night, dark
};

interface ThemeToggleProps {
  theme: MapTheme;
  onChange: (theme: MapTheme) => void;
  visualTheme: VisualTheme;
}

const THEME_OPTIONS: { value: MapTheme; label: string }[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'dawn', label: 'Dawn' },
  { value: 'day', label: 'Day' },
  { value: 'dusk', label: 'Dusk' },
  { value: 'night', label: 'Night' },
  { value: 'dark', label: 'Dark' },
];

export function ThemeToggle({ theme, onChange, visualTheme }: ThemeToggleProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const currentOption = THEME_OPTIONS.find(o => o.value === theme);

  const handleSelect = (value: MapTheme) => {
    onChange(value);
    setIsExpanded(false);
  };

  // 根據視覺主題調整顏色
  const isDark = visualTheme === 'dark';
  const bgColor = isDark ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.9)';
  const textColor = isDark ? '#fff' : '#333';
  const borderColor = isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.15)';
  const hoverBg = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)';
  const activeBg = isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)';

  return (
    <div style={{ position: 'relative' }}>
      {/* 收合時顯示的按鈕 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          background: bgColor,
          border: `1px solid ${borderColor}`,
          borderRadius: 6,
          color: textColor,
          cursor: 'pointer',
          padding: '6px 12px',
          fontSize: 12,
          fontWeight: 500,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          transition: 'all 0.2s ease',
          backdropFilter: 'blur(8px)',
        }}
      >
        <span>{currentOption?.label}</span>
        <span style={{
          fontSize: 10,
          transition: 'transform 0.2s ease',
          transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
        }}>
          ▼
        </span>
      </button>

      {/* 展開的選項列表 */}
      {isExpanded && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            marginTop: 4,
            background: bgColor,
            border: `1px solid ${borderColor}`,
            borderRadius: 8,
            padding: 4,
            minWidth: 100,
            backdropFilter: 'blur(8px)',
            boxShadow: isDark
              ? '0 4px 12px rgba(0, 0, 0, 0.4)'
              : '0 4px 12px rgba(0, 0, 0, 0.15)',
            zIndex: 100,
          }}
        >
          {THEME_OPTIONS.map((option) => {
            const isActive = theme === option.value;
            return (
              <button
                key={option.value}
                onClick={() => handleSelect(option.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: 'none',
                  borderRadius: 4,
                  background: isActive ? activeBg : 'transparent',
                  color: textColor,
                  fontSize: 12,
                  fontWeight: isActive ? 600 : 400,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'background 0.15s ease',
                  display: 'block',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) e.currentTarget.style.background = hoverBg;
                }}
                onMouseLeave={(e) => {
                  if (!isActive) e.currentTarget.style.background = 'transparent';
                }}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      )}

      {/* 點擊外部關閉 */}
      {isExpanded && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 99,
          }}
          onClick={() => setIsExpanded(false)}
        />
      )}
    </div>
  );
}
