import { useState } from 'react';

// 路線配置
const LINE_CONFIG = {
  R: { color: '#d90023', label: 'R', name: '紅線' },
  O: { color: '#f8b61c', label: 'O', name: '橘線' },
  G: { color: '#008659', label: 'G', name: '綠線' },
  BL: { color: '#0070c0', label: 'BL', name: '藍線' },
  BR: { color: '#c48c31', label: 'BR', name: '文湖線' },
  K: { color: '#8cc540', label: 'K', name: '安坑輕軌' },
  V: { color: '#a4ce4e', label: 'V', name: '淡海輕軌' },
};

interface LineFilterProps {
  visibleLines: Set<string>;
  onToggleLine: (lineId: string) => void;
}

export function LineFilter({ visibleLines, onToggleLine }: LineFilterProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 210, // 控制面板上方
        left: 20,
        zIndex: 10,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontFamily: 'system-ui',
      }}
    >
      {/* MRT 按鈕 */}
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          padding: '8px 14px',
          borderRadius: 20,
          border: '2px solid white',
          background: 'rgba(0, 0, 0, 0.75)',
          color: 'white',
          fontSize: 13,
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          transition: 'all 0.2s ease',
        }}
      >
        <span>MRT</span>
        <span style={{
          fontSize: 10,
          transition: 'transform 0.3s ease',
          transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
        }}>
          ▶
        </span>
      </button>

      {/* 路線按鈕列表 */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          maxWidth: expanded ? 350 : 0,
          overflow: 'hidden',
          transition: 'max-width 0.3s ease-out, opacity 0.3s ease-out',
          opacity: expanded ? 1 : 0,
        }}
      >
        {Object.entries(LINE_CONFIG).map(([lineId, config]) => {
          const isVisible = visibleLines.has(lineId);
          return (
            <button
              key={lineId}
              onClick={() => onToggleLine(lineId)}
              title={config.name}
              style={{
                width: 40,
                height: 40,
                borderRadius: '50%',
                border: '2px solid white',
                background: isVisible ? config.color : 'rgba(60, 60, 60, 0.8)',
                color: 'white',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                opacity: isVisible ? 1 : 0.4,
                transition: 'all 0.2s ease',
                boxShadow: isVisible ? `0 0 8px ${config.color}` : 'none',
              }}
            >
              {config.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
