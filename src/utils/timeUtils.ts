/**
 * 時間工具函數
 *
 * 延長日制 (Extended Day):
 * - 運營日從 05:50 開始（高鐵首班車），凌晨 00:00-05:49 視為前一天的延續
 * - 標準秒數: 0-86399 (00:00:00 - 23:59:59)
 * - 延長日秒數: 21000-107400 (05:50:00 - 29:49:59)
 *
 * 這解決了午夜時列車消失的問題：
 * - 23:45 發車的列車在 00:15 時應該還在運行
 * - 標準秒數: currentTime=900, departure=85500 → elapsed=-84600 (錯誤)
 * - 延長日秒數: currentTime=87300, departure=85500 → elapsed=1800 (正確)
 */

// 運營日起始時間：05:50 (21000秒)
const DAY_START_SECONDS = 5 * 3600 + 50 * 60; // 05:50

/**
 * 將標準時間秒數 (0-86399) 轉換為延長日秒數
 * @param standardSeconds 標準時間秒數 (0-86399)
 * @returns 延長日秒數 (21000-107400)
 */
export function toExtendedSeconds(standardSeconds: number): number {
  // 凌晨 00:00-05:49 (0-20999) → 視為 24:00-29:49 (86400-107400)
  if (standardSeconds < DAY_START_SECONDS) {
    return standardSeconds + 24 * 3600;
  }
  return standardSeconds;
}

/**
 * 將延長日秒數轉換為標準時間秒數 (0-86399)
 * @param extendedSeconds 延長日秒數
 * @returns 標準時間秒數 (0-86399)
 */
export function toStandardSeconds(extendedSeconds: number): number {
  // 24:00+ (86400+) → 轉回 00:00+ (0+)
  if (extendedSeconds >= 24 * 3600) {
    return extendedSeconds - 24 * 3600;
  }
  return extendedSeconds;
}

/**
 * 將時間字串轉換為延長日秒數
 * @param timeStr 時間字串，格式為 "HH:MM" 或 "HH:MM:SS"
 * @returns 延長日秒數
 */
export function timeToSeconds(timeStr: string): number {
  const parts = timeStr.split(':').map(Number);
  const standardSeconds = parts[0] * 3600 + parts[1] * 60 + (parts[2] || 0);
  return toExtendedSeconds(standardSeconds);
}

/**
 * 將秒數轉換為 "HH:MM" 格式字串
 * @param seconds 秒數（可以是延長日秒數）
 * @returns 格式化的時間字串 "HH:MM"
 */
export function secondsToTimeStr(seconds: number): string {
  // 處理延長日秒數（超過 24 小時的部分）
  let normalizedSeconds = seconds;
  if (normalizedSeconds >= 24 * 3600) {
    normalizedSeconds -= 24 * 3600;
  }
  const hours = Math.floor(normalizedSeconds / 3600);
  const minutes = Math.floor((normalizedSeconds % 3600) / 60);
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
}
