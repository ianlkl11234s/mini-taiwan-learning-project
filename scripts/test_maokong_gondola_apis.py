#!/usr/bin/env python3
"""
TDX 貓空纜車 API 測試腳本

測試 TRTCMG (Taipei Rapid Transit Corporation Maokong Gondola) 資料可用性

使用方式:
    cd /Users/migu/Desktop/資料庫/gen_ai_try/ichef_工作用/GIS/taipei-gis-analytics
    python ../mini-taipei-v3/scripts/test_maokong_gondola_apis.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# 加入 taipei-gis-analytics 專案路徑
gis_analytics_path = Path(__file__).parent.parent.parent / "taipei-gis-analytics"
sys.path.insert(0, str(gis_analytics_path))

from src.tdx_auth import TDXAuth
from src.tdx_client import TDXClient

# 輸出目錄
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "tdx_maokong"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RAIL_SYSTEM = "TRTCMG"  # 貓空纜車


class TDXMaokongClient(TDXClient):
    """擴展 TDXClient 以支援貓空纜車 API"""

    def get_metro_shape(self, rail_system: str = RAIL_SYSTEM) -> Any:
        """取得軌道圖資"""
        endpoint = f"/v2/Rail/Metro/Shape/{rail_system}"
        print(f"🚡 取得 {rail_system} 軌道圖資...")
        return self.get(endpoint)

    def get_metro_station(self, rail_system: str = RAIL_SYSTEM) -> Any:
        """取得車站資料"""
        endpoint = f"/v2/Rail/Metro/Station/{rail_system}"
        print(f"🏔️  取得 {rail_system} 車站資料...")
        return self.get(endpoint)

    def get_metro_line(self, rail_system: str = RAIL_SYSTEM) -> Any:
        """取得路線資料"""
        endpoint = f"/v2/Rail/Metro/Line/{rail_system}"
        print(f"🛤️  取得 {rail_system} 路線資料...")
        return self.get(endpoint)

    def get_metro_first_last_timetable(self, rail_system: str = RAIL_SYSTEM) -> Any:
        """取得首末班車時刻表"""
        endpoint = f"/v2/Rail/Metro/FirstLastTimetable/{rail_system}"
        print(f"🕐 取得 {rail_system} 首末班車時刻表...")
        return self.get(endpoint)

    def get_metro_frequency(self, rail_system: str = RAIL_SYSTEM) -> Any:
        """取得班距頻率"""
        endpoint = f"/v2/Rail/Metro/Frequency/{rail_system}"
        print(f"⏱️  取得 {rail_system} 班距頻率...")
        return self.get(endpoint)

    def get_metro_s2s_travel_time(self, rail_system: str = RAIL_SYSTEM) -> Any:
        """取得站間行駛時間"""
        endpoint = f"/v2/Rail/Metro/S2STravelTime/{rail_system}"
        print(f"🚀 取得 {rail_system} 站間行駛時間...")
        return self.get(endpoint)

    def get_metro_route(self, rail_system: str = RAIL_SYSTEM) -> Any:
        """取得營運路線資料"""
        endpoint = f"/v2/Rail/Metro/Route/{rail_system}"
        print(f"🗺️  取得 {rail_system} 營運路線...")
        return self.get(endpoint)


def save_result(data: Any, filename: str) -> Path:
    """儲存 API 回應結果"""
    output_path = OUTPUT_DIR / filename
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 已儲存: {output_path}")
    return output_path


def analyze_data(data: Any, api_name: str) -> Dict[str, Any]:
    """分析 API 回應資料"""
    analysis = {
        'api_name': api_name,
        'data_type': type(data).__name__,
        'status': 'success'
    }

    if isinstance(data, list):
        analysis['record_count'] = len(data)
        if data:
            analysis['sample_fields'] = list(data[0].keys()) if isinstance(data[0], dict) else None
            # 顯示第一筆資料
            print(f"\n   📄 第一筆資料範例:")
            print(f"   {json.dumps(data[0], ensure_ascii=False, indent=6)[:500]}...")
    elif isinstance(data, dict):
        analysis['top_level_keys'] = list(data.keys())

    return analysis


def main():
    """主程式"""
    print("=" * 70)
    print("TDX 貓空纜車 (TRTCMG) API 測試")
    print("=" * 70)
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"輸出目錄: {OUTPUT_DIR}")
    print()

    # 初始化認證與客戶端
    print("📋 初始化 TDX 認證...")
    try:
        auth = TDXAuth()
        client = TDXMaokongClient(auth)
    except Exception as e:
        print(f"❌ 認證失敗: {e}")
        print("請確認 .env 檔案中已設定 TDX_APP_ID 和 TDX_APP_KEY")
        return

    # 測試結果收集
    results = []

    # 測試的 API 清單
    apis_to_test = [
        ('station', 'Station (車站資料)', client.get_metro_station),
        ('shape', 'Shape (軌道圖資)', client.get_metro_shape),
        ('line', 'Line (路線資料)', client.get_metro_line),
        ('route', 'Route (營運路線)', client.get_metro_route),
        ('first_last', 'FirstLastTimetable (首末班車)', client.get_metro_first_last_timetable),
        ('frequency', 'Frequency (班距頻率)', client.get_metro_frequency),
        ('s2s_travel_time', 'S2STravelTime (站間行駛時間)', client.get_metro_s2s_travel_time),
    ]

    for api_key, api_name, api_func in apis_to_test:
        print(f"\n{'─' * 60}")
        print(f"測試: {api_name}")
        print(f"{'─' * 60}")

        result = {
            'api_key': api_key,
            'api_name': api_name,
            'status': 'pending'
        }

        try:
            data = api_func()
            analysis = analyze_data(data, api_name)
            result.update(analysis)

            # 儲存資料
            filename = f"{api_key}.json"
            save_result(data, filename)

            result['status'] = 'success'

        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            print(f"❌ 失敗: {e}")

        results.append(result)

    # ========== 結果摘要 ==========

    print("\n" + "=" * 70)
    print("測試結果摘要")
    print("=" * 70)

    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"\n✅ 成功: {success_count}/{len(results)} 個 API")

    print("\n📋 各 API 狀態:")
    for r in results:
        status_icon = "✅" if r['status'] == 'success' else "❌"
        print(f"   {status_icon} {r['api_name']}")
        if r['status'] == 'success':
            if 'record_count' in r:
                print(f"      資料筆數: {r['record_count']}")
        else:
            print(f"      錯誤: {r.get('error', 'Unknown')}")

    # ========== 貓空纜車實作可行性評估 ==========

    print("\n" + "=" * 70)
    print("貓空纜車實作可行性評估")
    print("=" * 70)

    station_ok = any(r['api_key'] == 'station' and r['status'] == 'success' for r in results)
    shape_ok = any(r['api_key'] == 'shape' and r['status'] == 'success' for r in results)
    frequency_ok = any(r['api_key'] == 'frequency' and r['status'] == 'success' for r in results)
    s2s_ok = any(r['api_key'] == 's2s_travel_time' and r['status'] == 'success' for r in results)
    first_last_ok = any(r['api_key'] == 'first_last' and r['status'] == 'success' for r in results)

    print(f"\n📊 資料可用性:")
    print(f"   車站資料 (Station): {'✅ 可用' if station_ok else '❌ 不可用'}")
    print(f"   軌道圖資 (Shape): {'✅ 可用' if shape_ok else '❌ 不可用'}")
    print(f"   班距頻率 (Frequency): {'✅ 可用' if frequency_ok else '❌ 不可用'}")
    print(f"   站間行駛時間 (S2STravelTime): {'✅ 可用' if s2s_ok else '❌ 不可用'}")
    print(f"   首末班車 (FirstLastTimetable): {'✅ 可用' if first_last_ok else '❌ 不可用'}")

    print(f"\n🎯 建議實作方案:")
    if station_ok and shape_ok:
        print("   ✅ 基礎資料充足，可以建立路線和車站")
        if frequency_ok and s2s_ok:
            print("   ✅ 可使用 TDX 資料生成時刻表")
        else:
            print("   ⚠️  班距/行駛時間資料不完整")
            print("   💡 建議方案：使用固定間距模擬")
            print("      - 尖峰：每 12-15 秒發車")
            print("      - 離峰：每 20-30 秒發車")
            print("      - 速度：約 6 m/s (21.6 km/h)")
            print("      - 總行程：約 17-25 分鐘")
    else:
        print("   ❌ 基礎資料不足，需手動建立")

    # 儲存測試報告
    report = {
        'test_time': datetime.now().isoformat(),
        'rail_system': RAIL_SYSTEM,
        'results': results
    }
    report_path = OUTPUT_DIR / "api_test_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 測試報告: {report_path}")

    print("\n" + "=" * 70)
    print("測試完成！")
    print("=" * 70)


if __name__ == '__main__':
    main()
