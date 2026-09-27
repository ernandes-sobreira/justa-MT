#!/usr/bin/env python3
"""Inspect MapBiomas map-export contract and find a national territory id.

Read-only except for the deliberately inert POST with an empty body used to
validate the export contract. No TEA-Brasil data are written.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import urllib.error

HOME = 'https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
HEADERS = {'User-Agent': 'TEA-Brasil/1.0'}
API_HEADERS = {
    'User-Agent': 'TEA-Brasil/1.0',
    'tenant-id': 'mapbiomas',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
}
PRD = 'https://prd.plataforma.mapbiomas.org/api/v1/brazil'


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode('utf-8', errors='replace')


def api_get(url: str):
    req = urllib.request.Request(url, headers=API_HEADERS, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            body = r.read().decode('utf-8', errors='replace')
            return r.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            obj = json.loads(body)
        except Exception:
            obj = {'raw': body[:12000]}
        return e.code, obj
    except Exception as e:
        return -1, {'error': repr(e)}


def compact(s: str, limit: int = 4200) -> str:
    return re.sub(r'\s+', ' ', s).strip()[:limit]


def contexts(js: str, needle: str, radius: int = 2600, limit: int = 15):
    pos = 0; out = []
    while len(out) < limit:
        i = js.find(needle, pos)
        if i < 0:
            break
        out.append((i, compact(js[max(0, i-radius):min(len(js), i+len(needle)+radius)])))
        pos = i + len(needle)
    return out


def validation_post(host: str):
    url = f'https://{host}.plataforma.mapbiomas.org/api/v1/brazil/maps/export'
    req = urllib.request.Request(url, data=b'{}', headers=API_HEADERS, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read().decode('utf-8', errors='replace')
            status = r.status
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode('utf-8', errors='replace')
    except Exception as e:
        print('EXPORT_VALIDATION', host, 'ERROR', repr(e)); return
    print('\nEXPORT_VALIDATION', host, 'HTTP', status)
    try:
        print(json.dumps(json.loads(body), ensure_ascii=False, indent=2)[:12000])
    except Exception:
        print(body[:12000])


def print_json(label: str, status: int, obj):
    print('\n===', label, 'HTTP', status, '===')
    print(json.dumps(obj, ensure_ascii=False, indent=2)[:50000])


def probe_national_territory():
    # A point in Brasilia should return the full territory hierarchy containing
    # municipality/state/Brazil. We need the national territory ID for maps/export.
    params = urllib.parse.urlencode({'latitude': -15.793889, 'longitude': -47.882778})
    status, obj = api_get(f'{PRD}/territories/point?{params}')
    print_json('TERRITORIES_POINT_BRASILIA', status, obj)

    # Also inspect groups/categories around the point contract so we can identify
    # the national-level candidate without guessing from translated names.
    status, obj = api_get(f'{PRD}/territories/groups')
    print_json('TERRITORY_GROUPS', status, obj)


def main():
    probe_national_territory()

    html = get(HOME)
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', html, re.I)
    urls = [urllib.parse.urljoin(HOME, s) for s in scripts if '/assets/' in s and s.endswith('.js')]
    for url in urls:
        js = get(url)
        if '/maps/export' not in js:
            continue
        print('BUNDLE', url, 'BYTES', len(js))
        for needle in ('/maps/export', 'Dk(', 'territoryId', 'subthemeKey', 'exportFormat', 'fileName'):
            hits = contexts(js, needle)
            if not hits:
                continue
            print(f'\n### {needle} {len(hits)}')
            for idx, text in hits:
                print('AT', idx, text)

    validation_post('prd')
    validation_post('dev')


if __name__ == '__main__':
    main()
