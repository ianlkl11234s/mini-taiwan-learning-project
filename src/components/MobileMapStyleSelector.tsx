import { useState } from 'react';
import type { MapTheme, VisualTheme } from './ThemeToggle';

interface MobileMapStyleSelectorProps {
  theme: MapTheme;
  onChange: (theme: MapTheme) => void;
  visualTheme: VisualTheme;
}

const THEME_OPTIONS: { value: MapTheme; label: string }[] = [
  { value: 'auto', label: '自動' },
  { value: 'dawn', label: '黎明' },
  { value: 'day', label: '白天' },
  { value: 'dusk', label: '黃昏' },
  { value: 'night', label: '夜晚' },
  { value: 'dark', label: '深色' },
  { value: 'light', label: '淺色' },
  { value: 'satellite', label: '衛星' },
];

export function MobileMapStyleSelector({ theme, onChange, visualTheme }: MobileMapStyleSelectorProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const currentOption = THEME_OPTIONS.find(o => o.value === theme);

  const handleSelect = (value: MapTheme) => {
    onChange(value);
    setIsExpanded(false);
  };

  // 根據視覺主題調整顏色
  const isDark = visualTheme === 'dark';
  const bgColor = isDark ? 'rgba(0, 0, 0, 0.8)' : 'rgba(255, 255, 255, 0.95)';
  const textColor = isDark ? '#fff' : '#333';
  const borderColor = isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.15)';
  const hoverBg = isDark ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.08)';
  const activeBg = isDark ? 'rgba(255, 255, 255, 0.25)' : 'rgba(0, 0, 0, 0.12)';

  return (
    <div style={{ position: 'relative' }}>
      {/* 收合時顯示的按鈕 - 圓形，只顯示 Map 圖示 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          background: bgColor,
          border: `1px solid ${borderColor}`,
          color: textColor,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backdropFilter: 'blur(8px)',
          padding: 0,
        }}
        title={`地圖樣式: ${currentOption?.label}`}
      >
        {/* Map icon */}
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5zM15 19l-6-2.11V5l6 2.11V19z"/>
        </svg>
      </button>

      {/* 展開的選項列表 */}
      {isExpanded && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            right: 44,
            background: bgColor,
            border: `1px solid ${borderColor}`,
            borderRadius: 8,
            padding: 4,
            minWidth: 70,
            backdropFilter: 'blur(8px)',
            boxShadow: isDark
              ? '0 4px 12px rgba(0, 0, 0, 0.5)'
              : '0 4px 12px rgba(0, 0, 0, 0.2)',
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
                  padding: '6px 10px',
                  border: 'none',
                  borderRadius: 4,
                  background: isActive ? activeBg : 'transparent',
                  color: textColor,
                  fontSize: 11,
                  fontWeight: isActive ? 600 : 400,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'background 0.15s ease',
                  display: 'block',
                  whiteSpace: 'nowrap',
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
