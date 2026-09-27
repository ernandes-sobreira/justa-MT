#!/usr/bin/env python3
"""Read-only probe for the public MapBiomas Platform API used by Atmosphere.

Goal: identify the public endpoints and request shape used by the 2022 municipal
air-temperature statistics before falling back to raster zonal statistics.
This script never writes TEA-Brasil data files.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

HOME = 'https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
API = 'https://dev.plataforma.mapbiomas.org/api/v1'
THEME_MACHINE = 'atmosphere_annual_air_temperature'
UA = {'User-Agent': 'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)'}


def request(url: str, method: str = 'GET', data=None, timeout: int = 90):
    payload = None
    headers = dict(UA)
    if data is not None:
        payload = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get('content-type', ''), r.geturl(), r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('content-type', ''), e.geturl(), e.read(), dict(e.headers)
    except Exception as e:
        return -1, '', url, str(e).encode(), {}


def text_body(body: bytes) -> str:
    return body.decode('utf-8', errors='replace')


def contexts(text: str, needle: str, radius: int = 2500, limit: int = 8):
    low = text.lower(); target = needle.lower(); start = 0; out = []
    while len(out) < limit:
        i = low.find(target, start)
        if i < 0:
            break
        out.append(re.sub(r'\s+', ' ', text[max(0, i-radius):min(len(text), i+len(needle)+radius)]))
        start = i + len(target)
    return out


def show_http(label: str, url: str):
    status, ctype, final, body, headers = request(url)
    txt = text_body(body)
    print(f'\n=== HTTP {label} ===')
    print('STATUS', status, 'TYPE', ctype, 'FINAL', final, 'BYTES', len(body))
    print('BODY', re.sub(r'\s+', ' ', txt[:20000]))
    return status, ctype, txt


def main():
    status, _, final, body, _ = request(HOME)
    if status != 200:
        raise SystemExit(f'Platform home returned {status}')
    html = text_body(body)
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', html, re.I)
    bundles = [urllib.parse.urljoin(final, s) for s in scripts if '/assets/index-' in s]
    if not bundles:
        raise SystemExit('Main JS bundle not found')

    _, ctype, bundle_url, raw, _ = request(bundles[0])
    js = text_body(raw)
    print('BUNDLE', bundle_url, ctype, len(raw))

    # Show literal API route fragments, prioritizing the analysis/statistics machinery.
    print('\n=== UNIQUE API ROUTE LITERALS ===')
    route_re = re.compile(r'https://dev\.plataforma\.mapbiomas\.org/api/v1/[^`"\'\s)}]+')
    routes = sorted(set(route_re.findall(js)))
    interesting = [r for r in routes if any(k in r.lower() for k in (
        'stat', 'rank', 'chart', 'theme', 'subtheme', 'territor', 'project', 'dashboard'
    ))]
    for r in interesting[:300]:
        print(r)
    print('ROUTES_TOTAL', len(routes), 'INTERESTING', len(interesting))

    print('\n=== FOCUSED BUNDLE CONTEXT ===')
    for needle in [
        THEME_MACHINE,
        'subtheme_ranking',
        'subtheme_historical',
        'statistics',
        'statistic',
        'ranking',
        'territoryId',
        'territory_id',
        'pixelValues',
        'projectKey',
    ]:
        hits = contexts(js, needle)
        print(f'\n--- {needle} : {len(hits)} hit(s) ---')
        for i, hit in enumerate(hits, 1):
            print(f'[{i}] {hit[:6000]}')

    # Public project configuration. Validation errors are useful because they expose
    # route shape and required query parameters without mutating anything.
    candidates = [
        ('project_brazil', f'{API}/projects/by/key/brazil'),
        ('project_mapbiomas', f'{API}/projects/by/key/mapbiomas'),
        ('brazil_themes', f'{API}/brazil/themes'),
        ('brazil_territories', f'{API}/brazil/territories'),
        ('brazil_territory_categories', f'{API}/brazil/territories/categories'),
        ('brazil_statistics', f'{API}/brazil/statistics'),
        ('brazil_theme_temperature', f'{API}/brazil/themes/{THEME_MACHINE}'),
    ]
    for label, url in candidates:
        show_http(label, url)


if __name__ == '__main__':
    main()
