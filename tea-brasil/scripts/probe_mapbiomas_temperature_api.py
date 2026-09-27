#!/usr/bin/env python3
"""Read-only probe for MapBiomas Atmosphere public API.

Uses the same production API and tenant header as the public MapBiomas client,
locates temperature/PM2.5 subthemes, and prints their asset metadata. Never
writes TEA-Brasil data files.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

API = 'https://prd.plataforma.mapbiomas.org/api/v1'
TENANT = 'mapbiomas'
TARGETS = {
    'atmosphere_annual_air_temperature',
    'atmosphere_annual_mean_air_temperature',
    'atmosphere_annual_maximum_air_temperature',
    'atmosphere_annual_minimum_air_temperature',
    'atmosphere_annual_fine_particulate_matter_pm2_5',
}
HEADERS = {
    'User-Agent': 'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)',
    'tenant-id': TENANT,
    'Accept': 'application/json',
}


def request(url: str, timeout: int = 120):
    req = urllib.request.Request(url, headers=HEADERS, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get('content-type', ''), r.geturl(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('content-type', ''), e.geturl(), e.read()
    except Exception as e:
        return -1, '', url, str(e).encode()


def get_json(label: str, url: str):
    status, ctype, final, body = request(url)
    text = body.decode('utf-8', errors='replace')
    print(f'\n=== {label} ===')
    print('STATUS', status, 'TYPE', ctype, 'FINAL', final, 'BYTES', len(body))
    if status != 200:
        print('BODY', re.sub(r'\s+', ' ', text[:12000]))
        return None
    try:
        data = json.loads(text)
    except Exception as e:
        print('JSON_ERROR', repr(e), 'BODY', text[:5000])
        return None
    if isinstance(data, dict):
        print('TOP_KEYS', list(data.keys())[:80])
    else:
        print('TOP', type(data).__name__, 'LEN', len(data) if hasattr(data, '__len__') else '?')
    return data


def collect_targets(obj, path='$', out=None):
    if out is None:
        out = []
    if isinstance(obj, dict):
        key = obj.get('key')
        if key in TARGETS:
            out.append((path, obj))
        for k, v in obj.items():
            collect_targets(v, f'{path}.{k}', out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            collect_targets(v, f'{path}[{i}]', out)
    return out


def main():
    project = get_json('project', f'{API}/projects/by/key/brazil')
    themes = get_json('themes', f'{API}/brazil/themes?page=1&pageSize=1000&expand=true')
    subthemes = get_json('subthemes', f'{API}/brazil/themes/subthemes?page=1&pageSize=1000')
    categories = get_json('territory_categories', f'{API}/brazil/territories/categories?page=1&pageSize=1000')

    found = []
    for label, data in [('project', project), ('themes', themes), ('subthemes', subthemes)]:
        if data is None:
            continue
        for path, item in collect_targets(data):
            found.append((label, path, item))

    print('\n=== TARGET SUBTHEMES ===')
    unique = {}
    for label, path, item in found:
        ident = item.get('id') or item.get('key')
        unique[str(ident)] = item
        print('\nSOURCE', label, 'PATH', path)
        print(json.dumps(item, ensure_ascii=False, indent=2)[:50000])

    print('\nTARGET_COUNT', len(unique))
    if not unique:
        raise SystemExit('No target atmosphere subthemes found')

    # Fetch each subtheme individually to expose full asset/band/year metadata.
    for item in unique.values():
        sid = item.get('id')
        if sid:
            full = get_json(f'subtheme_{item.get("key")}', f'{API}/brazil/themes/subthemes/{sid}')
            if full is not None:
                print(json.dumps(full, ensure_ascii=False, indent=2)[:50000])

    # Print municipality-related categories so the future extraction can select
    # exactly the municipal territorial level rather than guessing.
    if isinstance(categories, dict):
        cats = categories.get('categories', [])
        print('\n=== MUNICIPAL CATEGORY CANDIDATES ===')
        for c in cats:
            hay = json.dumps(c, ensure_ascii=False).lower()
            if 'munic' in hay:
                print(json.dumps(c, ensure_ascii=False, indent=2)[:10000])


if __name__ == '__main__':
    main()
