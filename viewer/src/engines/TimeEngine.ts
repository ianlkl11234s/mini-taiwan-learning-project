/**
 * TimeEngine - 時間引擎
 *
 * 管理模擬時間，支援：
 * - 播放/暫停
 * - 時間跳轉
 * - 播放速度調整 (1x, 2x, 5x, 10x, 60x)
 */

export type TimeEngineCallback = (currentTime: Date) => void;

export interface TimeEngineOptions {
  initialTime?: Date;
  speed?: number;
  onTick?: TimeEngineCallback;
}

export class TimeEngine {
  private currentTime: Date;
  private speed: number;
  private isPlaying: boolean = false;
  private animationFrameId: number | null = null;
  private lastRealTime: number = 0;
  private callbacks: Set<TimeEngineCallback> = new Set();

  // 預設速度選項
  static readonly SPEED_OPTIONS = [1, 2, 5, 10, 30, 60];

  constructor(options: TimeEngineOptions = {}) {
    // 預設為今天早上 6:00
    const defaultTime = new Date();
    defaultTime.setHours(6, 0, 0, 0);

    this.currentTime = options.initialTime || defaultTime;
    this.speed = options.speed || 1;

    if (options.onTick) {
      this.callbacks.add(options.onTick);
    }
  }

  /**
   * 取得當前模擬時間
   */
  getTime(): Date {
    return new Date(this.currentTime);
  }

  /**
   * 取得當天的秒數 (0-86399)
   */
  getTimeOfDaySeconds(): number {
    return (
      this.currentTime.getHours() * 3600 +
      this.currentTime.getMinutes() * 60 +
      this.currentTime.getSeconds()
    );
  }

  /**
   * 取得格式化的時間字串 (HH:MM:SS)
   */
  getFormattedTime(): string {
    const hours = this.currentTime.getHours().toString().padStart(2, '0');
    const minutes = this.currentTime.getMinutes().toString().padStart(2, '0');
    const seconds = this.currentTime.getSeconds().toString().padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
  }

  /**
   * 設定模擬時間
   */
  setTime(time: Date): void {
    this.currentTime = new Date(time);
    this.notifyCallbacks();
  }

  /**
   * 設定當天的時間 (使用秒數)
   */
  setTimeOfDay(seconds: number): void {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    this.currentTime.setHours(hours, minutes, secs, 0);
    this.notifyCallbacks();
  }

  /**
   * 取得播放速度
   */
  getSpeed(): number {
    return this.speed;
  }

  /**
   * 設定播放速度
   */
  setSpeed(speed: number): void {
    this.speed = Math.max(0.1, Math.min(100, speed));
  }

  /**
   * 是否正在播放
   */
  isRunning(): boolean {
    return this.isPlaying;
  }

  /**
   * 開始播放
   */
  play(): void {
    if (this.isPlaying) return;

    this.isPlaying = true;
    this.lastRealTime = performance.now();
    this.tick();
  }

  /**
   * 暫停播放
   */
  pause(): void {
    this.isPlaying = false;
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  /**
   * 切換播放/暫停
   */
  toggle(): void {
    if (this.isPlaying) {
      this.pause();
    } else {
      this.play();
    }
  }

  /**
   * 跳到指定時間 (格式: "HH:MM:SS" 或 "HH:MM")
   */
  jumpTo(timeString: string): void {
    const parts = timeString.split(':').map(Number);
    const hours = parts[0] || 0;
    const minutes = parts[1] || 0;
    const seconds = parts[2] || 0;

    this.currentTime.setHours(hours, minutes, seconds, 0);
    this.notifyCallbacks();
  }

  /**
   * 新增時間更新回調
   */
  onTick(callback: TimeEngineCallback): () => void {
    this.callbacks.add(callback);
    return () => this.callbacks.delete(callback);
  }

  /**
   * 銷毀引擎
   */
  destroy(): void {
    this.pause();
    this.callbacks.clear();
  }

  /**
   * 動畫循環
   */
  private tick = (): void => {
    if (!this.isPlaying) return;

    const now = performance.now();
    const realDelta = now - this.lastRealTime;
    this.lastRealTime = now;

    // 根據播放速度計算模擬時間增量
    const simulatedDelta = realDelta * this.speed;
    this.currentTime = new Date(this.currentTime.getTime() + simulatedDelta);

    // 通知所有回調
    this.notifyCallbacks();

    // 繼續動畫循環
    this.animationFrameId = requestAnimationFrame(this.tick);
  };

  /**
   * 通知所有回調
   */
  private notifyCallbacks(): void {
    const time = this.getTime();
    this.callbacks.forEach((callback) => callback(time));
  }
}
