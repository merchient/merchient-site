#!/usr/bin/env python3
"""build_pricing: checks config/links.json, then hands the pricing page to build.py (site 51).

Until site 50 this filled pricing.html's three audit buttons and the places count. Site 51 made /pricing the
configurator and Vera's screen, the same blocks as the home page, written by build.py from config/links.json
("audit" by band, "call"). This tool now validates links.json and calls build.py.

  python3 tools/build_pricing.py            validate links.json, then python3 build.py
  python3 tools/build_pricing.py --check    validate links.json, then python3 build.py --check
  python3 tools/build_pricing.py --selftest the built-in cases (links.json validation)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINKS = ROOT / "config" / "links.json"
BANDS = {"up-to-25": "up to 25", "26-100": "26 to 100", "over-100": "more than 100"}
HTTPS = re.compile(r'https://[^\s"<>]+')


def load(raw):
    """Validates links.json; returns (links by band, open, total). Raises ValueError."""
    d = json.loads(raw)
    audit = d.get("audit")
    if not isinstance(audit, dict) or set(audit) != set(BANDS):
        raise ValueError("links.json: audit must have exactly the bands " + ", ".join(BANDS))
    for band, url in audit.items():
        if not isinstance(url, str) or (url and not HTTPS.fullmatch(url)):
            raise ValueError("links.json: audit[%s] must be empty or an https URL" % band)
    call = d.get("call", "")
    if not isinstance(call, str) or (call and not HTTPS.fullmatch(call)):
        raise ValueError("links.json: call must be empty or an https URL")
    n, total = d.get("founding_open"), d.get("founding_total")
    if type(n) is not int or type(total) is not int or not 0 <= n <= total or total < 1:
        raise ValueError("links.json: founding_open must be a whole number from 0 to founding_total")
    return audit, n, total


def selftest():
    ok = 0
    cases = 0

    def check(name, cond):
        nonlocal ok, cases
        cases += 1
        ok += bool(cond)
        if not cond:
            print("FAIL " + name)

    empty = {"audit": {b: "" for b in BANDS}, "founding_open": 10, "founding_total": 10}
    check("empty links load", load(json.dumps(empty))[1:] == (10, 10))
    check("a band's https checkout loads",
          bool(load(json.dumps(dict(empty, audit={"up-to-25": "https://buy.stripe.com/x", "26-100": "",
                                                  "over-100": ""})))))
    for name, bad in [("http rejected", dict(empty, audit={"up-to-25": "http://x", "26-100": "", "over-100": ""})),
                      ("open above total rejected", dict(empty, founding_open=11)),
                      ("missing band rejected", dict(empty, audit={"up-to-25": ""})),
                      ("http call rejected", dict(empty, call="http://calendar.example"))]:
        try:
            load(json.dumps(bad))
            check(name, False)
        except ValueError:
            check(name, True)
    check("the real links.json loads", bool(load(LINKS.read_text(encoding="utf-8"))))
    print("selftest: %d/%d ok" % (ok, cases))
    return 0 if ok == cases else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    try:
        load(LINKS.read_text(encoding="utf-8"))
    except ValueError as e:
        print("build_pricing: " + str(e), file=sys.stderr)
        return 2
    print("build_pricing: links.json ok; pricing.html is written by build.py (the configurator block)")
    return subprocess.call([sys.executable, str(ROOT / "build.py")] + (["--check"] if "--check" in argv else []))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
