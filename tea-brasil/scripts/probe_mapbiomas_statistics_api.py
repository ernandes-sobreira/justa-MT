#!/usr/bin/env python3
"""Discover concise read-only statistics routes used by the public MapBiomas SPA.

This probe intentionally prints only endpoint-like literals and short contexts.
It writes no project data and exists only to identify the exact public API call
needed for reproducible municipal temperature statistics in TEA-Brasil.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request

HOME = 'https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
HEADERS = {'User-Agent': 'TEA-Brasil/1.0'}
KEYWORDS = (
    'statistics', 'statistic', 'ranking', 'territor', 'subtheme',
    'historical', 'summary', 'native_grid'
)


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode('utf-8', errors='replace')


def compact(value: str, limit: int = 900) -> str:
    value = re.sub(r'\s+', ' ', value).strip()
    return value[:limit]


def short_contexts(text: str, needle: str, radius: int = 550, limit: int = 6):
    low = text.lower(); target = needle.lower(); pos = 0; out = []
    while len(out) < limit:
        idx = low.find(target, pos)
        if idx < 0:
            break
        out.append(compact(text[max(0, idx-radius):min(len(text), idx+len(needle)+radius)], 1300))
        pos = idx + len(target)
    return out


def quoted_endpoint_literals(js: str):
    """Return unique short quoted/template literals related to target API concepts."""
    found = set()
    # Minified SPA uses ordinary strings and template literals. Keep only short,
    # endpoint-like values so logs remain human-auditable.
    for quote in ('`', '"', "'"):
        pattern = re.escape(quote) + r'([^' + re.escape(quote) + r'\n\r]{1,700})' + re.escape(quote)
        for match in re.finditer(pattern, js):
            value = match.group(1)
            low = value.lower()
            if any(k in low for k in KEYWORDS) and ('/' in value or 'api' in low):
                found.add(compact(value, 700))
    return sorted(found)


def call_contexts(js: str):
    """Find compact get/post/fetch/url call fragments near statistics concepts."""
    found = set()
    patterns = [
        r'(?:url\s*:\s*|\.get\(|\.post\(|fetch\()(.{0,900}?(?:statistics|statistic|ranking|territor|subtheme).{0,900}?)(?=\}\)|\)\}|;|,headers:|,params:)',
        r'((?:statistics|ranking|territories|subthemes)[A-Za-z0-9_$]*\s*[:=]\s*.{0,1100})',
    ]
    for pat in patterns:
        for m in re.finditer(pat, js, re.I):
            found.add(compact(m.group(0), 1500))
            if len(found) >= 60:
                return sorted(found)
    return sorted(found)


def main():
    html = get(HOME)
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', html, re.I)
    urls = [urllib.parse.urljoin(HOME, s) for s in scripts if '/assets/' in s and s.endswith('.js')]
    print('JS_FILES', len(urls))

    for url in urls:
        js = get(url)
        if not any(x in js for x in ('subtheme_ranking', 'subtheme_historical', 'subtheme_summary', 'native_grid_statistics')):
            continue

        print('\n### BUNDLE', url, 'BYTES', len(js))

        literals = quoted_endpoint_literals(js)
        print('ENDPOINT_LITERALS', len(literals))
        for value in literals[:120]:
            print('LITERAL', value)

        calls = call_contexts(js)
        print('\nCALL_FRAGMENTS', len(calls))
        for value in calls[:60]:
            print('CALL', value)

        # A few surgical contexts around the exact concepts we need. No huge dump.
        for needle in (
            'subtheme_ranking', 'native_grid_statistics', 'territoryIds',
            'territory_ids', 'subthemeId', 'subtheme_id', 'statistics'
        ):
            hits = short_contexts(js, needle)
            print(f'\nCONTEXT {needle} {len(hits)}')
            for i, value in enumerate(hits, 1):
                print(f'{needle}[{i}]', value)


if __name__ == '__main__':
    main()
