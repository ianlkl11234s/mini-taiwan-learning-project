import { useEffect, useRef, useState, useCallback } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useData } from './hooks/useData';
import { TimeEngine } from './engines/TimeEngine';
import { TrainEngine, type Train } from './engines/TrainEngine';
import { TimeControl } from './components/TimeControl';

// 設定 Mapbox Token
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || '';

// 軌道顏色
const TRACK_COLORS: Record<string, string> = {
  'R-1-0': '#d90023',
  'R-1-1': '#d90023',
  'R-2-0': '#e63946',
  'R-2-1': '#e63946',
  'R-3-0': '#ff6b6b',
  'R-3-1': '#ff6b6b',
};

function App() {
  // 資料載入
  const { tracks, stations, schedules, trackMap, stationProgress, loading, error } = useData();

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
  const [speed, setSpeed] = useState(1);

  // 列車引擎
  const trainEngineRef = useRef<TrainEngine | null>(null);
  const [trains, setTrains] = useState<Train[]>([]);

  // 初始化地圖 - 當 loading 完成後才初始化
  useEffect(() => {
    if (loading || !mapContainer.current || map.current) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [121.52, 25.08],
      zoom: 11.5,
    });

    map.current.on('load', () => {
      setMapLoaded(true);
    });

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');

    return () => {
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
        'line-color': ['get', 'color'],
        'line-width': 4,
        // R-1 主線顯示, R-3 新北投支線顯示, R-2 共用區段隱藏 (與 R-1 重疊)
        'line-opacity': [
          'case',
          ['in', 'R-1', ['get', 'track_id']], 0.8, // R-1-0, R-1-1 可見 (主線)
          ['in', 'R-3', ['get', 'track_id']], 0.8, // R-3-0, R-3-1 可見 (新北投支線)
          0.0 // R-2 透明 (與 R-1 共用區段，避免重複顯示)
        ],
      },
    });
  }, [mapLoaded, tracks]);

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
        'circle-color': '#ffffff',
        'circle-stroke-color': '#d90023',
        'circle-stroke-width': 2,
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

  // 初始化時間引擎
  useEffect(() => {
    const engine = new TimeEngine({
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

    const activeTrainIds = new Set(trains.map((t) => t.trainId));
    for (const [trainId, marker] of trainMarkers.current) {
      if (!activeTrainIds.has(trainId)) {
        marker.remove();
        trainMarkers.current.delete(trainId);
      }
    }

    for (const train of trains) {
      let marker = trainMarkers.current.get(train.trainId);
      const isStopped = train.status === 'stopped';
      const isColliding = train.isColliding;
      const baseColor = TRACK_COLORS[train.trackId] || '#d90023';
      // 碰撞時使用不同顏色區分 R-1 和 R-2
      const displayColor = isColliding
        ? (train.trackId.startsWith('R-1') ? '#ff4444' : '#ff8800')
        : baseColor;

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
  }, [mapLoaded, trains]);

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
          淡水信義線 模擬
        </p>
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

      {/* 時間控制 */}
      {timeEngineRef.current && (
        <TimeControl
          timeEngine={timeEngineRef.current}
          currentTime={currentTime}
          trainCount={trains.length}
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
