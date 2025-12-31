#!/usr/bin/env python3
"""
TDX 捷運 API 測試腳本

測試以下 API 端點，評估是否可用於建立文湖線時刻表：
1. /v2/Rail/Metro/Shape/TRTC - 軌道圖資
2. /v2/Rail/Metro/Frequency/TRTC - 班距頻率
3. /v2/Rail/Metro/S2STravelTime/TRTC - 站間行駛時間
4. /v2/Rail/Metro/FirstLastTimetable/TRTC - 首末班車
5. /V3/Map/Rail/Network/Station/OperatorCode/TRTC - 車站圖資
6. /V3/Map/Rail/Network/Line/OperatorCode/TRTC - 路線圖資

使用方式:
    cd /Users/migu/Desktop/資料庫/gen_ai_try/ichef_工作用/GIS/taipei-gis-analytics
    python ../mini-taipei-v3/scripts/test_tdx_metro_apis.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# 加入 taipei-gis-analytics 專案路徑
gis_analytics_path = Path(__file__).parent.parent.parent / "taipei-gis-analytics"
sys.path.insert(0, str(gis_analytics_path))

from src.tdx_auth import TDXAuth
from src.tdx_client import TDXClient

# 輸出目錄
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "tdx_metro_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class TDXMetroClient(TDXClient):
    """擴展 TDXClient 以支援捷運 API"""

    def get_metro_shape(self, rail_system: str = "TRTC") -> Dict[str, Any]:
        """取得捷運軌道圖資

        Args:
            rail_system: 捷運系統代碼 (TRTC=台北捷運)
        """
        endpoint = f"/v2/Rail/Metro/Shape/{rail_system}"
        print(f"🚇 取得 {rail_system} 軌道圖資...")
        return self.get(endpoint)

    def get_metro_frequency(self, rail_system: str = "TRTC") -> Dict[str, Any]:
        """取得捷運班距頻率

        Args:
            rail_system: 捷運系統代碼
        """
        endpoint = f"/v2/Rail/Metro/Frequency/{rail_system}"
        print(f"🕐 取得 {rail_system} 班距頻率...")
        return self.get(endpoint)

    def get_metro_s2s_travel_time(self, rail_system: str = "TRTC") -> Dict[str, Any]:
        """取得捷運站間行駛時間

        Args:
            rail_system: 捷運系統代碼
        """
        endpoint = f"/v2/Rail/Metro/S2STravelTime/{rail_system}"
        print(f"⏱️  取得 {rail_system} 站間行駛時間...")
        return self.get(endpoint)

    def get_metro_first_last_timetable(self, rail_system: str = "TRTC") -> Dict[str, Any]:
        """取得捷運首末班車時刻表

        Args:
            rail_system: 捷運系統代碼
        """
        endpoint = f"/v2/Rail/Metro/FirstLastTimetable/{rail_system}"
        print(f"🚉 取得 {rail_system} 首末班車時刻表...")
        return self.get(endpoint)

    def get_metro_station(self, rail_system: str = "TRTC") -> Dict[str, Any]:
        """取得捷運車站資料

        Args:
            rail_system: 捷運系統代碼
        """
        endpoint = f"/v2/Rail/Metro/Station/{rail_system}"
        print(f"🏢 取得 {rail_system} 車站資料...")
        return self.get(endpoint)

    def get_metro_line(self, rail_system: str = "TRTC") -> Dict[str, Any]:
        """取得捷運路線資料

        Args:
            rail_system: 捷運系統代碼
        """
        endpoint = f"/v2/Rail/Metro/Line/{rail_system}"
        print(f"🛤️  取得 {rail_system} 路線資料...")
        return self.get(endpoint)

    def get_v3_rail_station(self, operator_code: str = "TRTC") -> Dict[str, Any]:
        """取得 V3 軌道車站圖資

        Args:
            operator_code: 營運商代碼
        """
        original_version = self.version
        self.version = "basic"
        try:
            endpoint = f"/V3/Map/Rail/Network/Station/OperatorCode/{operator_code}"
            print(f"📍 取得 V3 {operator_code} 車站圖資...")
            return self.get(endpoint)
        finally:
            self.version = original_version

    def get_v3_rail_line(self, operator_code: str = "TRTC") -> Dict[str, Any]:
        """取得 V3 軌道路線圖資

        Args:
            operator_code: 營運商代碼
        """
        original_version = self.version
        self.version = "basic"
        try:
            endpoint = f"/V3/Map/Rail/Network/Line/OperatorCode/{operator_code}"
            print(f"🗺️  取得 V3 {operator_code} 路線圖資...")
            return self.get(endpoint)
        finally:
            self.version = original_version


def save_result(data: Any, filename: str, summary: Dict[str, Any]) -> Path:
    """儲存 API 回應結果"""
    output_path = OUTPUT_DIR / filename
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    summary['output_file'] = str(output_path)
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
            # 檢查是否包含文湖線資料
            br_records = [r for r in data if isinstance(r, dict) and
                         (r.get('LineID') == 'BR' or
                          r.get('LineNo') == 'BR' or
                          'BR' in str(r.get('StationID', '')) or
                          '文湖' in str(r.get('LineName', {})))]
            analysis['brown_line_records'] = len(br_records)
    elif isinstance(data, dict):
        analysis['top_level_keys'] = list(data.keys())
        # 檢查是否有嵌套的資料列表
        for key in ['Shapes', 'Frequencies', 'S2STravelTimes', 'FirstLastTimetables',
                    'Stations', 'Lines', 'Data', 'features']:
            if key in data:
                analysis[f'{key}_count'] = len(data[key]) if isinstance(data[key], list) else 1

    return analysis


def filter_brown_line(data: List[Dict], field: str = 'LineID') -> List[Dict]:
    """過濾出文湖線資料"""
    return [r for r in data if r.get(field) == 'BR' or
            'BR' in str(r.get('StationID', '')) or
            '文湖' in str(r.get('LineName', {}))]


def main():
    """主程式"""
    print("=" * 70)
    print("TDX 捷運 API 測試 - 文湖線資料可用性評估")
    print("=" * 70)
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"輸出目錄: {OUTPUT_DIR}")
    print()

    # 初始化認證與客戶端
    print("📋 初始化 TDX 認證...")
    try:
        auth = TDXAuth()
        client = TDXMetroClient(auth)
    except Exception as e:
        print(f"❌ 認證失敗: {e}")
        print("請確認 .env 檔案中已設定 TDX_APP_ID 和 TDX_APP_KEY")
        return

    # 測試結果收集
    results = []

    # ========== 測試各 API ==========

    apis_to_test = [
        ('metro_shape', 'Shape (軌道圖資)', client.get_metro_shape),
        ('metro_frequency', 'Frequency (班距頻率)', client.get_metro_frequency),
        ('metro_s2s_travel_time', 'S2STravelTime (站間行駛時間)', client.get_metro_s2s_travel_time),
        ('metro_first_last', 'FirstLastTimetable (首末班車)', client.get_metro_first_last_timetable),
        ('metro_station', 'Station (車站資料)', client.get_metro_station),
        ('metro_line', 'Line (路線資料)', client.get_metro_line),
        ('v3_rail_station', 'V3 Rail Station (車站圖資)', client.get_v3_rail_station),
        ('v3_rail_line', 'V3 Rail Line (路線圖資)', client.get_v3_rail_line),
    ]

    for api_key, api_name, api_func in apis_to_test:
        print(f"\n{'─' * 50}")
        print(f"測試: {api_name}")
        print(f"{'─' * 50}")

        result = {
            'api_key': api_key,
            'api_name': api_name,
            'status': 'pending'
        }

        try:
            data = api_func()
            analysis = analyze_data(data, api_name)
            result.update(analysis)

            # 儲存完整資料
            filename = f"{api_key}_TRTC_{datetime.now().strftime('%Y%m%d')}.json"
            save_result(data, filename, result)

            # 如果有文湖線資料，另存一份
            if isinstance(data, list) and result.get('brown_line_records', 0) > 0:
                br_data = filter_brown_line(data)
                br_filename = f"{api_key}_BR_{datetime.now().strftime('%Y%m%d')}.json"
                save_result(br_data, br_filename, {})
                result['brown_line_file'] = str(OUTPUT_DIR / br_filename)

            # 顯示分析結果
            print(f"\n📊 分析結果:")
            for key, value in analysis.items():
                if key not in ['api_name', 'status']:
                    print(f"   {key}: {value}")

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
            if 'brown_line_records' in r:
                print(f"      文湖線筆數: {r['brown_line_records']}")
        else:
            print(f"      錯誤: {r.get('error', 'Unknown')}")

    # 儲存測試報告
    report = {
        'test_time': datetime.now().isoformat(),
        'rail_system': 'TRTC',
        'target_line': 'BR (文湖線)',
        'summary': {
            'total_apis': len(results),
            'successful': success_count,
            'failed': len(results) - success_count
        },
        'results': results
    }

    report_path = OUTPUT_DIR / f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 測試報告已儲存: {report_path}")

    # ========== 文湖線資料可用性評估 ==========

    print("\n" + "=" * 70)
    print("文湖線資料可用性評估")
    print("=" * 70)

    # 檢查各資料來源
    shape_available = any(r['api_key'] == 'metro_shape' and r.get('brown_line_records', 0) > 0 for r in results)
    frequency_available = any(r['api_key'] == 'metro_frequency' and r.get('brown_line_records', 0) > 0 for r in results)
    s2s_available = any(r['api_key'] == 'metro_s2s_travel_time' and r.get('brown_line_records', 0) > 0 for r in results)
    first_last_available = any(r['api_key'] == 'metro_first_last' and r.get('brown_line_records', 0) > 0 for r in results)
    station_available = any(r['api_key'] == 'metro_station' and r.get('brown_line_records', 0) > 0 for r in results)

    print(f"\n📊 資料可用性:")
    print(f"   軌道圖資 (Shape): {'✅ 可用' if shape_available else '❌ 不可用'}")
    print(f"   班距頻率 (Frequency): {'✅ 可用' if frequency_available else '❌ 不可用'}")
    print(f"   站間行駛時間 (S2STravelTime): {'✅ 可用' if s2s_available else '❌ 不可用'}")
    print(f"   首末班車 (FirstLastTimetable): {'✅ 可用' if first_last_available else '❌ 不可用'}")
    print(f"   車站資料 (Station): {'✅ 可用' if station_available else '❌ 不可用'}")

    # 時刻表生成可行性
    can_generate_timetable = s2s_available and (frequency_available or first_last_available) and station_available

    print(f"\n🎯 時刻表生成可行性:")
    if can_generate_timetable:
        print("   ✅ 可以生成模擬時刻表")
        print("   建議方案:")
        if frequency_available:
            print("   - 使用 Frequency API 取得班距，動態生成發車時間")
        if first_last_available:
            print("   - 使用 FirstLastTimetable 確定首末班車時間範圍")
        if s2s_available:
            print("   - 使用 S2STravelTime 計算站間行駛時間")
    else:
        print("   ⚠️  資料不完整，需要補充:")
        if not s2s_available:
            print("   - 缺少站間行駛時間資料")
        if not frequency_available and not first_last_available:
            print("   - 缺少班距或首末班車資料")
        if not station_available:
            print("   - 缺少車站資料")

    print("\n" + "=" * 70)
    print("測試完成！")
    print("=" * 70)

    return results


if __name__ == '__main__':
    main()
