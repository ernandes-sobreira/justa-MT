#!/usr/bin/env python3
"""Read-only probe for MapBiomas 2022 municipal temperature ranking."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
import urllib.error

API = 'https://prd.plataforma.mapbiomas.org/api/v1/brazil/statistics/ranking/subtheme'
HEADERS = {
    'User-Agent': 'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)',
    'tenant-id': 'mapbiomas',
    'Accept': 'application/json',
}
MEAN_KEY = 'atmosphere_annual_mean_air_temperature'
MAX_KEY = 'atmosphere_annual_maximum_air_temperature'
MUNICIPAL_CATEGORY_ID = 230


def request(params: dict[str, object]):
    url = API + '?' + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers=HEADERS, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.status, url, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, url, e.read().decode('utf-8', errors='replace')
    except Exception as e:
        return -1, url, repr(e)


def summarize(label: str, params: dict[str, object]):
    status, url, body = request(params)
    print('\n===', label, '===')
    print('STATUS', status)
    print('URL', url)
    try:
        obj = json.loads(body)
    except Exception:
        print(body[:20000]); return
    if status != 200:
        print(json.dumps(obj, ensure_ascii=False, indent=2)[:20000]); return
    print('TYPE', type(obj).__name__)
    if isinstance(obj, dict):
        print('KEYS', list(obj.keys()))
        for k, v in obj.items():
            if isinstance(v, list):
                print('LIST', k, 'LEN', len(v))
                print(json.dumps(v[:5], ensure_ascii=False, indent=2)[:12000])
            elif isinstance(v, (int, float, str, bool)) or v is None:
                print(k, v)
            else:
                print(k, type(v).__name__, json.dumps(v, ensure_ascii=False)[:3000])
    elif isinstance(obj, list):
        print('LEN', len(obj))
        print(json.dumps(obj[:5], ensure_ascii=False, indent=2)[:12000])


def main():
    common = {
        'year': 2022,
        'territoryCategoryId': MUNICIPAL_CATEGORY_ID,
        'statMethod': 'mean',
        'page': 1,
        'pageSize': 10,
    }
    summarize('mean_2022_page10', {**common, 'subthemeKey': MEAN_KEY})
    summarize('max_2022_page10', {**common, 'subthemeKey': MAX_KEY})


if __name__ == '__main__':
    main()
