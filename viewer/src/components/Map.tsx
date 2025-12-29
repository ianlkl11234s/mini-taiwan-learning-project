import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import type { Train } from '../engines/TrainEngine';
import type { TrackCollection, StationCollection } from '../types/track';

// Mapbox Access Token (需要設定環境變數)
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || '';

interface MapProps {
  tracks: TrackCollection | null;
  stations: StationCollection | null;
  trains: Train[];
}

// 軌道顏色
const TRACK_COLORS: Record<string, string> = {
  'R-1-0': '#d90023',
  'R-1-1': '#d90023',
  'R-2-0': '#e63946',
  'R-2-1': '#e63946',
  'R-3-0': '#ff6b6b',
  'R-3-1': '#ff6b6b',
};

export function Map({ tracks, stations, trains }: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const trainMarkers = useRef<Map<string, mapboxgl.Marker>>(new Map());
  const [mapLoaded, setMapLoaded] = useState(false);

  // 初始化地圖
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [121.52, 25.08], // 台北市中心
      zoom: 11.5,
      pitch: 0,
      bearing: 0,
    });

    map.current.on('load', () => {
      setMapLoaded(true);
    });

    // 新增導航控制
    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  // 載入軌道圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !tracks) return;

    // 移除舊的軌道圖層
    if (map.current.getSource('tracks')) {
      map.current.removeLayer('tracks-line');
      map.current.removeSource('tracks');
    }

    // 新增軌道資料源
    map.current.addSource('tracks', {
      type: 'geojson',
      data: tracks,
    });

    // 新增軌道線條圖層
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
        'line-opacity': 0.8,
      },
    });
  }, [mapLoaded, tracks]);

  // 載入車站圖層
  useEffect(() => {
    if (!map.current || !mapLoaded || !stations) return;

    // 移除舊的車站圖層
    if (map.current.getSource('stations')) {
      map.current.removeLayer('stations-circle');
      map.current.removeLayer('stations-label');
      map.current.removeSource('stations');
    }

    // 新增車站資料源
    map.current.addSource('stations', {
      type: 'geojson',
      data: stations,
    });

    // 新增車站圓點圖層
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

    // 新增車站標籤圖層
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

  // 更新列車標記
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    // 移除不再活躍的列車標記
    const activeTrainIds = new Set(trains.map((t) => t.trainId));
    for (const [trainId, marker] of trainMarkers.current) {
      if (!activeTrainIds.has(trainId)) {
        marker.remove();
        trainMarkers.current.delete(trainId);
      }
    }

    // 更新或新增列車標記
    for (const train of trains) {
      let marker = trainMarkers.current.get(train.trainId);

      if (!marker) {
        // 建立新的列車標記
        const el = document.createElement('div');
        el.className = 'train-marker';
        el.style.cssText = `
          width: 12px;
          height: 12px;
          background-color: ${TRACK_COLORS[train.trackId] || '#d90023'};
          border: 2px solid #ffffff;
          border-radius: 50%;
          box-shadow: 0 0 4px rgba(0,0,0,0.5);
        `;

        marker = new mapboxgl.Marker({ element: el })
          .setLngLat(train.position)
          .addTo(map.current!);

        trainMarkers.current.set(train.trainId, marker);
      } else {
        // 更新位置
        marker.setLngLat(train.position);
      }
    }
  }, [mapLoaded, trains]);

  return (
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
  );
}
