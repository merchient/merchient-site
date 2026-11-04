#!/usr/bin/env python3
"""configurator_selftest: the configurator's band logic and links, and where prices may appear (site 51).

1. The configurator block (between <!--configurator--> and <!--/configurator-->) is the same on index.html and
   pricing.html, and carries the four result cards with content 44's prices: 1-25 $450, 26-100 $750, more than
   100 $1,200, several brands the agency card.
2. configurator.js's band(), mailto() and links() are run in Node against every answer (Q1 x Q2 x Q3, each
   also unanswered): Q1 alone sets the card and its price; Q2 and Q3 never change it; Start my audit is the band's
   checkout URL when links.json has one, else an email to hello@merchient.com whose subject and body carry the
   three answers; the soft call line is the booking link; the agency card books the call and its soft line is the
   email. The card's built href (no JavaScript) is the same as the script's for Q1 alone.
3. No price anywhere on index.html or pricing.html (text, attributes, comments) outside the result cards
   (class cfg-card) and Vera's price line (class vera-price); none in configurator.js.

  python3 tools/configurator_selftest.py      exit 0 when every case holds, else 1 (each failure printed)
"""
import json
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
PAGES = ("index.html", "pricing.html")
JS = ROOT / "configurator.js"
BLOCK = re.compile(r"<!--configurator-->.*?<!--/configurator-->", re.S)
MONEY = re.compile(r"[$£€]\s?\d|\b\d[\d,.]*\s?(?:USD|dollars?)\b", re.I)
ALLOWED = {"cfg-card", "vera-price"}
WANT_PRICE = {"up-to-25": "$450", "26-100": "$750", "over-100": "$1,200",
              "agency": "Each client brand at its own band: $450, $750 or $1,200, by its live ads."}
WANT_SUBJECT = {"up-to-25": "My audit: 1–25 live ads", "26-100": "My audit: 26–100 live ads",
                "over-100": "My audit: More than 100 live ads", "agency": "My audit: I run ads for several brands"}
WANT_START = {"up-to-25": "Start my audit", "26-100": "Start my audit", "over-100": "Start my audit",
              "agency": "Book a 15-minute call"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

fails = []


def check(name, cond):
    if not cond:
        fails.append(name)
        print("FAIL " + name)
    return cond


class Block(HTMLParser):
    """The configurator's parts: the box's data, the radios, and each card's price, button and soft link."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.box, self.radios, self.cards, self.card, self.grab = {}, {}, {}, None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if a.get("id") == "cfg":
            self.box = a
        if tag == "input" and a.get("type") == "radio":
            self.radios.setdefault(a["name"], {})[a["value"]] = a.get("data-say", "")
        if "cfg-card" in cls:
            self.card = self.cards.setdefault(a["data-band"], {"price": "", "start": "", "start_text": "", "soft": ""})
        if self.card is not None:
            if "cfg-price" in cls:
                self.grab = "price"
            elif "cfg-start" in cls:
                self.card["start"], self.grab = a.get("href", ""), "start_text"
            elif tag == "a" and not self.card["soft"] and self.card["start"]:
                self.card["soft"] = a.get("href", "")

    def handle_endtag(self, tag):
        if tag in ("p", "a"):
            self.grab = None
        if tag == "article":
            self.card = None

    def handle_data(self, data):
        if self.card is not None and self.grab:
            self.card[self.grab] += data


class Prices(HTMLParser):
    """Every money amount in a page with whether it sits inside a result card or Vera's price line."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.found = [], []

    def inside(self):
        return any(self.stack)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        ok = bool(ALLOWED & set((a.get("class") or "").split()))
        for k, v in attrs:
            if v and k not in ("href", "src", "class", "id") and MONEY.search(v):
                self.found.append((v.strip(), self.inside() or ok))
        if tag not in VOID:
            self.stack.append(ok)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag not in VOID and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if MONEY.search(data):
            self.found.append((" ".join(data.split()), self.inside()))

    def handle_comment(self, data):
        if MONEY.search(data):
            self.found.append(("<!--" + " ".join(data.split())[:80] + "-->", False))


def leaks(html):
    p = Prices()
    p.feed(html)
    p.close()
    return [s for s, ok in p.found if not ok]


def money(html):
    """Every money amount in a page, allowed or not (the prices-off check wants none at all)."""
    p = Prices()
    p.feed(html)
    p.close()
    return p.found


def node(cases):
    exe = shutil.which("node")
    if not exe:
        check("node is installed (the band logic is run in Node)", False)
        return None
    prog = ("const api=require(process.argv[1]);let s='';process.stdin.on('data',d=>s+=d);"
            "process.stdin.on('end',()=>{const c=JSON.parse(s);process.stdout.write(JSON.stringify("
            "c.map(x=>({band:api.band(x.a),links:api.links(x.a,x.say,x.cfg)}))));});")
    r = subprocess.run([exe, "-e", prog, str(JS)], input=json.dumps(cases), capture_output=True, text=True)
    if not check("node ran configurator.js (%s)" % r.stderr.strip()[:200], r.returncode == 0):
        return None
    return json.loads(r.stdout)


def mail_parts(url):
    m = re.fullmatch(r"mailto:([^?]+)\?subject=([^&]*)&body=(.*)", url or "")
    if not m:
        return None
    return m.group(1), unquote(m.group(2)), unquote(m.group(3)).split("\r\n")


def main():
    pages = {p: (ROOT / p).read_text(encoding="utf-8") for p in PAGES}
    blocks = {p: BLOCK.findall(t) for p, t in pages.items()}
    links = json.loads((ROOT / "config" / "links.json").read_text(encoding="utf-8"))
    if links.get("show_prices", True) is False:
        return main_no_prices(pages, blocks, links)
    for p, b in blocks.items():
        check("%s has one configurator block" % p, len(b) == 1)
    if not all(len(b) == 1 for b in blocks.values()):
        return 1
    check("the block is the same on both pages", blocks["index.html"][0] == blocks["pricing.html"][0])
    check('index.html says "Your price in 20 seconds"', "Your price in 20 seconds" in pages["index.html"])
    check("index.html loads configurator.js once", pages["index.html"].count('src="configurator.js"') == 1)

    b = Block()
    b.feed(blocks["index.html"][0])
    b.close()
    check("four cards, one per Q1 answer", sorted(b.cards) == sorted(WANT_PRICE))
    check("Q1 has the four answers", sorted(b.radios.get("q1", {})) == sorted(WANT_PRICE))
    check("Q2 has three answers", sorted(b.radios.get("q2", {})) == ["1-3", "4-10", "more"])
    check("Q3 has three answers", sorted(b.radios.get("q3", {})) == ["no", "not-sure", "yes"])
    for band, price in WANT_PRICE.items():
        c = b.cards.get(band, {})
        check("%s card price is %s" % (band, price), " ".join(c.get("price", "").split()) == price)
        check("%s card button reads %s" % (band, WANT_START[band]), c.get("start_text", "").strip() == WANT_START[band])
    page_cfg = {"mail": b.box.get("data-mail"), "call": b.box.get("data-call", ""),
                "checkout": {k: b.box.get("data-checkout-" + k, "") for k in ("up-to-25", "26-100", "over-100")}}
    check("the email goes to hello@merchient.com", page_cfg["mail"] == "hello@merchient.com")
    links = json.loads((ROOT / "config" / "links.json").read_text(encoding="utf-8"))
    check("data-call is links.json's call", page_cfg["call"] == links.get("call", ""))
    check("data-checkout-* are links.json's audit links", page_cfg["checkout"] == links.get("audit"))

    say = {q: dict(v) for q, v in b.radios.items()}
    q1s, q2s, q3s = [""] + list(say["q1"]), [""] + list(say["q2"]), [""] + list(say["q3"])
    cfgs = {"page": page_cfg,
            "no links": {"mail": "hello@merchient.com", "call": "", "checkout": {}},
            "one checkout": {"mail": "hello@merchient.com", "call": "https://cal.example/x",
                             "checkout": {"up-to-25": "https://buy.stripe.com/test_a", "26-100": "", "over-100": ""}}}
    cases, meta = [], []
    for cname, cfg in cfgs.items():
        for q1 in q1s:
            for q2 in q2s:
                for q3 in q3s:
                    s = {"value": q1, "q1": say["q1"].get(q1, ""), "q2": say["q2"].get(q2, ""),
                         "q3": say["q3"].get(q3, "")}
                    cases.append({"a": {"q1": q1, "q2": q2, "q3": q3}, "say": s, "cfg": cfg})
                    meta.append((cname, cfg, q1, q2, q3, s))
    out = node(cases)
    if out is None:
        return 1
    n_ok = 0
    for (cname, cfg, q1, q2, q3, s), r in zip(meta, out):
        tag = "%s: q1=%r q2=%r q3=%r" % (cname, q1, q2, q3)
        before = len(fails)
        if not q1:
            check(tag + ": no card before Q1", r["band"] is None and r["links"] is None)
            n_ok += len(fails) == before
            continue
        check(tag + ": the card is Q1's (%s)" % r["band"], r["band"] == q1)
        check(tag + ": the price is %s" % WANT_PRICE[q1], b.cards[r["band"]]["price"].strip() == WANT_PRICE[q1])
        l = r["links"] or {}
        mail_url = l.get("soft") if q1 == "agency" else l.get("start")
        if q1 != "agency" and cfg["checkout"].get(q1):
            check(tag + ": Start my audit is the checkout URL", l.get("start") == cfg["checkout"][q1])
            mail_url = None
        call_link = l.get("start") if q1 == "agency" else l.get("soft")
        if cfg["call"]:
            check(tag + ": the call link is links.json's call", call_link == cfg["call"])
        else:
            check(tag + ": with no call link, the email", (call_link or "").startswith("mailto:hello@merchient.com?"))
        if mail_url:
            parts = mail_parts(mail_url)
            if check(tag + ": the email link parses", parts is not None):
                to, subject, body = parts
                check(tag + ": to hello@merchient.com", to == "hello@merchient.com")
                check(tag + ": subject %r" % subject, subject == WANT_SUBJECT[q1])
                want = ["Website: ", "Live ads: %s." % s["q1"], "Pages: %s." % s["q2"] if s["q2"] else "Pages: ",
                        ("A rejection or restriction in the last 90 days: %s." % s["q3"]) if s["q3"]
                        else "A rejection or restriction in the last 90 days: "]
                check(tag + ": the body carries the three answers %r" % body, body == want)
        n_ok += len(fails) == before
    print("band logic: %d/%d answer cases ok" % (n_ok, len(meta)))

    # the built hrefs (no JavaScript) are the script's for Q1 alone, with the page's links
    for band in WANT_PRICE:
        r = [x for (cname, _, q1, q2, q3, _), x in zip(meta, out) if cname == "page" and q1 == band and not q2
             and not q3][0]["links"]
        check("%s: the built button href is the script's" % band, b.cards[band]["start"] == r["start"])
        check("%s: the built soft href is the script's" % band, b.cards[band]["soft"] == r["soft"])

    # prices: only on the cards and Vera's line
    check("the price check catches a planted price", leaks('<p>From $450.</p><p class="vera-price">$1</p>') == ["From $450."])
    check("the price check catches a price in an attribute", leaks('<meta name="description" content="$750 audit">') != [])
    for p, t in pages.items():
        bad = leaks(t)
        for s in bad:
            print("  price outside the cards and Vera's line, %s: %s" % (p, s))
        check("%s: no price outside the result cards and Vera's line" % p, not bad)
    check("configurator.js carries no price", not MONEY.search(JS.read_text(encoding="utf-8")))
    vera = re.findall(r'<p class="vera-price">([^<]*)</p>', pages["index.html"])
    check("Vera's price line is content 44's", vera == ["$1,500 a month for the founding brands, kept for twelve "
                                                        "months, cancel any time; ten places."])
    check("no $2,500 on either page", not any("2,500" in t for t in pages.values()))

    print("configurator_selftest: %s" % ("ok" if not fails else "%d failure(s)" % len(fails)))
    return 1 if fails else 0


def main_no_prices(pages, blocks, links):
    """show_prices false (4 Nov): the one-ad ask on both pages, no money amount anywhere on them, no configurator.js."""
    for p, b in blocks.items():
        check("%s has one configurator block" % p, len(b) == 1)
    if not all(len(b) == 1 for b in blocks.values()):
        return 1
    check("the block is the same on both pages", blocks["index.html"][0] == blocks["pricing.html"][0])
    blk = blocks["index.html"][0]
    check("the ask block", 'class="cfg cfg-ask"' in blk and "Send one ad" in blk)
    check("the ask emails hello@merchient.com", 'href="mailto:hello@merchient.com?subject=One%20ad%20for%20Vera' in blk)
    check("the call link is links.json's call", (links.get("call") or "") in blk if links.get("call") else "cfg-call" not in blk)
    check('index.html says "Send one ad. See what Vera finds."', "Send one ad. See what Vera finds." in pages["index.html"])
    check("no page loads configurator.js", not any('src="configurator.js"' in t for t in pages.values()))
    for p, t in pages.items():
        found = [s for s, ok in money(t)]
        for s in found:
            print("  price on %s: %s" % (p, s))
        check("%s: no money amount anywhere" % p, not found)
    check("no vera-price line", not any("vera-price" in t for t in pages.values()))
    print("configurator_selftest (prices off): %s" % ("ok" if not fails else "%d failure(s)" % len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
