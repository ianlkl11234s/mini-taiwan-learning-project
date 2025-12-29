"""
TDX API 認證模組

提供 TDX (運輸資料流通服務) API 的 OAuth 2.0 認證功能。
支援 Token 快取與自動更新機制。

使用方式:
    from src.tdx_auth import TDXAuth

    auth = TDXAuth()  # 從 .env 讀取金鑰
    header = auth.get_auth_header()
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, Dict

import requests
from dotenv import load_dotenv


class TDXAuth:
    """TDX API 認證管理器

    提供 OAuth 2.0 Client Credentials 認證流程，
    包含 Token 快取與自動更新功能。
    """

    AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    TOKEN_CACHE_FILE = "cache/tdx_token_cache.json"
    TOKEN_REFRESH_BUFFER = 3600  # 提前 1 小時更新 Token

    def __init__(self, app_id: Optional[str] = None, app_key: Optional[str] = None):
        """初始化認證管理器

        Args:
            app_id: TDX API Client ID，若未提供則從環境變數讀取
            app_key: TDX API Client Secret，若未提供則從環境變數讀取
        """
        # data_collector 目錄
        data_collector_root = Path(__file__).parent.parent
        # 專案根目錄 (mini-taipei-v3)
        project_root = data_collector_root.parent

        # 載入環境變數 (從專案根目錄)
        load_dotenv(project_root / '.env')

        self.app_id = app_id or os.getenv('TDX_APP_ID')
        self.app_key = app_key or os.getenv('TDX_APP_KEY')

        if not self.app_id or not self.app_key:
            raise ValueError(
                "TDX API 金鑰未設定。請在 .env 檔案中設定 TDX_APP_ID 和 TDX_APP_KEY，"
                "或在初始化時直接提供 app_id 和 app_key 參數。"
            )

        self._access_token: Optional[str] = None
        self._token_expiry: Optional[float] = None

        # 確保快取目錄存在 (在 data_collector 內)
        self._cache_path = data_collector_root / self.TOKEN_CACHE_FILE
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)

        # 嘗試載入快取的 Token
        self._load_cached_token()

    def _load_cached_token(self) -> None:
        """從快取檔案載入 Token"""
        if self._cache_path.exists():
            try:
                with open(self._cache_path, 'r') as f:
                    cache_data = json.load(f)

                # 檢查快取是否有效
                if cache_data.get('expiry', 0) > time.time() + self.TOKEN_REFRESH_BUFFER:
                    self._access_token = cache_data.get('access_token')
                    self._token_expiry = cache_data.get('expiry')
                    print("✅ 已從快取載入有效的 Access Token")
            except (json.JSONDecodeError, KeyError):
                pass  # 快取無效，稍後重新取得

    def _save_token_cache(self) -> None:
        """將 Token 儲存至快取檔案"""
        cache_data = {
            'access_token': self._access_token,
            'expiry': self._token_expiry
        }
        with open(self._cache_path, 'w') as f:
            json.dump(cache_data, f)

    def is_token_valid(self) -> bool:
        """檢查目前 Token 是否有效"""
        if not self._access_token or not self._token_expiry:
            return False
        return time.time() < self._token_expiry - self.TOKEN_REFRESH_BUFFER

    def get_access_token(self) -> str:
        """取得 Access Token

        若 Token 已快取且有效，直接回傳；否則重新取得。
        """
        if self.is_token_valid():
            return self._access_token

        # 準備認證請求
        headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }

        data = {
            'grant_type': 'client_credentials',
            'client_id': self.app_id,
            'client_secret': self.app_key
        }

        print("📡 正在取得 TDX Access Token...")

        try:
            response = requests.post(self.AUTH_URL, headers=headers, data=data)
            response.raise_for_status()

            auth_data = response.json()
            self._access_token = auth_data.get('access_token')
            expires_in = auth_data.get('expires_in', 86400)  # 預設 24 小時
            self._token_expiry = time.time() + expires_in

            # 儲存至快取
            self._save_token_cache()

            print(f"✅ 成功取得 Access Token")
            print(f"   有效期限: {expires_in} 秒 ({expires_in / 3600:.1f} 小時)")

            return self._access_token

        except requests.exceptions.RequestException as e:
            print(f"❌ 認證失敗: {e}")
            raise

    def get_auth_header(self) -> Dict[str, str]:
        """取得包含認證資訊的 HTTP Header"""
        token = self.get_access_token()
        return {
            'authorization': f'Bearer {token}',
            'Accept-Encoding': 'gzip'
        }


if __name__ == '__main__':
    # 測試認證功能
    auth = TDXAuth()
    token = auth.get_access_token()
    print(f"\nToken 前 50 字元: {token[:50]}...")
