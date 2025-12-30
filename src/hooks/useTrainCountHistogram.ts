import { useMemo } from 'react';
import type { TrackSchedule } from '../types/schedule';

export interface TrainCountData {
  intervals: number[];  // 各 15 分鐘區間的列車數
  maxCount: number;     // 最大值（用於正規化高度）
  intervalMinutes: number;  // 區間長度（分鐘）
  startHour: number;    // 開始時間（小時）
  endHour: number;      // 結束時間（小時，延長日制）
}

/**
 * 將 HH:MM:SS 格式轉換為當天秒數（支援延長日制）
 */
function parseTimeToSeconds(timeStr: string): number {
  const [h, m, s] = timeStr.split(':').map(Number);
  let seconds = h * 3600 + m * 60 + (s || 0);
  // 凌晨 00:00-05:59 視為 24:00-29:59
  if (h < 6) {
    seconds += 24 * 3600;
  }
  return seconds;
}

/**
 * 預計算各時段的列車數量
 * @param schedules - 所有軌道的時刻表
 * @returns 各 15 分鐘區間的列車數量統計
 */
export function useTrainCountHistogram(
  schedules: Map<string, TrackSchedule>
): TrainCountData {
  return useMemo(() => {
    const intervalMinutes = 15;
    const startHour = 6;    // 06:00
    const endHour = 25.5;   // 01:30 (延長日制 25:30)
    const totalMinutes = (endHour - startHour) * 60;  // 1170 分鐘
    const intervalCount = Math.ceil(totalMinutes / intervalMinutes);  // 78 個區間

    // 初始化區間計數
    const intervals: number[] = new Array(intervalCount).fill(0);

    // 遍歷所有時刻表
    for (const schedule of schedules.values()) {
      for (const departure of schedule.departures) {
        // 發車時間（秒）
        const depSeconds = parseTimeToSeconds(departure.departure_time);
        // 到達終點時間（秒）
        const arrSeconds = depSeconds + departure.total_travel_time;

        // 計算這班車在哪些區間運行中
        const startSeconds = startHour * 3600;  // 06:00 = 21600

        for (let i = 0; i < intervalCount; i++) {
          const intervalStart = startSeconds + i * intervalMinutes * 60;
          const intervalEnd = intervalStart + intervalMinutes * 60;

          // 如果列車在這個區間內運行中
          if (depSeconds < intervalEnd && arrSeconds > intervalStart) {
            intervals[i]++;
          }
        }
      }
    }

    const maxCount = Math.max(...intervals, 1);  // 至少為 1 避免除以 0

    return {
      intervals,
      maxCount,
      intervalMinutes,
      startHour,
      endHour,
    };
  }, [schedules]);
}
