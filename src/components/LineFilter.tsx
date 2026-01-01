import { useState } from 'react';

// MRT 路線配置
const MRT_LINES = {
  R: { color: '#d90023', label: 'R', name: '紅線' },
  O: { color: '#f8b61c', label: 'O', name: '橘線' },
  Y: { color: '#fedb00', label: 'Y', name: '環狀線' },
  G: { color: '#008659', label: 'G', name: '綠線' },
  BL: { color: '#0070c0', label: 'BL', name: '藍線' },
  BR: { color: '#c48c31', label: 'BR', name: '文湖線' },
  A: { color: '#8246af', label: 'A', name: '機場捷運' },
  K: { color: '#8cc540', label: 'K', name: '安坑輕軌' },
  V: { color: '#a4ce4e', label: 'V', name: '淡海輕軌' },
};

// Cable 路線配置
const CABLE_LINES = {
  MK: { color: '#06b8e6', label: 'MK', name: '貓空纜車' },
};

// MK 三段式狀態
export type MKFilterState = 'full' | 'tracks-only' | 'hidden';

interface LineFilterProps {
  visibleLines: Set<string>;
  onToggleLine: (lineId: string) => void;
  mkState: MKFilterState;
  onMKStateChange: (state: MKFilterState) => void;
}

type ExpandedCategory = 'mrt' | 'cable' | null;

export function LineFilter({
  visibleLines,
  onToggleLine,
  mkState,
  onMKStateChange,
}: LineFilterProps) {
  const [expanded, setExpanded] = useState<ExpandedCategory>(null);

  const handleCategoryClick = (category: ExpandedCategory) => {
    // 如果點擊已展開的分類，則收起；否則展開該分類
    setExpanded(expanded === category ? null : category);
  };

  // MK 三段式切換
  const handleMKClick = () => {
    const nextState: MKFilterState =
      mkState === 'full' ? 'tracks-only' :
      mkState === 'tracks-only' ? 'hidden' : 'full';
    onMKStateChange(nextState);
  };

  // MK 狀態對應的視覺效果
  const getMKStyle = () => {
    const config = CABLE_LINES.MK;
    switch (mkState) {
      case 'full':
        return {
          background: config.color,
          opacity: 1,
          boxShadow: `0 0 8px ${config.color}`,
          border: '2px solid white',
        };
      case 'tracks-only':
        return {
          background: config.color,
          opacity: 0.5,
          boxShadow: 'none',
          border: '2px dashed white',
        };
      case 'hidden':
        return {
          background: 'rgba(60, 60, 60, 0.8)',
          opacity: 0.4,
          boxShadow: 'none',
          border: '2px solid white',
        };
    }
  };

  // MK 狀態 tooltip
  const getMKTooltip = () => {
    switch (mkState) {
      case 'full': return '貓空纜車 (全部顯示)';
      case 'tracks-only': return '貓空纜車 (僅軌道與車站)';
      case 'hidden': return '貓空纜車 (隱藏)';
    }
  };

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 210,
        left: 20,
        zIndex: 10,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontFamily: 'system-ui',
      }}
    >
      {/* MRT 分類按鈕 */}
      <button
        onClick={() => handleCategoryClick('mrt')}
        style={{
          padding: '8px 14px',
          borderRadius: 20,
          border: expanded === 'mrt' ? '2px solid white' : '2px solid #666',
          background: expanded === 'mrt' ? 'rgba(0, 0, 0, 0.85)' : 'rgba(0, 0, 0, 0.5)',
          color: expanded === 'mrt' ? 'white' : '#999',
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
          transform: expanded === 'mrt' ? 'rotate(90deg)' : 'rotate(0deg)',
        }}>
          ▶
        </span>
      </button>

      {/* MRT 路線按鈕列表 */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          maxWidth: expanded === 'mrt' ? 400 : 0,
          overflow: 'hidden',
          transition: 'max-width 0.3s ease-out, opacity 0.3s ease-out',
          opacity: expanded === 'mrt' ? 1 : 0,
        }}
      >
        {Object.entries(MRT_LINES).map(([lineId, config]) => {
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

      {/* Cable 分類按鈕 */}
      <button
        onClick={() => handleCategoryClick('cable')}
        style={{
          padding: '8px 14px',
          borderRadius: 20,
          border: expanded === 'cable' ? '2px solid white' : '2px solid #666',
          background: expanded === 'cable' ? 'rgba(0, 0, 0, 0.85)' : 'rgba(0, 0, 0, 0.5)',
          color: expanded === 'cable' ? 'white' : '#999',
          fontSize: 13,
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          transition: 'all 0.2s ease',
        }}
      >
        <span>Cable</span>
        <span style={{
          fontSize: 10,
          transition: 'transform 0.3s ease',
          transform: expanded === 'cable' ? 'rotate(90deg)' : 'rotate(0deg)',
        }}>
          ▶
        </span>
      </button>

      {/* Cable 路線按鈕列表 */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          maxWidth: expanded === 'cable' ? 60 : 0,
          overflow: 'hidden',
          transition: 'max-width 0.3s ease-out, opacity 0.3s ease-out',
          opacity: expanded === 'cable' ? 1 : 0,
        }}
      >
        <button
          onClick={handleMKClick}
          title={getMKTooltip()}
          style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            color: 'white',
            fontSize: 12,
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease',
            ...getMKStyle(),
          }}
        >
          MK
        </button>
      </div>
    </div>
  );
}
