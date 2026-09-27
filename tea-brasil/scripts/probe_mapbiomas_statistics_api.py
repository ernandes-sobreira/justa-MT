#!/usr/bin/env python3
"""Locate the exact task/poll endpoint used by the public MapBiomas SPA.

Read-only diagnostic. Prints only short contexts around taskID/task/status routes.
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


def compact(s: str, limit: int = 2200) -> str:
    return re.sub(r'\s+', ' ', s).strip()[:limit]


def contexts(js: str, needle: str, radius: int = 1300, limit: int = 10):
    pos = 0; out = []
    while len(out) < limit:
        i = js.find(needle, pos)
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
        if 'taskID' not in js and 'taskId' not in js:
            continue
        print('BUNDLE', url, 'BYTES', len(js))
        # Exact async concepts and likely task-result routes.
        for needle in ('taskID', 'taskId', '/tasks', '/task', 'task/status', 'taskStatus', 'statistics/ranking/subtheme'):
            hits = contexts(js, needle)
            print(f'\n### {needle} {len(hits)}')
            for idx, text in hits:
                print('AT', idx, text)

        # Endpoint-like quoted literals containing task/job/status/result.
        found = set()
        for q in ('`', '"', "'"):
            pat = re.escape(q) + r'([^' + re.escape(q) + r'\n\r]{1,500})' + re.escape(q)
            for m in re.finditer(pat, js):
                s = m.group(1)
                low = s.lower()
                if '/' in s and any(k in low for k in ('task', 'job', 'status', 'result')):
                    found.add(compact(s, 500))
        print('\n### ROUTE_LITERALS', len(found))
        for s in sorted(found)[:120]:
            print('ROUTE', s)


if __name__ == '__main__':
    main()
