#!/usr/bin/env python3
"""
建立台鐵軌道 GeoJSON - 使用 Douglas-Peucker 簡化算法

從 TDX Map/Rail/Network API 獲取原始軌道數據，
使用 Douglas-Peucker 演算法簡化為平滑的單軌。

流程：
1. 從 TDX 獲取原始軌道幾何數據
2. 解析 WKT 格式（LINESTRING / MULTILINESTRING）
3. 應用 Douglas-Peucker 簡化
4. 輸出 GeoJSON

Usage:
    python scripts/build_tra_tracks.py --line CZ  # 建立成追線
    python scripts/build_tra_tracks.py --line SH  # 建立沙崙線
    python scripts/build_tra_tracks.py --line WL  # 建立西部幹線
    python scripts/build_tra_tracks.py --all      # 建立所有路線
"""

import json
import re
import math
import argparse
from pathlib import Path
from typing import List, Tuple, Optional
import sys

# 添加 TDX API 模組路徑
TDX_PATH = Path(__file__).parent.parent.parent / "tdx_api_docs"
sys.path.insert(0, str(TDX_PATH))

from src.tdx_auth import TDXAuth
import requests

# ============================================================
# 路徑設定
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "public" / "data-tra"
TRACKS_DIR = DATA_DIR / "tracks"
RAW_DIR = PROJECT_ROOT / "data-tra" / "raw"

# ============================================================
# 台鐵路線配置
# ============================================================
# tolerance 設定說明：
#   0.00001 ≈ 1.1m  - 極細緻，保留幾乎所有曲線
#   0.00002 ≈ 2.2m  - 細緻，適合短線/支線
#   0.00003 ≈ 3.3m  - 適中，平衡細節與簡化
#   0.00005 ≈ 5.5m  - 標準，適合主線
#   0.0001  ≈ 11m   - 粗略，大幅簡化

TRA_LINES = {
    # 簡單路線（優先測試）
    'CZ': {
        'name': '成追線',
        'start': '成功',
        'end': '追分',
        'tolerance': 0.00002,  # 2.2m - 保留更多曲線
    },
    'SH': {
        'name': '沙崙線',
        'start': '中洲',
        'end': '沙崙',
        'tolerance': 0.00002,  # 2.2m - 保留更多曲線
    },
    'SU': {
        'name': '蘇澳線',
        'start': '蘇澳新站',
        'end': '蘇澳',
        'tolerance': 0.00002,
    },
    # 支線
    'PX': {
        'name': '平溪線',
        'start': '三貂嶺',
        'end': '菁桐',
        'tolerance': 0.00003,  # 3.3m
    },
    'JJ': {
        'name': '集集線',
        'start': '二水',
        'end': '車埕',
        'tolerance': 0.00003,
    },
    'LJ': {
        'name': '六家線',
        'start': '竹中',
        'end': '六家',
        'tolerance': 0.00002,
    },
    'NW': {
        'name': '內灣線',
        'start': '新竹',
        'end': '內灣',
        'tolerance': 0.00003,
    },
    # 主線
    'SL': {
        'name': '南迴線',
        'start': '枋寮',
        'end': '台東',
        'tolerance': 0.00005,  # 5.5m - 主線標準
    },
    'EL': {
        'name': '東部幹線',
        'start': '八堵',
        'end': '枋寮',
        'tolerance': 0.00005,
    },
    'WL-C': {
        'name': '西部幹線(海線)',
        'start': '竹南',
        'end': '彰化',
        'tolerance': 0.00005,
    },
    'WL': {
        'name': '西部幹線',
        'start': '基隆',
        'end': '屏東',
        'tolerance': 0.00005,  # 5.5m - 約 1,900 點
    },
}

# ============================================================
# 軌道清理工具
# ============================================================

def remove_reversals_monotonic(coords: List[Tuple[float, float]],
                               direction: str = 'south') -> List[Tuple[float, float]]:
    """
    使用緯度單調性移除軌道中的回折點

    TDX 的某些路線數據包含雙軌或來回折返的座標，
    這會導致軌道長度異常和鋸齒狀外觀。

    策略：只保留緯度單調變化的座標點
    - south: 只保留緯度遞減的點（北→南）
    - north: 只保留緯度遞增的點（南→北）

    Args:
        coords: 原始座標列表
        direction: 主方向 ('south' 或 'north')

    Returns:
        清理後的座標列表
    """
    if len(coords) < 2:
        return coords

    result = [coords[0]]

    for i in range(1, len(coords)):
        if direction == 'south':
            # 緯度必須遞減（允許微小誤差）
            if coords[i][1] <= result[-1][1] + 0.0001:
                result.append(coords[i])
        else:
            # 緯度必須遞增
            if coords[i][1] >= result[-1][1] - 0.0001:
                result.append(coords[i])

    return result


def clean_track_data(coords: List[Tuple[float, float]],
                     line_id: str) -> List[Tuple[float, float]]:
    """
    清理軌道數據（針對特定路線的處理）

    使用緯度單調性過濾來移除回折點，
    產生平滑的單向軌道。

    Args:
        coords: 原始座標列表
        line_id: 路線 ID

    Returns:
        清理後的座標列表
    """
    # 定義每條路線的主方向
    # south: 北→南（緯度遞減）
    # north: 南→北（緯度遞增）
    # None: 不需要清理
    LINE_DIRECTIONS = {
        'WL': 'south',      # 西部幹線：基隆→屏東
        'WL-C': 'south',    # 西部幹線海線：竹南→彰化
        'EL': 'south',      # 東部幹線：八堵→枋寮（大致南下）
        'SL': 'south',      # 南迴線：枋寮→台東（大致南下）
    }

    direction = LINE_DIRECTIONS.get(line_id)

    if direction:
        cleaned = remove_reversals_monotonic(coords, direction=direction)
        return cleaned

    return coords


# ============================================================
# Douglas-Peucker 簡化演算法
# ============================================================

def distance_point_to_line(point: Tuple[float, float],
                           line_start: Tuple[float, float],
                           line_end: Tuple[float, float]) -> float:
    """計算點到線段的垂直距離"""
    x, y = point
    x1, y1 = line_start
    x2, y2 = line_end

    line_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2

    if line_len_sq == 0:
        return math.sqrt((x - x1) ** 2 + (y - y1) ** 2)

    t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / line_len_sq))
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)

    return math.sqrt((x - proj_x) ** 2 + (y - proj_y) ** 2)


def douglas_peucker(coords: List[Tuple[float, float]],
                    tolerance: float) -> List[Tuple[float, float]]:
    """
    Douglas-Peucker 線段簡化演算法

    保留曲線特徵，移除不必要的中間點，
    產生平滑的軌道線條。

    Args:
        coords: 座標列表 [(lng, lat), ...]
        tolerance: 簡化容許值（經緯度單位，0.0001 ≈ 11米）

    Returns:
        簡化後的座標列表
    """
    if len(coords) <= 2:
        return coords

    # 找到距離首尾連線最遠的點
    max_dist = 0
    max_idx = 0

    for i in range(1, len(coords) - 1):
        dist = distance_point_to_line(coords[i], coords[0], coords[-1])
        if dist > max_dist:
            max_dist = dist
            max_idx = i

    # 如果最大距離大於容許值，遞迴處理
    if max_dist > tolerance:
        left = douglas_peucker(coords[:max_idx + 1], tolerance)
        right = douglas_peucker(coords[max_idx:], tolerance)
        return left[:-1] + right
    else:
        return [coords[0], coords[-1]]


# ============================================================
# WKT 解析器
# ============================================================

def parse_wkt_linestring(geometry_str: str) -> List[Tuple[float, float]]:
    """
    解析 WKT LINESTRING 格式

    輸入: "LINESTRING(121.62089 25.05456, 121.62083 25.05455, ...)"
    輸出: [(121.62089, 25.05456), (121.62083, 25.05455), ...]
    """
    coords_str = re.sub(r'^LINESTRING\s*\(', '', geometry_str, flags=re.IGNORECASE)
    coords_str = re.sub(r'\)\s*$', '', coords_str)

    coords = []
    for pair in coords_str.split(','):
        parts = pair.strip().split()
        if len(parts) >= 2:
            lng = float(parts[0])
            lat = float(parts[1])
            coords.append((lng, lat))

    return coords


def parse_wkt_multilinestring(geometry_str: str) -> List[Tuple[float, float]]:
    """
    解析 WKT MULTILINESTRING 格式並合併為單一線段

    輸入: "MULTILINESTRING((x y, x y), (x y, x y))"
    輸出: 合併後的座標列表
    """
    # 提取所有座標對
    raw_coords = re.findall(r'([\d.]+)\s+([\d.]+)', geometry_str)
    coords = [(float(lng), float(lat)) for lng, lat in raw_coords]

    return coords


def parse_wkt_geometry(geometry_str: str) -> List[Tuple[float, float]]:
    """解析 WKT 幾何格式（自動識別類型）"""
    if geometry_str.upper().startswith('MULTILINESTRING'):
        return parse_wkt_multilinestring(geometry_str)
    elif geometry_str.upper().startswith('LINESTRING'):
        return parse_wkt_linestring(geometry_str)
    else:
        raise ValueError(f"Unknown geometry type: {geometry_str[:50]}...")


# ============================================================
# TDX API 存取
# ============================================================

def fetch_tra_track_geometry(line_id: str) -> Optional[str]:
    """
    從 TDX API 獲取台鐵軌道幾何數據

    Args:
        line_id: 路線 ID (例如 'CZ', 'SH', 'WL')

    Returns:
        WKT 格式的幾何字串
    """
    auth = TDXAuth()
    headers = auth.get_auth_header()

    url = "https://tdx.transportdata.tw/api/basic/V3/Map/Rail/Network/Line/OperatorCode/TRA"
    params = {
        "$filter": f"LineID eq '{line_id}'",
        "$format": "JSON"
    }

    print(f"📡 正在從 TDX 獲取 {line_id} 軌道數據...")

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()

        if data and isinstance(data, list) and len(data) > 0:
            item = data[0]
            if isinstance(item, dict):
                geometry = item.get('Geometry', '')
                if geometry:
                    print(f"✅ 成功獲取軌道數據")
                    return geometry

        print(f"⚠️ 未找到 {line_id} 的軌道數據")
        return None

    except Exception as e:
        print(f"❌ 獲取軌道數據失敗: {e}")
        return None


# ============================================================
# 軌道分析工具
# ============================================================

def analyze_track_smoothness(coords: List[Tuple[float, float]]) -> dict:
    """
    分析軌道平滑度

    Returns:
        包含分析結果的字典
    """
    if len(coords) < 3:
        return {'angle_changes': [], 'avg_angle': 0, 'max_angle': 0}

    angle_changes = []

    for i in range(1, len(coords) - 1):
        # 計算兩個相鄰向量
        v1 = (coords[i][0] - coords[i-1][0], coords[i][1] - coords[i-1][1])
        v2 = (coords[i+1][0] - coords[i][0], coords[i+1][1] - coords[i][1])

        len1 = math.sqrt(v1[0]**2 + v1[1]**2)
        len2 = math.sqrt(v2[0]**2 + v2[1]**2)

        if len1 > 0 and len2 > 0:
            dot = v1[0]*v2[0] + v1[1]*v2[1]
            cos_angle = max(-1, min(1, dot / (len1 * len2)))
            angle = math.degrees(math.acos(cos_angle))
            angle_changes.append(angle)

    return {
        'angle_changes': angle_changes,
        'avg_angle': sum(angle_changes) / len(angle_changes) if angle_changes else 0,
        'max_angle': max(angle_changes) if angle_changes else 0,
        'sharp_turns': sum(1 for a in angle_changes if a > 30),  # 大於30度的轉彎
    }


def calculate_track_length(coords: List[Tuple[float, float]]) -> float:
    """計算軌道總長度（公里）"""
    total = 0
    for i in range(len(coords) - 1):
        # 使用簡化的距離計算（適用於台灣地區）
        dlng = (coords[i+1][0] - coords[i][0]) * 111 * math.cos(math.radians(coords[i][1]))
        dlat = (coords[i+1][1] - coords[i][1]) * 111
        total += math.sqrt(dlng**2 + dlat**2)
    return total


# ============================================================
# GeoJSON 輸出
# ============================================================

def build_track_geojson(line_id: str,
                        coords: List[Tuple[float, float]],
                        direction: int,
                        line_config: dict) -> dict:
    """
    建立軌道 GeoJSON

    Args:
        line_id: 路線 ID
        coords: 座標列表
        direction: 方向 (0=去程, 1=返程)
        line_config: 路線配置

    Returns:
        GeoJSON FeatureCollection
    """
    track_id = f"{line_id}-{direction}"

    if direction == 0:
        name = f"{line_config['name']} ({line_config['start']}→{line_config['end']})"
        origin = line_config['start']
        destination = line_config['end']
        track_coords = coords
    else:
        name = f"{line_config['name']} ({line_config['end']}→{line_config['start']})"
        origin = line_config['end']
        destination = line_config['start']
        track_coords = list(reversed(coords))

    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "line_id": line_id,
                "direction": direction,
                "name": name,
                "origin": origin,
                "destination": destination,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[c[0], c[1]] for c in track_coords]
            }
        }]
    }


# ============================================================
# 主要處理流程
# ============================================================

def build_tra_track(line_id: str, save_raw: bool = True) -> bool:
    """
    建立單一台鐵路線的軌道

    Args:
        line_id: 路線 ID
        save_raw: 是否保存原始數據

    Returns:
        成功與否
    """
    if line_id not in TRA_LINES:
        print(f"❌ 未知的路線 ID: {line_id}")
        print(f"   可用路線: {', '.join(TRA_LINES.keys())}")
        return False

    config = TRA_LINES[line_id]
    print(f"\n{'='*60}")
    print(f"🚂 建立 {config['name']} ({line_id}) 軌道")
    print(f"{'='*60}")

    # 確保輸出目錄存在
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)
    if save_raw:
        RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 獲取 TDX 數據
    geometry = fetch_tra_track_geometry(line_id)
    if not geometry:
        return False

    # 保存原始數據
    if save_raw:
        raw_file = RAW_DIR / f"{line_id}_raw.wkt"
        with open(raw_file, 'w', encoding='utf-8') as f:
            f.write(geometry)
        print(f"💾 原始數據已保存: {raw_file}")

    # 2. 解析 WKT
    print(f"\n[1/5] 解析 WKT 幾何數據...")
    coords = parse_wkt_geometry(geometry)
    original_count = len(coords)
    print(f"      原始座標點數: {original_count}")

    # 3. 清理軌道數據（移除回折）
    print(f"\n[2/5] 清理軌道數據...")
    cleaned = clean_track_data(coords, line_id)
    cleaned_count = len(cleaned)
    if cleaned_count != original_count:
        print(f"      清理後座標點數: {cleaned_count} (移除 {original_count - cleaned_count} 點)")
    else:
        print(f"      無需清理")

    # 4. 分析清理後數據
    print(f"\n[3/5] 分析數據品質...")
    original_analysis = analyze_track_smoothness(cleaned)
    print(f"      平均轉角: {original_analysis['avg_angle']:.2f}°")
    print(f"      最大轉角: {original_analysis['max_angle']:.2f}°")
    print(f"      銳角轉彎 (>30°): {original_analysis['sharp_turns']} 次")

    # 5. Douglas-Peucker 簡化
    print(f"\n[4/5] 簡化座標 (tolerance={config['tolerance']})...")
    simplified = douglas_peucker(cleaned, config['tolerance'])
    simplified_count = len(simplified)
    reduction = (1 - simplified_count / cleaned_count) * 100
    print(f"      簡化後座標點數: {simplified_count} (減少 {reduction:.1f}%)")

    # 分析簡化後的品質
    simplified_analysis = analyze_track_smoothness(simplified)
    print(f"      平均轉角: {simplified_analysis['avg_angle']:.2f}°")
    print(f"      最大轉角: {simplified_analysis['max_angle']:.2f}°")
    print(f"      銳角轉彎 (>30°): {simplified_analysis['sharp_turns']} 次")

    # 計算軌道長度
    track_length = calculate_track_length(simplified)
    print(f"      軌道長度: {track_length:.2f} km")

    # 6. 輸出 GeoJSON
    print(f"\n[5/5] 輸出 GeoJSON...")

    # 去程 (direction=0)
    geojson_0 = build_track_geojson(line_id, simplified, 0, config)
    output_0 = TRACKS_DIR / f"{line_id}-0.geojson"
    with open(output_0, 'w', encoding='utf-8') as f:
        json.dump(geojson_0, f, ensure_ascii=False, indent=2)
    print(f"      ✅ {output_0}")

    # 返程 (direction=1)
    geojson_1 = build_track_geojson(line_id, simplified, 1, config)
    output_1 = TRACKS_DIR / f"{line_id}-1.geojson"
    with open(output_1, 'w', encoding='utf-8') as f:
        json.dump(geojson_1, f, ensure_ascii=False, indent=2)
    print(f"      ✅ {output_1}")

    print(f"\n{'='*60}")
    print(f"✅ {config['name']} 軌道建立完成！")
    if cleaned_count != original_count:
        print(f"   清理: {original_count} → {cleaned_count} (移除 {original_count - cleaned_count} 回折點)")
    print(f"   簡化: {cleaned_count} → {simplified_count} (減少 {reduction:.1f}%)")
    print(f"   長度: {track_length:.2f} km")
    print(f"{'='*60}")

    return True


def build_all_tra_tracks():
    """建立所有台鐵路線軌道"""
    print("\n" + "="*60)
    print("🚂 建立所有台鐵軌道")
    print("="*60)

    success = []
    failed = []

    for line_id in TRA_LINES:
        try:
            if build_tra_track(line_id):
                success.append(line_id)
            else:
                failed.append(line_id)
        except Exception as e:
            print(f"❌ {line_id} 處理失敗: {e}")
            failed.append(line_id)

    print("\n" + "="*60)
    print("📊 建立結果")
    print("="*60)
    print(f"成功: {len(success)} 條 - {', '.join(success)}")
    if failed:
        print(f"失敗: {len(failed)} 條 - {', '.join(failed)}")


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='建立台鐵軌道 GeoJSON（使用 Douglas-Peucker 簡化）'
    )
    parser.add_argument(
        '--line', '-l',
        type=str,
        help=f"路線 ID，可選: {', '.join(TRA_LINES.keys())}"
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='建立所有路線'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='列出所有可用路線'
    )

    args = parser.parse_args()

    if args.list:
        print("\n📋 可用的台鐵路線:")
        print("-" * 40)
        for line_id, config in TRA_LINES.items():
            print(f"  {line_id:6} - {config['name']}")
        return

    if args.all:
        build_all_tra_tracks()
    elif args.line:
        build_tra_track(args.line.upper())
    else:
        # 預設建立測試路線（成追線）
        print("💡 未指定路線，預設建立成追線 (CZ) 作為測試")
        build_tra_track('CZ')


if __name__ == '__main__':
    main()
