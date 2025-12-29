import { useState, useEffect, useRef, useCallback } from 'react';
import { Map } from './components/Map';
import { TimeControl } from './components/TimeControl';
import { TimeEngine } from './engines/TimeEngine';
import { TrainEngine, type Train } from './engines/TrainEngine';
import { useData } from './hooks/useData';

function App() {
  const { tracks, stations, schedules, trackMap, loading, error } = useData();

  // 時間引擎
  const timeEngineRef = useRef<TimeEngine | null>(null);
  const [currentTime, setCurrentTime] = useState('06:00:00');
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);

  // 列車引擎
  const trainEngineRef = useRef<TrainEngine | null>(null);
  const [trains, setTrains] = useState<Train[]>([]);

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

    return () => {
      engine.destroy();
    };
  }, []);

  // 初始化列車引擎
  useEffect(() => {
    if (schedules.size === 0 || trackMap.size === 0) return;

    trainEngineRef.current = new TrainEngine({
      schedules,
      tracks: trackMap,
    });
  }, [schedules, trackMap]);

  // 更新列車位置
  useEffect(() => {
    if (!timeEngineRef.current || !trainEngineRef.current) return;

    const unsubscribe = timeEngineRef.current.onTick(() => {
      if (trainEngineRef.current && timeEngineRef.current) {
        const timeSeconds = timeEngineRef.current.getTimeOfDaySeconds();
        const activeTrains = trainEngineRef.current.update(timeSeconds);
        setTrains(activeTrains);
      }
    });

    // 初始更新
    const timeSeconds = timeEngineRef.current.getTimeOfDaySeconds();
    if (trainEngineRef.current) {
      setTrains(trainEngineRef.current.update(timeSeconds));
    }

    return unsubscribe;
  }, [schedules, trackMap]);

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

    // 立即更新列車
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
      <Map tracks={tracks} stations={stations} trains={trains} />

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
