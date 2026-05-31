import { useState } from 'react';
import type { WeatherType } from '../layers/Weather3DLayer';
import type { VisualTheme } from './ThemeToggle';

interface WeatherSelectorProps {
  currentType: WeatherType;
  manualType: WeatherType | null;
  weatherSource: 'api' | 'manual';
  hasApiKey: boolean;
  loading: boolean;
  onSelect: (type: WeatherType | null) => void;
  visualTheme: VisualTheme;
}

const WEATHER_OPTIONS: { value: WeatherType; label: string; icon: string }[] = [
  { value: 'clear',        label: 'Clear',   icon: '\u2600\uFE0F' },   // ☀️
  { value: 'drizzle',      label: 'Drizzle', icon: '\uD83C\uDF26\uFE0F' },  // 🌦️
  { value: 'rain',         label: 'Rain',    icon: '\uD83C\uDF27\uFE0F' },  // 🌧️
  { value: 'heavy-rain',   label: 'Heavy',   icon: '\u26C8\uFE0F' },   // ⛈️
  { value: 'thunderstorm', label: 'Storm',   icon: '\uD83C\uDF29\uFE0F' },  // 🌩️
  { value: 'snow',         label: 'Snow',    icon: '\u2744\uFE0F' },   // ❄️
];

export function WeatherSelector({
  currentType,
  manualType,
  weatherSource,
  hasApiKey,
  loading,
  onSelect,
  visualTheme,
}: WeatherSelectorProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const isDark = visualTheme === 'dark';
  const bgColor = isDark ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.9)';
  const textColor = isDark ? '#fff' : '#333';
  const borderColor = isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.15)';
  const hoverBg = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)';
  const activeBg = isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)';
  const accentColor = '#66b8ff';

  const currentOption = WEATHER_OPTIONS.find(o => o.value === currentType) || WEATHER_OPTIONS[0];

  const handleSelect = (type: WeatherType) => {
    onSelect(type);
    setIsExpanded(false);
  };

  const handleResetToLive = () => {
    onSelect(null);
    setIsExpanded(false);
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      {/* 觸發按鈕 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          background: isExpanded ? activeBg : 'transparent',
          border: `1px solid ${borderColor}`,
          borderRadius: 4,
          color: textColor,
          cursor: 'pointer',
          padding: '3px 8px',
          fontSize: 12,
          fontWeight: 500,
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          transition: 'all 0.2s',
          whiteSpace: 'nowrap',
        }}
        title="天氣模擬"
      >
        <span style={{ fontSize: 14 }}>{currentOption.icon}</span>
        <span>{currentOption.label}</span>
        {loading && (
          <span style={{ fontSize: 10, opacity: 0.6 }}>...</span>
        )}
        {weatherSource === 'api' && hasApiKey && (
          <span style={{
            fontSize: 9,
            background: accentColor,
            color: '#000',
            borderRadius: 3,
            padding: '0 3px',
            fontWeight: 700,
          }}>
            LIVE
          </span>
        )}
      </button>

      {/* 下拉選單 */}
      {isExpanded && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            marginTop: 4,
            background: bgColor,
            border: `1px solid ${borderColor}`,
            borderRadius: 6,
            padding: 4,
            zIndex: 1000,
            minWidth: 140,
            backdropFilter: 'blur(8px)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
        >
          {WEATHER_OPTIONS.map((opt) => {
            const isActive = currentType === opt.value && manualType === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => handleSelect(opt.value)}
                onMouseEnter={(e) => {
                  if (!isActive) e.currentTarget.style.background = hoverBg;
                }}
                onMouseLeave={(e) => {
                  if (!isActive) e.currentTarget.style.background = 'transparent';
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  width: '100%',
                  padding: '6px 8px',
                  border: 'none',
                  borderRadius: 4,
                  background: isActive ? activeBg : 'transparent',
                  color: textColor,
                  cursor: 'pointer',
                  fontSize: 12,
                  textAlign: 'left',
                }}
              >
                <span style={{ fontSize: 15 }}>{opt.icon}</span>
                <span>{opt.label}</span>
              </button>
            );
          })}

          {/* 切回 Live 模式 */}
          {hasApiKey && manualType !== null && (
            <>
              <div style={{
                height: 1,
                background: borderColor,
                margin: '4px 0',
              }} />
              <button
                onClick={handleResetToLive}
                onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  width: '100%',
                  padding: '6px 8px',
                  border: 'none',
                  borderRadius: 4,
                  background: 'transparent',
                  color: accentColor,
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 600,
                  textAlign: 'left',
                }}
              >
                <span style={{ fontSize: 14 }}>&#x1F4E1;</span>
                <span>Live Weather</span>
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
