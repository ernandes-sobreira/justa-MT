#!/usr/bin/env python3
"""Discover the exact continuous-statistics request used by MapBiomas public SPA.

Read-only diagnostic. It inspects the current public JS bundle and prints short
contexts around continuous statistics, territory IDs, subtheme IDs and async
task polling. No TEA-Brasil data files are written.
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


def compact(s: str, limit: int = 6000) -> str:
    return re.sub(r'\s+', ' ', s).strip()[:limit]


def contexts(js: str, needle: str, radius: int = 3200, limit: int = 20):
    low = js.lower(); target = needle.lower(); pos = 0; out = []
    while len(out) < limit:
        i = low.find(target, pos)
        if i < 0:
            break
        out.append((i, compact(js[max(0, i-radius):min(len(js), i+len(needle)+radius)])))
        pos = i + len(target)
    return out


def main():
    html = get(HOME)
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', html, re.I)
    urls = [urllib.parse.urljoin(HOME, s) for s in scripts if '/assets/' in s and s.endswith('.js')]
    print('JS_FILES', len(urls))

    needles = (
        'statistics/continuous', '/continuous', 'continuous',
        'native_grid_statistics', 'statistics/ranking/subtheme',
        'territoryIds', 'territory_ids', 'territoryCategoryId',
        'subthemeId', 'subtheme_id', 'yearStart', 'yearEnd',
        'taskID', 'taskId', '/tasks', 'task/status', 'taskStatus'
    )

    for url in urls:
        js = get(url)
        if not any(n.lower() in js.lower() for n in needles):
            continue
        print('\n### BUNDLE', url, 'BYTES', len(js))

        # Pull endpoint-like strings/templates that mention the concepts we need.
        found = set()
        for q in ('`', '"', "'"):
            pat = re.escape(q) + r'([^' + re.escape(q) + r'\n\r]{1,900})' + re.escape(q)
            for m in re.finditer(pat, js):
                s = m.group(1)
                low = s.lower()
                if '/' in s and any(k in low for k in ('continuous', 'statistic', 'ranking', 'task', 'territor')):
                    found.add(compact(s, 900))
        print('\n### ROUTE_LITERALS', len(found))
        for s in sorted(found)[:250]:
            print('ROUTE', s)

        for needle in needles:
            hits = contexts(js, needle)
            print(f'\n### {needle}: {len(hits)} context(s)')
            for idx, text in hits:
                print('AT', idx, text)


if __name__ == '__main__':
    main()
