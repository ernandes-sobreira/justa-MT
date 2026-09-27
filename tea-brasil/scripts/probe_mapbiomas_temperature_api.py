#!/usr/bin/env python3
"""Focused read-only probe for MapBiomas public Platform API used by Atmosphere air temperature.

Goal: discover whether 2022 municipal statistics can be retrieved directly from the public
MapBiomas API, preserving IBGE municipality identifiers, before considering raster zonal stats.
This script never writes TEA-Brasil data files.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

HOME = 'https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
API = 'https://api.mapbiomas.org'
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


def text_body(body: bytes) -> str:
    return body.decode('utf-8', errors='replace')


def contexts(text: str, needle: str, radius: int = 3500, limit: int = 10):
    low = text.lower(); target = needle.lower(); start = 0; out = []
    while len(out) < limit:
        i = low.find(target, start)
        if i < 0:
            break
        out.append(re.sub(r'\s+', ' ', text[max(0, i-radius):min(len(text), i+len(needle)+radius)]))
        start = i + len(target)
    return out


def show_http(label: str, url: str, method: str = 'GET', data=None):
    status, ctype, final, body, headers = request(url, method=method, data=data)
    txt = text_body(body)
    print(f'\n=== HTTP {label} ===')
    print('METHOD', method, 'STATUS', status, 'TYPE', ctype, 'FINAL', final, 'BYTES', len(body))
    print('ALLOW', headers.get('Allow') or headers.get('allow'))
    print('BODY', re.sub(r'\s+', ' ', txt[:12000]))
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

    print('\n=== FOCUSED BUNDLE CONTEXT ===')
    needles = [
        'project_statistic_data',
        '/api/v1/projects',
        '/api/v1/subthemes',
        '/api/v1/municipalities',
        THEME_MACHINE,
        'territory_id',
        'territory_type',
        'subtheme_id',
        'project_id',
        'year',
    ]
    for needle in needles:
        hits = contexts(js, needle)
        print(f'\n--- {needle} : {len(hits)} hit(s) ---')
        for i, hit in enumerate(hits, 1):
            print(f'[{i}] {hit[:8000]}')

    # Plain GETs are intentionally first: validation errors often reveal required params.
    endpoints = [
        ('projects', f'{API}/api/v1/projects'),
        ('subthemes', f'{API}/api/v1/subthemes'),
        ('municipalities', f'{API}/api/v1/municipalities'),
        ('project_statistic_data', f'{API}/api/v1/project_statistic_data'),
        ('states', f'{API}/api/v1/states'),
        ('biomes', f'{API}/api/v1/biomes'),
        ('categories', f'{API}/api/v1/categories'),
    ]
    responses = {}
    for label, url in endpoints:
        responses[label] = show_http(label, url)

    # Also test common project filters, read-only. These are harmless even if unsupported.
    candidates = [
        ('projects_slug', f'{API}/api/v1/projects?slug=mapbiomas'),
        ('projects_name', f'{API}/api/v1/projects?name=mapbiomas'),
        ('subthemes_machine', f'{API}/api/v1/subthemes?name={urllib.parse.quote(THEME_MACHINE)}'),
        ('subthemes_slug', f'{API}/api/v1/subthemes?slug={urllib.parse.quote(THEME_MACHINE)}'),
        ('municipalities_brazil', f'{API}/api/v1/municipalities?country=BR'),
    ]
    for label, url in candidates:
        show_http(label, url)


if __name__ == '__main__':
    main()
