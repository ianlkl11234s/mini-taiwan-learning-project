import { useState } from 'react';
import type { VisualTheme } from './ThemeToggle';

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

// HSR 路線配置
const HSR_LINES = {
  THSR: { color: '#f47920', label: 'HSR', name: '台灣高鐵' },
};

// MK 三段式狀態
export type MKFilterState = 'full' | 'tracks-only' | 'hidden';

// THSR 三段式狀態
export type ThsrFilterState = 'full' | 'tracks-only' | 'hidden';

// KRTC 三段式狀態
export type KrtcFilterState = 'full' | 'tracks-only' | 'hidden';

interface LineFilterProps {
  visibleLines: Set<string>;
  onToggleLine: (lineId: string) => void;
  onToggleAllMrt: (visible: boolean) => void;
  mkState: MKFilterState;
  onMKStateChange: (state: MKFilterState) => void;
  thsrState: ThsrFilterState;
  onThsrStateChange: (state: ThsrFilterState) => void;
  krtcState: KrtcFilterState;
  onKrtcStateChange: (state: KrtcFilterState) => void;
  visualTheme?: VisualTheme;
}

type ExpandedCategory = 'mrt' | 'cable' | 'hsr' | 'krtc' | null;

export function LineFilter({
  visibleLines,
  onToggleLine,
  onToggleAllMrt,
  mkState,
  onMKStateChange,
  thsrState,
  onThsrStateChange,
  krtcState,
  onKrtcStateChange,
  visualTheme = 'dark',
}: LineFilterProps) {
  const [expanded, setExpanded] = useState<ExpandedCategory>(null);

  // 計算 MRT 路線的顯示狀態
  const mrtLineIds = Object.keys(MRT_LINES);
  const visibleMrtCount = mrtLineIds.filter(id => visibleLines.has(id)).length;
  const allMrtVisible = visibleMrtCount === mrtLineIds.length;
  const noneMrtVisible = visibleMrtCount === 0;

  // 主題顏色
  const isDark = visualTheme === 'dark';
  const colors = {
    bgInactive: isDark ? 'rgba(0, 0, 0, 0.5)' : 'rgba(255, 255, 255, 0.7)',
    bgActive: isDark ? 'rgba(0, 0, 0, 0.85)' : 'rgba(255, 255, 255, 0.95)',
    textInactive: isDark ? '#999' : '#666',
    textActive: isDark ? 'white' : '#333',
    borderInactive: isDark ? '#666' : '#aaa',
    borderActive: isDark ? 'white' : '#333',
    disabledBg: isDark ? 'rgba(60, 60, 60, 0.8)' : 'rgba(200, 200, 200, 0.8)',
  };

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

  // THSR 三段式切換
  const handleThsrClick = () => {
    const nextState: ThsrFilterState =
      thsrState === 'full' ? 'tracks-only' :
      thsrState === 'tracks-only' ? 'hidden' : 'full';
    onThsrStateChange(nextState);
  };

  // KRTC 三段式切換
  const handleKrtcClick = () => {
    const nextState: KrtcFilterState =
      krtcState === 'full' ? 'tracks-only' :
      krtcState === 'tracks-only' ? 'hidden' : 'full';
    onKrtcStateChange(nextState);
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
          border: `2px solid ${colors.borderActive}`,
        };
      case 'tracks-only':
        return {
          background: config.color,
          opacity: 0.5,
          boxShadow: 'none',
          border: `2px dashed ${colors.borderActive}`,
        };
      case 'hidden':
        return {
          background: colors.disabledBg,
          opacity: 0.4,
          boxShadow: 'none',
          border: `2px solid ${colors.borderActive}`,
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

  // THSR 狀態對應的視覺效果
  const getThsrStyle = () => {
    const config = HSR_LINES.THSR;
    switch (thsrState) {
      case 'full':
        return {
          background: config.color,
          opacity: 1,
          boxShadow: `0 0 8px ${config.color}`,
          border: `2px solid ${colors.borderActive}`,
        };
      case 'tracks-only':
        return {
          background: config.color,
          opacity: 0.5,
          boxShadow: 'none',
          border: `2px dashed ${colors.borderActive}`,
        };
      case 'hidden':
        return {
          background: colors.disabledBg,
          opacity: 0.4,
          boxShadow: 'none',
          border: `2px solid ${colors.borderActive}`,
        };
    }
  };

  // THSR 狀態 tooltip
  const getThsrTooltip = () => {
    switch (thsrState) {
      case 'full': return '台灣高鐵 (全部顯示)';
      case 'tracks-only': return '台灣高鐵 (僅軌道與車站)';
      case 'hidden': return '台灣高鐵 (隱藏)';
    }
  };

  // KRTC 狀態對應的視覺效果
  const getKrtcStyle = () => {
    switch (krtcState) {
      case 'full':
        return {
          background: 'linear-gradient(135deg, #f8981d, #e2211c)',
          opacity: 1,
          boxShadow: '0 0 8px rgba(248, 152, 29, 0.5)',
          border: `2px solid ${colors.borderActive}`,
        };
      case 'tracks-only':
        return {
          background: 'linear-gradient(135deg, #f8981d, #e2211c)',
          opacity: 0.5,
          boxShadow: 'none',
          border: `2px dashed ${colors.borderActive}`,
        };
      case 'hidden':
        return {
          background: colors.disabledBg,
          opacity: 0.4,
          boxShadow: 'none',
          border: `2px solid ${colors.borderActive}`,
        };
    }
  };

  // KRTC 狀態 tooltip
  const getKrtcTooltip = () => {
    switch (krtcState) {
      case 'full': return '高雄捷運 (全部顯示)';
      case 'tracks-only': return '高雄捷運 (僅軌道與車站)';
      case 'hidden': return '高雄捷運 (隱藏)';
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
          border: expanded === 'mrt' ? `2px solid ${colors.borderActive}` : `2px solid ${colors.borderInactive}`,
          background: expanded === 'mrt' ? colors.bgActive : colors.bgInactive,
          color: expanded === 'mrt' ? colors.textActive : colors.textInactive,
          fontSize: 13,
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          transition: 'all 0.2s ease',
          backdropFilter: 'blur(8px)',
        }}
      >
        <span>TPE MRT</span>
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
          maxWidth: expanded === 'mrt' ? 500 : 0,
          overflow: 'hidden',
          transition: 'max-width 0.3s ease-out, opacity 0.3s ease-out',
          opacity: expanded === 'mrt' ? 1 : 0,
        }}
      >
        {/* All 切換按鈕 */}
        <button
          onClick={() => onToggleAllMrt(!allMrtVisible)}
          title={allMrtVisible ? '隱藏全部 MRT' : '顯示全部 MRT'}
          style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            border: `2px solid ${colors.borderActive}`,
            background: allMrtVisible
              ? 'linear-gradient(135deg, #d90023, #f8b61c, #008659, #0070c0)'
              : noneMrtVisible
              ? colors.disabledBg
              : 'linear-gradient(135deg, rgba(217,0,35,0.5), rgba(248,182,28,0.5), rgba(0,134,89,0.5), rgba(0,112,192,0.5))',
            color: colors.textActive,
            fontSize: 10,
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            opacity: noneMrtVisible ? 0.4 : 1,
            transition: 'all 0.2s ease',
            boxShadow: allMrtVisible ? '0 0 8px rgba(255,255,255,0.5)' : 'none',
          }}
        >
          All
        </button>
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
                border: `2px solid ${colors.borderActive}`,
                background: isVisible ? config.color : colors.disabledBg,
                color: colors.textActive,
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

      {/* KHH MRT 分類按鈕 */}
      <button
        onClick={() => handleCategoryClick('krtc')}
        style={{
          padding: '8px 14px',
          borderRadius: 20,
          border: expanded === 'krtc' ? `2px solid ${colors.borderActive}` : `2px solid ${colors.borderInactive}`,
          background: expanded === 'krtc' ? colors.bgActive : colors.bgInactive,
          color: expanded === 'krtc' ? colors.textActive : colors.textInactive,
          fontSize: 13,
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          transition: 'all 0.2s ease',
          backdropFilter: 'blur(8px)',
        }}
      >
        <span>KHH MRT</span>
        <span style={{
          fontSize: 10,
          transition: 'transform 0.3s ease',
          transform: expanded === 'krtc' ? 'rotate(90deg)' : 'rotate(0deg)',
        }}>
          ▶
        </span>
      </button>

      {/* KHH MRT 路線按鈕列表 */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          maxWidth: expanded === 'krtc' ? 60 : 0,
          overflow: 'hidden',
          transition: 'max-width 0.3s ease-out, opacity 0.3s ease-out',
          opacity: expanded === 'krtc' ? 1 : 0,
        }}
      >
        <button
          onClick={handleKrtcClick}
          title={getKrtcTooltip()}
          style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            color: colors.textActive,
            fontSize: 10,
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease',
            ...getKrtcStyle(),
          }}
        >
          高捷
        </button>
      </div>

      {/* HSR 分類按鈕 */}
      <button
        onClick={() => handleCategoryClick('hsr')}
        style={{
          padding: '8px 14px',
          borderRadius: 20,
          border: expanded === 'hsr' ? `2px solid ${colors.borderActive}` : `2px solid ${colors.borderInactive}`,
          background: expanded === 'hsr' ? colors.bgActive : colors.bgInactive,
          color: expanded === 'hsr' ? colors.textActive : colors.textInactive,
          fontSize: 13,
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          transition: 'all 0.2s ease',
          backdropFilter: 'blur(8px)',
        }}
      >
        <span>HSR</span>
        <span style={{
          fontSize: 10,
          transition: 'transform 0.3s ease',
          transform: expanded === 'hsr' ? 'rotate(90deg)' : 'rotate(0deg)',
        }}>
          ▶
        </span>
      </button>

      {/* HSR 路線按鈕列表 */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          maxWidth: expanded === 'hsr' ? 60 : 0,
          overflow: 'hidden',
          transition: 'max-width 0.3s ease-out, opacity 0.3s ease-out',
          opacity: expanded === 'hsr' ? 1 : 0,
        }}
      >
        <button
          onClick={handleThsrClick}
          title={getThsrTooltip()}
          style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            color: colors.textActive,
            fontSize: 10,
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease',
            ...getThsrStyle(),
          }}
        >
          高鐵
        </button>
      </div>

      {/* Cable 分類按鈕 */}
      <button
        onClick={() => handleCategoryClick('cable')}
        style={{
          padding: '8px 14px',
          borderRadius: 20,
          border: expanded === 'cable' ? `2px solid ${colors.borderActive}` : `2px solid ${colors.borderInactive}`,
          background: expanded === 'cable' ? colors.bgActive : colors.bgInactive,
          color: expanded === 'cable' ? colors.textActive : colors.textInactive,
          fontSize: 13,
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          transition: 'all 0.2s ease',
          backdropFilter: 'blur(8px)',
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
            color: colors.textActive,
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
