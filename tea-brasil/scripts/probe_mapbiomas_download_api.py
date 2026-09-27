#!/usr/bin/env python3
"""Inspect and validate the public MapBiomas map-export contract.

The only POST sent here has an empty JSON body, so it can only trigger backend
validation; it cannot request a real export. No TEA-Brasil data are changed.
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


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode('utf-8', errors='replace')


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


def main():
    html = get(HOME)
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', html, re.I)
    urls = [urllib.parse.urljoin(HOME, s) for s in scripts if '/assets/' in s and s.endswith('.js')]
    for url in urls:
        js = get(url)
        if '/maps/export' not in js:
            continue
        print('BUNDLE', url, 'BYTES', len(js))
        # Dk is the query hook around POST /maps/export. Its callers expose the body.
        for needle in ('/maps/export', 'Dk(', 'territoryId', 'subthemeKey', 'exportFormat', 'fileName'):
            hits = contexts(js, needle)
            if not hits:
                continue
            print(f'\n### {needle} {len(hits)}')
            for idx, text in hits:
                print('AT', idx, text)

    # Ask backend validation for the exact required body fields; empty JSON is inert.
    validation_post('prd')
    validation_post('dev')


if __name__ == '__main__':
    main()
