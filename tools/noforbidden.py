#!/usr/bin/env python3
"""noforbidden: content 42's forbidden-word list (the register) on the home page and /pricing (site 51).

The list is the REGISTER rule of ~/code/merchient-content/tools/check.py (content 42, read only), copied here: an
exclamation mark, "only", "just", "discount", "cheap", "free", "trial", "no card", approv*, "ban" or "ban-proof",
and "Meta rejected". As in content 44's offer/v4 kind, an exclamation mark inside a curly-quoted line (“...”, a
brand's line quoted as it ran, in the sample) is not ours and is skipped; every other word still counts in quotes.

It reads what nofree.py reads: the visible text, inline scripts, mailto links and the attributes a reader or a
search engine sees (content, alt, title, aria-label, placeholder, value, data-say).

  python3 tools/noforbidden.py              index.html and pricing.html; exit 1 on any hit
  python3 tools/noforbidden.py PAGE ...     the pages named
  python3 tools/noforbidden.py --selftest   the built-in cases
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nofree  # noqa: E402  (the same page reader)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ("index.html", "pricing.html")
nofree.ATTRS = nofree.ATTRS | {"data-say"}
REGISTER = (
    (re.compile(r"(?<!<)!(?!\[)"), "an exclamation mark"),
    (re.compile(r"\bonly\b", re.I), '"only"'),
    (re.compile(r"\bjust\b", re.I), '"just"'),
    (re.compile(r"\bdiscount\w*", re.I), '"discount"'),
    (re.compile(r"\bcheap\w*", re.I), '"cheap"'),
    (re.compile(r"\bfree\b", re.I), '"free"'),
    (re.compile(r"\btrials?\b", re.I), '"trial"'),
    (re.compile(r"\bno[\s-]+card\b", re.I), '"no card"'),
    (re.compile(r"\bapprov\w*", re.I), "approval (never promised)"),
    (re.compile(r"\bban(?:s|ned|[\s-]*proof)?\b", re.I), '"ban" or "ban-proof"'),
    (re.compile(r"\bMeta\s+(?:has\s+|had\s+)?reject\w*|\breject\w*\s+by\s+Meta\b", re.I), '"Meta rejected"'),
)
CURLY = re.compile(r"“[^”\n]*”")


def scan_html(html):
    """[(label, sentence)] for every register word in the page."""
    p = nofree.Pages()
    p.feed(html)
    p.close()
    hits = []
    for text, _quoted in p.chunks:
        quoted = [(m.start(), m.end()) for m in CURLY.finditer(text)]
        for rx, label in REGISTER:
            for m in rx.finditer(text):
                if label == "an exclamation mark" and any(a <= m.start() < b for a, b in quoted):
                    continue
                hits.append((label, nofree.sentence(text, m.start(), m.end())))
    return hits


def selftest():
    cases = [
        ("<p>Your price in 20 seconds!</p>", 1),
        ("<p>“I have so much energy!”</p>", 0),
        ('<p>Your line: "So much energy!"</p>', 1),
        ("<p>Only the Red and Yellow lines.</p>", 1),
        ("<p>It is just one line.</p>", 1),
        ("<p>A founding discount.</p>", 1),
        ("<p>Cheaper than a lawyer.</p>", 1),
        ("<p>The first audit is free.</p>", 1),
        ("<p>Start your trial. No card.</p>", 2),
        ("<p>Vera gets your ads approved.</p>", 1),
        ("<p>Ban-proof copy.</p>", 1),
        ("<p>Meta rejected the ad.</p>", 1),
        ('<meta name="description" content="Only today">', 1),
        ("<p>A rejection names the policy. Banner ads. Justice.</p>", 0),
        ("<!-- just a comment --><p>Sell hard.</p>", 0),
    ]
    bad = 0
    for html, want in cases:
        got = len(scan_html(html))
        if got != want:
            bad += 1
            print("FAIL %r: %d hits (want %d)" % (html, got, want))
    print("selftest: %d/%d ok" % (len(cases) - bad, len(cases)))
    return 1 if bad else 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    names = [a for a in argv if not a.startswith("--")] or list(DEFAULT)
    n = 0
    for name in names:
        for label, s in scan_html((ROOT / name).read_text(encoding="utf-8")):
            n += 1
            print("%s: %s: %s" % (name, label, s))
    print("noforbidden: %d page(s), %d hit(s) (content 42's register)" % (len(names), n))
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
