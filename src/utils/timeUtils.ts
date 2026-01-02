/**
 * 時間工具函數
 *
 * 延長日制 (Extended Day):
 * - 運營日從 06:00 開始，凌晨 00:00-05:59 視為前一天的延續
 * - 標準秒數: 0-86399 (00:00:00 - 23:59:59)
 * - 延長日秒數: 21600-108000 (06:00:00 - 29:59:59)
 *
 * 這解決了午夜時列車消失的問題：
 * - 23:45 發車的列車在 00:15 時應該還在運行
 * - 標準秒數: currentTime=900, departure=85500 → elapsed=-84600 (錯誤)
 * - 延長日秒數: currentTime=87300, departure=85500 → elapsed=1800 (正確)
 */

/**
 * 將標準時間秒數 (0-86399) 轉換為延長日秒數
 * @param standardSeconds 標準時間秒數 (0-86399)
 * @returns 延長日秒數 (21600-108000)
 */
export function toExtendedSeconds(standardSeconds: number): number {
  // 凌晨 00:00-05:59 (0-21599) → 視為 24:00-29:59 (86400-108000)
  if (standardSeconds < 6 * 3600) {
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
