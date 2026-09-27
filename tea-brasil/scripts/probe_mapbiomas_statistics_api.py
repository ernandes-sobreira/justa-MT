#!/usr/bin/env python3
"""Discover the read-only statistics routes used by the public MapBiomas SPA.

No project data are written. The goal is to identify the exact endpoint/payload
for subtheme ranking/summary so TEA-Brasil can extract 2022 values reproducibly.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request

HOME = 'https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
HEADERS = {'User-Agent': 'TEA-Brasil/1.0'}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode('utf-8', errors='replace')


def contexts(text: str, needle: str, radius=5000, limit=30):
    low = text.lower(); target = needle.lower(); p = 0; out = []
    while len(out) < limit:
        i = low.find(target, p)
        if i < 0:
            break
        out.append(re.sub(r'\s+', ' ', text[max(0, i-radius):min(len(text), i+len(needle)+radius)]))
        p = i + len(target)
    return out


def main():
    html = get(HOME)
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', html, re.I)
    urls = [urllib.parse.urljoin(HOME, s) for s in scripts if '/assets/' in s and s.endswith('.js')]
    print('JS_FILES', len(urls))
    for url in urls:
        js = get(url)
        if not any(x in js for x in ('subtheme_ranking', 'subtheme_historical', 'subtheme_summary', '/statistics')):
            continue
        print('\n### BUNDLE', url, 'BYTES', len(js))
        # Route-like literals, including minified template fragments.
        route_patterns = [
            r'https://(?:prd|dev)\.plataforma\.mapbiomas\.org/api/v1/[^`"\'\s)}]+',
            r'url:`([^`]{0,300}(?:stat|rank)[^`]{0,500})`',
            r'url:"([^"]{0,300}(?:stat|rank)[^"]{0,500})"',
        ]
        found = set()
        for pat in route_patterns:
            for m in re.findall(pat, js, re.I):
                found.add(m if isinstance(m, str) else str(m))
        print('ROUTE_CANDIDATES', len(found))
        for item in sorted(found):
            print('ROUTE', item[:1500])
        for needle in [
            'subtheme_ranking', 'subtheme_historical', 'subtheme_summary',
            'ranking', 'statistics', 'statistic', 'native_grid_statistics',
            'territoryIds', 'territory_ids', 'subthemeId', 'subtheme_id'
        ]:
            hits = contexts(js, needle)
            print(f'\n--- {needle}: {len(hits)} context(s) ---')
            for i, hit in enumerate(hits, 1):
                print(f'[{i}] {hit[:12000]}')


if __name__ == '__main__':
    main()
