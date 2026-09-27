#!/usr/bin/env python3
"""Discover public MapBiomas SPA routes related to raster/statistics downloads.

Read-only diagnostic: fetches the public JS bundle and prints compact endpoint
contexts only. No project data are changed.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request

HOME = 'https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
HEADERS = {'User-Agent': 'TEA-Brasil/1.0'}
NEEDLES = (
    '/downloads', 'download/', 'downloads/', 'export/', '/export',
    'analysis/download', 'asset/download', 'statistics/export',
    'fileUrl', 'downloadUrl', 'signedUrl'
)


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode('utf-8', errors='replace')


def compact(s: str, limit: int = 2600) -> str:
    return re.sub(r'\s+', ' ', s).strip()[:limit]


def contexts(js: str, needle: str, radius: int = 1600, limit: int = 12):
    pos = 0; out = []
    low = js.lower(); target = needle.lower()
    while len(out) < limit:
        i = low.find(target, pos)
        if i < 0:
            break
        out.append((i, compact(js[max(0, i-radius):min(len(js), i+len(needle)+radius)])))
        pos = i + len(needle)
    return out


def main():
    html = get(HOME)
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', html, re.I)
    urls = [urllib.parse.urljoin(HOME, s) for s in scripts if '/assets/' in s and s.endswith('.js')]
    for url in urls:
        js = get(url)
        if 'download' not in js.lower() and 'export' not in js.lower():
            continue
        print('BUNDLE', url, 'BYTES', len(js))
        for needle in NEEDLES:
            hits = contexts(js, needle)
            if not hits:
                continue
            print(f'\n### {needle} {len(hits)}')
            for idx, text in hits:
                print('AT', idx, text)

        found = set()
        for q in ('`', '"', "'"):
            pat = re.escape(q) + r'([^' + re.escape(q) + r'\n\r]{1,700})' + re.escape(q)
            for m in re.finditer(pat, js):
                s = m.group(1)
                low = s.lower()
                if '/' in s and any(k in low for k in ('download','export','analysis')):
                    if 'api/v1' in low or low.startswith('/') or 'mapbiomas.org' in low:
                        found.add(compact(s, 700))
        print('\n### DOWNLOAD_EXPORT_ROUTES', len(found))
        for s in sorted(found)[:160]:
            print('ROUTE', s)


if __name__ == '__main__':
    main()
