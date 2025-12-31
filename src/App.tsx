import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useData } from './hooks/useData';
import { TimeEngine } from './engines/TimeEngine';
import { TrainEngine, type Train } from './engines/TrainEngine';
import { TimeControl } from './components/TimeControl';
import { LineFilter } from './components/LineFilter';
import { TrainHistogram } from './components/TrainHistogram';
import { useTrainCountHistogram } from './hooks/useTrainCountHistogram';

// 設定 Mapbox Token
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || '';

// 軌道顏色
const TRACK_COLORS = {
  R: '#d90023',   // 紅線
  BL: '#0070c0',  // 藍線
  G: '#008659',   // 綠線
  G3: '#66c4a0',  // 小碧潭支線（淺綠色）
  O: '#f8b61c',   // 橘線
  V: '#a4ce4e',   // 淡海輕軌
  BR: '#c48c31',  // 文湖線（棕色）
  K: '#8cc540',   // 安坑輕軌（草綠色）
  A: '#8246af',   // 機場捷運（紫色）
};

// 列車顏色（依路線與方向區分）
const TRAIN_COLORS = {
  // 紅線
  R_0: '#d90023',   // 往淡水（北上/direction 0）- 深紅色
  R_1: '#ff8a8a',   // 往象山（南下/direction 1）- 淡紅色
  // 藍線
  BL_0: '#0070c0',  // 往南港展覽館（往東/direction 0）- 深藍色
  BL_1: '#80bfff',  // 往頂埔（往西/direction 1）- 淡藍色
  // 綠線
  G_0: '#008659',   // 往新店（南下/direction 0）- 深綠色
  G_1: '#66c4a0',   // 往松山（北上/direction 1）- 淡綠色
  // 橘線
  O_0: '#f8b61c',   // 往南勢角（direction 0）- 深橘色
  O_1: '#ffd966',   // 往迴龍/蘆洲（direction 1）- 淡橘色
  // 文湖線
  BR_0: '#c48c31',  // 往南港展覽館（direction 0）- 深棕色
  BR_1: '#d4a65a',  // 往動物園（direction 1）- 淡棕色
  // 安坑輕軌
  K_0: '#8cc540',   // 往十四張（direction 0）- 深草綠色
  K_1: '#b8e080',   // 往雙城（direction 1）- 淡草綠色
  // 淡海輕軌
  V_0: '#a4ce4e',   // 綠山線/藍海線 往崁頂/台北海洋大學（direction 0）- 深黃綠色
  V_1: '#c8e588',   // 綠山線/藍海線 往紅樹林/淡水漁人碼頭（direction 1）- 淡黃綠色
  // 機場捷運
  A_0: '#67378b',   // 去程（往機場/老街溪）- 深紫色
  A_1: '#a778c9',   // 回程（往台北）- 淡紫色
};

// 判斷列車顏色：根據路線和方向
function getTrainColor(trackId: string): string {
  let lineId: string;
  if (trackId.startsWith('K')) {
    lineId = 'K';
  } else if (trackId.startsWith('V')) {
    lineId = 'V';
  } else if (trackId.startsWith('BR')) {
    lineId = 'BR';
  } else if (trackId.startsWith('BL')) {
    lineId = 'BL';
  } else if (trackId.startsWith('G')) {
    lineId = 'G';
  } else if (trackId.startsWith('O')) {
    lineId = 'O';
  } else if (trackId.startsWith('A')) {
    lineId = 'A';
  } else {
    lineId = 'R';
  }
  const direction = trackId.endsWith('-0') ? '0' : '1';
  return TRAIN_COLORS[`${lineId}_${direction}` as keyof typeof TRAIN_COLORS];
}

function App() {
  // 資料載入
  const { tracks, stations, schedules, trackMap, stationProgress, loading, error } = useData();

  // 預計算直方圖資料
  const histogramData = useTrainCountHistogram(schedules);

  // 地圖狀態
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const trainMarkers = useRef<Map<string, mapboxgl.Marker>>(new Map());

  // 時間引擎
  const timeEngineRef = useRef<TimeEngine | null>(null);
  const [timeEngineReady, setTimeEngineReady] = useState(false);
  const [currentTime, setCurrentTime] = useState('06:00:00');
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(90);

  // 列車引擎
  const trainEngineRef = useRef<TrainEngine | null>(null);
  const [trains, setTrains] = useState<Train[]>([]);

  // 圖例收合狀態（預設收合）
  const [legendCollapsed, setLegendCollapsed] = useState(true);

  // 路線篩選狀態
  const [visibleLines, setVisibleLines] = useState<Set<string>>(
    new Set(['R', 'BL', 'G', 'O', 'BR', 'K', 'V', 'A'])
  );

  // 切換路線可見性
  const handleToggleLine = useCallback((lineId: string) => {
    setVisibleLines(prev => {
      const next = new Set(prev);
      if (next.has(lineId)) {
        next.delete(lineId);
      } else {
        next.add(lineId);
      }
      return next;
    });
  }, []);

  // 根據可見路線過濾列車
  const filteredTrains = useMemo(() => {
    return trains.filter(train => {
      // 從 trackId 判斷路線
      let lineId: string;
      if (train.trackId.startsWith('K')) {
        lineId = 'K';
      } else if (train.trackId.startsWith('V')) {
        lineId = 'V';
      } else if (train.trackId.startsWith('BR')) {
        lineId = 'BR';
      } else if (train.trackId.startsWith('BL')) {
        lineId = 'BL';
      } else if (train.trackId.startsWith('G')) {
        lineId = 'G';
      } else if (train.trackId.startsWith('O')) {
        lineId = 'O';
      } else if (train.trackId.startsWith('A')) {
        lineId = 'A';
      } else {
        lineId = 'R';
      }
      return visibleLines.has(lineId);
    });
  }, [trains, visibleLines]);

  // 初始化地圖 - 當 loading 完成後才初始化
  useEffect(() => {
    if (loading || !mapContainer.current || map.current) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [121.52, 25.02],  // 調整以顯示紅線+藍線
      zoom: 10.8,  // 稍微縮小以容納兩條線
    });

    map.current.on('load', () => {
      setMapLoaded(true);
    });

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');

    // 監聽容器尺寸變化，自動調整地圖大小
    const resizeObserver = new ResizeObserver(() => {
      if (map.current) {
        map.current.resize();
      }
    });
    resizeObserver.observe(mapContainer.current);

    return () => {
      resizeObserver.disconnect();
      map.current?.remove();
      map.current = null;
    };
  }, [loading]);

  // 載入軌道圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !tracks) return;

    if (map.current.getSource('tracks')) {
      map.current.removeLayer('tracks-line');
      map.current.removeSource('tracks');
    }

    map.current.addSource('tracks', {
      type: 'geojson',
      data: tracks as GeoJSON.FeatureCollection,
    });

    map.current.addLayer({
      id: 'tracks-line',
      type: 'line',
      source: 'tracks',
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        // 依路線設定顏色：G-3 小碧潭支線（淺綠）, K 安坑輕軌, V 淡海輕軌, G 綠線, BL 藍線, BR 文湖線, O 橘線, R 紅線
        'line-color': [
          'case',
          ['in', 'G-3', ['get', 'track_id']], TRACK_COLORS.G3,  // 小碧潭支線（淺綠色）
          ['==', ['get', 'line_id'], 'K'], TRACK_COLORS.K,      // 安坑輕軌
          ['==', ['get', 'line_id'], 'V'], TRACK_COLORS.V,      // 淡海輕軌
          ['==', ['get', 'line_id'], 'G'], TRACK_COLORS.G,
          ['==', ['get', 'line_id'], 'BL'], TRACK_COLORS.BL,
          ['==', ['get', 'line_id'], 'BR'], TRACK_COLORS.BR,
          ['==', ['get', 'line_id'], 'O'], TRACK_COLORS.O,
          ['==', ['get', 'line_id'], 'A'], TRACK_COLORS.A,      // 機場捷運
          TRACK_COLORS.R
        ],
        'line-width': 4,
        // 顯示規則：使用 slice 匹配各線所有軌道 (包含主線、區間車、首班車)
        'line-opacity': [
          'case',
          ['==', ['slice', ['get', 'track_id'], 0, 2], 'K-'], 0.8,   // 所有 K 線軌道可見 (安坑輕軌)
          ['==', ['slice', ['get', 'track_id'], 0, 2], 'V-'], 0.8,   // 所有 V 線軌道可見 (淡海輕軌)
          ['==', ['slice', ['get', 'track_id'], 0, 2], 'R-'], 0.8,   // 所有 R 線軌道可見 (含首班車)
          ['==', ['slice', ['get', 'track_id'], 0, 3], 'BL-'], 0.8,  // 所有 BL 線軌道可見 (含首班車)
          ['==', ['slice', ['get', 'track_id'], 0, 3], 'BR-'], 0.8,  // 所有 BR 線軌道可見 (文湖線)
          ['==', ['slice', ['get', 'track_id'], 0, 2], 'G-'], 0.8,   // 所有 G 線軌道可見 (含首班車)
          ['==', ['slice', ['get', 'track_id'], 0, 2], 'O-'], 0.8,   // 所有 O 線軌道可見 (含首班車)
          ['==', ['slice', ['get', 'track_id'], 0, 2], 'A-'], 0.8,   // 所有 A 線軌道可見 (機場捷運)
          0.0 // 其他軌道透明
        ],
      },
    });
  }, [mapLoaded, tracks]);

  // 更新軌道可見性（當 visibleLines 變化時）
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (!map.current.getLayer('tracks-line')) return;

    // 根據 visibleLines 動態設定 opacity
    map.current.setPaintProperty('tracks-line', 'line-opacity', [
      'case',
      ['all',
        ['==', ['slice', ['get', 'track_id'], 0, 2], 'K-'],
        visibleLines.has('K')
      ], 0.8,
      ['all',
        ['==', ['slice', ['get', 'track_id'], 0, 2], 'V-'],
        visibleLines.has('V')
      ], 0.8,
      ['all',
        ['==', ['slice', ['get', 'track_id'], 0, 2], 'R-'],
        visibleLines.has('R')
      ], 0.8,
      ['all',
        ['==', ['slice', ['get', 'track_id'], 0, 3], 'BL-'],
        visibleLines.has('BL')
      ], 0.8,
      ['all',
        ['==', ['slice', ['get', 'track_id'], 0, 3], 'BR-'],
        visibleLines.has('BR')
      ], 0.8,
      ['all',
        ['==', ['slice', ['get', 'track_id'], 0, 2], 'G-'],
        visibleLines.has('G')
      ], 0.8,
      ['all',
        ['==', ['slice', ['get', 'track_id'], 0, 2], 'O-'],
        visibleLines.has('O')
      ], 0.8,
      ['all',
        ['==', ['slice', ['get', 'track_id'], 0, 2], 'A-'],
        visibleLines.has('A')
      ], 0.8,
      0.0
    ]);
  }, [mapLoaded, visibleLines]);

  // 載入車站圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !stations) return;

    if (map.current.getSource('stations')) {
      map.current.removeLayer('stations-circle');
      map.current.removeLayer('stations-label');
      map.current.removeSource('stations');
    }

    map.current.addSource('stations', {
      type: 'geojson',
      data: stations as GeoJSON.FeatureCollection,
    });

    map.current.addLayer({
      id: 'stations-circle',
      type: 'circle',
      source: 'stations',
      paint: {
        'circle-radius': 5,
        'circle-color': '#000000',  // 黑色填充
        // 依路線設定邊線顏色：K 開頭 → 安坑輕軌, V 開頭 → 淡海輕軌, G 開頭 → 綠線, BL 開頭 → 藍線, BR 開頭 → 文湖線, O 開頭 → 橘線, 其餘 → 紅線
        'circle-stroke-color': [
          'case',
          ['==', ['slice', ['get', 'station_id'], 0, 1], 'K'], TRACK_COLORS.K,
          ['==', ['slice', ['get', 'station_id'], 0, 1], 'V'], TRACK_COLORS.V,
          ['==', ['slice', ['get', 'station_id'], 0, 1], 'G'], TRACK_COLORS.G,
          ['==', ['slice', ['get', 'station_id'], 0, 2], 'BL'], TRACK_COLORS.BL,
          ['==', ['slice', ['get', 'station_id'], 0, 2], 'BR'], TRACK_COLORS.BR,
          ['==', ['slice', ['get', 'station_id'], 0, 1], 'O'], TRACK_COLORS.O,
          ['==', ['slice', ['get', 'station_id'], 0, 1], 'A'], TRACK_COLORS.A,  // 機場捷運
          TRACK_COLORS.R
        ],
        'circle-stroke-width': 1.8,
      },
    });

    map.current.addLayer({
      id: 'stations-label',
      type: 'symbol',
      source: 'stations',
      layout: {
        'text-field': ['get', 'name_zh'],
        'text-size': 11,
        'text-offset': [0, 1.5],
        'text-anchor': 'top',
      },
      paint: {
        'text-color': '#ffffff',
        'text-halo-color': '#000000',
        'text-halo-width': 1,
      },
    });
  }, [mapLoaded, stations]);

  // 更新車站可見性（當 visibleLines 變化時）
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (!map.current.getLayer('stations-circle')) return;

    // 根據 visibleLines 動態設定車站 opacity
    const stationOpacityExpr: mapboxgl.Expression = [
      'case',
      ['all',
        ['==', ['slice', ['get', 'station_id'], 0, 1], 'K'],
        visibleLines.has('K')
      ], 1,
      ['all',
        ['==', ['slice', ['get', 'station_id'], 0, 1], 'V'],
        visibleLines.has('V')
      ], 1,
      ['all',
        ['==', ['slice', ['get', 'station_id'], 0, 1], 'R'],
        visibleLines.has('R')
      ], 1,
      ['all',
        ['==', ['slice', ['get', 'station_id'], 0, 2], 'BL'],
        visibleLines.has('BL')
      ], 1,
      ['all',
        ['==', ['slice', ['get', 'station_id'], 0, 2], 'BR'],
        visibleLines.has('BR')
      ], 1,
      ['all',
        ['==', ['slice', ['get', 'station_id'], 0, 1], 'G'],
        visibleLines.has('G')
      ], 1,
      ['all',
        ['==', ['slice', ['get', 'station_id'], 0, 1], 'O'],
        visibleLines.has('O')
      ], 1,
      ['all',
        ['==', ['slice', ['get', 'station_id'], 0, 1], 'A'],
        visibleLines.has('A')
      ], 1,
      0
    ];

    map.current.setPaintProperty('stations-circle', 'circle-opacity', stationOpacityExpr);
    map.current.setPaintProperty('stations-circle', 'circle-stroke-opacity', stationOpacityExpr);
    map.current.setLayoutProperty('stations-label', 'visibility',
      visibleLines.size > 0 ? 'visible' : 'none'
    );
    // 標籤使用相同的 opacity 邏輯
    map.current.setPaintProperty('stations-label', 'text-opacity', stationOpacityExpr);
  }, [mapLoaded, visibleLines]);

  // 初始化時間引擎
  useEffect(() => {
    const engine = new TimeEngine({
      speed: 90, // 初始速度與 UI 同步
      onTick: (time) => {
        setCurrentTime(
          `${time.getHours().toString().padStart(2, '0')}:${time
            .getMinutes()
            .toString()
            .padStart(2, '0')}:${time.getSeconds().toString().padStart(2, '0')}`
        );
      },
    });
    timeEngineRef.current = engine;
    setTimeEngineReady(true);

    return () => {
      engine.destroy();
      setTimeEngineReady(false);
    };
  }, []);

  // 初始化列車引擎並訂閱時間更新
  // 注意：將兩個 effect 合併以避免競態條件，使用 timeEngineReady 狀態確保順序
  useEffect(() => {
    // 確保所有必要資料都已載入，且時間引擎已準備好
    if (!timeEngineReady || !timeEngineRef.current) return;
    if (schedules.size === 0 || trackMap.size === 0 || !stationProgress) return;

    // 建立列車引擎
    const trainEngine = new TrainEngine({
      schedules,
      tracks: trackMap,
      stationProgress,
    });
    trainEngineRef.current = trainEngine;

    // 訂閱時間更新
    const unsubscribe = timeEngineRef.current.onTick(() => {
      if (timeEngineRef.current) {
        const timeSeconds = timeEngineRef.current.getTimeOfDaySeconds();
        const activeTrains = trainEngine.update(timeSeconds);
        setTrains(activeTrains);
      }
    });

    // 初始更新 - 確保立即顯示列車
    const timeSeconds = timeEngineRef.current.getTimeOfDaySeconds();
    setTrains(trainEngine.update(timeSeconds));

    return () => {
      unsubscribe();
      trainEngineRef.current = null;
    };
  }, [timeEngineReady, schedules, trackMap, stationProgress]);

  // 更新列車標記
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    const activeTrainIds = new Set(filteredTrains.map((t) => t.trainId));
    for (const [trainId, marker] of trainMarkers.current) {
      if (!activeTrainIds.has(trainId)) {
        marker.remove();
        trainMarkers.current.delete(trainId);
      }
    }

    for (const train of filteredTrains) {
      let marker = trainMarkers.current.get(train.trainId);
      const isStopped = train.status === 'stopped';
      const isColliding = train.isColliding;
      const baseColor = getTrainColor(train.trackId);  // 依路線和方向區分顏色
      // 碰撞時使用警示色
      const displayColor = isColliding ? '#ffcc00' : baseColor;

      if (!marker) {
        const el = document.createElement('div');
        el.className = 'train-marker';
        el.dataset.trainId = train.trainId;

        marker = new mapboxgl.Marker({
          element: el,
          anchor: 'center',  // 確保 marker 以中心點對齊座標
        })
          .setLngLat(train.position)
          .addTo(map.current!);

        trainMarkers.current.set(train.trainId, marker);
      }

      // 更新位置
      marker.setLngLat(train.position);

      // 更新樣式 (停站 vs 運行 vs 碰撞)
      const el = marker.getElement();
      // 基礎樣式：pointer-events: none 防止 hover 干擾定位
      const baseStyles = `
        pointer-events: none;
        border-radius: 50%;
        transition: width 0.3s ease, height 0.3s ease, box-shadow 0.3s ease;
      `;

      if (isColliding) {
        // 碰撞中：較大、有警示效果
        el.style.cssText = `
          ${baseStyles}
          width: 16px;
          height: 16px;
          background-color: ${displayColor};
          border: 3px solid #ffff00;
          box-shadow: 0 0 12px ${displayColor}, 0 0 20px rgba(255,255,0,0.7);
        `;
      } else if (isStopped) {
        // 停站中：較大、有脈動效果
        el.style.cssText = `
          ${baseStyles}
          width: 14px;
          height: 14px;
          background-color: ${displayColor};
          border: 3px solid #ffffff;
          box-shadow: 0 0 8px ${displayColor}, 0 0 12px rgba(255,255,255,0.5);
        `;
      } else {
        // 運行中：正常大小
        el.style.cssText = `
          ${baseStyles}
          width: 12px;
          height: 12px;
          background-color: ${displayColor};
          border: 2px solid #ffffff;
          box-shadow: 0 0 4px rgba(0,0,0,0.5);
        `;
      }
    }
  }, [mapLoaded, filteredTrains]);

  // 控制處理器
  const handleTogglePlay = useCallback(() => {
    if (!timeEngineRef.current) return;
    timeEngineRef.current.toggle();
    setIsPlaying(timeEngineRef.current.isRunning());
  }, []);

  const handleSpeedChange = useCallback((newSpeed: number) => {
    if (!timeEngineRef.current) return;
    timeEngineRef.current.setSpeed(newSpeed);
    setSpeed(newSpeed);
  }, []);

  const handleTimeChange = useCallback((seconds: number) => {
    if (!timeEngineRef.current) return;
    timeEngineRef.current.setTimeOfDay(seconds);

    if (trainEngineRef.current) {
      const activeTrains = trainEngineRef.current.update(seconds);
      setTrains(activeTrains);
    }
  }, []);

  // 載入中畫面
  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          background: '#1a1a1a',
          color: 'white',
          fontFamily: 'system-ui',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🚇</div>
          <div>載入資料中...</div>
        </div>
      </div>
    );
  }

  // 錯誤畫面
  if (error) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          background: '#1a1a1a',
          color: '#ff6b6b',
          fontFamily: 'system-ui',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
          <div>載入失敗: {error}</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      {/* 標題 */}
      <div
        style={{
          position: 'absolute',
          top: 20,
          left: 20,
          zIndex: 10,
          color: 'white',
          fontFamily: 'system-ui',
        }}
      >
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>
          Mini Taipei V3
        </h1>
        <p style={{ margin: '4px 0 0', fontSize: 14, color: '#888' }}>
          台北交通運輸模擬
        </p>
      </div>

      {/* 圖例 */}
      <div
        style={{
          position: 'absolute',
          top: 90,
          left: 20,
          zIndex: 10,
          background: 'rgba(0, 0, 0, 0.75)',
          borderRadius: 8,
          padding: '10px 14px',
          color: 'white',
          fontFamily: 'system-ui',
          fontSize: 12,
        }}
      >
        {/* 可點擊的標題 */}
        <div
          onClick={() => setLegendCollapsed(!legendCollapsed)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            cursor: 'pointer',
            userSelect: 'none',
            marginBottom: legendCollapsed ? 0 : 8,
          }}
        >
          <span style={{
            fontSize: 10,
            transition: 'transform 0.3s ease',
            transform: legendCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
            display: 'inline-block',
          }}>
            ▼
          </span>
          <span style={{ fontWeight: 600, color: '#aaa' }}>圖例</span>
        </div>

        {/* 可收合內容區 */}
        <div
          style={{
            maxHeight: legendCollapsed ? 0 : 400,
            overflow: 'hidden',
            transition: 'max-height 0.3s ease-out, opacity 0.3s ease-out',
            opacity: legendCollapsed ? 0 : 1,
          }}
        >
          {/* 紅線區塊 */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <div style={{ width: 20, height: 3, background: TRACK_COLORS.R, borderRadius: 2 }} />
              <span style={{ fontWeight: 500 }}>淡水信義線</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.R_0, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往淡水</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.R_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往象山</span>
            </div>
          </div>

          {/* 藍線區塊 */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <div style={{ width: 20, height: 3, background: TRACK_COLORS.BL, borderRadius: 2 }} />
              <span style={{ fontWeight: 500 }}>板南線</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.BL_0, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往南港展覽館</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.BL_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往頂埔</span>
            </div>
          </div>

          {/* 綠線區塊 */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <div style={{ width: 20, height: 3, background: TRACK_COLORS.G, borderRadius: 2 }} />
              <span style={{ fontWeight: 500 }}>松山新店線</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.G_0, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往新店</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.G_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往松山</span>
            </div>
          </div>

          {/* 小碧潭支線區塊 */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <div style={{ width: 20, height: 3, background: TRACK_COLORS.G3, borderRadius: 2 }} />
              <span style={{ fontWeight: 500 }}>小碧潭支線</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRACK_COLORS.G3, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>七張↔小碧潭</span>
            </div>
          </div>

          {/* 橘線區塊 */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <div style={{ width: 20, height: 3, background: TRACK_COLORS.O, borderRadius: 2 }} />
              <span style={{ fontWeight: 500 }}>中和新蘆線</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.O_0, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往南勢角</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.O_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往迴龍/蘆洲</span>
            </div>
          </div>

          {/* 文湖線區塊 */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <div style={{ width: 20, height: 3, background: TRACK_COLORS.BR, borderRadius: 2 }} />
              <span style={{ fontWeight: 500 }}>文湖線</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.BR_0, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往南港展覽館</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.BR_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往動物園</span>
            </div>
          </div>

          {/* 安坑輕軌區塊 */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <div style={{ width: 20, height: 3, background: TRACK_COLORS.K, borderRadius: 2 }} />
              <span style={{ fontWeight: 500 }}>安坑輕軌</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.K_0, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往十四張</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.K_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往雙城</span>
            </div>
          </div>

          {/* 淡海輕軌區塊 */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <div style={{ width: 20, height: 3, background: TRACK_COLORS.V, borderRadius: 2 }} />
              <span style={{ fontWeight: 500 }}>淡海輕軌</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.V_0, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往崁頂/台北海洋大學</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.V_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: '#ccc' }}>往紅樹林/淡水漁人碼頭</span>
            </div>
          </div>
        </div>
      </div>

      {/* 社群連結與提示 */}
      <div
        style={{
          position: 'absolute',
          top: 20,
          right: 60,
          zIndex: 10,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          fontFamily: 'system-ui',
        }}
      >
        <span style={{ fontSize: 12, color: '#888' }}>
          網站為學習性質，仍需持續優化中！
        </span>
        <a
          href="https://github.com/ianlkl11234s/mini-taiwan-learning-project"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: '#888', transition: 'color 0.2s' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
          onMouseLeave={(e) => (e.currentTarget.style.color = '#888')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
          </svg>
        </a>
        <a
          href="https://www.threads.com/@ianlkl1314"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: '#888', transition: 'color 0.2s' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
          onMouseLeave={(e) => (e.currentTarget.style.color = '#888')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.96-.065-1.182.408-2.256 1.332-3.025.88-.732 2.084-1.195 3.59-1.377.954-.115 1.963-.104 2.998.032-.06-1.289-.693-1.95-1.89-1.984-1.1-.033-1.921.564-2.214 1.013l-1.706-1.046c.655-1.07 1.916-1.828 3.534-2.127l.085-.015c.822-.14 1.67-.14 2.494 0 1.588.268 2.765.985 3.498 2.132.68 1.064.882 2.37.6 3.887l.007-.024.007.024c-.02.1-.043.198-.068.295.85.39 1.577.94 2.133 1.62.832 1.016 1.233 2.29 1.16 3.692-.094 1.77-.74 3.353-1.921 4.705C18.09 22.843 15.448 23.977 12.186 24zm.102-7.26c.775-.045 1.39-.315 1.828-.803.438-.487.728-1.164.863-2.012-.65-.078-1.307-.112-1.958-.102-.986.016-1.779.2-2.36.548-.59.355-.873.81-.84 1.354.034.538.345.967.876 1.209.53.24 1.122.307 1.59.306z"/>
          </svg>
        </a>
      </div>

      {/* 地圖 */}
      <div
        ref={mapContainer}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
        }}
      />

      {/* 路線篩選器 - 控制面板左上方漂浮 */}
      <LineFilter
        visibleLines={visibleLines}
        onToggleLine={handleToggleLine}
      />

      {/* 列車數量直方圖 - 控制面板右上方漂浮 */}
      {timeEngineRef.current && (
        <div
          style={{
            position: 'absolute',
            bottom: 205,
            right: 20,
            zIndex: 10,
          }}
        >
          <TrainHistogram
            data={histogramData}
            currentTimeSeconds={timeEngineRef.current.getTimeOfDaySeconds()}
            width={200}
            height={50}
          />
        </div>
      )}

      {/* 時間控制 */}
      {timeEngineRef.current && (
        <TimeControl
          timeEngine={timeEngineRef.current}
          currentTime={currentTime}
          trainCount={filteredTrains.length}
          isPlaying={isPlaying}
          speed={speed}
          onTogglePlay={handleTogglePlay}
          onSpeedChange={handleSpeedChange}
          onTimeChange={handleTimeChange}
        />
      )}
    </div>
  );
}

export default App;
