#!/usr/bin/env python3
"""nofree: no HTML page on the site carries "free" as an offer word (site 49, offer v3).

Walks every .html page under the site root, skipping node_modules, .bak-* copies and the
gitignored folders that are never published (reports/, previews/). Reads the visible text,
inline scripts, mailto links and the attributes a reader or a search engine sees (content,
alt, title, aria-label, placeholder, value).

Allowed (compound and chemical senses): "-free" (sugar-free, gluten-free), "free of",
"free from", "free radical(s)", "caffeine free"; and brand-quoted lines inside <blockquote>
or an element with class "quote".

Every other "free" is printed with its file and sentence; exit 1 if any, else 0.
--allowed lists the kept instances (file and sentence) for the report.
--selftest runs the built-in cases.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"node_modules", "reports", "previews", ".git", ".claude", "gates"}
ATTRS = {"content", "alt", "title", "aria-label", "placeholder", "value", "data-b"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr"}

FREE = re.compile(r"\bfree\b", re.I)
ALLOWED = [
    re.compile(r"-\s*free\b", re.I),                 # sugar-free, gluten-free
    re.compile(r"\bfree\s+(of|from)\b", re.I),       # free of, free from
    re.compile(r"\bfree[\s-]+radicals?\b", re.I),     # free radical(s)
    re.compile(r"\bcaffeine\s+free\b", re.I),         # caffeine free
]


class Pages(HTMLParser):
    """Collects (text, quoted) chunks; quoted is True inside a blockquote or class="quote"."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # (tag, is_quote)
        self.chunks = []

    def quoted(self):
        return any(q for _, q in self.stack)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        is_quote = tag == "blockquote" or "quote" in (a.get("class") or "").split()
        for k, v in attrs:
            if not v:
                continue
            if k in ATTRS or (k == "href" and v.lower().startswith("mailto:")):
                text = v
                if k == "href":
                    from urllib.parse import unquote
                    text = unquote(v)
                self.chunks.append((text, self.quoted() or is_quote))
        if tag not in VOID:
            self.stack.append((tag, is_quote))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1][0] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if data.strip():
            self.chunks.append((data, self.quoted()))


def sentence(text, start, end):
    left = max(text.rfind(c, 0, start) for c in ".!?\n")
    rights = [p for p in (text.find(c, end) for c in ".!?\n") if p != -1]
    right = min(rights) + 1 if rights else len(text)
    return " ".join(text[left + 1:right].split())


def is_allowed(text, m):
    for pat in ALLOWED:
        for a in pat.finditer(text):
            if a.start() <= m.start() < a.end() or a.start() <= m.end() - 1 < a.end():
                return True
    return False


def scan_html(html):
    """Returns (hits, kept): lists of (sentence, why)."""
    p = Pages()
    p.feed(html)
    p.close()
    hits, kept = [], []
    for text, quoted in p.chunks:
        for m in FREE.finditer(text):
            s = sentence(text, m.start(), m.end())
            if quoted:
                kept.append((s, "quote"))
            elif is_allowed(text, m):
                kept.append((s, "sense"))
            else:
                hits.append((s, "offer"))
    return hits, kept


def pages(root):
    for path in sorted(root.rglob("*.html")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if ".bak-" in path.name:
            continue
        yield path, rel


def selftest():
    cases = [
        ("<p>Start free today.</p>", 1, 0),
        ("<p>Free. No card.</p>", 1, 0),
        ("<p>A sugar-free gummy.</p>", 0, 1),
        ("<p>Free of fillers and free from soy.</p>", 0, 2),
        ("<p>It fights free radicals.</p>", 0, 1),
        ("<p>Caffeine free at night.</p>", 0, 1),
        ("<blockquote><p>Try it free for 30 days!</p></blockquote>", 0, 1),
        ('<div class="ad quote">Get one free</div><p>Freedom is not a hit.</p>', 0, 1),
        ('<meta name="description" content="A free scan of your ads.">', 1, 0),
        ('<a href="mailto:x@y.z?subject=Free%20scan">mail</a>', 1, 0),
        ("<script>el.textContent = 'Start free';</script>", 1, 0),
        ('<img src="a.png" alt="gluten free label"><p>freely</p>', 1, 0),
    ]
    bad = 0
    for html, n_hits, n_kept in cases:
        hits, kept = scan_html(html)
        if (len(hits), len(kept)) != (n_hits, n_kept):
            bad += 1
            print(f"FAIL {html!r}: hits {len(hits)} (want {n_hits}), kept {len(kept)} (want {n_kept})")
    print(f"selftest: {len(cases) - bad}/{len(cases)} ok")
    return 1 if bad else 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    show_kept = "--allowed" in argv
    n_pages = n_hits = n_kept = 0
    for path, rel in pages(ROOT):
        n_pages += 1
        hits, kept = scan_html(path.read_text(encoding="utf-8", errors="replace"))
        for s, _ in hits:
            print(f"{rel}: {s}")
        if show_kept:
            for s, why in kept:
                print(f"kept ({why}) {rel}: {s}")
        n_hits += len(hits)
        n_kept += len(kept)
    print(f"nofree: {n_pages} pages, {n_hits} offer hits, {n_kept} kept (compound/chemical sense or quote)")
    return 1 if n_hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
