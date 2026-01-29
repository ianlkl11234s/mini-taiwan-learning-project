/**
 * 軌道預處理工具
 * 效能優化：預計算軌道距離資料，避免每幀重複計算
 */

import type { Track, TrackDistanceCache } from '../types/track';

/**
 * 計算兩點間的歐幾里得距離
 */
function euclideanDistance(p1: [number, number], p2: [number, number]): number {
  const dx = p2[0] - p1[0];
  const dy = p2[1] - p1[1];
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * 為單一軌道計算距離快取
 */
export function calculateDistanceCache(coords: [number, number][]): TrackDistanceCache {
  if (coords.length === 0) {
    return { totalLength: 0, cumulativeDistances: [] };
  }

  if (coords.length === 1) {
    return { totalLength: 0, cumulativeDistances: [0] };
  }

  const cumulativeDistances: number[] = [0];

  for (let i = 1; i < coords.length; i++) {
    const segmentLength = euclideanDistance(coords[i - 1], coords[i]);
    cumulativeDistances.push(cumulativeDistances[i - 1] + segmentLength);
  }

  return {
    totalLength: cumulativeDistances[cumulativeDistances.length - 1],
    cumulativeDistances,
  };
}

/**
 * 預處理單一軌道，加入距離快取
 */
export function preprocessTrack(track: Track): Track {
  if (track.geometry.type !== 'LineString') {
    // MultiLineString 暫不處理，維持原樣
    return track;
  }

  const coords = track.geometry.coordinates as [number, number][];
  const distanceCache = calculateDistanceCache(coords);

  return {
    ...track,
    distanceCache,
  };
}

/**
 * 批次預處理軌道 Map
 */
export function preprocessTracks(tracks: Map<string, Track>): Map<string, Track> {
  const result = new Map<string, Track>();

  for (const [trackId, track] of tracks) {
    result.set(trackId, preprocessTrack(track));
  }

  return result;
}

/**
 * 使用預計算的快取進行二分搜尋，找到 progress 對應的線段索引
 * 回傳值：線段起點的索引 (0 到 coords.length - 2)
 */
export function findSegmentByProgress(
  cache: TrackDistanceCache,
  progress: number
): number {
  if (cache.cumulativeDistances.length <= 1) {
    return 0;
  }

  const targetDistance = cache.totalLength * Math.max(0, Math.min(1, progress));
  const distances = cache.cumulativeDistances;

  // 二分搜尋找到第一個 >= targetDistance 的位置
  let left = 0;
  let right = distances.length - 1;

  while (left < right) {
    const mid = Math.floor((left + right) / 2);
    if (distances[mid] < targetDistance) {
      left = mid + 1;
    } else {
      right = mid;
    }
  }

  // 回傳線段起點索引（確保不超出範圍）
  return Math.max(0, Math.min(left - 1, distances.length - 2));
}

/**
 * 使用快取進行高效內插
 * 回傳：[經度, 緯度] 座標
 */
export function interpolateWithCache(
  coords: [number, number][],
  cache: TrackDistanceCache,
  progress: number
): [number, number] {
  if (coords.length === 0) return [0, 0];
  if (coords.length === 1) return coords[0];
  if (progress <= 0) return coords[0];
  if (progress >= 1) return coords[coords.length - 1];

  const targetDistance = cache.totalLength * progress;
  const segmentIndex = findSegmentByProgress(cache, progress);

  const startDist = cache.cumulativeDistances[segmentIndex];
  const endDist = cache.cumulativeDistances[segmentIndex + 1];
  const segmentLength = endDist - startDist;

  if (segmentLength < 0.0000001) {
    return coords[segmentIndex];
  }

  const segmentProgress = (targetDistance - startDist) / segmentLength;
  const p1 = coords[segmentIndex];
  const p2 = coords[segmentIndex + 1];

  return [
    p1[0] + (p2[0] - p1[0]) * segmentProgress,
    p1[1] + (p2[1] - p1[1]) * segmentProgress,
  ];
}
