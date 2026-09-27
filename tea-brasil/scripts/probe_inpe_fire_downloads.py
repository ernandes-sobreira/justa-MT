#!/usr/bin/env python3
"""Probe official INPE Programa Queimadas open-data page to locate annual CSV endpoints.
Read-only diagnostic used before implementing the TEA-Brasil fire pipeline.
"""
from __future__ import annotations

import html.parser
import re
import urllib.parse
import urllib.request

PAGE = "https://terrabrasilis.dpi.inpe.br/queimadas/portal/pages/secao_downloads/dados-abertos/"
UA = {"User-Agent": "TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)"}


def get(url: str, timeout: int = 60) -> tuple[bytes, str, str]:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("content-type", ""), r.geturl()


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("href", "src", "data-url", "data-href"):
            if a.get(key):
                self.urls.append((f"{tag}:{key}", a[key]))


def interesting(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("csv", "foco", "anual", "dados_abertos", "download"))


def main():
    raw, ctype, final = get(PAGE)
    text = raw.decode("utf-8", errors="replace")
    print("PAGE", final, ctype, len(raw))

    print("\n=== LINHAS HTML RELEVANTES ===")
    for line in text.splitlines():
        if interesting(line):
            clean = re.sub(r"\s+", " ", line).strip()
            print(clean[:1500])

    p = Links()
    p.feed(text)
    resolved: list[tuple[str, str]] = []
    print("\n=== LINKS/SCRIPTS RELEVANTES ===")
    for kind, url in p.urls:
        full = urllib.parse.urljoin(final, url)
        resolved.append((kind, full))
        if interesting(full):
            print(kind, full)

    print("\n=== INSPEÇÃO DE JAVASCRIPT ===")
    seen = set()
    for kind, url in resolved:
        if "script:src" not in kind or url in seen:
            continue
        seen.add(url)
        try:
            body, jsctype, jsfinal = get(url, timeout=30)
        except Exception as exc:
            print("JS ERROR", url, repr(exc))
            continue
        js = body.decode("utf-8", errors="replace")
        hits = []
        for m in re.finditer(r"(?i)(csv|focos?|anuais?|dados[_-]?abertos|download)", js):
            a = max(0, m.start() - 220)
            b = min(len(js), m.end() + 420)
            snippet = re.sub(r"\s+", " ", js[a:b]).strip()
            if snippet not in hits:
                hits.append(snippet)
            if len(hits) >= 12:
                break
        if hits:
            print("\nJS", jsfinal, jsctype, len(body))
            for h in hits:
                print(h[:1200])


if __name__ == "__main__":
    main()
