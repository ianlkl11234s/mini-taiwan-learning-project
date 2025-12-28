"""
TDX API 客戶端

提供 TDX (運輸資料流通服務) API 的通用請求功能。
專為 Mini-Taipei V3 專案設計。

使用方式:
    from src.tdx_auth import TDXAuth
    from src.tdx_client import TDXClient

    auth = TDXAuth()
    client = TDXClient(auth)

    # 取得歷史時刻表
    data = client.get_metro_station_timetable('TRTC', '2024-12-25')
"""

import time
from typing import Optional, Dict, Any

import requests

try:
    from .tdx_auth import TDXAuth
except ImportError:
    from tdx_auth import TDXAuth


class TDXClient:
    """TDX API 通用客戶端

    提供 TDX API 的通用請求方法。
    支援自動重試與速率限制處理。
    """

    BASE_URL = "https://tdx.transportdata.tw/api/basic"
    REQUEST_INTERVAL = 0.5  # 500ms 間隔，避免速率限制
    MAX_RETRIES = 5  # 最大重試次數
    RETRY_DELAY = 3  # 重試初始延遲 (秒)

    def __init__(self, auth: TDXAuth):
        """初始化 API 客戶端

        Args:
            auth: TDXAuth 認證物件
        """
        self.auth = auth
        self._last_request_time = 0

    def _rate_limit(self) -> None:
        """執行速率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_INTERVAL:
            time.sleep(self.REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        output_format: str = 'JSON'
    ) -> Any:
        """通用 GET 請求 (含自動重試)

        Args:
            endpoint: API 端點路徑（不含基礎 URL）
            params: 查詢參數
            output_format: 輸出格式，預設 'JSON'

        Returns:
            API 回應的 JSON 資料
        """
        url = f"{self.BASE_URL}{endpoint}"

        # 合併參數
        request_params = {'$format': output_format}
        if params:
            request_params.update(params)

        headers = self.auth.get_auth_header()

        for attempt in range(self.MAX_RETRIES):
            self._rate_limit()

            print(f"📡 請求: {url}" + (f" (重試 {attempt})" if attempt > 0 else ""))

            try:
                response = requests.get(url, headers=headers, params=request_params)

                # 處理 429 Rate Limit
                if response.status_code == 429:
                    retry_delay = self.RETRY_DELAY * (2 ** attempt)  # 指數退避
                    print(f"⏳ API 速率限制，等待 {retry_delay} 秒後重試...")
                    time.sleep(retry_delay)
                    continue

                response.raise_for_status()

                data = response.json()
                print(f"✅ 成功取得資料")

                return data

            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    continue  # 重試
                print(f"❌ HTTP 錯誤: {e}")
                print(f"   回應內容: {response.text[:500]}")
                raise

            except requests.exceptions.RequestException as e:
                print(f"❌ 請求失敗: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    retry_delay = self.RETRY_DELAY * (2 ** attempt)
                    print(f"⏳ 等待 {retry_delay} 秒後重試...")
                    time.sleep(retry_delay)
                else:
                    raise

        # 達到最大重試次數
        raise requests.exceptions.RequestException(f"達到最大重試次數 ({self.MAX_RETRIES})")

    # ========== 捷運歷史時刻表 API ==========

    def get_metro_station_timetable(self, operator: str = 'TRTC', date: str = None) -> Any:
        """取得捷運站別時刻表 (歷史資料)

        這個 API 提供每個車站的發車時刻，包含 DestinationStationID 欄位，
        可用於識別不同的營運模式（如：往淡水 vs 往北投）。

        Args:
            operator: 營運單位代碼 (TRTC=台北捷運)
            date: 查詢日期，格式為 'YYYY-MM-DD'，預設為今天

        Returns:
            站別時刻表資料列表
        """
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime('%Y-%m-%d')

        endpoint = f"/v2/Historical/Rail/Metro/StationTimeTable/Date/{date}/{operator}"
        print(f"🚇 取得 {operator} 站別時刻表 ({date})...")
        return self.get(endpoint)


if __name__ == '__main__':
    # 測試 API 客戶端
    auth = TDXAuth()
    client = TDXClient(auth)

    print("\n" + "=" * 60)
    print("測試：取得台北捷運歷史時刻表")
    print("=" * 60)

    try:
        data = client.get_metro_station_timetable('TRTC', '2024-12-25')
        print(f"\n回傳資料類型: {type(data)}")
        if isinstance(data, list):
            print(f"資料筆數: {len(data)}")
            if data:
                print(f"第一筆資料欄位: {list(data[0].keys())}")
    except Exception as e:
        print(f"測試失敗: {e}")
