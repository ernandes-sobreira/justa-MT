#!/usr/bin/env python3
"""Read-only probe for MapBiomas 2022 municipal temperature ranking and task status."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import urllib.error

BASE = 'https://prd.plataforma.mapbiomas.org/api/v1/brazil'
RANKING_API = BASE + '/statistics/ranking/subtheme'
HEADERS = {
    'User-Agent': 'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)',
    'tenant-id': 'mapbiomas',
    'Accept': 'application/json',
}
MEAN_KEY = 'atmosphere_annual_mean_air_temperature'
MAX_KEY = 'atmosphere_annual_maximum_air_temperature'
MUNICIPAL_CATEGORY_ID = 230
SETTLED = {'success','succeeded','completed','exported','failed','error','cancelled','canceled'}


def get_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            body = r.read().decode('utf-8', errors='replace')
            return r.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try: obj = json.loads(body)
        except Exception: obj = {'raw': body[:10000]}
        return e.code, obj
    except Exception as e:
        return -1, {'error': repr(e)}


def ranking(params: dict[str, object]):
    url = RANKING_API + '?' + urllib.parse.urlencode(params, doseq=True)
    status, obj = get_json(url)
    return status, url, obj


def print_result(label: str, status: int, url: str, obj):
    print('\n===', label, '===')
    print('STATUS', status)
    print('URL', url)
    if isinstance(obj, dict):
        print('KEYS', list(obj.keys()))
        for k, v in obj.items():
            if isinstance(v, list):
                print('LIST', k, 'LEN', len(v))
                print(json.dumps(v[:5], ensure_ascii=False, indent=2)[:16000])
            elif isinstance(v, (int, float, str, bool)) or v is None:
                print(k, v)
            else:
                print(k, type(v).__name__, json.dumps(v, ensure_ascii=False)[:5000])
    else:
        print(json.dumps(obj, ensure_ascii=False, indent=2)[:20000])


def run_one(label: str, subtheme: str):
    params = {
        'year': 2022,
        'territoryCategoryId': MUNICIPAL_CATEGORY_ID,
        'statMethod': 'mean',
        'page': 1,
        'pageSize': 10,
        'subthemeKey': subtheme,
    }
    status, url, obj = ranking(params)
    print_result(label + '_initial', status, url, obj)
    task_id = obj.get('taskID') if status == 200 and isinstance(obj, dict) else None
    if not task_id:
        return

    task_url = f'{BASE}/statistics/task/{task_id}'
    for attempt in range(1, 13):
        ts, task = get_json(task_url)
        print(f'\nTASK {label} attempt={attempt} http={ts}')
        print(json.dumps(task, ensure_ascii=False, indent=2)[:12000])
        state = str(task.get('status','')).lower() if isinstance(task, dict) else ''
        if state in SETTLED:
            break
        time.sleep(2)

    # The SPA refetches the original ranking endpoint once the task settles.
    status2, url2, obj2 = ranking(params)
    print_result(label + '_after_task', status2, url2, obj2)


def main():
    run_one('mean_2022_page10', MEAN_KEY)
    run_one('max_2022_page10', MAX_KEY)


if __name__ == '__main__':
    main()
