#!/usr/bin/env python3
"""Read-only probe for MapBiomas ranking/subtheme validation and 2022 temperature.

The API itself is allowed to reveal required query fields through validation
errors; no parameter names are guessed silently and no TEA-Brasil data are written.
"""
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
MUNICIPAL_CATEGORY_ID = '230'


def request(params: dict[str, object]):
    qs = urllib.parse.urlencode(params, doseq=True)
    url = API + ('?' + qs if qs else '')
    req = urllib.request.Request(url, headers=HEADERS, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, url, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, url, e.read().decode('utf-8', errors='replace')
    except Exception as e:
        return -1, url, repr(e)


def show(label: str, params: dict[str, object]):
    status, url, body = request(params)
    print('\n===', label, '===')
    print('STATUS', status)
    print('URL', url)
    try:
        obj = json.loads(body)
        print(json.dumps(obj, ensure_ascii=False, indent=2)[:30000])
    except Exception:
        print(body[:30000])
    return status, body


def main():
    # First request deliberately empty: backend validation is authoritative.
    show('empty', {})

    # Then test the smallest scientifically plausible parameter sets, preserving
    # the current official municipal category only as a diagnostic. If the API
    # ranks 2025 municipality geometry, we will NOT use it as the 2022 base.
    candidates = [
        {'subthemeKey': MEAN_KEY},
        {'subthemeKey': MEAN_KEY, 'year': 2022},
        {'subthemeKey': MEAN_KEY, 'year': 2022, 'territoryCategoryId': MUNICIPAL_CATEGORY_ID},
        {'subthemeKey': MEAN_KEY, 'year': 2022, 'territoryCategoryId': MUNICIPAL_CATEGORY_ID, 'page': 1, 'pageSize': 10},
        {'subthemeKey': MAX_KEY, 'year': 2022, 'territoryCategoryId': MUNICIPAL_CATEGORY_ID, 'page': 1, 'pageSize': 10},
    ]
    for i, params in enumerate(candidates, 1):
        show(f'candidate_{i}', params)


if __name__ == '__main__':
    main()
