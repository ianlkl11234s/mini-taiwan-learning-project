// 地圖主題模式
export type MapTheme = 'dawn' | 'day' | 'dusk' | 'night' | 'auto';

interface ThemeToggleProps {
  theme: MapTheme;
  onChange: (theme: MapTheme) => void;
}

const THEME_OPTIONS: { value: MapTheme; icon: string; label: string }[] = [
  { value: 'dawn', icon: '🌅', label: '清晨' },
  { value: 'day', icon: '☀️', label: '日間' },
  { value: 'dusk', icon: '🌇', label: '黃昏' },
  { value: 'night', icon: '🌙', label: '夜間' },
  { value: 'auto', icon: '🔄', label: '自動' },
];

export function ThemeToggle({ theme, onChange }: ThemeToggleProps) {
  return (
    <div
      style={{
        display: 'flex',
        gap: 4,
        background: 'rgba(0, 0, 0, 0.6)',
        borderRadius: 8,
        padding: 4,
      }}
    >
      {THEME_OPTIONS.map((option) => {
        const isActive = theme === option.value;
        return (
          <button
            key={option.value}
            onClick={() => onChange(option.value)}
            title={option.label}
            style={{
              width: 32,
              height: 32,
              borderRadius: 6,
              border: 'none',
              background: isActive ? 'rgba(255, 255, 255, 0.2)' : 'transparent',
              color: 'white',
              fontSize: 16,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s ease',
              opacity: isActive ? 1 : 0.6,
            }}
          >
            {option.icon}
          </button>
        );
      })}
    </div>
  );
}
