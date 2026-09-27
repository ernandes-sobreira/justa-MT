#!/usr/bin/env python3
"""Inspect the exact MapBiomas ranking/subtheme parameter builder used by the SPA."""
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


def compact(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def dump(js: str, needle: str, radius: int = 5000, limit: int = 12) -> None:
    pos = 0; hits = 0
    while hits < limit:
        i = js.find(needle, pos)
        if i < 0:
            break
        hits += 1
        print(f'\n--- {needle} HIT {hits} @ {i} ---')
        print(compact(js[max(0, i-radius):min(len(js), i+len(needle)+radius)]))
        pos = i + len(needle)
    print(f'\nCOUNT {needle} {hits}')


def main():
    html = get(HOME)
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', html, re.I)
    urls = [urllib.parse.urljoin(HOME, s) for s in scripts if '/assets/' in s and s.endswith('.js')]
    for url in urls:
        js = get(url)
        if 'statistics/ranking/subtheme' not in js:
            continue
        print('BUNDLE', url, 'BYTES', len(js))
        # Dq is the wrapper that strips `disabled` then calls O$ -> ranking/subtheme.
        # Its downstream callers expose the exact query object used by the ranking chart.
        for needle in ('Dq(', 'subtheme_ranking', 'territoryCategoryId', 'pageSize', 'sortDirection', 'rankingData'):
            dump(js, needle)


if __name__ == '__main__':
    main()
