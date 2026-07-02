#!/usr/bin/env python3
"""
三鶯線 (Sanying Line, 新北捷運 LB) 建置腳本

TDX 尚未收錄本線（2026-06-30 通車第 1 天），改用 OSM Overpass 為暫時 SSOT。
待 TDX 於 /v2/Rail/Metro/{Station|Shape}/NTMC 加入 LineID=LB 後，
可以另寫 TDX 版覆蓋此腳本（比照 build_ankeng_lrt.py）。

OSM: relation 5341250 (name=捷運三鶯線, ref=LB, network=新北捷運, colour=#6DB7D0)
     14 條 way member + 12 個 role=stop node (LB01~LB12)

輸出：
- public/data/sanying_line_stations.geojson   (12 站 FeatureCollection)
- public/data/tracks/LB-1-0.geojson           (單條 MultiLineString)
- public/data/sanying_line_progress.json      ({"LB-1-0": {"LB01": 0.0, ...}})
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
from typing import List, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 前端 useData.ts 從 /data/trtc/ 底下抓（mini-taipei-v3 viewer 慣例）
STATION_FILE = os.path.join(PROJECT_ROOT, "public/data/trtc/sanying_stations.geojson")
TRACK_DIR = os.path.join(PROJECT_ROOT, "public/data/trtc/tracks")
SCHEDULE_DIR = os.path.join(PROJECT_ROOT, "public/data/trtc/schedules")
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "public/data/trtc/station_progress.json")

LINE_ID = "LB"
LINE_COLOR = "#6DB7D0"
TRACK_IDS = ("LB-1-0", "LB-1-1")  # 0 往鶯桃福德，1 往頂埔
OSM_RELATION_ID = 5341250
DWELL_SEC = 25
# 官方段行駛時間（分）— 頂埔→鶯桃福德，共 34 分
# LB01→LB02→LB03→...→LB12
SEG_TIME_MIN = [2, 3, 2, 3, 3, 3, 5, 3, 3, 4, 3]
SEG_TIME_SEC = [m * 60 for m in SEG_TIME_MIN]
TRAVEL_TIME_SEC = sum(SEG_TIME_SEC) + DWELL_SEC * 10  # 34*60 + 250 = 2290 s

# main mirror 較不穩，kumi 目前較穩
OVERPASS_MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]


def overpass_query(query: str) -> dict:
    """打 Overpass API，多 mirror + backoff retry。"""
    last_err = None
    for mirror in OVERPASS_MIRRORS:
        for attempt in range(3):
            try:
                data = urllib.parse.urlencode({"data": query}).encode()
                req = urllib.request.Request(
                    mirror,
                    data=data,
                    headers={"User-Agent": "mini-taipei-v3/build_sanying_line"},
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    return json.loads(resp.read())
            except Exception as e:
                last_err = e
                print(f"  overpass {mirror} attempt {attempt+1} 失敗: {e}", file=sys.stderr)
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Overpass 全 mirror 失敗，最後錯誤: {last_err}")


def fetch_relation_geom() -> Tuple[List[dict], List[dict]]:
    """回傳 (way geometries list, stop node member list)。已 hardcode 排除機廠側線。"""
    q = f"[out:json][timeout:180];rel({OSM_RELATION_ID});out geom;"
    d = overpass_query(q)
    rel = d["elements"][0]
    ways = [m for m in rel["members"] if m["type"] == "way"]
    stops = [m for m in rel["members"] if m["type"] == "node" and m.get("role") == "stop"]

    # 已知純機廠側線 way id（無 name/ref，只有 service=yard）— 手動確認 2026-07-02
    EXCLUDE_WAY_IDS = {1320105946}
    before = len(ways)
    main_ways = [w for w in ways if w["ref"] not in EXCLUDE_WAY_IDS]
    dropped = before - len(main_ways)
    if dropped > 0:
        print(f"      過濾掉 {dropped} 條側線 way (id: {EXCLUDE_WAY_IDS})", file=sys.stderr)
    return main_ways, stops


def fetch_station_tags(node_ids: List[int]) -> List[dict]:
    """對站點 node 拿 tags（name/name:en/ref）。"""
    id_list = ",".join(str(i) for i in node_ids)
    q = f"[out:json][timeout:60];node(id:{id_list});out;"
    d = overpass_query(q)
    return d["elements"]


def haversine_m(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    import math
    lon1, lat1 = p1
    lon2, lat2 = p2
    R = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _euclid(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    # 歐幾里得距離（lng/lat 平面）— 與前端 TrainEngine 一致，用於 station progress。
    import math
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def build_multilinestring(ways: List[dict]) -> List[List[List[float]]]:
    """把 14 條 way 的 geometry ([{lat,lon},...]) 轉成 MultiLineString 座標 [[lon,lat],...]。"""
    segments = []
    for w in ways:
        geom = w.get("geometry") or []
        if len(geom) < 2:
            continue
        segments.append([[g["lon"], g["lat"]] for g in geom])
    return segments


def chain_segments(
    segments: List[List[List[float]]],
    start_hint: Tuple[float, float],
) -> List[List[float]]:
    """
    OSM relation members 通常已按路線順序，只需判斷每段正/反向使頭尾相接。
    第一段：選其兩端點中離 start_hint 較近的一端當開頭。
    後續段：選其頭或尾與前段尾端點相同的方向。
    """
    if not segments:
        return []

    first = list(segments[0])
    if len(segments) > 1:
        next_head = (segments[1][0][0], segments[1][0][1])
        next_tail = (segments[1][-1][0], segments[1][-1][1])
        # 讓 first 的尾端點接近 segments[1] 任一端點
        d_tail_to_next = min(
            haversine_m((first[-1][0], first[-1][1]), next_head),
            haversine_m((first[-1][0], first[-1][1]), next_tail),
        )
        d_head_to_next = min(
            haversine_m((first[0][0], first[0][1]), next_head),
            haversine_m((first[0][0], first[0][1]), next_tail),
        )
        if d_head_to_next < d_tail_to_next:
            first = list(reversed(first))
    else:
        # 只有一段時用 start_hint 決定方向
        if haversine_m((first[-1][0], first[-1][1]), start_hint) < haversine_m((first[0][0], first[0][1]), start_hint):
            first = list(reversed(first))
    chain = first[:]

    for seg in segments[1:]:
        seg_list = list(seg)
        tail = (chain[-1][0], chain[-1][1])
        d_head = haversine_m((seg_list[0][0], seg_list[0][1]), tail)
        d_tail = haversine_m((seg_list[-1][0], seg_list[-1][1]), tail)
        if d_tail < d_head:
            seg_list = list(reversed(seg_list))
        # 去重相接點
        if chain and seg_list and chain[-1] == seg_list[0]:
            chain.extend(seg_list[1:])
        else:
            chain.extend(seg_list)
    return chain


def _project_point_to_chain(
    point: Tuple[float, float],
    chain: List[Tuple[float, float]],
    cum: List[float],
) -> Tuple[float, Tuple[float, float], int]:
    """
    對 chain 每個 segment 找 point 的 perpendicular foot（用 lon/lat 近似平面）。
    回傳 (arc_position_m, foot_lonlat, best_segment_idx)。
    """
    best = (float("inf"), 0.0, point, 0)  # (dist_m, arc, foot, seg_idx)
    for i in range(len(chain) - 1):
        a = chain[i]
        b = chain[i + 1]
        # 近似：小範圍以度為單位當歐氏
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        seg_len_deg2 = dx * dx + dy * dy
        if seg_len_deg2 == 0:
            t = 0.0
        else:
            t = ((point[0] - ax) * dx + (point[1] - ay) * dy) / seg_len_deg2
            t = max(0.0, min(1.0, t))
        foot = (ax + t * dx, ay + t * dy)
        d = haversine_m(point, foot)
        if d < best[0]:
            seg_len_m = haversine_m(a, b)
            arc = cum[i] + t * seg_len_m
            best = (d, arc, foot, i)
    return best[1], best[2], best[3]


def project_station_progress(
    stations: List[dict],  # {"station_id", "coord"}，已按 station_id 排序 (LB01..LB12)
    segments: List[List[List[float]]],
) -> Tuple[dict, List[List[float]]]:
    """
    回傳 (progress dict, 拓撲排好且截到主線的 chain — 供 track geometry 用)。

    - chain：從 LB01 座標起點貪婪串接所有 segment，然後截到 [LB01 nearest vertex .. LB12 nearest vertex]，
      避免 depot / 側線把 track 拉出主軸。
    - progress：station 序 index 為主（LB01=0.0, LB12=1.0），因無 realtime 無需真距離，
      只要單調遞增即可讓 loader / postProcess 不出錯。
    """
    stations_by_id = {s["station_id"]: s for s in stations}
    start_hint = tuple(stations_by_id["LB01"]["coord"])
    end_hint = tuple(stations_by_id["LB12"]["coord"])

    chain = chain_segments(segments, start_hint)
    flat: List[Tuple[float, float]] = []
    for pt in chain:
        p = (pt[0], pt[1])
        if not flat or flat[-1] != p:
            flat.append(p)

    # 用 perpendicular projection 找 LB01 / LB12 在 chain 上的 arc 位置 → 精確切斷（不只 nearest vertex）
    cum_full = [0.0]
    for i in range(1, len(flat)):
        cum_full.append(cum_full[-1] + haversine_m(flat[i - 1], flat[i]))

    arc_start, foot_start, _ = _project_point_to_chain(start_hint, flat, cum_full)
    arc_end, foot_end, _ = _project_point_to_chain(end_hint, flat, cum_full)
    reverse = arc_end < arc_start
    lo_arc, hi_arc = (arc_end, arc_start) if reverse else (arc_start, arc_end)

    # 取 chain 中 arc 落在 [lo_arc, hi_arc] 的 vertex，兩端接上精確 foot 座標
    trimmed: List[Tuple[float, float]] = [foot_start if not reverse else foot_end]
    for i, v in enumerate(flat):
        if lo_arc <= cum_full[i] <= hi_arc:
            trimmed.append(v)
    trimmed.append(foot_end if not reverse else foot_start)
    # dedupe 相鄰重複
    dedup: List[Tuple[float, float]] = []
    for p in trimmed:
        if not dedup or dedup[-1] != p:
            dedup.append(p)
    trimmed = dedup
    if reverse:
        trimmed.reverse()

    # station coord：snap 到 trimmed 最近 vertex，讓圓圈落在畫出的軌道上
    snapped_coords: dict = {}
    for s in stations:
        raw = tuple(s["coord"])
        bi, bd = 0, float("inf")
        for i, v in enumerate(trimmed):
            d = haversine_m((v[0], v[1]), raw)
            if d < bd:
                bd, bi = d, i
        snapped_coords[s["station_id"]] = [trimmed[bi][0], trimmed[bi][1]]

    # progress：站點投影到 trimmed chain 的 arc-length 比例（歐幾里得），
    # 讓 TrainEngine 停站時 interpolateOnLineString(progress) 精準落在站圓圈上。
    # 站點已 snap 到 chain vertex，投影零誤差且單調遞增。
    seglens = [_euclid(trimmed[i], trimmed[i + 1]) for i in range(len(trimmed) - 1)]
    total = sum(seglens) or 1.0
    progress = {}
    for s in stations:
        pt = snapped_coords[s["station_id"]]
        best_along, best_d, acc = 0.0, float("inf"), 0.0
        for i in range(len(trimmed) - 1):
            a, b = trimmed[i], trimmed[i + 1]
            dx, dy = b[0] - a[0], b[1] - a[1]
            l2 = dx * dx + dy * dy
            t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dy) / l2))
            proj = (a[0] + t * dx, a[1] + t * dy)
            d = _euclid(pt, proj)
            if d < best_d:
                best_d, best_along = d, acc + t * seglens[i]
            acc += seglens[i]
        progress[s["station_id"]] = round(best_along / total, 6)

    return progress, [list(p) for p in trimmed], snapped_coords


def main():
    print(f"[1/4] Overpass 抓 relation {OSM_RELATION_ID} geometry...")
    ways, stops = fetch_relation_geom()
    print(f"      ways={len(ways)} stops={len(stops)}")

    stop_ids = [s["ref"] for s in stops]
    print(f"[2/4] Overpass 抓 {len(stop_ids)} 個站點 tags...")
    time.sleep(1)
    try:
        nodes = fetch_station_tags(stop_ids)
        print(f"      got {len(nodes)} node tags")
    except Exception as e:
        print(f"      ⚠ 抓 tags 失敗（{e}），用 relation 附帶座標 + auto ref", file=sys.stderr)
        nodes = []
    node_by_id = {n["id"]: n for n in nodes}

    # relation stops 按官方 route 順序（頂埔 → 鶯桃福德）
    stations = []
    for idx, stop in enumerate(stops):
        nid = stop["ref"]
        n = node_by_id.get(nid)
        tags = (n or {}).get("tags", {})
        sid = tags.get("ref") or f"LB{idx+1:02d}"
        # 座標優先用 tags query 拿的 lon/lat，缺就 fallback 到 relation out geom 的 lat/lon
        if n and "lon" in n and "lat" in n:
            coord = [n["lon"], n["lat"]]
        else:
            coord = [stop["lon"], stop["lat"]]
        stations.append({
            "station_id": sid,
            "name": tags.get("name", ""),
            "name_en": tags.get("name:en", ""),
            "coord": coord,
        })
    print(f"      站點: {[s['station_id'] for s in stations]}")
    assert len(stations) == 12, f"預期 12 站，實得 {len(stations)}"

    print("[3/4] 合成 MultiLineString + 計算 station progress...")
    segments = build_multilinestring(ways)
    seg_pts = sum(len(s) for s in segments)
    print(f"      segments={len(segments)}, total points={seg_pts}")
    progress, chain, snapped = project_station_progress(stations, segments)
    # 用投影後座標覆蓋 raw OSM 座標
    for s in stations:
        s["coord"] = snapped[s["station_id"]]

    # sanity：全 12 站 progress 應單調遞增（LB01→LB12）
    print(f"      chain points={len(chain)}")
    for sid in sorted(progress.keys()):
        print(f"      {sid} = {progress[sid]:.4f}")

    print("[4/4] 寫檔...")
    os.makedirs(TRACK_DIR, exist_ok=True)
    os.makedirs(SCHEDULE_DIR, exist_ok=True)
    write_tracks(stations, chain)
    write_progress(stations, progress)
    # 段時間直接用官方公告（頂埔→鶯桃福德每段行駛分鐘）
    write_schedules(stations, SEG_TIME_SEC, is_weekday=True)
    write_schedules(stations, SEG_TIME_SEC, is_weekday=False)
    write_stations_geojson(stations)
    print("✅ 完成")


# ── 輸出 helpers ──

def _track_feature(track_id: str, direction: int, stations: List[dict], coords: List[List[float]]) -> dict:
    origin, dest = (stations[0], stations[-1]) if direction == 0 else (stations[-1], stations[0])
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "track_id": track_id,
                "color": LINE_COLOR,
                "route_id": f"{LINE_ID}-1",
                "direction": direction,
                "name": f"{origin['name']}站 → {dest['name']}站",
                "start_station": origin["station_id"],
                "end_station": dest["station_id"],
                "line_id": LINE_ID,
                "system_id": "trtc",
                "source": "osm:relation/5341250",
            },
            "geometry": {"type": "LineString", "coordinates": coords},
        }],
    }


def write_tracks(stations: List[dict], chain: List[List[float]]) -> None:
    # LB-1-0 頂埔→鶯桃福德，LB-1-1 反向
    fwd = chain
    rev = list(reversed(chain))
    with open(os.path.join(TRACK_DIR, "LB-1-0.geojson"), "w", encoding="utf-8") as f:
        json.dump(_track_feature("LB-1-0", 0, stations, fwd), f, ensure_ascii=False)
    with open(os.path.join(TRACK_DIR, "LB-1-1.geojson"), "w", encoding="utf-8") as f:
        json.dump(_track_feature("LB-1-1", 1, stations, rev), f, ensure_ascii=False)


def write_progress(stations: List[dict], progress: dict) -> None:
    existing = {}
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception as e:
            print(f"      ⚠ 讀既有 progress 失敗，覆寫: {e}", file=sys.stderr)
    existing["LB-1-0"] = progress
    # 反向：LB12=0.0, ..., LB01=1.0
    rev_progress = {sid: 1.0 - p for sid, p in progress.items()}
    existing["LB-1-1"] = rev_progress
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def _seconds_since_10(hh: int, mm: int) -> int:
    return (hh - 10) * 3600 + mm * 60


def _generate_departures_10_20(is_weekday: bool) -> List[Tuple[int, int]]:
    """
    產生 [(hh, mm), ...] 出發時刻列表。
    平日：10:00~17:30 每 8 分、17:30~19:30 每 6 分、19:30~20:00 每 8 分。
    假日：10:00~20:00 每 8 分。
    """
    times: List[Tuple[int, int]] = []
    cur = 10 * 60  # minutes from midnight
    end = 20 * 60
    peak_start = 17 * 60 + 30
    peak_end = 19 * 60 + 30
    while cur <= end:
        times.append((cur // 60, cur % 60))
        if is_weekday and peak_start <= cur < peak_end:
            cur += 6
        else:
            cur += 8
    return times


def _distance_weighted_segment_times(stations: List[dict], progress: dict) -> List[int]:
    """
    以 progress 差值（實距比例）分配總行駛時間到 11 個段。
    回傳 [seg0_sec, seg1_sec, ..., seg10_sec]。
    總行駛時間 = TRAVEL_TIME_SEC - dwell_total（中間 10 站 dwell）。
    """
    n = len(stations)
    total_driving = TRAVEL_TIME_SEC - DWELL_SEC * (n - 2)  # 首末不算 dwell
    diffs = []
    for i in range(n - 1):
        diffs.append(progress[stations[i + 1]["station_id"]] - progress[stations[i]["station_id"]])
    total_ratio = sum(diffs) or 1.0
    return [max(1, round(total_driving * d / total_ratio)) for d in diffs]


def write_schedules(stations: List[dict], seg_travel: List[int], is_weekday: bool) -> None:
    n = len(stations)
    total_travel = sum(seg_travel) + DWELL_SEC * (n - 2)
    departure_times = _generate_departures_10_20(is_weekday)

    for direction, track_id in enumerate(TRACK_IDS):
        seq = stations if direction == 0 else list(reversed(stations))
        # 反向的段時間也要反轉
        seg_time_seq = seg_travel if direction == 0 else list(reversed(seg_travel))
        origin = seq[0]["station_id"]
        destination = seq[-1]["station_id"]

        departures = []
        for i, (hh, mm) in enumerate(departure_times):
            dep_time_str = f"{hh:02d}:{mm:02d}:00"
            train_id = f"{track_id}-{i+1:03d}"
            station_times = []
            t = 0
            for k, s in enumerate(seq):
                station_times.append({
                    "station_id": s["station_id"],
                    "arrival": t,
                    "departure": t + (DWELL_SEC if 0 < k < n - 1 else 0),
                })
                if k < n - 1:
                    t += seg_time_seq[k] + (DWELL_SEC if k > 0 else 0)
            departures.append({
                "departure_time": dep_time_str,
                "train_id": train_id,
                "origin_station": origin,
                "destination_station": destination,
                "total_travel_time": total_travel,
                "stations": station_times,
            })

        sched = {
            "track_id": track_id,
            "route_id": f"{LINE_ID}-1",
            "name": f"{seq[0]['name']}站 → {seq[-1]['name']}站",
            "train_type": "local",
            "train_color": LINE_COLOR,
            "origin": origin,
            "destination": destination,
            "stations": [s["station_id"] for s in seq],
            "travel_time_minutes": TRAVEL_TIME_SEC // 60,
            "dwell_time_seconds": DWELL_SEC,
            "is_weekday": is_weekday,
            "departure_count": len(departures),
            "departures": departures,
        }
        # 平日檔覆蓋預設 <track>.json；假日檔另存 (若前端只吃預設檔，先只寫平日；假日檔備用)
        fname = f"{track_id}.json" if is_weekday else f"{track_id}.holiday.json"
        with open(os.path.join(SCHEDULE_DIR, fname), "w", encoding="utf-8") as f:
            json.dump(sched, f, ensure_ascii=False, indent=2)


def write_stations_geojson(stations: List[dict]) -> None:
    fc = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "station_id": s["station_id"],
                "name_zh": s["name"],
                "name_en": s["name_en"],
                "line_id": LINE_ID,
                "system_id": "trtc",
                "color": LINE_COLOR,
            },
            "geometry": {"type": "Point", "coordinates": s["coord"]},
        } for s in stations],
    }
    with open(STATION_FILE, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
