import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useData } from './hooks/useData';
import { useThsrData } from './hooks/useThsrData';
import { useKrtcData } from './hooks/useKrtcData';
import { useKlrtData } from './hooks/useKlrtData';
import { useTmrtData } from './hooks/useTmrtData';
import { TimeEngine } from './engines/TimeEngine';
import { TrainEngine, type Train } from './engines/TrainEngine';
import { ThsrTrainEngine, type ThsrTrain } from './engines/ThsrTrainEngine';
import { KrtcTrainEngine, type KrtcTrain } from './engines/KrtcTrainEngine';
import { KlrtTrainEngine, type KlrtTrain } from './engines/KlrtTrainEngine';
import { TmrtTrainEngine, type TmrtTrain } from './engines/TmrtTrainEngine';
import { TimeControl } from './components/TimeControl';
import { LineFilter, type MKFilterState, type ThsrFilterState } from './components/LineFilter';
import { TrainHistogram } from './components/TrainHistogram';
import { TrainInfoPanel } from './components/TrainInfoPanel';
import { useTrainCountHistogram } from './hooks/useTrainCountHistogram';
import { Train3DLayer } from './layers/Train3DLayer';
import { Thsr3DLayer } from './layers/Thsr3DLayer';
import { Krtc3DLayer } from './layers/Krtc3DLayer';
import { Klrt3DLayer } from './layers/Klrt3DLayer';
import { Tmrt3DLayer } from './layers/Tmrt3DLayer';
import { ThemeToggle, type MapTheme, type VisualTheme, getVisualTheme } from './components/ThemeToggle';
import { TRACK_COLORS, TRAIN_COLORS, getTrainColor, getLineIdFromTrackId } from './constants/lineInfo';
import { THSR_TRACK_COLOR, THSR_TRAIN_COLORS, getThsrDirection } from './constants/thsrInfo';
import { KRTC_TRACK_COLORS, KRTC_TRAIN_COLORS, getKrtcLineId, getKrtcDirection } from './constants/krtcInfo';
import { KLRT_TRACK_COLORS, KLRT_TRAIN_COLORS, getKlrtLineId, getKlrtDirection } from './constants/klrtInfo';
import { TMRT_TRACK_COLORS, getTmrtLineId } from './constants/tmrtInfo';
import { CitySelector, type CityId, CITIES } from './components/CitySelector';

// 光線預設類型（用於 standard 樣式）
type LightPreset = 'dawn' | 'day' | 'dusk' | 'night';

// 地圖樣式
const MAP_STYLES = {
  standard: 'mapbox://styles/mapbox/standard',
  dark: 'mapbox://styles/mapbox/dark-v11',
} as const;

// 根據小時取得光線預設
const getPresetForHour = (hour: number): LightPreset => {
  if (hour >= 5 && hour < 7) return 'dawn';    // 05:00 - 06:59
  if (hour >= 7 && hour < 17) return 'day';    // 07:00 - 16:59
  if (hour >= 17 && hour < 19) return 'dusk';  // 17:00 - 18:59
  return 'night';                               // 19:00 - 04:59
};

// 設定 Mapbox Token
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || '';

function App() {
  // MRT 資料載入
  const { tracks, stations, schedules, trackMap, stationProgress, loading, error } = useData();

  // THSR 資料載入（THSR 載入錯誤不阻止 MRT 顯示）
  const {
    tracks: thsrTracks,
    stations: thsrStations,
    schedules: thsrSchedules,
    trackMap: thsrTrackMap,
    stationProgress: thsrStationProgress,
    loading: _thsrLoading,
    error: _thsrError,
  } = useThsrData();
  void _thsrLoading; void _thsrError; // 抑制未使用變數警告

  // KRTC 資料載入（KRTC 載入錯誤不阻止其他顯示）
  const {
    tracks: krtcTracks,
    stations: krtcStations,
    schedules: krtcSchedules,
    trackMap: krtcTrackMap,
    stationProgress: krtcStationProgress,
    loading: _krtcLoading,
    error: _krtcError,
  } = useKrtcData();
  void _krtcLoading; void _krtcError; // 抑制未使用變數警告

  // KLRT 資料載入（KLRT 載入錯誤不阻止其他顯示）
  const {
    tracks: klrtTracks,
    stations: klrtStations,
    schedules: klrtSchedules,
    trackMap: klrtTrackMap,
    stationProgress: klrtStationProgress,
    loading: _klrtLoading,
    error: _klrtError,
  } = useKlrtData();
  void _klrtLoading; void _klrtError; // 抑制未使用變數警告

  // TMRT 資料載入（TMRT 載入錯誤不阻止其他顯示）
  const {
    tracks: tmrtTracks,
    stations: tmrtStations,
    schedules: tmrtSchedules,
    trackMap: tmrtTrackMap,
    stationProgress: tmrtStationProgress,
    loading: _tmrtLoading,
    error: _tmrtError,
  } = useTmrtData();
  void _tmrtLoading; void _tmrtError; // 抑制未使用變數警告

  // 預計算直方圖資料
  const histogramData = useTrainCountHistogram(schedules);

  // 地圖狀態
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const trainMarkers = useRef<Map<string, mapboxgl.Marker>>(new Map());
  const thsrTrainMarkers = useRef<Map<string, mapboxgl.Marker>>(new Map());
  const krtcTrainMarkers = useRef<Map<string, mapboxgl.Marker>>(new Map());
  const klrtTrainMarkers = useRef<Map<string, mapboxgl.Marker>>(new Map());
  const tmrtTrainMarkers = useRef<Map<string, mapboxgl.Marker>>(new Map());
  void tmrtTrainMarkers; // 預留給 2D 模式使用

  // 時間引擎
  const timeEngineRef = useRef<TimeEngine | null>(null);
  const [timeEngineReady, setTimeEngineReady] = useState(false);
  const [currentTime, setCurrentTime] = useState('06:00:00');
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(60);

  // 列車引擎 (MRT)
  const trainEngineRef = useRef<TrainEngine | null>(null);
  const [trains, setTrains] = useState<Train[]>([]);

  // 列車引擎 (THSR)
  const thsrTrainEngineRef = useRef<ThsrTrainEngine | null>(null);
  const [thsrTrains, setThsrTrains] = useState<ThsrTrain[]>([]);

  // 列車引擎 (KRTC)
  const krtcTrainEngineRef = useRef<KrtcTrainEngine | null>(null);
  const [krtcTrains, setKrtcTrains] = useState<KrtcTrain[]>([]);

  // 列車引擎 (KLRT)
  const klrtTrainEngineRef = useRef<KlrtTrainEngine | null>(null);
  const [klrtTrains, setKlrtTrains] = useState<KlrtTrain[]>([]);

  // 列車引擎 (TMRT)
  const tmrtTrainEngineRef = useRef<TmrtTrainEngine | null>(null);
  const [tmrtTrains, setTmrtTrains] = useState<TmrtTrain[]>([]);

  // 圖例收合狀態（預設收合）
  const [legendCollapsed, setLegendCollapsed] = useState(true);

  // 說明/公告 Modal 狀態
  const [showInfoModal, setShowInfoModal] = useState(false);

  // 3D 模式狀態
  const [use3DMode, setUse3DMode] = useState(false);
  const train3DLayerRef = useRef<Train3DLayer | null>(null);
  const thsr3DLayerRef = useRef<Thsr3DLayer | null>(null);
  const krtc3DLayerRef = useRef<Krtc3DLayer | null>(null);
  const klrt3DLayerRef = useRef<Klrt3DLayer | null>(null);
  const tmrt3DLayerRef = useRef<Tmrt3DLayer | null>(null);

  // 地圖主題模式（日夜切換）- 預設使用 dark 樣式
  const [mapTheme, setMapTheme] = useState<MapTheme>('dark');
  const currentLightPresetRef = useRef<LightPreset>('day');
  const currentMapStyleRef = useRef<'standard' | 'dark'>('dark'); // 與預設 mapTheme 一致
  const [styleVersion, setStyleVersion] = useState(0); // 樣式版本，用於觸發圖層重建

  // 視覺主題（用於面板顏色）
  const [visualTheme, setVisualTheme] = useState<VisualTheme>('dark');

  // 當前小時（用於自動模式判斷）
  const [currentHour, setCurrentHour] = useState(6);

  // 列車選擇狀態
  const [selectedTrainId, setSelectedTrainId] = useState<string | null>(null);
  const [isFollowing, setIsFollowing] = useState(false);
  const [interactionVersion, setInteractionVersion] = useState(0); // 用於觸發 effect 重新執行
  const isUserInteracting = useRef(false); // 追蹤使用者是否正在操作地圖

  // 路線篩選狀態（MRT 線路）
  const [visibleLines, setVisibleLines] = useState<Set<string>>(
    new Set(['R', 'BL', 'G', 'O', 'BR', 'K', 'V', 'A', 'Y'])
  );

  // 貓空纜車三段式狀態：full | tracks-only | hidden
  const [mkState, setMkState] = useState<MKFilterState>('tracks-only');

  // 高鐵三段式狀態：full | tracks-only | hidden
  const [thsrState, setThsrState] = useState<ThsrFilterState>('full');

  // 高雄捷運 + 輕軌路線可見性狀態
  const [visibleKrtcLines, setVisibleKrtcLines] = useState<Set<string>>(
    new Set(['R', 'O', 'C'])
  );

  // 台中捷運路線可見性狀態
  const [visibleTmrtLines, setVisibleTmrtLines] = useState<Set<string>>(
    new Set(['G'])
  );

  // 城市選擇狀態
  const [selectedCity, setSelectedCity] = useState<CityId | null>('TPE');

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

  // 切換全部 MRT 路線可見性
  const handleToggleAllMrt = useCallback((visible: boolean) => {
    const mrtLines = ['R', 'O', 'Y', 'G', 'BL', 'BR', 'A', 'K', 'V'];
    setVisibleLines(prev => {
      const next = new Set(prev);
      if (visible) {
        mrtLines.forEach(lineId => next.add(lineId));
      } else {
        mrtLines.forEach(lineId => next.delete(lineId));
      }
      return next;
    });
  }, []);

  // 切換 MK 狀態
  const handleMKStateChange = useCallback((state: MKFilterState) => {
    setMkState(state);
  }, []);

  // 切換 THSR 狀態
  const handleThsrStateChange = useCallback((state: ThsrFilterState) => {
    setThsrState(state);
  }, []);

  // 切換 KRTC 路線可見性
  const handleToggleKrtcLine = useCallback((lineId: string) => {
    setVisibleKrtcLines(prev => {
      const next = new Set(prev);
      if (next.has(lineId)) {
        next.delete(lineId);
      } else {
        next.add(lineId);
      }
      return next;
    });
  }, []);

  // 切換全部 KHH 路線可見性（KRTC + KLRT）
  const handleToggleAllKrtc = useCallback((visible: boolean) => {
    const krtcLines = ['R', 'O', 'C'];
    setVisibleKrtcLines(prev => {
      const next = new Set(prev);
      if (visible) {
        krtcLines.forEach(lineId => next.add(lineId));
      } else {
        krtcLines.forEach(lineId => next.delete(lineId));
      }
      return next;
    });
  }, []);

  // 切換 TMRT 路線可見性
  const handleToggleTmrtLine = useCallback((lineId: string) => {
    setVisibleTmrtLines(prev => {
      const next = new Set(prev);
      if (next.has(lineId)) {
        next.delete(lineId);
      } else {
        next.add(lineId);
      }
      return next;
    });
  }, []);

  // 切換全部 TXG 路線可見性
  const handleToggleAllTmrt = useCallback((visible: boolean) => {
    const tmrtLines = ['G'];
    setVisibleTmrtLines(prev => {
      const next = new Set(prev);
      if (visible) {
        tmrtLines.forEach(lineId => next.add(lineId));
      } else {
        tmrtLines.forEach(lineId => next.delete(lineId));
      }
      return next;
    });
  }, []);

  // 城市選擇處理
  const handleCitySelect = useCallback((center: [number, number], zoom: number) => {
    if (!map.current) return;

    // 找出選擇的城市 ID
    const cityEntry = Object.entries(CITIES).find(
      ([, config]) => config.center[0] === center[0] && config.center[1] === center[1]
    );
    if (cityEntry) {
      setSelectedCity(cityEntry[0] as CityId);
    }

    // 飛往該城市
    map.current.flyTo({
      center: center,
      zoom: zoom,
      duration: 1500,
      essential: true,
    });
  }, []);

  // 根據可見路線過濾列車 (MRT)
  const filteredTrains = useMemo(() => {
    return trains.filter(train => {
      const lineId = getLineIdFromTrackId(train.trackId);
      // MK 線使用三段式狀態
      if (lineId === 'MK') {
        return mkState === 'full'; // 只有 full 狀態才顯示纜車
      }
      return visibleLines.has(lineId);
    });
  }, [trains, visibleLines, mkState]);

  // 根據高鐵狀態過濾列車 (THSR)
  const filteredThsrTrains = useMemo(() => {
    // 只有 full 狀態才顯示高鐵列車
    if (thsrState !== 'full') return [];
    return thsrTrains;
  }, [thsrTrains, thsrState]);

  // 根據高雄捷運路線可見性過濾列車 (KRTC)
  const filteredKrtcTrains = useMemo(() => {
    return krtcTrains.filter(train => {
      const lineId = getKrtcLineId(train.trackId);
      return visibleKrtcLines.has(lineId);
    });
  }, [krtcTrains, visibleKrtcLines]);

  // 根據高雄輕軌路線可見性過濾列車 (KLRT)
  const filteredKlrtTrains = useMemo(() => {
    return klrtTrains.filter(train => {
      const lineId = getKlrtLineId(train.trackId);
      return visibleKrtcLines.has(lineId);
    });
  }, [klrtTrains, visibleKrtcLines]);

  // 根據台中捷運路線可見性過濾列車 (TMRT)
  const filteredTmrtTrains = useMemo(() => {
    return tmrtTrains.filter(train => {
      const lineId = getTmrtLineId(train.trackId);
      return visibleTmrtLines.has(lineId);
    });
  }, [tmrtTrains, visibleTmrtLines]);

  // 計算 MRT 列車數量（排除纜車）
  const mrtCount = useMemo(() => {
    return filteredTrains.filter(train => !train.trackId.startsWith('MK')).length;
  }, [filteredTrains]);

  // 建立車站座標索引（用於 3D 圖層停站定位）
  const stationCoordinates = useMemo(() => {
    const coords = new Map<string, [number, number]>();
    if (stations) {
      for (const feature of stations.features) {
        const stationId = feature.properties.station_id;
        const geometry = feature.geometry as GeoJSON.Point;
        coords.set(stationId, geometry.coordinates as [number, number]);
      }
    }
    return coords;
  }, [stations]);

  // 建立車站名稱索引（用於資訊面板顯示，包含 MRT + THSR + KRTC + KLRT）
  const stationNames = useMemo(() => {
    const names = new Map<string, string>();
    // MRT 車站
    if (stations) {
      for (const feature of stations.features) {
        const stationId = feature.properties.station_id;
        const stationName = feature.properties.name_zh;
        names.set(stationId, stationName);
      }
    }
    // THSR 車站
    if (thsrStations) {
      for (const feature of thsrStations.features) {
        const stationId = feature.properties.station_id;
        const stationName = feature.properties.name_zh;
        names.set(stationId, stationName);
      }
    }
    // KRTC 車站
    if (krtcStations) {
      for (const feature of krtcStations.features) {
        const stationId = feature.properties.station_id;
        const stationName = feature.properties.name_zh;
        names.set(stationId, stationName);
      }
    }
    // KLRT 車站
    if (klrtStations) {
      for (const feature of klrtStations.features) {
        const stationId = feature.properties.station_id;
        const stationName = feature.properties.name_zh;
        names.set(stationId, stationName);
      }
    }
    // TMRT 車站
    if (tmrtStations) {
      for (const feature of tmrtStations.features) {
        const stationId = feature.properties.station_id;
        const stationName = feature.properties.name_zh;
        names.set(stationId, stationName);
      }
    }
    return names;
  }, [stations, thsrStations, krtcStations, klrtStations, tmrtStations]);

  // 取得選中的列車資料（同時支援 MRT、THSR、KRTC、KLRT 和 TMRT）
  const selectedTrain = useMemo(() => {
    if (!selectedTrainId) return null;
    // 先從 MRT 找
    const mrtTrain = filteredTrains.find(t => t.trainId === selectedTrainId);
    if (mrtTrain) return mrtTrain;
    // 再從 THSR 找
    const thsrTrain = filteredThsrTrains.find(t => t.trainId === selectedTrainId);
    if (thsrTrain) return thsrTrain;
    // 再從 KRTC 找
    const krtcTrain = filteredKrtcTrains.find(t => t.trainId === selectedTrainId);
    if (krtcTrain) return krtcTrain;
    // 再從 KLRT 找
    const klrtTrain = filteredKlrtTrains.find(t => t.trainId === selectedTrainId);
    if (klrtTrain) return klrtTrain;
    // 最後從 TMRT 找
    const tmrtTrain = filteredTmrtTrains.find(t => t.trainId === selectedTrainId);
    if (tmrtTrain) return tmrtTrain;
    return null;
  }, [selectedTrainId, filteredTrains, filteredThsrTrains, filteredKrtcTrains, filteredKlrtTrains, filteredTmrtTrains]);


  // 選擇列車
  const handleSelectTrain = useCallback((trainId: string) => {
    setSelectedTrainId(trainId);
    setIsFollowing(true); // 選中時自動開啟跟隨
  }, []);

  // 取消選擇
  const handleDeselectTrain = useCallback(() => {
    setSelectedTrainId(null);
    setIsFollowing(false);
  }, []);

  // 當選中的列車消失時，自動取消選擇
  useEffect(() => {
    if (selectedTrainId && !selectedTrain) {
      handleDeselectTrain();
    }
  }, [selectedTrainId, selectedTrain, handleDeselectTrain]);

  // 視線跟隨：當 isFollowing 且有選中列車時，地圖中心跟隨列車
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (!isFollowing || !selectedTrain) return;

    // 使用者正在操作時不更新位置，讓使用者可以自由旋轉視角
    if (isUserInteracting.current && use3DMode) return;

    const [lng, lat] = selectedTrain.position;

    if (use3DMode) {
      const currentPitch = map.current.getPitch();
      const currentBearing = map.current.getBearing();

      // 效能優化：3D 模式使用 jumpTo 替代 easeTo，避免每幀觸發動畫
      // 使用 padding 來補償 3D 視角的偏移（螢幕空間，不受 bearing 影響）
      const bottomPadding = Math.round(currentPitch * 3); // pitch 45 → padding 135

      map.current.jumpTo({
        center: [lng, lat],
        padding: { top: 0, bottom: bottomPadding, left: 0, right: 0 },
        bearing: currentBearing,
        pitch: currentPitch,
      });
    } else {
      // 2D 模式：使用平滑動畫
      map.current.easeTo({
        center: [lng, lat],
        duration: 300,
      });
    }
  }, [mapLoaded, isFollowing, selectedTrain, use3DMode, interactionVersion]);

  // 偵測使用者地圖操作
  // 2D 模式：拖曳取消跟隨
  // 3D 模式：允許自由旋轉視角，操作期間暫停跟隨更新，放開後繼續跟隨
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    const handleInteractionStart = () => {
      isUserInteracting.current = true;
      // 只在 2D 模式下，拖曳時取消跟隨
      // 3D 模式允許自由旋轉而不取消跟隨
      if (isFollowing && !use3DMode) {
        setIsFollowing(false);
      }
    };

    const handleInteractionEnd = () => {
      isUserInteracting.current = false;
      // 在 3D 跟隨模式下，操作結束後觸發重新置中
      if (use3DMode && isFollowing) {
        setInteractionVersion(v => v + 1);
      }
    };

    // 監聽各種使用者操作事件
    map.current.on('dragstart', handleInteractionStart);
    map.current.on('rotatestart', handleInteractionStart);
    map.current.on('pitchstart', handleInteractionStart);
    map.current.on('dragend', handleInteractionEnd);
    map.current.on('rotateend', handleInteractionEnd);
    map.current.on('pitchend', handleInteractionEnd);

    return () => {
      if (map.current) {
        map.current.off('dragstart', handleInteractionStart);
        map.current.off('rotatestart', handleInteractionStart);
        map.current.off('pitchstart', handleInteractionStart);
        map.current.off('dragend', handleInteractionEnd);
        map.current.off('rotateend', handleInteractionEnd);
        map.current.off('pitchend', handleInteractionEnd);
      }
    };
  }, [mapLoaded, isFollowing, use3DMode]);

  // 初始化地圖 - 當 loading 完成後才初始化
  useEffect(() => {
    if (loading || !mapContainer.current || map.current) return;

    // 根據預設主題選擇初始樣式，避免載入時閃爍
    const initialStyle = MAP_STYLES[currentMapStyleRef.current];

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: initialStyle,
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
      if (map.current.getLayer('tracks-line-mk')) {
        map.current.removeLayer('tracks-line-mk');
      }
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
      filter: ['!=', ['get', 'line_id'], 'MK'],  // 排除貓空纜車（使用虛線圖層）
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        // 依路線設定顏色：G-3 小碧潭支線（淺綠）, K 安坑輕軌, V 淡海輕軌, G 綠線, BL 藍線, BR 文湖線, O 橘線, A 機場捷運, Y 環狀線, R 紅線
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
          ['==', ['get', 'line_id'], 'Y'], TRACK_COLORS.Y,      // 環狀線
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
          ['==', ['slice', ['get', 'track_id'], 0, 2], 'Y-'], 0.8,   // 所有 Y 線軌道可見 (環狀線)
          0.0 // 其他軌道透明
        ],
        // 發光強度：讓軌道在夜間模式也保持明亮
        'line-emissive-strength': 1.0,
      },
    });

    // 貓空纜車專用圖層（虛線樣式）
    map.current.addLayer({
      id: 'tracks-line-mk',
      type: 'line',
      source: 'tracks',
      filter: ['==', ['get', 'line_id'], 'MK'],  // 只顯示貓空纜車
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': TRACK_COLORS.MK,
        'line-width': 4,
        'line-opacity': 0.8,
        'line-dasharray': [2, 2],  // 虛線樣式
        // 發光強度：讓軌道在夜間模式也保持明亮
        'line-emissive-strength': 1.0,
      },
    });
  }, [mapLoaded, tracks, styleVersion]);

  // 載入高鐵軌道圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !thsrTracks) return;

    if (map.current.getSource('thsr-tracks')) {
      map.current.removeLayer('thsr-tracks-line');
      map.current.removeSource('thsr-tracks');
    }

    map.current.addSource('thsr-tracks', {
      type: 'geojson',
      data: thsrTracks as GeoJSON.FeatureCollection,
    });

    map.current.addLayer({
      id: 'thsr-tracks-line',
      type: 'line',
      source: 'thsr-tracks',
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': THSR_TRACK_COLOR,
        'line-width': 4,
        'line-opacity': thsrState !== 'hidden' ? 0.8 : 0.0,
        'line-emissive-strength': 1.0,
      },
    });
  }, [mapLoaded, thsrTracks, thsrState, styleVersion]);

  // 更新高鐵軌道可見性
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (!map.current.getLayer('thsr-tracks-line')) return;

    map.current.setPaintProperty('thsr-tracks-line', 'line-opacity',
      thsrState !== 'hidden' ? 0.8 : 0.0
    );
  }, [mapLoaded, thsrState, styleVersion]);

  // 載入高鐵車站圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !thsrStations) return;

    if (map.current.getSource('thsr-stations')) {
      map.current.removeLayer('thsr-stations-circle');
      map.current.removeLayer('thsr-stations-label');
      map.current.removeSource('thsr-stations');
    }

    map.current.addSource('thsr-stations', {
      type: 'geojson',
      data: thsrStations as GeoJSON.FeatureCollection,
    });

    map.current.addLayer({
      id: 'thsr-stations-circle',
      type: 'circle',
      source: 'thsr-stations',
      paint: {
        'circle-radius': 6,
        'circle-color': '#000000',
        'circle-stroke-color': THSR_TRACK_COLOR,
        'circle-stroke-width': 2,
        'circle-opacity': thsrState !== 'hidden' ? 1 : 0,
        'circle-stroke-opacity': thsrState !== 'hidden' ? 1 : 0,
        'circle-emissive-strength': 1.0,
      },
    });

    map.current.addLayer({
      id: 'thsr-stations-label',
      type: 'symbol',
      source: 'thsr-stations',
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
        'text-opacity': thsrState !== 'hidden' ? 1 : 0,
        'text-emissive-strength': 1.0,
      },
    });
  }, [mapLoaded, thsrStations, thsrState, styleVersion]);

  // 更新高鐵車站可見性
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (!map.current.getLayer('thsr-stations-circle')) return;

    const opacity = thsrState !== 'hidden' ? 1 : 0;
    map.current.setPaintProperty('thsr-stations-circle', 'circle-opacity', opacity);
    map.current.setPaintProperty('thsr-stations-circle', 'circle-stroke-opacity', opacity);
    map.current.setPaintProperty('thsr-stations-label', 'text-opacity', opacity);
  }, [mapLoaded, thsrState, styleVersion]);

  // 載入高雄捷運軌道圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !krtcTracks) return;

    if (map.current.getSource('krtc-tracks')) {
      if (map.current.getLayer('krtc-tracks-line-O')) {
        map.current.removeLayer('krtc-tracks-line-O');
      }
      if (map.current.getLayer('krtc-tracks-line-R')) {
        map.current.removeLayer('krtc-tracks-line-R');
      }
      map.current.removeSource('krtc-tracks');
    }

    map.current.addSource('krtc-tracks', {
      type: 'geojson',
      data: krtcTracks as GeoJSON.FeatureCollection,
    });

    // 橘線
    map.current.addLayer({
      id: 'krtc-tracks-line-O',
      type: 'line',
      source: 'krtc-tracks',
      filter: ['==', ['slice', ['get', 'track_id'], 5, 6], 'O'],
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': KRTC_TRACK_COLORS.O,
        'line-width': 4,
        'line-opacity': visibleKrtcLines.has('O') ? 0.8 : 0.0,
        'line-emissive-strength': 1.0,
      },
    });

    // 紅線
    map.current.addLayer({
      id: 'krtc-tracks-line-R',
      type: 'line',
      source: 'krtc-tracks',
      filter: ['==', ['slice', ['get', 'track_id'], 5, 6], 'R'],
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': KRTC_TRACK_COLORS.R,
        'line-width': 4,
        'line-opacity': visibleKrtcLines.has('R') ? 0.8 : 0.0,
        'line-emissive-strength': 1.0,
      },
    });
  }, [mapLoaded, krtcTracks, visibleKrtcLines, styleVersion]);

  // 更新高雄捷運軌道可見性
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (!map.current.getLayer('krtc-tracks-line-O')) return;

    map.current.setPaintProperty('krtc-tracks-line-O', 'line-opacity', visibleKrtcLines.has('O') ? 0.8 : 0.0);
    map.current.setPaintProperty('krtc-tracks-line-R', 'line-opacity', visibleKrtcLines.has('R') ? 0.8 : 0.0);
  }, [mapLoaded, visibleKrtcLines, styleVersion]);

  // 載入高雄捷運車站圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !krtcStations) return;

    if (map.current.getSource('krtc-stations')) {
      map.current.removeLayer('krtc-stations-circle');
      map.current.removeLayer('krtc-stations-label');
      map.current.removeSource('krtc-stations');
    }

    map.current.addSource('krtc-stations', {
      type: 'geojson',
      data: krtcStations as GeoJSON.FeatureCollection,
    });

    map.current.addLayer({
      id: 'krtc-stations-circle',
      type: 'circle',
      source: 'krtc-stations',
      paint: {
        'circle-radius': 5,
        'circle-color': '#000000',
        'circle-stroke-color': [
          'case',
          ['==', ['slice', ['get', 'station_id'], 0, 1], 'O'], KRTC_TRACK_COLORS.O,
          KRTC_TRACK_COLORS.R,
        ],
        'circle-stroke-width': 2,
        'circle-opacity': visibleKrtcLines.size > 0 ? 1 : 0,
        'circle-stroke-opacity': visibleKrtcLines.size > 0 ? 1 : 0,
        'circle-emissive-strength': 1.0,
      },
    });

    map.current.addLayer({
      id: 'krtc-stations-label',
      type: 'symbol',
      source: 'krtc-stations',
      layout: {
        'text-field': ['get', 'name_zh'],
        'text-size': 10,
        'text-offset': [0, 1.3],
        'text-anchor': 'top',
      },
      paint: {
        'text-color': '#ffffff',
        'text-halo-color': '#000000',
        'text-halo-width': 1,
        'text-opacity': visibleKrtcLines.size > 0 ? 1 : 0,
        'text-emissive-strength': 1.0,
      },
    });
  }, [mapLoaded, krtcStations, visibleKrtcLines, styleVersion]);

  // 更新高雄捷運車站可見性
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (!map.current.getLayer('krtc-stations-circle')) return;

    const opacity = visibleKrtcLines.size > 0 ? 1 : 0;
    map.current.setPaintProperty('krtc-stations-circle', 'circle-opacity', opacity);
    map.current.setPaintProperty('krtc-stations-circle', 'circle-stroke-opacity', opacity);
    map.current.setPaintProperty('krtc-stations-label', 'text-opacity', opacity);
  }, [mapLoaded, visibleKrtcLines, styleVersion]);

  // 載入高雄輕軌軌道圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !klrtTracks) return;

    if (map.current.getSource('klrt-tracks')) {
      if (map.current.getLayer('klrt-tracks-line-C')) {
        map.current.removeLayer('klrt-tracks-line-C');
      }
      map.current.removeSource('klrt-tracks');
    }

    map.current.addSource('klrt-tracks', {
      type: 'geojson',
      data: klrtTracks as GeoJSON.FeatureCollection,
    });

    // 環狀線 (C)
    map.current.addLayer({
      id: 'klrt-tracks-line-C',
      type: 'line',
      source: 'klrt-tracks',
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': KLRT_TRACK_COLORS.C,
        'line-width': 3,  // 輕軌軌道較細
        'line-opacity': visibleKrtcLines.has('C') ? 0.8 : 0.0,
        'line-emissive-strength': 1.0,
      },
    });
  }, [mapLoaded, klrtTracks, visibleKrtcLines, styleVersion]);

  // 更新高雄輕軌軌道可見性
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (!map.current.getLayer('klrt-tracks-line-C')) return;

    map.current.setPaintProperty('klrt-tracks-line-C', 'line-opacity', visibleKrtcLines.has('C') ? 0.8 : 0.0);
  }, [mapLoaded, visibleKrtcLines, styleVersion]);

  // 載入高雄輕軌車站圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !klrtStations) return;

    if (map.current.getSource('klrt-stations')) {
      map.current.removeLayer('klrt-stations-circle');
      map.current.removeLayer('klrt-stations-label');
      map.current.removeSource('klrt-stations');
    }

    map.current.addSource('klrt-stations', {
      type: 'geojson',
      data: klrtStations as GeoJSON.FeatureCollection,
    });

    map.current.addLayer({
      id: 'klrt-stations-circle',
      type: 'circle',
      source: 'klrt-stations',
      paint: {
        'circle-radius': 4,  // 輕軌車站較小
        'circle-color': '#000000',
        'circle-stroke-color': KLRT_TRACK_COLORS.C,
        'circle-stroke-width': 2,
        'circle-opacity': visibleKrtcLines.has('C') ? 1 : 0,
        'circle-stroke-opacity': visibleKrtcLines.has('C') ? 1 : 0,
        'circle-emissive-strength': 1.0,
      },
    });

    map.current.addLayer({
      id: 'klrt-stations-label',
      type: 'symbol',
      source: 'klrt-stations',
      layout: {
        'text-field': ['get', 'name_zh'],
        'text-size': 9,  // 輕軌車站標籤較小
        'text-offset': [0, 1.3],
        'text-anchor': 'top',
      },
      paint: {
        'text-color': '#ffffff',
        'text-halo-color': '#000000',
        'text-halo-width': 1,
        'text-opacity': visibleKrtcLines.has('C') ? 1 : 0,
        'text-emissive-strength': 1.0,
      },
    });
  }, [mapLoaded, klrtStations, visibleKrtcLines, styleVersion]);

  // 更新高雄輕軌車站可見性
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (!map.current.getLayer('klrt-stations-circle')) return;

    const opacity = visibleKrtcLines.has('C') ? 1 : 0;
    map.current.setPaintProperty('klrt-stations-circle', 'circle-opacity', opacity);
    map.current.setPaintProperty('klrt-stations-circle', 'circle-stroke-opacity', opacity);
    map.current.setPaintProperty('klrt-stations-label', 'text-opacity', opacity);
  }, [mapLoaded, visibleKrtcLines, styleVersion]);

  // 載入台中捷運軌道圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !tmrtTracks) return;

    if (map.current.getSource('tmrt-tracks')) {
      if (map.current.getLayer('tmrt-tracks-line-G')) {
        map.current.removeLayer('tmrt-tracks-line-G');
      }
      map.current.removeSource('tmrt-tracks');
    }

    map.current.addSource('tmrt-tracks', {
      type: 'geojson',
      data: tmrtTracks as GeoJSON.FeatureCollection,
    });

    // 綠線
    map.current.addLayer({
      id: 'tmrt-tracks-line-G',
      type: 'line',
      source: 'tmrt-tracks',
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': TMRT_TRACK_COLORS.G,
        'line-width': 4,
        'line-opacity': visibleTmrtLines.has('G') ? 0.8 : 0.0,
        'line-emissive-strength': 1.0,
      },
    });
  }, [mapLoaded, tmrtTracks, visibleTmrtLines, styleVersion]);

  // 更新台中捷運軌道可見性
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (!map.current.getLayer('tmrt-tracks-line-G')) return;

    map.current.setPaintProperty('tmrt-tracks-line-G', 'line-opacity', visibleTmrtLines.has('G') ? 0.8 : 0.0);
  }, [mapLoaded, visibleTmrtLines, styleVersion]);

  // 載入台中捷運車站圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !tmrtStations) return;

    if (map.current.getSource('tmrt-stations')) {
      if (map.current.getLayer('tmrt-stations-circle')) {
        map.current.removeLayer('tmrt-stations-circle');
      }
      if (map.current.getLayer('tmrt-stations-label')) {
        map.current.removeLayer('tmrt-stations-label');
      }
      map.current.removeSource('tmrt-stations');
    }

    map.current.addSource('tmrt-stations', {
      type: 'geojson',
      data: tmrtStations as GeoJSON.FeatureCollection,
    });

    map.current.addLayer({
      id: 'tmrt-stations-circle',
      type: 'circle',
      source: 'tmrt-stations',
      paint: {
        'circle-radius': 5,
        'circle-color': '#000000',
        'circle-stroke-color': TMRT_TRACK_COLORS.G,
        'circle-stroke-width': 2,
        'circle-opacity': visibleTmrtLines.has('G') ? 1 : 0,
        'circle-stroke-opacity': visibleTmrtLines.has('G') ? 1 : 0,
        'circle-emissive-strength': 1.0,
      },
    });

    map.current.addLayer({
      id: 'tmrt-stations-label',
      type: 'symbol',
      source: 'tmrt-stations',
      layout: {
        'text-field': ['get', 'name_zh'],
        'text-size': 10,
        'text-offset': [0, 1.3],
        'text-anchor': 'top',
      },
      paint: {
        'text-color': '#ffffff',
        'text-halo-color': '#000000',
        'text-halo-width': 1,
        'text-opacity': visibleTmrtLines.has('G') ? 1 : 0,
        'text-emissive-strength': 1.0,
      },
    });
  }, [mapLoaded, tmrtStations, visibleTmrtLines, styleVersion]);

  // 更新台中捷運車站可見性
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (!map.current.getLayer('tmrt-stations-circle')) return;

    const opacity = visibleTmrtLines.has('G') ? 1 : 0;
    map.current.setPaintProperty('tmrt-stations-circle', 'circle-opacity', opacity);
    map.current.setPaintProperty('tmrt-stations-circle', 'circle-stroke-opacity', opacity);
    map.current.setPaintProperty('tmrt-stations-label', 'text-opacity', opacity);
  }, [mapLoaded, visibleTmrtLines, styleVersion]);

  // 初始化 3D 列車圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !use3DMode) return;
    if (trackMap.size === 0) return;

    // 建立 3D 圖層
    const layer = new Train3DLayer(trackMap);
    layer.setStations(stationCoordinates);
    layer.setOnSelect(handleSelectTrain);
    train3DLayerRef.current = layer;

    // 加入地圖
    map.current.addLayer(layer);

    return () => {
      if (map.current && map.current.getLayer('train-3d-layer')) {
        map.current.removeLayer('train-3d-layer');
      }
      train3DLayerRef.current = null;
    };
  }, [mapLoaded, trackMap, stationCoordinates, use3DMode, handleSelectTrain, styleVersion]);

  // 更新 3D 圖層列車資料
  useEffect(() => {
    if (!train3DLayerRef.current || !use3DMode) return;
    train3DLayerRef.current.updateTrains(filteredTrains);
  }, [filteredTrains, use3DMode]);

  // 更新 3D 圖層選中狀態
  useEffect(() => {
    if (!train3DLayerRef.current || !use3DMode) return;
    train3DLayerRef.current.setSelectedTrainId(selectedTrainId);
  }, [selectedTrainId, use3DMode]);

  // 建立高鐵車站座標索引
  const thsrStationCoordinates = useMemo(() => {
    const coords = new Map<string, [number, number]>();
    if (thsrStations) {
      for (const feature of thsrStations.features) {
        const stationId = feature.properties.station_id;
        const geometry = feature.geometry as GeoJSON.Point;
        coords.set(stationId, geometry.coordinates as [number, number]);
      }
    }
    return coords;
  }, [thsrStations]);

  // 初始化高鐵 3D 圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !use3DMode) return;
    if (thsrTrackMap.size === 0) return;
    if (thsrState === 'hidden') return;  // 隱藏時不顯示 3D 圖層

    // 建立高鐵 3D 圖層
    const layer = new Thsr3DLayer(thsrTrackMap);
    layer.setStations(thsrStationCoordinates);
    layer.setOnSelect(handleSelectTrain);  // 綁定點擊回調
    thsr3DLayerRef.current = layer;

    // 加入地圖
    map.current.addLayer(layer);

    return () => {
      if (map.current && map.current.getLayer('thsr-3d-layer')) {
        map.current.removeLayer('thsr-3d-layer');
      }
      thsr3DLayerRef.current = null;
    };
  }, [mapLoaded, thsrTrackMap, thsrStationCoordinates, use3DMode, thsrState, handleSelectTrain, styleVersion]);

  // 更新高鐵 3D 圖層列車資料
  useEffect(() => {
    if (!thsr3DLayerRef.current || !use3DMode) return;
    thsr3DLayerRef.current.updateTrains(filteredThsrTrains);
  }, [filteredThsrTrains, use3DMode]);

  // 更新高鐵 3D 圖層選中狀態
  useEffect(() => {
    if (!thsr3DLayerRef.current || !use3DMode) return;
    thsr3DLayerRef.current.setSelectedTrainId(selectedTrainId);
  }, [selectedTrainId, use3DMode]);

  // 建立高雄捷運車站座標索引
  const krtcStationCoordinates = useMemo(() => {
    const coords = new Map<string, [number, number]>();
    if (krtcStations) {
      for (const feature of krtcStations.features) {
        const stationId = feature.properties.station_id;
        const geometry = feature.geometry as GeoJSON.Point;
        coords.set(stationId, geometry.coordinates as [number, number]);
      }
    }
    return coords;
  }, [krtcStations]);

  // 初始化高雄捷運 3D 圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !use3DMode) return;
    if (krtcTrackMap.size === 0) return;
    if (visibleKrtcLines.size === 0) return;  // 全部隱藏時不顯示 3D 圖層

    // 建立高雄捷運 3D 圖層
    const layer = new Krtc3DLayer(krtcTrackMap);
    layer.setStations(krtcStationCoordinates);
    layer.setOnSelect(handleSelectTrain);  // 綁定點擊回調
    krtc3DLayerRef.current = layer;

    // 加入地圖
    map.current.addLayer(layer);

    return () => {
      if (map.current && map.current.getLayer('krtc-3d-layer')) {
        map.current.removeLayer('krtc-3d-layer');
      }
      krtc3DLayerRef.current = null;
    };
  }, [mapLoaded, krtcTrackMap, krtcStationCoordinates, use3DMode, visibleKrtcLines, handleSelectTrain, styleVersion]);

  // 更新高雄捷運 3D 圖層列車資料
  useEffect(() => {
    if (!krtc3DLayerRef.current || !use3DMode) return;
    krtc3DLayerRef.current.updateTrains(filteredKrtcTrains);
  }, [filteredKrtcTrains, use3DMode]);

  // 更新高雄捷運 3D 圖層選中狀態
  useEffect(() => {
    if (!krtc3DLayerRef.current || !use3DMode) return;
    krtc3DLayerRef.current.setSelectedTrainId(selectedTrainId);
  }, [selectedTrainId, use3DMode]);

  // 建立高雄輕軌車站座標索引
  const klrtStationCoordinates = useMemo(() => {
    const coords = new Map<string, [number, number]>();
    if (klrtStations) {
      for (const feature of klrtStations.features) {
        const stationId = feature.properties.station_id;
        const geometry = feature.geometry as GeoJSON.Point;
        coords.set(stationId, geometry.coordinates as [number, number]);
      }
    }
    return coords;
  }, [klrtStations]);

  // 初始化高雄輕軌 3D 圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !use3DMode) return;
    if (klrtTrackMap.size === 0) return;
    if (!visibleKrtcLines.has('C')) return;  // C 線隱藏時不顯示 3D 圖層

    // 建立高雄輕軌 3D 圖層
    const layer = new Klrt3DLayer(klrtTrackMap);
    layer.setStations(klrtStationCoordinates);
    layer.setOnSelect(handleSelectTrain);  // 綁定點擊回調
    klrt3DLayerRef.current = layer;

    // 加入地圖
    map.current.addLayer(layer);

    return () => {
      if (map.current && map.current.getLayer('klrt-3d-layer')) {
        map.current.removeLayer('klrt-3d-layer');
      }
      klrt3DLayerRef.current = null;
    };
  }, [mapLoaded, klrtTrackMap, klrtStationCoordinates, use3DMode, visibleKrtcLines, handleSelectTrain, styleVersion]);

  // 更新高雄輕軌 3D 圖層列車資料
  useEffect(() => {
    if (!klrt3DLayerRef.current || !use3DMode) return;
    klrt3DLayerRef.current.updateTrains(filteredKlrtTrains);
  }, [filteredKlrtTrains, use3DMode]);

  // 更新高雄輕軌 3D 圖層選中狀態
  useEffect(() => {
    if (!klrt3DLayerRef.current || !use3DMode) return;
    klrt3DLayerRef.current.setSelectedTrainId(selectedTrainId);
  }, [selectedTrainId, use3DMode]);

  // 建立台中捷運車站座標索引
  const tmrtStationCoordinates = useMemo(() => {
    const coords = new Map<string, [number, number]>();
    if (tmrtStations) {
      for (const feature of tmrtStations.features) {
        const stationId = feature.properties.station_id;
        const geometry = feature.geometry as GeoJSON.Point;
        coords.set(stationId, geometry.coordinates as [number, number]);
      }
    }
    return coords;
  }, [tmrtStations]);

  // 初始化台中捷運 3D 圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !use3DMode) return;
    if (tmrtTrackMap.size === 0) return;
    if (visibleTmrtLines.size === 0) return;  // 全部隱藏時不顯示 3D 圖層

    // 建立台中捷運 3D 圖層
    const layer = new Tmrt3DLayer(tmrtTrackMap);
    layer.setStations(tmrtStationCoordinates);
    layer.setOnSelect(handleSelectTrain);  // 綁定點擊回調
    tmrt3DLayerRef.current = layer;

    // 加入地圖
    map.current.addLayer(layer);

    return () => {
      if (map.current && map.current.getLayer('tmrt-3d-layer')) {
        map.current.removeLayer('tmrt-3d-layer');
      }
      tmrt3DLayerRef.current = null;
    };
  }, [mapLoaded, tmrtTrackMap, tmrtStationCoordinates, use3DMode, visibleTmrtLines, handleSelectTrain, styleVersion]);

  // 更新台中捷運 3D 圖層列車資料
  useEffect(() => {
    if (!tmrt3DLayerRef.current || !use3DMode) return;
    tmrt3DLayerRef.current.updateTrains(filteredTmrtTrains);
  }, [filteredTmrtTrains, use3DMode]);

  // 更新台中捷運 3D 圖層選中狀態
  useEffect(() => {
    if (!tmrt3DLayerRef.current || !use3DMode) return;
    tmrt3DLayerRef.current.setSelectedTrainId(selectedTrainId);
  }, [selectedTrainId, use3DMode]);

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
      ['all',
        ['==', ['slice', ['get', 'track_id'], 0, 2], 'Y-'],
        visibleLines.has('Y')
      ], 0.8,
      0.0
    ]);

    // 貓空纜車圖層可見性（三段式控制：full/tracks-only 顯示，hidden 隱藏）
    if (map.current.getLayer('tracks-line-mk')) {
      map.current.setPaintProperty('tracks-line-mk', 'line-opacity',
        mkState !== 'hidden' ? 0.8 : 0.0
      );
    }
  }, [mapLoaded, visibleLines, mkState, styleVersion]);

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
        // 依路線設定邊線顏色：K 開頭 → 安坑輕軌, V 開頭 → 淡海輕軌, G 開頭 → 綠線, BL 開頭 → 藍線, BR 開頭 → 文湖線, O 開頭 → 橘線, A 開頭 → 機場捷運, Y 開頭 → 環狀線, 其餘 → 紅線
        'circle-stroke-color': [
          'case',
          ['==', ['slice', ['get', 'station_id'], 0, 2], 'MK'], TRACK_COLORS.MK, // 貓空纜車（須在 K 之前檢查）
          ['==', ['slice', ['get', 'station_id'], 0, 1], 'K'], TRACK_COLORS.K,
          ['==', ['slice', ['get', 'station_id'], 0, 1], 'V'], TRACK_COLORS.V,
          ['==', ['slice', ['get', 'station_id'], 0, 1], 'G'], TRACK_COLORS.G,
          ['==', ['slice', ['get', 'station_id'], 0, 2], 'BL'], TRACK_COLORS.BL,
          ['==', ['slice', ['get', 'station_id'], 0, 2], 'BR'], TRACK_COLORS.BR,
          ['==', ['slice', ['get', 'station_id'], 0, 1], 'O'], TRACK_COLORS.O,
          ['==', ['slice', ['get', 'station_id'], 0, 1], 'A'], TRACK_COLORS.A,  // 機場捷運
          ['==', ['slice', ['get', 'station_id'], 0, 1], 'Y'], TRACK_COLORS.Y,  // 環狀線
          TRACK_COLORS.R
        ],
        'circle-stroke-width': 1.8,
        // 發光強度：讓車站在夜間模式也保持明亮
        'circle-emissive-strength': 1.0,
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
        // 發光強度：讓標籤在夜間模式也保持明亮
        'text-emissive-strength': 1.0,
      },
    });
  }, [mapLoaded, stations, styleVersion]);

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
      ['all',
        ['==', ['slice', ['get', 'station_id'], 0, 1], 'Y'],
        visibleLines.has('Y')
      ], 1,
      ['all',
        ['==', ['slice', ['get', 'station_id'], 0, 2], 'MK'],
        mkState !== 'hidden'  // MK 使用三段式：full/tracks-only 顯示，hidden 隱藏
      ], 1,
      0
    ];

    map.current.setPaintProperty('stations-circle', 'circle-opacity', stationOpacityExpr);
    map.current.setPaintProperty('stations-circle', 'circle-stroke-opacity', stationOpacityExpr);
    map.current.setLayoutProperty('stations-label', 'visibility',
      visibleLines.size > 0 || mkState !== 'hidden' ? 'visible' : 'none'
    );
    // 標籤使用相同的 opacity 邏輯
    map.current.setPaintProperty('stations-label', 'text-opacity', stationOpacityExpr);
  }, [mapLoaded, visibleLines, mkState, styleVersion]);

  // 初始化時間引擎
  useEffect(() => {
    const engine = new TimeEngine({
      speed: 60, // 初始速度與 UI 同步
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

  // 初始化高鐵列車引擎並訂閱時間更新
  useEffect(() => {
    if (!timeEngineReady || !timeEngineRef.current) return;
    if (thsrSchedules.size === 0 || thsrTrackMap.size === 0) return;

    // 建立高鐵列車引擎
    const thsrEngine = new ThsrTrainEngine({
      schedules: thsrSchedules,
      tracks: thsrTrackMap,
    });

    // 設置車站進度（用於軌道內插定位）
    thsrEngine.setStationProgress(thsrStationProgress);

    thsrTrainEngineRef.current = thsrEngine;

    // 訂閱時間更新
    const unsubscribe = timeEngineRef.current.onTick(() => {
      if (timeEngineRef.current) {
        const timeSeconds = timeEngineRef.current.getTimeOfDaySeconds();
        const activeTrains = thsrEngine.update(timeSeconds);
        setThsrTrains(activeTrains);
      }
    });

    // 初始更新
    const timeSeconds = timeEngineRef.current.getTimeOfDaySeconds();
    setThsrTrains(thsrEngine.update(timeSeconds));

    return () => {
      unsubscribe();
      thsrTrainEngineRef.current = null;
    };
  }, [timeEngineReady, thsrSchedules, thsrTrackMap, thsrStationProgress]);

  // 初始化高雄捷運列車引擎並訂閱時間更新
  useEffect(() => {
    if (!timeEngineReady || !timeEngineRef.current) return;
    if (krtcSchedules.size === 0 || krtcTrackMap.size === 0) return;

    // 建立高雄捷運列車引擎
    const krtcEngine = new KrtcTrainEngine({
      schedules: krtcSchedules,
      tracks: krtcTrackMap,
    });

    // 設置車站進度（用於軌道內插定位）
    krtcEngine.setStationProgress(krtcStationProgress);

    krtcTrainEngineRef.current = krtcEngine;

    // 訂閱時間更新
    const unsubscribe = timeEngineRef.current.onTick(() => {
      if (timeEngineRef.current) {
        const timeSeconds = timeEngineRef.current.getTimeOfDaySeconds();
        const activeTrains = krtcEngine.update(timeSeconds);
        setKrtcTrains(activeTrains);
      }
    });

    // 初始更新
    const timeSeconds = timeEngineRef.current.getTimeOfDaySeconds();
    setKrtcTrains(krtcEngine.update(timeSeconds));

    return () => {
      unsubscribe();
      krtcTrainEngineRef.current = null;
    };
  }, [timeEngineReady, krtcSchedules, krtcTrackMap, krtcStationProgress]);

  // 初始化高雄輕軌列車引擎並訂閱時間更新
  useEffect(() => {
    if (!timeEngineReady || !timeEngineRef.current) return;
    if (klrtSchedules.size === 0 || klrtTrackMap.size === 0) return;

    // 建立高雄輕軌列車引擎
    const klrtEngine = new KlrtTrainEngine({
      schedules: klrtSchedules,
      tracks: klrtTrackMap,
    });

    // 設置車站進度（用於軌道內插定位）
    klrtEngine.setStationProgress(klrtStationProgress);

    klrtTrainEngineRef.current = klrtEngine;

    // 訂閱時間更新
    const unsubscribe = timeEngineRef.current.onTick(() => {
      if (timeEngineRef.current) {
        const timeSeconds = timeEngineRef.current.getTimeOfDaySeconds();
        const activeTrains = klrtEngine.update(timeSeconds);
        setKlrtTrains(activeTrains);
      }
    });

    // 初始更新
    const timeSeconds = timeEngineRef.current.getTimeOfDaySeconds();
    setKlrtTrains(klrtEngine.update(timeSeconds));

    return () => {
      unsubscribe();
      klrtTrainEngineRef.current = null;
    };
  }, [timeEngineReady, klrtSchedules, klrtTrackMap, klrtStationProgress]);

  // 初始化台中捷運列車引擎並訂閱時間更新
  useEffect(() => {
    if (!timeEngineReady || !timeEngineRef.current) return;
    if (tmrtSchedules.size === 0 || tmrtTrackMap.size === 0) return;

    // 建立台中捷運列車引擎
    const tmrtEngine = new TmrtTrainEngine({
      schedules: tmrtSchedules,
      tracks: tmrtTrackMap,
    });

    // 設置車站進度（用於軌道內插定位）
    tmrtEngine.setStationProgress(tmrtStationProgress);

    tmrtTrainEngineRef.current = tmrtEngine;

    // 訂閱時間更新
    const unsubscribe = timeEngineRef.current.onTick(() => {
      if (timeEngineRef.current) {
        const timeSeconds = timeEngineRef.current.getTimeOfDaySeconds();
        const activeTrains = tmrtEngine.update(timeSeconds);
        setTmrtTrains(activeTrains);
      }
    });

    // 初始更新
    const timeSeconds = timeEngineRef.current.getTimeOfDaySeconds();
    setTmrtTrains(tmrtEngine.update(timeSeconds));

    return () => {
      unsubscribe();
      tmrtTrainEngineRef.current = null;
    };
  }, [timeEngineReady, tmrtSchedules, tmrtTrackMap, tmrtStationProgress]);

  // 更新列車標記（2D 模式時使用）
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    // 3D 模式時清除所有 2D 標記並跳過
    if (use3DMode) {
      for (const marker of trainMarkers.current.values()) {
        marker.remove();
      }
      trainMarkers.current.clear();
      return;
    }

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
      const isSelected = train.trainId === selectedTrainId;
      const baseColor = getTrainColor(train.trackId);  // 依路線和方向區分顏色
      // 碰撞時使用警示色
      const displayColor = isColliding ? '#ffcc00' : baseColor;

      if (!marker) {
        const el = document.createElement('div');
        el.className = 'train-marker';
        el.dataset.trainId = train.trainId;

        // 點擊事件：選取列車
        el.addEventListener('click', (e) => {
          e.stopPropagation();
          const trainId = el.dataset.trainId;
          if (trainId) {
            handleSelectTrain(trainId);
          }
        });

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
      // 效能優化：追蹤狀態變化，只在狀態改變時才更新 cssText
      const el = marker.getElement();
      const newState = `${isSelected}-${isColliding}-${isStopped}-${displayColor}`;
      const prevState = el.dataset.trainState;

      if (prevState !== newState) {
        el.dataset.trainState = newState;

        // 基礎樣式：啟用點擊、顯示指標手勢
        const baseStyles = `
          pointer-events: auto;
          cursor: pointer;
          border-radius: 50%;
          transition: width 0.3s ease, height 0.3s ease, box-shadow 0.3s ease;
        `;

        if (isSelected) {
          // 選中狀態：顯示粗白框
          el.style.cssText = `
            ${baseStyles}
            width: 18px;
            height: 18px;
            background-color: ${displayColor};
            border: 4px solid #ffffff;
            box-shadow: 0 0 16px rgba(255,255,255,0.8), 0 0 24px ${displayColor};
            z-index: 10;
          `;
        } else if (isColliding) {
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
    }
  }, [mapLoaded, filteredTrains, use3DMode, handleSelectTrain, selectedTrainId]);

  // 更新高鐵列車標記（2D 模式時使用）
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    // 3D 模式時清除所有 2D 標記並跳過
    if (use3DMode) {
      for (const marker of thsrTrainMarkers.current.values()) {
        marker.remove();
      }
      thsrTrainMarkers.current.clear();
      return;
    }

    const activeTrainIds = new Set(filteredThsrTrains.map((t) => t.trainId));
    for (const [trainId, marker] of thsrTrainMarkers.current) {
      if (!activeTrainIds.has(trainId)) {
        marker.remove();
        thsrTrainMarkers.current.delete(trainId);
      }
    }

    for (const train of filteredThsrTrains) {
      let marker = thsrTrainMarkers.current.get(train.trainId);
      const isStopped = train.status === 'stopped';
      const isSelected = train.trainId === selectedTrainId;
      const direction = getThsrDirection(train.trackId);
      const baseColor = THSR_TRAIN_COLORS[`THSR_${direction}`] || THSR_TRACK_COLOR;

      if (!marker) {
        const el = document.createElement('div');
        el.className = 'thsr-train-marker';
        el.dataset.trainId = train.trainId;

        // 點擊事件：選取列車
        el.addEventListener('click', (e) => {
          e.stopPropagation();
          const trainId = el.dataset.trainId;
          if (trainId) {
            handleSelectTrain(trainId);
          }
        });

        marker = new mapboxgl.Marker({
          element: el,
          anchor: 'center',
        })
          .setLngLat(train.position)
          .addTo(map.current!);

        thsrTrainMarkers.current.set(train.trainId, marker);
      }

      // 更新位置
      marker.setLngLat(train.position);

      // 更新樣式（含選中狀態）
      const el = marker.getElement();
      const newState = `${isSelected}-${isStopped}-${baseColor}`;
      const prevState = el.dataset.trainState;

      if (prevState !== newState) {
        el.dataset.trainState = newState;

        const baseStyles = `
          pointer-events: auto;
          cursor: pointer;
          border-radius: 4px;
          transition: width 0.3s ease, height 0.3s ease, box-shadow 0.3s ease;
        `;

        if (isSelected) {
          // 選中狀態：顯示粗白框
          el.style.cssText = `
            ${baseStyles}
            width: 20px;
            height: 12px;
            background-color: ${baseColor};
            border: 4px solid #ffffff;
            box-shadow: 0 0 16px rgba(255,255,255,0.8), 0 0 24px ${baseColor};
            z-index: 10;
          `;
        } else if (isStopped) {
          el.style.cssText = `
            ${baseStyles}
            width: 16px;
            height: 10px;
            background-color: ${baseColor};
            border: 2px solid #ffffff;
            box-shadow: 0 0 8px ${baseColor}, 0 0 12px rgba(255,255,255,0.5);
          `;
        } else {
          el.style.cssText = `
            ${baseStyles}
            width: 14px;
            height: 8px;
            background-color: ${baseColor};
            border: 2px solid #ffffff;
            box-shadow: 0 0 4px rgba(0,0,0,0.5);
          `;
        }
      }
    }
  }, [mapLoaded, filteredThsrTrains, use3DMode, handleSelectTrain, selectedTrainId]);

  // 更新高雄捷運列車標記（2D 模式時使用）
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    // 3D 模式時清除所有 2D 標記並跳過
    if (use3DMode) {
      for (const marker of krtcTrainMarkers.current.values()) {
        marker.remove();
      }
      krtcTrainMarkers.current.clear();
      return;
    }

    const activeTrainIds = new Set(filteredKrtcTrains.map((t) => t.trainId));
    for (const [trainId, marker] of krtcTrainMarkers.current) {
      if (!activeTrainIds.has(trainId)) {
        marker.remove();
        krtcTrainMarkers.current.delete(trainId);
      }
    }

    for (const train of filteredKrtcTrains) {
      let marker = krtcTrainMarkers.current.get(train.trainId);
      const isStopped = train.status === 'stopped';
      const isSelected = train.trainId === selectedTrainId;
      const lineId = getKrtcLineId(train.trackId);
      const direction = getKrtcDirection(train.trackId);
      const baseColor = KRTC_TRAIN_COLORS[`${lineId}_${direction}`] || KRTC_TRACK_COLORS[lineId] || '#f8981d';

      if (!marker) {
        const el = document.createElement('div');
        el.className = 'krtc-train-marker';
        el.dataset.trainId = train.trainId;

        // 點擊事件：選取列車
        el.addEventListener('click', (e) => {
          e.stopPropagation();
          const trainId = el.dataset.trainId;
          if (trainId) {
            handleSelectTrain(trainId);
          }
        });

        marker = new mapboxgl.Marker({
          element: el,
          anchor: 'center',
        })
          .setLngLat(train.position)
          .addTo(map.current!);

        krtcTrainMarkers.current.set(train.trainId, marker);
      }

      // 更新位置
      marker.setLngLat(train.position);

      // 更新樣式（含選中狀態）
      const el = marker.getElement();
      const newState = `${isSelected}-${isStopped}-${baseColor}`;
      const prevState = el.dataset.trainState;

      if (prevState !== newState) {
        el.dataset.trainState = newState;

        const baseStyles = `
          pointer-events: auto;
          cursor: pointer;
          border-radius: 50%;
          transition: width 0.3s ease, height 0.3s ease, box-shadow 0.3s ease;
        `;

        if (isSelected) {
          // 選中狀態：顯示粗白框
          el.style.cssText = `
            ${baseStyles}
            width: 18px;
            height: 18px;
            background-color: ${baseColor};
            border: 4px solid #ffffff;
            box-shadow: 0 0 16px rgba(255,255,255,0.8), 0 0 24px ${baseColor};
            z-index: 10;
          `;
        } else if (isStopped) {
          el.style.cssText = `
            ${baseStyles}
            width: 14px;
            height: 14px;
            background-color: ${baseColor};
            border: 2px solid #ffffff;
            box-shadow: 0 0 8px ${baseColor}, 0 0 12px rgba(255,255,255,0.5);
          `;
        } else {
          el.style.cssText = `
            ${baseStyles}
            width: 12px;
            height: 12px;
            background-color: ${baseColor};
            border: 2px solid #ffffff;
            box-shadow: 0 0 4px rgba(0,0,0,0.5);
          `;
        }
      }
    }
  }, [mapLoaded, filteredKrtcTrains, use3DMode, handleSelectTrain, selectedTrainId]);

  // 更新高雄輕軌列車標記（2D 模式時使用）
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    // 3D 模式時清除所有 2D 標記並跳過
    if (use3DMode) {
      for (const marker of klrtTrainMarkers.current.values()) {
        marker.remove();
      }
      klrtTrainMarkers.current.clear();
      return;
    }

    const activeTrainIds = new Set(filteredKlrtTrains.map((t) => t.trainId));
    for (const [trainId, marker] of klrtTrainMarkers.current) {
      if (!activeTrainIds.has(trainId)) {
        marker.remove();
        klrtTrainMarkers.current.delete(trainId);
      }
    }

    for (const train of filteredKlrtTrains) {
      let marker = klrtTrainMarkers.current.get(train.trainId);
      const isStopped = train.status === 'stopped';
      const isSelected = train.trainId === selectedTrainId;
      const lineId = getKlrtLineId(train.trackId);
      const direction = getKlrtDirection(train.trackId);
      const baseColor = KLRT_TRAIN_COLORS[`${lineId}_${direction}`] || KLRT_TRACK_COLORS[lineId] || '#99cc00';

      if (!marker) {
        const el = document.createElement('div');
        el.className = 'klrt-train-marker';
        el.dataset.trainId = train.trainId;

        // 點擊事件：選取列車
        el.addEventListener('click', (e) => {
          e.stopPropagation();
          const trainId = el.dataset.trainId;
          if (trainId) {
            handleSelectTrain(trainId);
          }
        });

        marker = new mapboxgl.Marker({
          element: el,
          anchor: 'center',
        })
          .setLngLat(train.position)
          .addTo(map.current!);

        klrtTrainMarkers.current.set(train.trainId, marker);
      }

      // 更新位置
      marker.setLngLat(train.position);

      // 更新樣式（含選中狀態）
      const el = marker.getElement();
      const newState = `${isSelected}-${isStopped}-${baseColor}`;
      const prevState = el.dataset.trainState;

      if (prevState !== newState) {
        el.dataset.trainState = newState;

        const baseStyles = `
          pointer-events: auto;
          cursor: pointer;
          border-radius: 50%;
          transition: width 0.3s ease, height 0.3s ease, box-shadow 0.3s ease;
        `;

        if (isSelected) {
          // 選中狀態：顯示粗白框
          el.style.cssText = `
            ${baseStyles}
            width: 18px;
            height: 18px;
            background-color: ${baseColor};
            border: 4px solid #ffffff;
            box-shadow: 0 0 16px rgba(255,255,255,0.8), 0 0 24px ${baseColor};
            z-index: 10;
          `;
        } else if (isStopped) {
          el.style.cssText = `
            ${baseStyles}
            width: 14px;
            height: 14px;
            background-color: ${baseColor};
            border: 2px solid #ffffff;
            box-shadow: 0 0 8px ${baseColor}, 0 0 12px rgba(255,255,255,0.5);
          `;
        } else {
          el.style.cssText = `
            ${baseStyles}
            width: 12px;
            height: 12px;
            background-color: ${baseColor};
            border: 2px solid #ffffff;
            box-shadow: 0 0 4px rgba(0,0,0,0.5);
          `;
        }
      }
    }
  }, [mapLoaded, filteredKlrtTrains, use3DMode, handleSelectTrain, selectedTrainId]);

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

    if (thsrTrainEngineRef.current) {
      const activeThsrTrains = thsrTrainEngineRef.current.update(seconds);
      setThsrTrains(activeThsrTrains);
    }

    if (krtcTrainEngineRef.current) {
      const activeKrtcTrains = krtcTrainEngineRef.current.update(seconds);
      setKrtcTrains(activeKrtcTrains);
    }

    if (klrtTrainEngineRef.current) {
      const activeKlrtTrains = klrtTrainEngineRef.current.update(seconds);
      setKlrtTrains(activeKlrtTrains);
    }
  }, []);

  // 2D/3D 模式切換（含視角轉換）
  const handleToggle3DMode = useCallback(() => {
    if (!map.current) return;

    const newMode = !use3DMode;
    setUse3DMode(newMode);

    if (newMode) {
      // 切換到 3D 模式：拉近、傾斜 45 度
      map.current.easeTo({
        zoom: 14,
        pitch: 45,
        bearing: 0,
        duration: 1000,
      });
    } else {
      // 切換到 2D 模式：拉遠、回復平面
      map.current.easeTo({
        zoom: 10.8,
        pitch: 0,
        bearing: 0,
        duration: 1000,
      });
    }
  }, [use3DMode]);

  // 切換光線預設（僅用於 standard 樣式）
  const switchLightPreset = useCallback((preset: LightPreset) => {
    if (!map.current || currentMapStyleRef.current !== 'standard') return;
    if (currentLightPresetRef.current === preset) return;
    currentLightPresetRef.current = preset;
    map.current.setConfigProperty('basemap', 'lightPreset', preset);
  }, []);

  // 切換地圖樣式（standard 或 dark-v11）
  const switchMapStyle = useCallback((targetStyle: 'standard' | 'dark') => {
    if (!map.current || currentMapStyleRef.current === targetStyle) return;
    currentMapStyleRef.current = targetStyle;

    // 切換樣式會移除所有圖層
    map.current.setStyle(MAP_STYLES[targetStyle]);

    // 樣式載入完成後，遞增版本號觸發圖層重建
    map.current.once('style.load', () => {
      setStyleVersion(v => v + 1);
    });
  }, []);

  // 更新視覺主題
  useEffect(() => {
    const newVisualTheme = getVisualTheme(mapTheme, currentHour);
    setVisualTheme(newVisualTheme);
  }, [mapTheme, currentHour]);

  // 自動模式：根據時間軸時間切換光線
  useEffect(() => {
    if (mapTheme !== 'auto' || !timeEngineRef.current || !mapLoaded) return;

    // 確保使用 standard 樣式
    if (currentMapStyleRef.current !== 'standard') {
      switchMapStyle('standard');
    }

    // 初始設定
    const initialHour = timeEngineRef.current.getTime().getHours();
    setCurrentHour(initialHour);
    switchLightPreset(getPresetForHour(initialHour));

    // 監聯時間變化
    const unsubscribe = timeEngineRef.current.onTick((time) => {
      const hour = time.getHours();
      setCurrentHour(hour);
      const targetPreset = getPresetForHour(hour);
      if (currentLightPresetRef.current !== targetPreset) {
        switchLightPreset(targetPreset);
      }
    });

    return () => unsubscribe();
  }, [mapTheme, mapLoaded, switchLightPreset, switchMapStyle]);

  // 手動模式：切換樣式或光線
  useEffect(() => {
    if (mapTheme === 'auto' || !mapLoaded) return;

    if (mapTheme === 'dark') {
      // 使用 dark-v11 樣式
      switchMapStyle('dark');
    } else {
      // 使用 standard 樣式 + lightPreset
      if (currentMapStyleRef.current !== 'standard') {
        switchMapStyle('standard');
        // 樣式切換後需要等待 style.load 才能設定 lightPreset
        map.current?.once('style.load', () => {
          switchLightPreset(mapTheme as LightPreset);
        });
      } else {
        switchLightPreset(mapTheme as LightPreset);
      }
    }
  }, [mapTheme, mapLoaded, switchLightPreset, switchMapStyle]);

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

  // 根據視覺主題設定的樣式
  const isDarkTheme = visualTheme === 'dark';
  const themeColors = {
    panelBg: isDarkTheme ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.9)',
    panelText: isDarkTheme ? '#fff' : '#333',
    panelTextSecondary: isDarkTheme ? '#888' : '#666',
    panelBorder: isDarkTheme ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
  };

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      {/* 標題 */}
      <div
        style={{
          position: 'absolute',
          top: 20,
          left: 20,
          zIndex: 10,
          color: themeColors.panelText,
          fontFamily: 'system-ui',
        }}
      >
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>
          Mini Taipei V3
        </h1>
        <p style={{ margin: '4px 0 0', fontSize: 14, color: themeColors.panelTextSecondary }}>
          台北交通運輸模擬
        </p>
      </div>

      {/* 跟隨模式狀態提示 */}
      <div
        style={{
          position: 'absolute',
          top: 20,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 10,
          background: themeColors.panelBg,
          borderRadius: 20,
          padding: '8px 16px',
          color: themeColors.panelText,
          fontFamily: 'system-ui',
          fontSize: 12,
          whiteSpace: 'nowrap',
          backdropFilter: 'blur(8px)',
          border: isFollowing ? '1px solid rgba(217, 0, 35, 0.6)' : `1px solid ${themeColors.panelBorder}`,
          boxShadow: isFollowing ? '0 0 12px rgba(217, 0, 35, 0.4), 0 0 24px rgba(217, 0, 35, 0.2)' : 'none',
          transition: 'all 0.3s ease',
        }}
      >
        {isFollowing ? (
          <span style={{ color: '#ff8a8a' }}>
            跟隨模式中，可縮放焦距，關閉右上面板可退出
          </span>
        ) : (
          <span style={{ color: themeColors.panelTextSecondary }}>
            可暫停後點選列車開啟跟隨模式
          </span>
        )}
      </div>

      {/* 圖例 */}
      <div
        style={{
          position: 'absolute',
          top: 90,
          left: 20,
          zIndex: 10,
          background: themeColors.panelBg,
          borderRadius: 8,
          padding: '10px 14px',
          color: themeColors.panelText,
          fontFamily: 'system-ui',
          fontSize: 12,
          backdropFilter: 'blur(8px)',
          border: `1px solid ${themeColors.panelBorder}`,
          transition: 'background 0.3s, color 0.3s, border-color 0.3s',
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
          <span style={{ fontWeight: 600, color: themeColors.panelTextSecondary }}>圖例</span>
        </div>

        {/* 可收合內容區 */}
        <div
          style={{
            maxHeight: legendCollapsed ? 0 : 320,
            overflow: legendCollapsed ? 'hidden' : 'auto',
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
              <span style={{ color: themeColors.panelTextSecondary }}>往淡水</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.R_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: themeColors.panelTextSecondary }}>往象山</span>
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
              <span style={{ color: themeColors.panelTextSecondary }}>往南港展覽館</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.BL_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: themeColors.panelTextSecondary }}>往頂埔</span>
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
              <span style={{ color: themeColors.panelTextSecondary }}>往新店</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.G_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: themeColors.panelTextSecondary }}>往松山</span>
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
              <span style={{ color: themeColors.panelTextSecondary }}>七張↔小碧潭</span>
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
              <span style={{ color: themeColors.panelTextSecondary }}>往南勢角</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.O_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: themeColors.panelTextSecondary }}>往迴龍/蘆洲</span>
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
              <span style={{ color: themeColors.panelTextSecondary }}>往南港展覽館</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.BR_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: themeColors.panelTextSecondary }}>往動物園</span>
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
              <span style={{ color: themeColors.panelTextSecondary }}>往十四張</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.K_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: themeColors.panelTextSecondary }}>往雙城</span>
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
              <span style={{ color: themeColors.panelTextSecondary }}>往崁頂/台北海洋大學</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
              <div style={{ width: 8, height: 8, background: TRAIN_COLORS.V_1, borderRadius: '50%', border: '1px solid white' }} />
              <span style={{ color: themeColors.panelTextSecondary }}>往紅樹林/淡水漁人碼頭</span>
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
          background: themeColors.panelBg,
          borderRadius: 20,
          padding: '8px 16px',
          backdropFilter: 'blur(8px)',
          border: `1px solid ${themeColors.panelBorder}`,
          transition: 'background 0.3s, border-color 0.3s',
        }}
      >
        <a
          href="https://github.com/ianlkl11234s/mini-taiwan-learning-project"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: themeColors.panelTextSecondary, transition: 'color 0.2s' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = themeColors.panelText)}
          onMouseLeave={(e) => (e.currentTarget.style.color = themeColors.panelTextSecondary)}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
          </svg>
        </a>
        <a
          href="https://www.threads.com/@ianlkl1314"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: themeColors.panelTextSecondary, transition: 'color 0.2s' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = themeColors.panelText)}
          onMouseLeave={(e) => (e.currentTarget.style.color = themeColors.panelTextSecondary)}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.96-.065-1.182.408-2.256 1.332-3.025.88-.732 2.084-1.195 3.59-1.377.954-.115 1.963-.104 2.998.032-.06-1.289-.693-1.95-1.89-1.984-1.1-.033-1.921.564-2.214 1.013l-1.706-1.046c.655-1.07 1.916-1.828 3.534-2.127l.085-.015c.822-.14 1.67-.14 2.494 0 1.588.268 2.765.985 3.498 2.132.68 1.064.882 2.37.6 3.887l.007-.024.007.024c-.02.1-.043.198-.068.295.85.39 1.577.94 2.133 1.62.832 1.016 1.233 2.29 1.16 3.692-.094 1.77-.74 3.353-1.921 4.705C18.09 22.843 15.448 23.977 12.186 24zm.102-7.26c.775-.045 1.39-.315 1.828-.803.438-.487.728-1.164.863-2.012-.65-.078-1.307-.112-1.958-.102-.986.016-1.779.2-2.36.548-.59.355-.873.81-.84 1.354.034.538.345.967.876 1.209.53.24 1.122.307 1.59.306z"/>
          </svg>
        </a>
        {/* 日夜模式切換 */}
        <ThemeToggle theme={mapTheme} onChange={setMapTheme} visualTheme={visualTheme} />
        {/* 2D/3D 切換按鈕 */}
        <button
          onClick={handleToggle3DMode}
          style={{
            background: use3DMode ? 'rgba(102, 196, 160, 0.2)' : 'rgba(128, 191, 255, 0.2)',
            border: `1px solid ${use3DMode ? '#66c4a0' : '#80bfff'}`,
            borderRadius: 4,
            color: use3DMode ? '#66c4a0' : '#80bfff',
            cursor: 'pointer',
            padding: '4px 8px',
            fontSize: 12,
            fontWeight: 600,
            transition: 'all 0.2s',
          }}
          title={use3DMode ? '切換至 2D 模式' : '切換至 3D 模式'}
        >
          {use3DMode ? '3D' : '2D'}
        </button>
        {/* 說明/公告按鈕 */}
        <button
          onClick={() => setShowInfoModal(true)}
          style={{
            background: 'none',
            border: 'none',
            color: themeColors.panelTextSecondary,
            cursor: 'pointer',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            transition: 'color 0.2s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = themeColors.panelText)}
          onMouseLeave={(e) => (e.currentTarget.style.color = themeColors.panelTextSecondary)}
          title="說明與公告"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z"/>
          </svg>
        </button>
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

      {/* 城市選擇器 - 路線篩選器上方 */}
      <CitySelector
        onCitySelect={handleCitySelect}
        selectedCity={selectedCity}
        visualTheme={visualTheme}
      />

      {/* 路線篩選器 - 控制面板左上方漂浮 */}
      <LineFilter
        visibleLines={visibleLines}
        onToggleLine={handleToggleLine}
        onToggleAllMrt={handleToggleAllMrt}
        mkState={mkState}
        onMKStateChange={handleMKStateChange}
        thsrState={thsrState}
        onThsrStateChange={handleThsrStateChange}
        visibleKrtcLines={visibleKrtcLines}
        onToggleKrtcLine={handleToggleKrtcLine}
        onToggleAllKrtc={handleToggleAllKrtc}
        visibleTmrtLines={visibleTmrtLines}
        onToggleTmrtLine={handleToggleTmrtLine}
        onToggleAllTmrt={handleToggleAllTmrt}
        visualTheme={visualTheme}
      />

      {/* 列車資訊面板 */}
      {selectedTrain && (
        <TrainInfoPanel
          train={selectedTrain}
          stationNames={stationNames}
          onClose={handleDeselectTrain}
          visualTheme={visualTheme}
        />
      )}

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
            visualTheme={visualTheme}
          />
        </div>
      )}

      {/* 時間控制 */}
      {timeEngineRef.current && (
        <TimeControl
          timeEngine={timeEngineRef.current}
          currentTime={currentTime}
          trainCount={mrtCount}
          isPlaying={isPlaying}
          speed={speed}
          onTogglePlay={handleTogglePlay}
          onSpeedChange={handleSpeedChange}
          onTimeChange={handleTimeChange}
          visualTheme={visualTheme}
        />
      )}

      {/* 說明/公告 Modal */}
      {showInfoModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setShowInfoModal(false)}
        >
          <div
            style={{
              background: '#1a1a1a',
              borderRadius: 12,
              padding: '24px 28px',
              maxWidth: 500,
              width: '90%',
              maxHeight: '80vh',
              overflow: 'auto',
              color: 'white',
              fontFamily: 'system-ui',
              boxShadow: '0 4px 24px rgba(0, 0, 0, 0.5)',
              border: '1px solid #333',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* 標題與關閉按鈕 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>說明與公告</h2>
              <button
                onClick={() => setShowInfoModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#888',
                  cursor: 'pointer',
                  padding: 4,
                  display: 'flex',
                  alignItems: 'center',
                  transition: 'color 0.2s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
                onMouseLeave={(e) => (e.currentTarget.style.color = '#888')}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
              </button>
            </div>

            {/* 公告區塊 */}
            <div style={{ marginBottom: 24 }}>
              <h3 style={{ margin: '0 0 12px', fontSize: 16, fontWeight: 600, color: '#f8b61c', display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 18 }}>📢</span> 公告
              </h3>
              <div style={{ background: '#2a2a2a', borderRadius: 8, padding: '12px 16px', fontSize: 14, lineHeight: 1.6 }}>
                <p style={{ margin: '0 0 8px', color: '#fff' }}>網站為學習性質，仍需持續優化中！</p>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li style={{ color: '#ccc' }}>文湖線與環狀線，目前還未調整好首班車時刻表</li>
                </ul>
              </div>
            </div>

            {/* 使用說明區塊 */}
            <div>
              <h3 style={{ margin: '0 0 12px', fontSize: 16, fontWeight: 600, color: '#66c4a0', display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 18 }}>📖</span> 使用說明
              </h3>
              <div style={{ background: '#2a2a2a', borderRadius: 8, padding: '12px 16px', fontSize: 14, lineHeight: 1.8 }}>
                <div style={{ marginBottom: 12 }}>
                  <strong style={{ color: '#80bfff' }}>時間控制</strong>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 20, color: '#ccc' }}>
                    <li>點擊播放/暫停按鈕控制時間流動</li>
                    <li>拖動時間軸可跳轉至任意時刻</li>
                    <li>使用速度滑桿調整模擬速度（1x - 300x）</li>
                  </ul>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <strong style={{ color: '#80bfff' }}>路線篩選</strong>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 20, color: '#ccc' }}>
                    <li>點擊左下角 MRT / Cable 按鈕展開路線選單</li>
                    <li>點擊路線按鈕可顯示/隱藏特定路線</li>
                    <li>貓空纜車支援三段式切換：全部顯示 → 僅軌道 → 隱藏</li>
                  </ul>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <strong style={{ color: '#80bfff' }}>列車跟隨</strong>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 20, color: '#ccc' }}>
                    <li>暫停後點擊任意列車可開啟跟隨模式</li>
                    <li>跟隨時地圖會自動追蹤列車位置</li>
                    <li>右上角會顯示列車詳細資訊（路線、前後站、狀態）</li>
                    <li>關閉資訊面板即可退出跟隨模式</li>
                  </ul>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <strong style={{ color: '#80bfff' }}>2D / 3D 模式</strong>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 20, color: '#ccc' }}>
                    <li>點擊右上角 2D/3D 按鈕切換視角</li>
                    <li>3D 模式下列車以立體方塊呈現</li>
                    <li>3D 跟隨時可自由旋轉視角，放開後自動回到列車位置</li>
                  </ul>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <strong style={{ color: '#80bfff' }}>日夜主題</strong>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 20, color: '#ccc' }}>
                    <li>點擊右上角主題選單切換地圖外觀</li>
                    <li>支援：Auto（隨時間自動切換）、Dawn、Day、Dusk、Night、Dark</li>
                    <li>所有控制面板會自動配合主題調整顏色</li>
                  </ul>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <strong style={{ color: '#80bfff' }}>列車狀態</strong>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 20, color: '#ccc' }}>
                    <li><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: '#d90023', marginRight: 6, verticalAlign: 'middle' }}></span>運行中：正常大小</li>
                    <li><span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: '#d90023', border: '2px solid white', marginRight: 6, verticalAlign: 'middle', boxShadow: '0 0 8px #d90023' }}></span>停站中：較大、有光暈</li>
                  </ul>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <strong style={{ color: '#80bfff' }}>列車數量圖</strong>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 20, color: '#ccc' }}>
                    <li>右下角顯示全天列車數量變化</li>
                    <li>白色線條表示目前時刻</li>
                  </ul>
                </div>
                <div>
                  <strong style={{ color: '#80bfff' }}>地圖操作</strong>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 20, color: '#ccc' }}>
                    <li>滾輪縮放地圖</li>
                    <li>拖曳平移地圖</li>
                    <li>右鍵拖曳可旋轉視角（3D 模式）</li>
                    <li>右上角有縮放控制按鈕</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
