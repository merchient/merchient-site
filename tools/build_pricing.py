#!/usr/bin/env python3
"""build_pricing: fills pricing.html from config/links.json (site 49, offer v3).

- Each audit button, <a class="btn" data-band="BAND" href="...">Start the audit</a>, gets the band's checkout URL
  from links.json "audit"; while that is empty, it opens an email:
  mailto:hello@merchient.com?subject=Audit%20for%20yourbrand.com with the band in the body.
- <span id="places">N of 10</span> gets "founding_open of founding_total".

  python3 tools/build_pricing.py            write pricing.html if it changed
  python3 tools/build_pricing.py --check    exit 1 if pricing.html is out of date
  python3 tools/build_pricing.py --selftest run the built-in cases
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "pricing.html"
LINKS = ROOT / "config" / "links.json"
BANDS = {"up-to-25": "up to 25", "26-100": "26 to 100", "over-100": "more than 100"}
BUTTON = re.compile(r'(<a class="btn" data-band=")([a-z0-9-]+)(" href=")([^"]*)(">)([^<]*)(</a>)')
PLACES = re.compile(r'(<span id="places">)[^<]*(</span>)')


def mailto(band):
    return ("mailto:hello@merchient.com?subject=Audit%20for%20yourbrand.com&amp;body="
            "Website%3A%20%0D%0ALive%20ads%3A%20" + BANDS[band].replace(" ", "%20") + "%0D%0A")


def load(raw):
    """Validates links.json; returns (links by band, open, total). Raises ValueError."""
    d = json.loads(raw)
    audit = d.get("audit")
    if not isinstance(audit, dict) or set(audit) != set(BANDS):
        raise ValueError("links.json: audit must have exactly the bands " + ", ".join(BANDS))
    for band, url in audit.items():
        if not isinstance(url, str) or (url and not re.fullmatch(r'https://[^\s"<>]+', url)):
            raise ValueError("links.json: audit[%s] must be empty or an https URL" % band)
    n, total = d.get("founding_open"), d.get("founding_total")
    if type(n) is not int or type(total) is not int or not 0 <= n <= total or total < 1:
        raise ValueError("links.json: founding_open must be a whole number from 0 to founding_total")
    return audit, n, total


def fill(page, audit, n, total):
    seen = []

    def button(m):
        band = m.group(2)
        if band not in BANDS:
            raise ValueError("pricing.html: unknown band " + band)
        seen.append(band)
        url = audit[band].replace("&", "&amp;") if audit[band] else mailto(band)
        return m.group(1) + band + m.group(3) + url + m.group(5) + "Start the audit" + m.group(7)

    page = BUTTON.sub(button, page)
    if sorted(seen) != sorted(BANDS):
        raise ValueError("pricing.html: want one audit button per band, found " + (", ".join(seen) or "none"))
    page, k = PLACES.subn(lambda m: "%s%d of %d%s" % (m.group(1), n, total, m.group(2)), page)
    if k != 1:
        raise ValueError('pricing.html: want one <span id="places">, found %d' % k)
    return page


def selftest():
    page = ('<a class="btn" data-band="up-to-25" href="x">Old</a>'
            '<a class="btn" data-band="26-100" href="x">Old</a>'
            '<a class="btn" data-band="over-100" href="x">Old</a>'
            '<p><span id="places">? of ?</span> places open</p>')
    empty = json.dumps({"audit": {b: "" for b in BANDS}, "founding_open": 10, "founding_total": 10})
    one = json.dumps({"audit": {"up-to-25": "https://buy.stripe.com/test_a?x=1&y=2", "26-100": "", "over-100": ""},
                      "founding_open": 7, "founding_total": 10})
    ok = 0
    cases = 0

    def check(name, cond):
        nonlocal ok, cases
        cases += 1
        ok += bool(cond)
        if not cond:
            print("FAIL " + name)

    out = fill(page, *load(empty))
    check("empty links: three mailto buttons", out.count('href="mailto:hello@merchient.com?subject=Audit%20for%20') == 3)
    check("empty links: label", out.count(">Start the audit</a>") == 3)
    check("empty links: places 10 of 10", '<span id="places">10 of 10</span>' in out)
    check("idempotent", fill(out, *load(empty)) == out)
    out = fill(page, *load(one))
    check("one link: the band's checkout URL, escaped", 'href="https://buy.stripe.com/test_a?x=1&amp;y=2"' in out)
    check("one link: the other two stay mailto", out.count('href="mailto:') == 2)
    check("one link: places 7 of 10", '<span id="places">7 of 10</span>' in out)
    for name, bad in [("http rejected", {"audit": {"up-to-25": "http://x", "26-100": "", "over-100": ""},
                                          "founding_open": 1, "founding_total": 10}),
                      ("open above total rejected", {"audit": {b: "" for b in BANDS}, "founding_open": 11,
                                                     "founding_total": 10}),
                      ("missing band rejected", {"audit": {"up-to-25": ""}, "founding_open": 1, "founding_total": 10})]:
        try:
            load(json.dumps(bad))
            check(name, False)
        except ValueError:
            check(name, True)
    try:
        fill(page.replace('data-band="over-100"', 'data-band="26-100"'), *load(empty))
        check("duplicate band rejected", False)
    except ValueError:
        check("duplicate band rejected", True)
    check("the real links.json loads", bool(load(LINKS.read_text(encoding="utf-8"))))
    print("selftest: %d/%d ok" % (ok, cases))
    return 0 if ok == cases else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    try:
        was = PAGE.read_text(encoding="utf-8")
        new = fill(was, *load(LINKS.read_text(encoding="utf-8")))
    except ValueError as e:
        print("build_pricing: " + str(e), file=sys.stderr)
        return 2
    if "--check" in argv:
        print("build_pricing --check: " + ("up to date" if new == was else "out of date: pricing.html"))
        return 0 if new == was else 1
    if new != was:
        PAGE.write_text(new, encoding="utf-8")
    print("build_pricing: pricing.html " + ("written" if new != was else "unchanged"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
