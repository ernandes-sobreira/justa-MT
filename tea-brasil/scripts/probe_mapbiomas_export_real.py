#!/usr/bin/env python3
"""Request one real public MapBiomas Atmosphere export for Brazil, 2022.

This is a controlled probe for the annual mean air temperature raster. It does
not alter TEA-Brasil datasets. The public SPA uses the same POST repeatedly and
polls every 30 seconds while export statuses are pending.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

API = 'https://prd.plataforma.mapbiomas.org/api/v1/brazil/maps/export'
HEADERS = {
    'User-Agent': 'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)',
    'tenant-id': 'mapbiomas',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
}
PAYLOAD = {
    'territoryId': '0582a562-7ef9-419c-8d0f-02622b631f6b',
    'subthemeKey': 'atmosphere_annual_mean_air_temperature',
    'year': [2022],
    'exportType': 'separate',
}
IN_PROGRESS = {'PENDING', 'EXPORTING', 'GENERATING_MOSAIC', 'pending', 'running', 'exporting', 'generating_mosaic'}
TERMINAL_BAD = {'FAILED', 'ABORTED', 'failed', 'aborted'}


def post():
    data = json.dumps(PAYLOAD).encode('utf-8')
    req = urllib.request.Request(API, data=data, headers=HEADERS, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode('utf-8', errors='replace')
            return r.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            obj = json.loads(body)
        except Exception:
            obj = {'raw': body[:20000]}
        return e.code, obj
    except Exception as e:
        return -1, {'error': repr(e)}


def state(obj):
    if not isinstance(obj, dict):
        return 'unknown'
    if isinstance(obj.get('url'), str) and obj['url']:
        return 'ready'
    exports = obj.get('exports')
    if isinstance(exports, list) and exports:
        statuses = [str(x.get('status', '')) for x in exports if isinstance(x, dict)]
        urls = [x.get('url') for x in exports if isinstance(x, dict) and x.get('url')]
        if urls and not any(s in IN_PROGRESS for s in statuses):
            return 'ready'
        if any(s in TERMINAL_BAD for s in statuses):
            return 'failed'
        if statuses:
            return 'working'
    status = str(obj.get('status', ''))
    if status in TERMINAL_BAD:
        return 'failed'
    if status in IN_PROGRESS:
        return 'working'
    return 'unknown'


def main():
    print('REQUEST', json.dumps(PAYLOAD, ensure_ascii=False))
    for attempt in range(1, 9):
        status, obj = post()
        print('\nATTEMPT', attempt, 'HTTP', status, 'STATE', state(obj))
        print(json.dumps(obj, ensure_ascii=False, indent=2)[:30000])
        if status != 200:
            raise SystemExit(f'Export API HTTP {status}')
        st = state(obj)
        if st == 'ready':
            print('EXPORT_READY')
            return
        if st == 'failed':
            raise SystemExit('Export failed')
        if attempt < 8:
            time.sleep(30)
    raise SystemExit('Export did not become ready within probe window')


if __name__ == '__main__':
    main()
