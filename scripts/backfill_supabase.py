"""
從 S3 回填歷史時刻表到 Supabase reference.daily_schedules

資料來源：
1. mini-taipei/thsr/daily/*.json (已轉換格式，直接寫入)
2. rail_timetable/archives/*.tar.gz (TDX 原始格式，需轉換)

目標：寫入 tra_daily / thsr_daily 到 Supabase
"""

import sys
import os
import json
import tarfile
import tempfile
import io
from datetime import datetime

import boto3
import psycopg2

# ===== 設定 =====
S3_BUCKET = 'migu-gis-data-collector'
S3_REGION = 'ap-southeast-2'
S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY')
S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY')
SUPABASE_DB_URL = os.environ.get('SUPABASE_DB_URL')

if not (S3_ACCESS_KEY and S3_SECRET_KEY and SUPABASE_DB_URL):
    raise RuntimeError('請先設定環境變數 S3_ACCESS_KEY / S3_SECRET_KEY / SUPABASE_DB_URL')

# 轉換函數路徑 (data-collectors)
DATA_COLLECTORS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data-collectors')
sys.path.insert(0, DATA_COLLECTORS_PATH)

# ===== S3 Client =====
s3 = boto3.client('s3',
    region_name=S3_REGION,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY
)


def get_s3_json(key):
    """從 S3 取得 JSON"""
    obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
    return json.loads(obj['Body'].read().decode('utf-8'))


def upsert_schedule(conn, system, date, train_count, data):
    """寫入 Supabase daily_schedules"""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO reference.daily_schedules (system, schedule_date, train_count, data)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT (system, schedule_date) DO UPDATE SET
            train_count = EXCLUDED.train_count, data = EXCLUDED.data
        """, (system, date, train_count, json.dumps(data, ensure_ascii=False)))
    conn.commit()


def backfill_thsr_from_s3(conn):
    """回填 S3 上已轉換的 THSR 時刻表"""
    print('\n=== 回填 THSR (S3 已轉換格式) ===')
    paginator = s3.get_paginator('list_objects_v2')
    count = 0
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix='mini-taipei/thsr/daily/'):
        for obj in page.get('Contents', []):
            date = obj['Key'].split('/')[-1].replace('.json', '')
            if len(date) != 10:
                continue
            try:
                data = get_s3_json(obj['Key'])
                # 計算班次
                trains = 0
                for k, v in data.items():
                    if k.startswith('THSR-') and isinstance(v, dict):
                        trains += v.get('departure_count', len(v.get('departures', [])))
                upsert_schedule(conn, 'thsr_daily', date, trains, data)
                print(f'  ✅ THSR {date}: {trains} 班')
                count += 1
            except Exception as e:
                print(f'  ❌ THSR {date}: {e}')
    print(f'THSR 回填完成: {count} 天')


def backfill_from_archives(conn):
    """從 archives 解壓 TDX 原始資料，轉換後寫入"""
    print('\n=== 回填 TRA+THSR (archives 轉換) ===')

    # 載入轉換函數
    try:
        from tasks.mini_taipei_publish import (
            build_track_index, convert_tra_timetable, convert_thsr_timetable
        )
    except ImportError as e:
        print(f'❌ 無法載入轉換函數: {e}')
        print(f'   確認 data-collectors 路徑: {DATA_COLLECTORS_PATH}')
        return

    # 載入 od_station_progress
    print('載入 od_station_progress...')
    try:
        od_progress = get_s3_json('mini-taipei/tra/od_station_progress.json')
        track_index = build_track_index(od_progress)
        print(f'  ✅ {len(od_progress)} 條軌道')
    except Exception as e:
        print(f'  ❌ 無法載入 od_station_progress: {e}')
        return

    # 列出所有 archives
    paginator = s3.get_paginator('list_objects_v2')
    archives = []
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix='rail_timetable/archives/'):
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.tar.gz'):
                date = obj['Key'].split('/')[-1].replace('.tar.gz', '')
                if len(date) == 10:
                    archives.append((date, obj['Key']))

    archives.sort()
    print(f'找到 {len(archives)} 個 archives')

    tra_count = 0
    thsr_count = 0
    for date, key in archives:
        try:
            # 下載並解壓
            obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
            tar_bytes = obj['Body'].read()
            tar = tarfile.open(fileobj=io.BytesIO(tar_bytes), mode='r:gz')

            # 找 rail_timetable JSON
            raw_data = None
            for member in tar.getmembers():
                if 'rail_timetable' in member.name and member.name.endswith('.json'):
                    f = tar.extractfile(member)
                    if f:
                        raw_data = json.loads(f.read().decode('utf-8'))
                        break

            if not raw_data or 'data' not in raw_data:
                print(f'  ⚠️  {date}: 無 rail_timetable 資料')
                continue

            data = raw_data['data']

            # 轉換 TRA
            tra_raw = data.get('tra', {}).get('data', [])
            if tra_raw:
                try:
                    tra_output, _coverage = convert_tra_timetable(tra_raw, date, track_index, od_progress)
                    trains = tra_output['metadata']['total_trains']
                    upsert_schedule(conn, 'tra_daily', date, trains, tra_output)
                    print(f'  ✅ TRA  {date}: {trains} 班 (失敗 {tra_output["metadata"]["failed"]})')
                    tra_count += 1
                except Exception as e:
                    print(f'  ❌ TRA  {date}: {e}')

            # 轉換 THSR
            thsr_raw = data.get('thsr', {}).get('data', [])
            if thsr_raw:
                try:
                    thsr_output = convert_thsr_timetable(thsr_raw, date)
                    trains = thsr_output['_metadata']['total_trains']
                    upsert_schedule(conn, 'thsr_daily', date, thsr_output['_metadata']['total_trains'], thsr_output)
                    print(f'  ✅ THSR {date}: {trains} 班')
                    thsr_count += 1
                except Exception as e:
                    print(f'  ❌ THSR {date}: {e}')

        except Exception as e:
            print(f'  ❌ {date}: 解壓失敗 {e}')

    print(f'\nArchives 回填完成: TRA {tra_count} 天, THSR {thsr_count} 天')


def main():
    print('連線 Supabase...')
    conn = psycopg2.connect(SUPABASE_DB_URL)
    conn.autocommit = False
    print('✅ 連線成功')

    # 1. 先回填 S3 上已轉換的 THSR
    backfill_thsr_from_s3(conn)

    # 2. 從 archives 回填 TRA + THSR（會覆蓋 step 1 的 THSR）
    backfill_from_archives(conn)

    # 3. 確認結果
    print('\n=== 最終結果 ===')
    with conn.cursor() as cur:
        cur.execute("""
            SELECT system, count(*), min(schedule_date), max(schedule_date)
            FROM reference.daily_schedules
            WHERE system IN ('tra_daily', 'thsr_daily')
            GROUP BY system ORDER BY system
        """)
        for row in cur.fetchall():
            print(f'  {row[0]}: {row[1]} 天 ({row[2]} ~ {row[3]})')

    conn.close()
    print('\n完成！')


if __name__ == '__main__':
    main()
