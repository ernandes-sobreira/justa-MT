#!/usr/bin/env python3
"""Read-only probe for complete MapBiomas 2022 municipal temperature rankings.

The MapBiomas statistics API may answer with a taskID while Earth Engine
statistics are being prepared. This probe follows the same contract used by the
public SPA: poll the task, then refetch the original ranking. It never writes
TEA-Brasil data files.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import urllib.error

PRD_BASE = 'https://prd.plataforma.mapbiomas.org/api/v1/brazil'
DEV_BASE = 'https://dev.plataforma.mapbiomas.org/api/v1/brazil'
RANKING_API = PRD_BASE + '/statistics/ranking/subtheme'
HEADERS = {
    'User-Agent': 'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)',
    'tenant-id': 'mapbiomas',
    'Accept': 'application/json',
}
KEYS = {
    'mean': 'atmosphere_annual_mean_air_temperature',
    'max': 'atmosphere_annual_maximum_air_temperature',
    'min': 'atmosphere_annual_minimum_air_temperature',
}
MUNICIPAL_CATEGORY_ID = 230
SETTLED = {'success', 'exported', 'failed', 'aborted'}


def get_json(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers=HEADERS, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode('utf-8', errors='replace')
            return r.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            obj = json.loads(body)
        except Exception:
            obj = {'raw': body[:10000]}
        return e.code, obj
    except Exception as e:
        return -1, {'error': repr(e)}


def ranking(subtheme: str, page: int = 1, page_size: int = 6000):
    params = {
        'year': 2022,
        'territoryCategoryId': MUNICIPAL_CATEGORY_ID,
        'statMethod': 'mean',
        'page': page,
        'pageSize': page_size,
        'subthemeKey': subtheme,
    }
    url = RANKING_API + '?' + urllib.parse.urlencode(params, doseq=True)
    status, obj = get_json(url)
    return status, url, obj


def summarize(label: str, status: int, url: str, obj):
    print('\n===', label, '===')
    print('STATUS', status)
    print('URL', url)
    if not isinstance(obj, dict):
        print(json.dumps(obj, ensure_ascii=False)[:12000])
        return
    print('KEYS', list(obj.keys()))
    for k in ('taskID', 'page', 'numberOfPages', 'max', 'min', 'unit', 'statMethod'):
        if k in obj:
            print(k, obj[k])
    rows = obj.get('ranking')
    if isinstance(rows, list):
        print('RANKING_LEN', len(rows))
        if rows:
            print('RANKING_FIRST', json.dumps(rows[:3], ensure_ascii=False, indent=2)[:12000])
            print('RANKING_LAST', json.dumps(rows[-3:], ensure_ascii=False, indent=2)[:12000])
            if isinstance(rows[0], dict):
                print('RANKING_ITEM_KEYS', list(rows[0].keys()))


def poll_task(task_id: str, label: str, max_seconds: int = 150):
    started = time.monotonic()
    attempt = 0
    last = None
    while time.monotonic() - started <= max_seconds:
        attempt += 1
        # Production and dev currently expose the same public task object; use
        # production as the canonical source and only fall back to dev on error.
        status, obj = get_json(f'{PRD_BASE}/statistics/task/{task_id}', timeout=20)
        if status != 200:
            status, obj = get_json(f'{DEV_BASE}/statistics/task/{task_id}', timeout=20)
        task_status = str(obj.get('status', '')).lower() if isinstance(obj, dict) else ''
        if task_status != last or attempt == 1:
            print('TASK', label, 'attempt', attempt, 'http', status, 'status', task_status)
            print(json.dumps(obj, ensure_ascii=False, indent=2)[:8000])
            last = task_status
        if task_status in SETTLED:
            return obj
        time.sleep(4)
    print('TASK_TIMEOUT', label, task_id, 'seconds', max_seconds)
    return None


def run_one(label: str, subtheme: str):
    status, url, obj = ranking(subtheme)
    summarize(label + '_initial', status, url, obj)
    task_id = obj.get('taskID') if status == 200 and isinstance(obj, dict) else None
    if task_id:
        task = poll_task(str(task_id), label)
        if not task:
            return
        task_status = str(task.get('status', '')).lower()
        if task_status not in {'success', 'exported'}:
            print('TASK_NOT_SUCCESSFUL', label, task_status)
            return
        # Give the serving layer a short moment to expose computed results.
        time.sleep(2)
        status, url, obj = ranking(subtheme)
        summarize(label + '_after_task', status, url, obj)

    # Explicit verdict for the proposed direct-ranking route.
    if isinstance(obj, dict) and isinstance(obj.get('ranking'), list):
        rows = obj['ranking']
        print('DIRECT_RANKING_VERDICT', label, 'rows', len(rows), 'usable_for_5570', len(rows) >= 5570)


def main():
    for label, key in KEYS.items():
        run_one(label + '_2022', key)


if __name__ == '__main__':
    main()
