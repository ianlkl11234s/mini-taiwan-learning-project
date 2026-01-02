import type { VisualTheme } from './ThemeToggle';

// 城市配置
const CITIES = {
  TPE: {
    label: 'TPE',
    name: '台北',
    center: [121.5170, 25.0478] as [number, number],
    zoom: 12,
  },
  TXG: {
    label: 'TXG',
    name: '台中',
    center: [120.6847, 24.1472] as [number, number],
    zoom: 12,
  },
  KHH: {
    label: 'KHH',
    name: '高雄',
    center: [120.3017, 22.6274] as [number, number],
    zoom: 12,
  },
};

export type CityId = keyof typeof CITIES;

interface CitySelectorProps {
  onCitySelect: (center: [number, number], zoom: number) => void;
  selectedCity?: CityId | null;
  visualTheme?: VisualTheme;
}

export function CitySelector({
  onCitySelect,
  selectedCity,
  visualTheme = 'dark',
}: CitySelectorProps) {
  const isDark = visualTheme === 'dark';
  const colors = {
    bgInactive: isDark ? 'rgba(0, 0, 0, 0.5)' : 'rgba(255, 255, 255, 0.7)',
    bgActive: isDark ? 'rgba(0, 0, 0, 0.85)' : 'rgba(255, 255, 255, 0.95)',
    textInactive: isDark ? '#999' : '#666',
    textActive: isDark ? 'white' : '#333',
    borderInactive: isDark ? '#666' : '#aaa',
    borderActive: isDark ? 'white' : '#333',
  };

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 255,
        left: 20,
        zIndex: 10,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontFamily: 'system-ui',
      }}
    >
      {Object.entries(CITIES).map(([cityId, config]) => {
        const isSelected = selectedCity === cityId;
        return (
          <button
            key={cityId}
            onClick={() => onCitySelect(config.center, config.zoom)}
            title={config.name}
            style={{
              padding: '6px 12px',
              borderRadius: 16,
              border: isSelected
                ? `2px solid ${colors.borderActive}`
                : `2px solid ${colors.borderInactive}`,
              background: isSelected ? colors.bgActive : colors.bgInactive,
              color: isSelected ? colors.textActive : colors.textInactive,
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              backdropFilter: 'blur(8px)',
            }}
          >
            {config.label}
          </button>
        );
      })}
    </div>
  );
}

export { CITIES };
