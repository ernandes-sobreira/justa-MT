#!/usr/bin/env python3
"""Read-only probe for MapBiomas Atmosphere public API.

Discovers the public request shape used by the MapBiomas Brazil dashboard and
locates metadata for 2022 air-temperature subthemes. Never writes TEA data.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

HOME = 'https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
API = 'https://dev.plataforma.mapbiomas.org/api/v1'
TENANT = 'mapbiomas'
TARGETS = {
    'atmosphere_annual_air_temperature',
    'atmosphere_annual_mean_air_temperature',
    'atmosphere_annual_maximum_air_temperature',
    'atmosphere_annual_minimum_air_temperature',
    'atmosphere_annual_fine_particulate_matter_pm2_5',
}
UA = {'User-Agent': 'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)'}


def request(url: str, timeout: int = 90, headers=None):
    h = dict(UA)
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get('content-type', ''), r.geturl(), r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('content-type', ''), e.geturl(), e.read(), dict(e.headers)
    except Exception as e:
        return -1, '', url, str(e).encode(), {}


def txt(b):
    return b.decode('utf-8', errors='replace')


def add_tenant(url: str) -> str:
    sep = '&' if '?' in url else '?'
    return f'{url}{sep}cpTenant={urllib.parse.quote(TENANT)}'


def show(label, url, headers=None, body_limit=12000):
    status, ctype, final, body, _ = request(url, headers=headers)
    body_txt = txt(body)
    print(f'\n=== {label} ===')
    print('STATUS', status, 'TYPE', ctype, 'FINAL', final, 'BYTES', len(body))
    print('BODY', re.sub(r'\s+', ' ', body_txt[:body_limit]))
    return status, ctype, body_txt


def walk(obj, path='$'):
    if isinstance(obj, dict):
        key = obj.get('key')
        if isinstance(key, str) and key in TARGETS:
            print('\n*** TARGET FOUND', key, 'AT', path, '***')
            print(json.dumps(obj, ensure_ascii=False, indent=2)[:50000])
        for k, v in obj.items():
            walk(v, f'{path}.{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, f'{path}[{i}]')


def try_json(label, url, headers=None):
    status, ctype, body = show(label, url, headers=headers)
    if status == 200 and 'json' in ctype.lower():
        try:
            data = json.loads(body)
            print('JSON_TOP_KEYS', list(data)[:50] if isinstance(data, dict) else f'LIST[{len(data)}]')
            walk(data)
            return data
        except Exception as e:
            print('JSON_PARSE_ERROR', repr(e))
    return None


def contexts(text: str, needle: str, radius=2200, limit=10):
    low = text.lower(); target = needle.lower(); pos = 0; out = []
    while len(out) < limit:
        i = low.find(target, pos)
        if i < 0:
            break
        out.append(re.sub(r'\s+', ' ', text[max(0, i-radius):min(len(text), i+len(needle)+radius)]))
        pos = i + len(target)
    return out


def main():
    # First use the tenant query parameter visible in the dashboard client.
    urls = [
        ('project', add_tenant(f'{API}/projects/by/key/brazil')),
        ('themes', add_tenant(f'{API}/brazil/themes?page=1&pageSize=1000')),
        ('subthemes', add_tenant(f'{API}/brazil/subthemes?page=1&pageSize=1000')),
        ('territory_categories', add_tenant(f'{API}/brazil/territories/categories?page=1&pageSize=1000')),
        ('territories', add_tenant(f'{API}/brazil/territories?page=1&pageSize=5')),
    ]
    responses = {}
    for label, url in urls:
        responses[label] = try_json(label, url)

    # If query parameter alone is insufficient, test likely tenant headers read-only.
    if not any(v is not None for v in responses.values()):
        print('\n=== TENANT HEADER FALLBACKS ===')
        for hdr in ('x-tenant-id', 'x-tenant', 'tenant-id', 'tenant', 'cp-tenant', 'x-cp-tenant'):
            try_json(f'project header {hdr}', f'{API}/projects/by/key/brazil', headers={hdr: TENANT})

    # Inspect exact client contexts for transport and route constructor functions.
    status, _, final, body, _ = request(HOME)
    if status != 200:
        raise SystemExit(f'Platform home returned {status}')
    html = txt(body)
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', html, re.I)
    bundles = [urllib.parse.urljoin(final, s) for s in scripts if '/assets/index-' in s]
    if not bundles:
        raise SystemExit('Main JS bundle not found')
    _, _, bundle_url, raw, _ = request(bundles[0])
    js = txt(raw)
    print('\nBUNDLE', bundle_url, 'BYTES', len(raw))
    for needle in ['cpTenant', 'tenantId', '/subthemes', '/themes', '/territories', 'statisticsController', 'subtheme_ranking']:
        hits = contexts(js, needle)
        print(f'\n--- CONTEXT {needle}: {len(hits)} ---')
        for i, hit in enumerate(hits, 1):
            print(f'[{i}] {hit[:6500]}')


if __name__ == '__main__':
    main()
