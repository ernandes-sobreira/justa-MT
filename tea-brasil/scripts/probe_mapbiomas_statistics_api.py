#!/usr/bin/env python3
"""Discover concise read-only statistics routes and query construction in MapBiomas SPA."""
from __future__ import annotations

import re
import urllib.parse
import urllib.request

HOME = 'https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
HEADERS = {'User-Agent': 'TEA-Brasil/1.0'}
KEYWORDS = ('statistics','statistic','ranking','territor','subtheme','historical','summary','native_grid')


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode('utf-8', errors='replace')


def compact(value: str, limit: int = 1600) -> str:
    return re.sub(r'\s+', ' ', value).strip()[:limit]


def contexts(text: str, needle: str, radius: int = 1100, limit: int = 12):
    pos = 0; out = []
    while len(out) < limit:
        idx = text.find(needle, pos)
        if idx < 0:
            break
        out.append(compact(text[max(0, idx-radius):min(len(text), idx+len(needle)+radius)]))
        pos = idx + len(needle)
    return out


def quoted_endpoint_literals(js: str):
    found = set()
    for quote in ('`', '"', "'"):
        pattern = re.escape(quote) + r'([^' + re.escape(quote) + r'\n\r]{1,700})' + re.escape(quote)
        for match in re.finditer(pattern, js):
            value = match.group(1); low = value.lower()
            if any(k in low for k in KEYWORDS) and ('/' in value or 'api' in low):
                found.add(compact(value, 700))
    return sorted(found)


def main():
    html = get(HOME)
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', html, re.I)
    urls = [urllib.parse.urljoin(HOME, s) for s in scripts if '/assets/' in s and s.endswith('.js')]
    print('JS_FILES', len(urls))
    for url in urls:
        js = get(url)
        if 'statistics/ranking/subtheme' not in js:
            continue
        print('\n### BUNDLE', url, 'BYTES', len(js))
        literals = quoted_endpoint_literals(js)
        for value in literals:
            if 'statistics/' in value:
                print('ENDPOINT', value)

        # Minified names around the generated API hooks discovered in the previous probe.
        for needle in ('P$(', 'O$(', 'R$(', 'A$(', 'z$(', 'N$(', 'subtheme_ranking'):
            hits = contexts(js, needle)
            print(f'\n### USAGE {needle} {len(hits)}')
            for i, hit in enumerate(hits, 1):
                print(f'{needle}[{i}]', hit)

        # Print object fragments that visibly construct params with the fields relevant
        # to subtheme stats/ranking.
        field_re = re.compile(r'.{0,900}(?:categoryId|territoryId|subthemeKey|subthemeId|year|band|pageSize).{0,1400}', re.I)
        snippets = []
        for m in field_re.finditer(js):
            s = compact(m.group(0), 2200)
            if ('ranking' in s.lower() or 'subtheme' in s.lower()) and s not in snippets:
                snippets.append(s)
            if len(snippets) >= 50:
                break
        print('\n### PARAMETER_OBJECT_CONTEXTS', len(snippets))
        for i, s in enumerate(snippets, 1):
            print(f'PARAM[{i}]', s)


if __name__ == '__main__':
    main()
