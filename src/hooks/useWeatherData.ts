import { useState, useEffect, useCallback, useRef } from 'react';
import type { WeatherConfig, WeatherType } from '../layers/Weather3DLayer';
import { CLEAR_WEATHER } from '../layers/Weather3DLayer';

// ============================================================
// OpenWeatherMap → WeatherConfig 映射
// ============================================================

function mapOpenWeatherToConfig(data: {
  weather?: { id: number; main: string }[];
  rain?: { '1h'?: number; '3h'?: number };
  snow?: { '1h'?: number; '3h'?: number };
  wind?: { speed?: number; deg?: number };
}): WeatherConfig {
  const weatherId = data.weather?.[0]?.id ?? 800;
  const mainWeather = data.weather?.[0]?.main ?? 'Clear';
  const rainRate = data.rain?.['1h'] ?? data.rain?.['3h'] ?? 0;
  const snowRate = data.snow?.['1h'] ?? data.snow?.['3h'] ?? 0;
  const windSpeed = data.wind?.speed ?? 0;
  const windDeg = data.wind?.deg ?? 0;

  let type: WeatherType = 'clear';
  let intensity = 0;
  let precipitationRate = rainRate;

  if (mainWeather === 'Snow' || snowRate > 0) {
    type = 'snow';
    intensity = Math.min(snowRate / 5, 1);
    precipitationRate = snowRate;
  } else if (weatherId >= 200 && weatherId < 300) {
    // Thunderstorm
    type = 'thunderstorm';
    intensity = Math.min(0.7 + rainRate / 30, 1);
    precipitationRate = rainRate || 10;
  } else if (mainWeather === 'Drizzle' || (rainRate > 0 && rainRate < 2.5)) {
    type = 'drizzle';
    intensity = Math.min(rainRate / 2.5, 1) || 0.5;
    precipitationRate = rainRate || 1;
  } else if (rainRate >= 7.5) {
    type = 'heavy-rain';
    intensity = Math.min(rainRate / 20, 1);
  } else if (rainRate >= 2.5) {
    type = 'rain';
    intensity = (rainRate - 2.5) / 5;
  } else if (mainWeather === 'Rain') {
    type = 'rain';
    intensity = 0.5;
    precipitationRate = 3;
  }

  return {
    type,
    intensity: Math.max(0, Math.min(1, intensity)),
    precipitationRate,
    windSpeed,
    windDirection: windDeg,
  };
}

// ============================================================
// 天氣預設（手動模式用）
// ============================================================

function getPresetConfig(type: WeatherType): WeatherConfig {
  switch (type) {
    case 'clear':
      return { ...CLEAR_WEATHER };
    case 'drizzle':
      return { type: 'drizzle', intensity: 0.5, precipitationRate: 1.5, windSpeed: 2, windDirection: 30 };
    case 'rain':
      return { type: 'rain', intensity: 0.6, precipitationRate: 5, windSpeed: 3, windDirection: 45 };
    case 'heavy-rain':
      return { type: 'heavy-rain', intensity: 0.85, precipitationRate: 15, windSpeed: 6, windDirection: 60 };
    case 'thunderstorm':
      return { type: 'thunderstorm', intensity: 1.0, precipitationRate: 25, windSpeed: 10, windDirection: 90 };
    case 'snow':
      return { type: 'snow', intensity: 0.7, precipitationRate: 3, windSpeed: 2, windDirection: 0 };
  }
}

// ============================================================
// Hook
// ============================================================

const POLL_INTERVAL_MS = 10 * 60 * 1000; // 每 10 分鐘更新一次

export interface UseWeatherDataReturn {
  weather: WeatherConfig;
  weatherSource: 'api' | 'manual';
  loading: boolean;
  error: string | null;
  /** 手動設定天氣（設為 null 切回 API 模式） */
  setManualWeather: (type: WeatherType | null) => void;
  /** 目前手動選擇的天氣類型 */
  manualType: WeatherType | null;
  /** 是否有設定 API key */
  hasApiKey: boolean;
}

export function useWeatherData(
  mapCenter: { lng: number; lat: number } | null,
): UseWeatherDataReturn {
  const [weather, setWeather] = useState<WeatherConfig>({ ...CLEAR_WEATHER });
  const [manualType, setManualType] = useState<WeatherType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const apiKey = import.meta.env.VITE_OPENWEATHER_API_KEY as string | undefined;
  const hasApiKey = Boolean(apiKey);

  // 從 API 取得天氣
  const fetchWeather = useCallback(async () => {
    if (!apiKey || !mapCenter) return;

    setLoading(true);
    setError(null);

    try {
      const url = `https://api.openweathermap.org/data/2.5/weather?lat=${mapCenter.lat}&lon=${mapCenter.lng}&appid=${apiKey}&units=metric`;
      const resp = await fetch(url);

      if (!resp.ok) {
        throw new Error(`OpenWeatherMap API error: ${resp.status}`);
      }

      const data = await resp.json();
      const config = mapOpenWeatherToConfig(data);
      setWeather(config);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
      console.warn('[useWeatherData] Fetch failed:', msg);
    } finally {
      setLoading(false);
    }
  }, [apiKey, mapCenter?.lat, mapCenter?.lng]);

  // API 模式：定期更新
  useEffect(() => {
    if (manualType !== null) return; // 手動模式不 fetch
    if (!apiKey) return;

    fetchWeather();
    intervalRef.current = setInterval(fetchWeather, POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [fetchWeather, manualType, apiKey]);

  // 手動模式
  const setManualWeather = useCallback((type: WeatherType | null) => {
    setManualType(type);
    if (type !== null) {
      setWeather(getPresetConfig(type));
      setError(null);
    }
    // type === null 時，下次 useEffect 會自動 fetch
  }, []);

  // 沒有 API key 時，預設使用手動模式的 clear
  useEffect(() => {
    if (!apiKey && manualType === null) {
      setWeather({ ...CLEAR_WEATHER });
    }
  }, [apiKey, manualType]);

  return {
    weather,
    weatherSource: manualType !== null ? 'manual' : 'api',
    loading,
    error,
    setManualWeather,
    manualType,
    hasApiKey,
  };
}
