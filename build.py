#!/usr/bin/env python3
"""Builds the generated parts of merchient.com.

Run it from this folder after changing FOUNDING_PLACES_LEFT or anything in data/:

    python3 build.py            writes the pages
    python3 build.py --check    changes nothing, and fails if a page is out of date

It writes four things and changes nothing else:
1. The number of founding places left, into each <strong class="places-left">
   on the site's pages.
2. The ingredient guides: ingredients/index.html, and ingredients/<slug>.html for
   each guide in data/ (the guides' JSON, copied unchanged from Merchient's library).
3. sitemap.xml: the pages it already lists stay, and the ingredient guides follow.
4. The ad index: index/index.html (the list) and index/<year>-<month>/index.html for each data/index-<year>-<month>.json,
   which reports/tools/make_index39.py writes from the sweep files. The pages' URLs are added to sitemap.xml by hand.

The terms state only the total of 3 founding places: a count that changes would
change the contract each time a place goes.

The guides' words are the library's, unchanged. Where a guide points at a part of
the library that no page shows, such as "(see notes)", the build says so; fix it
in the library, copy the JSON into data/ again and run the build.
"""

# Founding places (site 49: ten) come from config/links.json, "founding_open" of "founding_total". When a
# founding brand signs, lower founding_open by one, run python3 build.py and python3 tools/build_pricing.py,
# then commit and push.

# The scan box in the home page's hero (the preview). False: the box opens the "Preview request"
# email, and the home page runs no JavaScript. True: the box posts the website and work
# email as JSON to SCAN_API_URL with scan.js, shows the service's answer, and falls
# back to that email if the service does not answer (and without JavaScript). Switching
# it on also loosens the home page's content security policy (script-src 'self',
# connect-src for the service) and means the privacy and security pages must say where
# the scan data goes. Then run build.py.
# (Chrome logs one console notice on https: a form that targets "mailto:" is not a
# secure endpoint. It changes nothing for the visitor.)
SCAN_API_ON = True       # site 30 (27 Oct 2026): the app's POST /api/scan is live (app paste 21)
SCAN_API_URL = 'https://api.merchient.com/api/scan'

import datetime
import html
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(ROOT, 'config', 'links.json'), encoding='utf-8') as _f:
    _links = json.load(_f)
FOUNDING_PLACES = _links.get('founding_total')
FOUNDING_PLACES_LEFT = _links.get('founding_open')
SITE = 'https://merchient.com/'
SCAN = ('mailto:hello@merchient.com?subject=Preview%20request&amp;'
        'body=Brand%20name%3A%20%0D%0AWebsite%3A%20%0D%0A')
# Site 51: the booking link (the 15-minute call) and the audit's checkout links live in config/links.json ("call",
# "audit"); the configurator block carries them into the home page and /pricing.
BOOK = _links.get('call') or ''
AUDIT_LINKS = _links.get('audit') or {}
# 4 Nov 20:30 (Varma): no price on the site for now. show_prices false in config/links.json turns the configurator
# into the one-ad ask on both pages and drops Vera's price line; true puts them back (python3 build.py).
PRICES_SHOWN = bool(_links.get('show_prices', True))
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December')
GUIDE_KEYS = {'slug', 'ingredient', 'also_called', 'title', 'summary', 'supported_wordings',
              'wordings_to_avoid', 'evidence_strengths', 'reasons_to_avoid', 'sources',
              'disclaimer', 'date_reviewed'}
GUIDE_OPTIONAL = {'evidence_gap', 'review_flag'}
SUPPORTED_KEYS = {'wording', 'evidence_strength', 'why', 'daily_dose', 'dose_details', 'form', 'sources'}
SUPPORTED_OPTIONAL = {'dose_warning', 'where_sources_disagree', 'meta_ads'}
AVOID_KEYS = {'wording', 'reason', 'why', 'meta_ads_only'}
PLACES = re.compile(r'(<strong class="places-left">)[^<]*(</strong>)')
NOT_ADVICE = 'Not legal advice. '
LINKED_BELOW = ', from the sources linked below'
TITLE = re.compile(r'What can you say about (.+) in your ads and on your site\?')
POINTER = re.compile(r'\bsee (?:notes|details|[a-z]+_[a-z_]+)\b|\bkept as a note\b')

HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; font-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Merchient">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="https://merchient.com/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Merchient. Keep the hook. Lose the claim.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="https://merchient.com/og-image.png">
<meta name="twitter:image:alt" content="Merchient. Keep the hook. Lose the claim.">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f2eee3" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121210" media="(prefers-color-scheme: dark)">
<link rel="icon" href="../favicon.ico" sizes="32x32">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="../apple-touch-icon.png">
<link rel="preload" href="../fonts/archivo-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="../styles.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="../">Merchient</a>
    <nav class="site-nav" aria-label="Main">
      <a href="../#how-it-works">How it works</a>
      <a href="../pricing">Price</a>
      <a href="../agencies">Agencies</a>
      <a href="../#faq">FAQ</a>
      <a href="../rescue">Send a rejected ad</a>
      <a class="btn btn-small" href="../#scan">Read my ads</a>
    </nav>
  </div>
</header>

<main id="main">
'''

TOP = '''
  <section class="sample-top guide-top">
    <div class="wrap">
      <p class="kicker"><a href="./">Merchient’s ingredient library</a></p>
      <h1>{h1}</h1>
      <p class="lede">{summary}</p>
{also}      <p class="updated">Reviewed <time datetime="{iso}">{date}</time></p>
      <p class="warnings"><b>Not legal advice.</b> {disclaimer}</p>
{flag}    </div>
  </section>
'''

CARD = '''        <article class="panel item">
          <p class="item-head">{head}<span class="item-no">Wording {n}</span></p>
          <p class="panel-title">Claims Facts</p>
          <div class="bar-xl" aria-hidden="true"></div>
          <p class="facts-line">\u201c{wording}\u201d</p>
          <div class="bar-m" aria-hidden="true"></div>
          <table class="item-table">
            <tbody>
{rows}
            </tbody>
          </table>
        </article>'''

GAP = '''      <div class="panel gap">
        <p class="panel-title">Claims Facts</p>
        <div class="bar-xl" aria-hidden="true"></div>
        <p class="facts-line">No supported wording yet.</p>
        <div class="bar-m" aria-hidden="true"></div>
        <p>{gap}</p>
      </div>
'''

SUPPORTED = '''
  <section class="section" id="supported">
    <div class="wrap">
      <p class="kicker">Supported wordings</p>
      <h2>What you can say.</h2>
{body}    </div>
  </section>
'''

AVOID = '''
  <section class="section" id="avoid">
    <div class="wrap">
      <p class="kicker">Wordings to avoid</p>
      <h2>What to leave out.</h2>
      <article class="facts panel avoid">
        <p class="panel-title">Claims Facts</p>
        <p class="meta">Ingredient: {ingredient}</p>
        <div class="bar-xl" aria-hidden="true"></div>
        <table>
          <thead><tr><th scope="col">Wording to avoid</th><th scope="col">Reason</th></tr></thead>
          <tbody>
{rows}
          </tbody>
        </table>
        <div class="hair" aria-hidden="true"></div>
        <p class="facts-fn">{notes}</p>
      </article>
    </div>
  </section>
'''

SOURCES = '''
  <section class="section" id="sources">
    <div class="wrap">
      <p class="kicker">Sources</p>
      <h2>Where this comes from.</h2>
{items}
      <p class="more-link"><a class="sample-link" href="./">All ingredient guides</a></p>
    </div>
  </section>
'''

INDEX = '''
  <section class="sample-top guide-top">
    <div class="wrap">
      <p class="kicker">Merchient’s ingredient library</p>
      <h1>What can you say about each ingredient?</h1>
      <p class="lede">For each of {n} supplement ingredients: the wordings its sources support, at a daily dose and with how strong the evidence is; the wordings to avoid, with the ones to keep out of Meta ads marked; and a link to every source the guide cites.</p>
      <p class="updated">Updated <time datetime="{iso}">{date}</time></p>
      <p class="warnings"><b>Not legal advice.</b> {disclaimer}</p>
    </div>
  </section>

  <section class="section" id="guides">
    <div class="wrap">
      <div class="panel guide-index">
        <p class="panel-title">Ingredients</p>
        <p class="meta">{n} guides \u00b7 {with_wording} with supported wordings \u00b7 reviewed {reviewed}</p>
        <div class="bar-xl" aria-hidden="true"></div>
        <ul class="guide-list">
{items}
        </ul>
      </div>
    </div>
  </section>
'''

FINAL = '''
  <section class="final">
    <div class="wrap">
      <h2>Read your own ads the same way.</h2>
      <p>Put your website in the preview on the home page. Vera, Merchient’s AI employee, shows how many lines carry a risk, and emails you one line in full once you confirm your work email. The rest is in the 48-Hour Claims Audit.</p>
      <div class="cta-row">
        <a class="btn" href="../#scan">Read my ads</a>
        <a class="secondary-link" href="../pricing#audit">The 48-Hour Claims Audit</a>
      </div>
      <p class="alt">Or write to hello@merchient.com</p>
    </div>
  </section>

</main>

<footer class="site-footer">
  <div class="wrap footer-inner">
    <p>Merchient is a trade name of Orbline LLC, 30 N Gould St, STE R, Sheridan, WY 82801, USA.</p>
    <p><a href="mailto:hello@merchient.com">hello@merchient.com</a></p>
    <p class="footer-more"><a href="../rescue">Send a rejected ad</a> · <a href="../claims-watch">Claims Watch</a> · <a href="../pricing">Price</a> · <a href="../agencies">Agencies</a> · <a href="../founder">Why I built this</a> · <a href="../method">How Vera decides</a> · <a href="../cases/">Case files</a></p>
    <nav class="footer-links" aria-label="Legal">
      <a href="../privacy.html">Privacy</a>
      <a href="../terms.html">Terms</a>
      <a href="../data-deletion.html">Data deletion</a>
      <a href="../security.html">Security</a>
    </nav>
  </div>
</footer>
</body>
</html>
'''


CSP_BASE = "default-src 'none'; style-src 'self'; font-src 'self'; img-src 'self'; base-uri 'none'; "
CSP_META = re.compile(r'<meta http-equiv="Content-Security-Policy" content="[^"]*">')
SCAN_BLOCK = re.compile(r'<!--scan-->.*?<!--/scan-->', re.S)
SCAN_OFF = '''<!--scan-->
          <form class="scan" action="mailto:hello@merchient.com" method="get">
            <input type="hidden" name="subject" value="Preview&nbsp;request">
            <label for="scan-website">Your website</label>
            <input id="scan-website" name="body" type="text" inputmode="url" autocomplete="url" placeholder="yourbrand.com" required>
            <button class="btn" type="submit">Read my ads</button>
            <p class="scan-note">Your email app opens with the request ready to send.</p>
          </form>
          <!--/scan-->'''
SCAN_ON = '''<!--scan-->
          <form class="scan" action="mailto:hello@merchient.com" method="get" data-api="%s">
            <input type="hidden" name="subject" value="Preview&nbsp;request">
            <label for="scan-website">Your website</label>
            <input id="scan-website" name="body" type="text" inputmode="url" autocomplete="url" placeholder="yourbrand.com" required>
            <label for="scan-email">Your work email</label>
            <input id="scan-email" name="email" type="email" autocomplete="email" required>
            <button class="btn" type="submit">Read my ads</button>
            <p class="scan-note">We send your website and work email to Merchient\u2019s scan service (api.merchient.com), which emails you a link to confirm. If it does not answer, your email app opens with the request ready.</p>
            <p class="scan-msg" role="status"></p>
          </form>
          <script src="scan.js"></script>
          <!--/scan-->'''
SCAN_JS = '''// The scan box on the home page. Without this script the form opens the "Preview request" email. With it, the
// box posts the website and work email as JSON to Merchient's scan service and shows the service's answer, word for
// word. When the service does not answer, the email opens instead, with the answers filled in.
(function () {
  var form = document.querySelector('form.scan[data-api]');
  if (!form || !window.fetch || !window.AbortController) { return; }
  var msg = form.querySelector('.scan-msg');
  var button = form.querySelector('button[type="submit"]');
  var website = document.getElementById('scan-website');
  var email = document.getElementById('scan-email');

  function mail(note) {
    msg.textContent = note;
    window.location.href = 'mailto:hello@merchient.com?subject=Preview%20request&body=' +
      encodeURIComponent('Website: ' + website.value.trim() + '\\r\\nWork email: ' + email.value.trim() + '\\r\\n');
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 10000);
    button.disabled = true;
    msg.textContent = 'Sending\u2026';
    fetch(form.getAttribute('data-api'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ website: website.value.trim(), email: email.value.trim() }),
      credentials: 'omit',
      signal: controller.signal
    }).then(function (r) {
      clearTimeout(timer);
      return r.json().catch(function () { return {}; }).then(function (b) { return { status: r.status, ok: r.ok, body: b }; });
    }).then(function (x) {
      button.disabled = false;
      var error = x.body.error || {};
      if (x.ok) {
        msg.textContent = x.body.message || 'Check your inbox: open the link we sent to start the scan.';
      } else if (x.status < 500 && error.message) {
        msg.textContent = error.message;
      } else {
        throw new Error('status ' + x.status);
      }
    }).catch(function () {
      clearTimeout(timer);
      button.disabled = false;
      mail('The scan service did not answer, so your email app is opening instead.');
    });
  });
}());
'''


def scan_apply(page):
    """Writes the scan box, and the home page's content security policy, for SCAN_API_ON."""
    # form-action 'self' (site 47): the closing input on the home page is a GET form back to the page (/?site=...).
    csp = CSP_BASE + ("script-src 'self'; connect-src %s; form-action 'self' mailto:" % SCAN_API_URL.rsplit('/', 2)[0]
                      if SCAN_API_ON else 'form-action mailto:')
    box = SCAN_ON % html.escape(SCAN_API_URL, quote=True) if SCAN_API_ON else SCAN_OFF
    page, n = SCAN_BLOCK.subn(lambda m: box, page)
    page, c = CSP_META.subn(lambda m: '<meta http-equiv="Content-Security-Policy" content="%s">' % csp, page)
    if n != 1 or c != 1:
        fail('index.html: the scan box markers or the content security policy meta are missing')
    return page


SWEEPS_BLOCK = re.compile(r'<!--sweeps-->.*?<!--/sweeps-->', re.S)


def sweeps_apply(page):
    """Writes the proof line under the home page's hero from data/sweeps.json (kept by the content lane): the ads read
    this week and how many carried a line an authority can act on. Counts only, never a percentage or a brand."""
    with open(os.path.join(ROOT, 'data', 'sweeps.json'), encoding='utf-8') as f:
        s = json.load(f)
    n, x, h = s.get('ads_read'), s.get('flagged'), s.get('high')
    if any(type(v) is not int for v in (n, x, h)) or not 0 <= h <= x <= n or not n:
        fail('data/sweeps.json: ads_read, flagged and high must be whole numbers, high <= flagged <= ads_read')
    line = ('<!--sweeps--><p class="proof-line">%d supplement ads in Meta’s public ad library read in the past '
            'week; %d carried a line Vera flagged under Meta’s health rules or FTC or FDA guidance, %d of them '
            'high risk.</p><!--/sweeps-->' % (n, x, h))
    page, k = SWEEPS_BLOCK.subn(lambda m: line, page)
    if k != 1:
        fail('index.html: the sweeps markers are missing')
    return page


# Site 52 (5 Nov 2026): the home page's one proof line is counted at build time from the sales lane's sweep files
# (read only), so it cannot go stale by hand. A file counts when its date, from its name (YYYY-MM-DD[-suffix]-lines.tsv),
# is within PROOF_DAYS of the build date; .bak-* files do not match the name. The rule is one row per line: the header
# is the line that starts "domain<TAB>page<TAB>library_id" and must be the first line; blank lines are not rows; every
# other line must have PROOF_COLS tab-separated fields, or the build stops (a file with another layout is not counted
# wrong, it is refused). A row counts when its tier is Red, Yellow or Green; a row with no tier (fit "no": read, not a
# supplement ad) is left out because the sentence says "graded"; any other tier stops the build. A stale or thin week
# fails the build: a stale number never ships.
PROOF_DIR = os.path.expanduser('~/code/merchient-sales/handoff/adlibrary')
PROOF_DAYS = 7      # a file is read when it is no more than this many days older than the build date
PROOF_MIN_ROWS = 100
PROOF_COLS = 12
PROOF_HEADER = 'domain\tpage\tlibrary_id\t'
PROOF_TIER_COL = 8   # the "tier" column; a row counts when it is graded Red, Yellow or Green (the sentence says "graded")
PROOF_TIERS = ('Red', 'Yellow', 'Green')
PROOF_FILE = re.compile(r'^(\d{4})-(\d{2})-(\d{2})(?:-[A-Za-z0-9]+)*-lines\.tsv$')
PROOF_BLOCK = re.compile(r'<!--proof-->.*?<!--/proof-->', re.S)
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November',
          'December']


def proof_dates(first, last):
    """'2 to 4 November', '30 October to 4 November', '4 November' (a year is added only when the two years differ)."""
    def one(d, month=True, year=False):
        return '%d%s%s' % (d.day, ' ' + MONTHS[d.month - 1] if month else '', ' %d' % d.year if year else '')
    if first == last:
        return one(first)
    if first.year != last.year:
        return '%s to %s' % (one(first, year=True), one(last, year=True))
    return '%s to %s' % (one(first, month=first.month != last.month), one(last))


def proof_rows(today, directory=None):
    """Reads the sweep files; returns (files, first date, last date) where files is [(name, rows)] in date order."""
    directory = directory or PROOF_DIR
    if not os.path.isdir(directory):
        fail('the sweep folder is missing: ' + directory)
    files = []
    for name in sorted(os.listdir(directory)):
        m = PROOF_FILE.match(name)
        if not m:
            continue
        try:
            d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            fail('the sweep file name has no real date: ' + name)
        if not 0 <= (today - d).days <= PROOF_DAYS:
            continue
        with open(os.path.join(directory, name), encoding='utf-8', newline='') as f:
            lines = f.read().split('\n')
        rows = skipped = 0
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            if i == 0:
                if not line.startswith(PROOF_HEADER):
                    fail('%s: the first line is not the header row (domain, page, library_id, ...)' % name)
                continue
            if line.startswith(PROOF_HEADER) or line.count('\t') + 1 != PROOF_COLS:
                fail('%s: line %d is not one row of %d fields' % (name, i + 1, PROOF_COLS))
            tier = line.split('\t')[PROOF_TIER_COL]
            if tier in PROOF_TIERS:
                rows += 1
            elif tier == '':
                skipped += 1    # read but not a supplement ad (fit "no"), so not graded: the sentence says "graded"
            else:
                fail('%s: line %d has the tier "%s", not Red, Yellow or Green' % (name, i + 1, tier))
        files.append((name, d, rows, skipped))
    if not files:
        # this is also the "newest file is older than seven days" rule: the newest file is out of the window
        fail('no sweep file in %s is dated within %d days of %s (the newest is too old)' % (directory, PROOF_DAYS, today.isoformat()))
    newest = max(f[1] for f in files)
    total = sum(f[2] for f in files)
    if total < PROOF_MIN_ROWS:
        fail('only %d graded sweep rows in the last %d days (the proof line needs %d)' % (total, PROOF_DAYS, PROOF_MIN_ROWS))
    return [(f[0], f[2], f[3]) for f in files], min(f[1] for f in files), newest


def proof_apply(page, today=None, directory=None):
    """Writes the home page's proof line between <!--proof--> and <!--/proof-->. Counts only: no percentage, no brand."""
    files, first, last = proof_rows(today or datetime.date.today(), directory)
    total = sum(f[1] for f in files)
    line = ('<!--proof--><p class="proof-line">This week, %d lines from supplement ads running on Meta, read and graded '
            'Red, Yellow or Green (our Ad Library sweeps, %s).</p><!--/proof-->' % (total, proof_dates(first, last)))
    page, k = PROOF_BLOCK.subn(lambda m: line, page)
    if k != 1:
        fail('index.html: the proof markers (<!--proof--> ... <!--/proof-->) are missing')
    return page


FOOTER_MORE = re.compile(r'(<p class="footer-more">)(.*?)(</p>)', re.S)


def founder_link(page, rel):
    """Adds "Why I built this", "How Vera decides" and "Case files" (site 46) to the footer line of a hand-written
    page. The generated pages carry them in their templates; method.html and cases/ are written by tools/build_method.py."""
    prefix = '/' if rel == '404.html' else '../' * rel.count(os.sep)
    links = (('founder"', ' · <a href="%sfounder">Why I built this</a>'), ('method"', ' · <a href="%smethod">How Vera decides</a>'),
             ('cases/"', ' · <a href="%scases/">Case files</a>'))

    def add(m):
        line = m.group(2)
        for mark, link in links:
            if mark not in line:
                line += link % prefix
        return m.group(1) + line + m.group(3)
    return FOOTER_MORE.sub(add, page)


# The home page v4 (site 51, 4 Nov 2026; ~/code/merchient-ops/docs/site-v4-brief.md). Three blocks are written here so
# they stay true and stay the same on both pages: the configurator (index.html and pricing.html, <!--configurator-->),
# Vera's screen (both, <!--vera-->) and the home page's Winning Lines (index.html, <!--winning-->). Every word is content
# 44's (~/code/merchient-content/offer/v4/home.md); every price is offer-v3 section 0's. The prices appear on the
# result cards and in Vera's price line alone; tools/configurator_selftest.py fails on a price anywhere else.
CFG_QUESTIONS = (
    ('q1', 'How many ads are live right now?',
     (('up-to-25', '1–25'), ('26-100', '26–100'), ('over-100', 'More than 100'),
      ('agency', 'I run ads for several brands'))),
    ('q2', 'How many pages do they send people to?', (('1-3', '1–3'), ('4-10', '4–10'), ('more', 'More'))),
    ('q3', 'Has an ad been rejected or the account restricted in the last 90 days?',
     (('yes', 'Yes'), ('no', 'No'), ('not-sure', 'Not sure'))),
)
CFG_BANDS = ('up-to-25', '26-100', 'over-100')
CFG_Q3 = (
    ('yes', 'Then start with the lines still running: the audit names each one at risk, and the rule it trips, '
            'within 48 hours.'),
    ('no', 'Then this is the quiet time to look, before a review picks the line for you.'),
    ('not-sure', 'Either way, the audit reads every live ad and names each line at risk with its rule.'),
)
CFG_IN = (
    'Every live ad and page, read in 48 hours.',
    'The Red and Yellow lines, one line each: the line, the rule it trips in plain words, and a safer line that keeps '
    'the sell.',
    'The lines that run longest in your category, with their ages, and your Claim Gap.',
    'Read by Vera, checked by a person. A numbered case file with your name on it.',
)
CFG_CARDS = (
    {'band': 'up-to-25', 'name': 'The 48-Hour Claims Audit', 'price': '$450',
     'for': 'Up to 25 live ads, and the pages they send people to.', 'in': CFG_IN,
     'refund': 'If we find nothing Red or Yellow, the audit is refunded in full, and the Winning Lines are yours to keep.',
     'start': 'Start my audit', 'soft': ('Prefer to talk first?', 'A 15-minute call, not a pitch.', '')},
    {'band': '26-100', 'name': 'The 48-Hour Claims Audit', 'price': '$750',
     'for': '26 to 100 live ads, and the pages they send people to.', 'in': CFG_IN,
     'refund': 'If we find nothing Red or Yellow, the audit is refunded in full, and the Winning Lines are yours to keep.',
     'start': 'Start my audit', 'soft': ('Prefer to talk first?', 'A 15-minute call, not a pitch.', '')},
    {'band': 'over-100', 'name': 'The 48-Hour Claims Audit', 'price': '$1,200',
     'for': 'More than 100 live ads, and the pages they send people to.', 'in': CFG_IN,
     'refund': 'If we find nothing Red or Yellow, the audit is refunded in full, and the Winning Lines are yours to keep.',
     'start': 'Start my audit', 'soft': ('Prefer to talk first?', 'A 15-minute call, not a pitch.', '')},
    {'band': 'agency', 'name': 'The 48-Hour Claims Audit, per client brand',
     'price': 'Each client brand at its own band: $450, $750 or $1,200, by its live ads.',
     'for': 'Vera for your first three client brands at the founding price.',
     'in': ('For each brand: every live ad and page, read in 48 hours, and a numbered case file with the brand’s name '
            'on it.',
            'The Red and Yellow lines, one line each, with the rule in plain words and a safer line that keeps the sell.'),
     'refund': 'If we find nothing Red or Yellow for a brand, that brand’s audit is refunded in full.',
     'start': 'Book a 15-minute call',
     'soft': ('Rather write?', 'Send your client list', ', and a person replies within the business day.')},
)
CFG_FAIR = 'The price depends on how much we read, and nothing else. It never goes up after you book.'
CFG_MAIL = 'hello@merchient.com'
CONFIGURATOR_BLOCK = re.compile(r'<!--configurator-->.*?<!--/configurator-->', re.S)
VERA_BLOCK = re.compile(r'<!--vera-->.*?<!--/vera-->', re.S)
WINNING_BLOCK = re.compile(r'<!--winning-->.*?<!--/winning-->', re.S)
HOME_WL_SLUG = 'gut'
HOME_WL_ROWS = 5


def cfg_mailto(say):
    """The email Start my audit opens while the band has no checkout URL. configurator.js builds the same one in the
    browser (the selftest compares them): content 44's subject "My audit: {band}" and its body, one answer a line, with
    a Website line (the old pricing email's) for the buyer to fill. say: the answers' words; '' when not answered."""
    q = lambda s: urllib.parse.quote(s, safe="-_.!~*'()")
    band = say['q1'] if say.get('value') == 'agency' else say['q1'] + ' live ads'
    line = lambda k, v: k + v + '.' if v else k
    body = '\r\n'.join(['Website: ', line('Live ads: ', say['q1']), line('Pages: ', say['q2']),
                        line('A rejection or restriction in the last 90 days: ', say['q3'])])
    return 'mailto:%s?subject=%s&body=%s' % (CFG_MAIL, q('My audit: ' + band), q(body))


H2_PRICE = '<h2>Your price in 20 seconds.</h2>'
H2_ASK = '<h2>Send one ad. See what Vera finds.</h2>'
ASK_SUBJECT = 'One ad for Vera'


def ask_html():
    """The block when prices are off: one ad in, the read back within a US business day, no price anywhere."""
    q = lambda t: urllib.parse.quote(t, safe="-_.!~*'()")
    mail = 'mailto:%s?subject=%s&body=%s' % (CFG_MAIL, q(ASK_SUBJECT),
                                             q('Website: \r\nThe ad (a link, or its text): \r\n'))
    call = ('  <p class="cfg-call">Prefer to talk first? <a href="%s">A 20-minute call</a>.</p>' % html.escape(BOOK, quote=True)
            if BOOK else '')
    return '\n'.join(x for x in [
        '<!--configurator-->',
        '<div class="cfg cfg-ask" id="cfg" data-mail="%s" data-call="%s">' % (CFG_MAIL, html.escape(BOOK, quote=True)),
        '  <p class="section-lede">Send one ad: the one you would least like to lose, or the one that was pulled. '
        'Within one US business day you get back what Vera found: each line at risk, the rule it trips in plain words, '
        'and a safer line that keeps the sell.</p>',
        '  <a class="btn cfg-start" href="%s">Send one ad</a>' % html.escape(mail, quote=True),
        call,
        '</div>',
        '<!--/configurator-->'] if x)


def configurator_html():
    if not PRICES_SHOWN:
        return ask_html()
    for b in CFG_BANDS:
        url = AUDIT_LINKS.get(b, '')
        if not isinstance(url, str) or (url and not re.fullmatch(r'https://[^\s"<>]+', url)):
            fail('config/links.json: audit[%s] must be empty or an https URL' % b)
    if BOOK and not re.fullmatch(r'https://[^\s"<>]+', BOOK):
        fail('config/links.json: call must be empty or an https URL')
    say1 = dict(CFG_QUESTIONS[0][2])
    data = ''.join(' data-checkout-%s="%s"' % (b, html.escape(AUDIT_LINKS.get(b, ''), quote=True)) for b in CFG_BANDS)
    out = ['<!--configurator-->',
           '<div class="cfg" id="cfg" data-mail="%s" data-call="%s"%s>' % (CFG_MAIL, html.escape(BOOK, quote=True), data),
           '  <div class="cfg-qs">']
    for name, legend, options in CFG_QUESTIONS:
        out.append('    <fieldset class="cfg-q"><legend>%s</legend><div class="cfg-opts">' % text(legend))
        for value, label in options:
            out.append('      <label class="cfg-opt"><input type="radio" name="%s" value="%s" data-say="%s"> %s</label>'
                       % (name, value, attr(label), text(label)))
        out.append('    </div></fieldset>')
    out += ['  </div>', '  <div class="cfg-result" aria-live="polite">']
    for c in CFG_CARDS:
        b = c['band']
        mail = cfg_mailto({'value': b, 'q1': say1[b], 'q2': '', 'q3': ''})
        start = (BOOK or mail) if b == 'agency' else (AUDIT_LINKS.get(b) or mail)
        soft = mail if b == 'agency' else (BOOK or mail)
        price_class = 'cfg-price cfg-price-s' if b == 'agency' else 'cfg-price'
        out += ['    <article class="panel cfg-card" data-band="%s">' % b,
                '      <p class="cfg-name">%s</p>' % text(c['name']),
                '      <div class="bar-xl" aria-hidden="true"></div>',
                '      <p class="%s">%s</p>' % (price_class, text(c['price'])),
                '      <p class="cfg-for">%s</p>' % text(c['for'])]
        out += ['      <p class="cfg-q3" data-q3="%s" hidden>%s</p>' % (k, text(v)) for k, v in CFG_Q3]
        out.append('      <ul class="cfg-in">%s</ul>' % ''.join('<li>%s</li>' % text(x) for x in c['in']))
        out.append('      <p class="cfg-refund">%s</p>' % text(c['refund']))
        out.append('      <a class="btn cfg-start" href="%s">%s</a>' % (html.escape(start, quote=True), text(c['start'])))
        out.append('      <p class="cfg-call">%s <a href="%s">%s</a>%s</p>' % (
            text(c['soft'][0]), html.escape(soft, quote=True), text(c['soft'][1]), text(c['soft'][2])))
        out.append('    </article>')
    out += ['    <p class="cfg-fair">%s</p>' % text(CFG_FAIR), '  </div>', '</div>',
            '<script src="configurator.js"></script>', '<!--/configurator-->']
    return '\n'.join(out)


VERA_HTML_PRICED = '''<!--vera-->
<h2>After the audit: Vera, every day.</h2>
<ol class="use">
  <li><h3>Before it runs</h3><p>Every new ad and page read against the three rule books, with a safer line for each flag.</p></li>
  <li><h3>While it runs</h3><p>The weekly watch on your live ads, and Winning Lines and your Claim Gap every month.</p></li>
  <li><h3>When something slips</h3><p>A pulled ad or a restricted account on a claims reason: the rewrite and the appeal letter, the same day.</p></li>
</ol>
<ul class="checks guard">
  <li>Vera never edits an ad or touches your account. She reads; you decide.</li>
  <li>Public ads and pages: no login, no access to give.</li>
  <li>A person checks what Vera writes before you see it.</li>
  <li>You decide what changes, and Meta makes the final call on every ad.</li>
</ul>
<p class="vera-price">$1,500 a month for the founding brands, kept for twelve months, cancel any time; ten places.</p>
<p class="section-lede">Every brand starts with the audit.</p>
<p class="more-link"><a class="sample-link" href="method">How Vera decides</a></p>
<!--/vera-->'''
VERA_PRICE_LINE = '<p class="vera-price">$1,500 a month for the founding brands, kept for twelve months, cancel any time; ten places.</p>\n'
assert VERA_PRICE_LINE in VERA_HTML_PRICED
VERA_HTML = VERA_HTML_PRICED if PRICES_SHOWN else VERA_HTML_PRICED.replace(VERA_PRICE_LINE, '')


def short_days(first, last):
    """'30 October to 2 November': the content's dates, without the year."""
    f, l = [(int(x[8:]), MONTHS[int(x[5:7]) - 1]) for x in (first, last)]
    if first == last:
        return '%d %s' % f
    return ('%d to %d %s' % (f[0], l[0], l[1]) if f[1] == l[1] else '%d %s to %d %s' % (f + l))


def home_winning_html():
    """The home page's Winning Lines (screen 3): the first rows of data/winning-lines-gut.json, the public file, as
    the category page shows them (rows 1 to 3 described or quoted, later rows locked), and content 44's method line
    with the file's count and dates."""
    found = dict(winning_lines())
    if HOME_WL_SLUG not in found:
        fail('data/winning-lines-%s.json is missing (the home page shows it)' % HOME_WL_SLUG)
    d = found[HOME_WL_SLUG]
    winning_lines_check(HOME_WL_SLUG, d)
    rows = []
    for r in d['rows'][:HOME_WL_ROWS]:
        if r['shown'] == 'described':
            line = text(r['described'])
        elif r['shown'] == 'quoted':
            line = '<span class="quote">“%s”</span>' % text(r['quote'])
        else:
            line = 'Locked: in the audit.'
        tier = '<span class="tier %s">%s</span>' % (
            {'Red': 'tier-red', 'Yellow': 'tier-yellow', 'Green': 'tier-open'}[r['tier']], r['tier'])
        rule = tier + (', ' + r['rule'] if r['rule'] else '')
        rows.append('    <tr%s><td data-label="Rank">%d</td><td data-label="The line">%s</td>'
                    '<td data-label="Tier and rule">%s</td><td data-label="Age">%s days</td></tr>' % (
                        ' class="wl-locked"' if r['shown'] == 'locked' else '', r['rank'], line, rule,
                        '{:,}'.format(r['age_days'])))
    return '\n'.join([
        '<!--winning-->',
        '<p class="section-lede">Gut health, from Meta’s Ad Library.</p>',
        '<table class="stack wl-home">',
        '  <thead><tr><th scope="col">Rank</th><th scope="col">The line</th><th scope="col">Tier and rule</th>'
        '<th scope="col">Age</th></tr></thead>',
        '  <tbody>'] + rows + [
        '  </tbody>',
        '</table>',
        '<p class="facts-fn wl-method">%d %s ads from Meta’s Ad Library, read %s. Age is the days from each ad’s start '
        'date to the last day we saw it running. Running longest is not proof a line sells: a brand keeps an ad running '
        'for its own reasons. A correlation, not a cause. No brand, product or ad is named; flagged lines are described, '
        'not quoted.</p>' % (d['ads_in_category'], d['category'].lower(), short_days(d['judged_first'], d['judged_last'])),
        '<!--/winning-->'])


def blocks_apply(page, rel):
    """Writes the site-51 blocks into the home page and /pricing; fails when a marker is missing."""
    want = {'index.html': ((CONFIGURATOR_BLOCK, configurator_html), (VERA_BLOCK, lambda: VERA_HTML),
                           (WINNING_BLOCK, home_winning_html)),
            'pricing.html': ((CONFIGURATOR_BLOCK, configurator_html), (VERA_BLOCK, lambda: VERA_HTML))}.get(rel, ())
    if rel == 'index.html':
        if PRICES_SHOWN and H2_ASK in page:
            page = page.replace(H2_ASK, H2_PRICE)
        elif not PRICES_SHOWN and H2_PRICE in page:
            page = page.replace(H2_PRICE, H2_ASK)
    for rx, make in want:
        block = make()
        page, k = rx.subn(lambda m: block, page)
        if k != 1:
            fail('%s: want one %s marker pair, found %d' % (rel, rx.pattern.split('-->')[0] + '-->', k))
    return page


# The copy's numbers (site 44, 3 Nov 2026). The content lane's copy writes a number as {{field}}; the page keeps it as
# <span data-field="field">value</span>, so the next build refills it when the source changes. A field is a dotted path
# into one of these files, under its prefix: {{index.ads_read}}, {{survival.tiers.Red.median_days}}. A placeholder
# inside a tag (an attribute) gets the bare value, which a later build cannot refill. A {{field}} that no file has stays
# in the page, and build.py --check fails on it.
FIELD_FILES = {
    'index': os.path.join(ROOT, 'data', 'index-2026-11.json'),
    'survival': os.path.expanduser('~/code/merchient-mining/sources/adlibrary/survival-number.json'),  # read only
}
PLACEHOLDER = re.compile(r'\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}')
FIELD_SPAN = re.compile(r'(<span data-field="([A-Za-z0-9_.-]+)">)(.*?)(</span>)', re.S)
_fields = None


def fields():
    """Every scalar in FIELD_FILES as {prefix.dotted.path: text}. A missing file gives no fields (and --check then fails
    on any placeholder that needs one)."""
    global _fields
    if _fields is None:
        _fields = {}

        def walk(o, path):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, path + '.' + str(k))
            elif isinstance(o, list):  # site 47: a list item by its place, {{index.rules_top.0.short}}
                for k, v in enumerate(o):
                    walk(v, path + '.' + str(k))
            elif isinstance(o, bool) or o is None:
                return
            elif isinstance(o, float) and o.is_integer():
                _fields[path] = str(int(o))
            else:
                _fields[path] = str(o)
        for prefix, path in FIELD_FILES.items():
            try:
                with open(path, encoding='utf-8') as f:
                    walk(json.load(f), prefix)
            except FileNotFoundError:
                print('build.py: note: %s not found; its fields stay unfilled' % path, file=sys.stderr)
    return _fields


def fields_apply(page):
    """Refills every data-field span, then turns each {{field}} the files know into a span (or the bare value inside a
    tag). Unknown fields are left as {{field}} for --check to catch."""
    f = fields()
    page = FIELD_SPAN.sub(lambda m: m.group(1) + html.escape(f[m.group(2)], quote=False) + m.group(4)
                          if m.group(2) in f else m.group(0), page)

    def put(m):
        name = m.group(1)
        if name not in f:
            return m.group(0)
        before = page[:m.start()]
        if before.rfind('<') > before.rfind('>'):
            return html.escape(f[name], quote=True)
        return '<span data-field="%s">%s</span>' % (name, html.escape(f[name], quote=False))
    return PLACEHOLDER.sub(put, page)


def unfilled(want):
    """[(page, field)] for every {{field}} still in a built page, and every data-field span no file knows."""
    left = []
    for p, content in sorted(want.items()):
        if p.endswith('.html'):
            left += [(p, m.group(1)) for m in PLACEHOLDER.finditer(content)]
            left += [(p, m.group(2)) for m in FIELD_SPAN.finditer(content) if m.group(2) not in fields()]
    return left


def fail(message):
    sys.exit('build.py: ' + message)


# The ad index (site 39, 3 Nov 2026): /index/ lists the issues, /index/<year>-<month>/ is one issue. Each issue is built
# from data/index-<year>-<month>.json, which tools/index_issue.py writes from the sweep files (site 43; it is
# reports/tools/make_index39.py promoted; counts only: no brand, domain, page name, ad id or quote). Every number on an
# issue page is read from that file. The sentences that depend on the numbers are checked here; if a number makes one
# untrue, the build stops and the sentence has to be reworded.
INDEX_HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; font-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@TITLE@</title>
<meta name="description" content="@DESC@">
<link rel="canonical" href="@URL@">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Merchient">
<meta property="og:title" content="@TITLE@">
<meta property="og:description" content="@DESC@">
<meta property="og:url" content="@URL@">
<meta property="og:image" content="https://merchient.com/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Merchient. Keep the hook. Lose the claim.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="@TITLE@">
<meta name="twitter:description" content="@DESC@">
<meta name="twitter:image" content="https://merchient.com/og-image.png">
<meta name="twitter:image:alt" content="Merchient. Keep the hook. Lose the claim.">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f2eee3" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121210" media="(prefers-color-scheme: dark)">
<link rel="icon" href="@UP@favicon.ico" sizes="32x32">
<link rel="icon" href="@UP@favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="@UP@apple-touch-icon.png">
<link rel="preload" href="@UP@fonts/archivo-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="@UP@styles.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="@UP@">Merchient</a>
    <nav class="site-nav" aria-label="Main">
      <a href="@UP@#how-it-works">How it works</a>
      <a href="@UP@pricing">Price</a>
      <a href="@UP@agencies">Agencies</a>
      <a href="@UP@#faq">FAQ</a>
      <a href="@UP@rescue">Send a rejected ad</a>
      <a class="btn btn-small" href="@UP@#scan">Read my ads</a>
    </nav>
  </div>
</header>

<main id="main" class="legal">
  <div class="wrap narrow">
'''
INDEX_FOOT = '''  </div>
</main>

<footer class="site-footer">
  <div class="wrap footer-inner">
    <p>Merchient is a trade name of Orbline LLC, 30 N Gould St, STE R, Sheridan, WY 82801, USA.</p>
    <p><a href="mailto:hello@merchient.com">hello@merchient.com</a></p>
    <p class="footer-more"><a href="@UP@rescue">Send a rejected ad</a> · <a href="@UP@claims-watch">Claims Watch</a> · <a href="@UP@pricing">Price</a> · <a href="@UP@agencies">Agencies</a> · <a href="@UP@founder">Why I built this</a> · <a href="@UP@method">How Vera decides</a> · <a href="@UP@cases/">Case files</a></p>
    <nav class="footer-links" aria-label="Legal">
      <a href="@UP@privacy.html">Privacy</a>
      <a href="@UP@terms.html">Terms</a>
      <a href="@UP@data-deletion.html">Data deletion</a>
      <a href="@UP@security.html">Security</a>
    </nav>
  </div>
</footer>
</body>
</html>
'''


def index_frame(up, title, desc, url, body):
    head = INDEX_HEAD.replace('@SCAN@', SCAN)
    for token, value in (('@TITLE@', attr(title)), ('@DESC@', attr(desc)), ('@URL@', url), ('@UP@', up)):
        head = head.replace(token, value)
    return head + body + INDEX_FOOT.replace('@UP@', up)


def index_issues():
    """The issues in data/, newest first: (month as 2026-11, the data)."""
    out = []
    for name in sorted(os.listdir(os.path.join(ROOT, 'data')), reverse=True):
        m = re.fullmatch(r'index-(\d{4}-\d\d)\.json', name)
        if m:
            with open(os.path.join(ROOT, 'data', name), encoding='utf-8') as f:
                out.append((m.group(1), json.load(f)))
    return out


def month_name(month):
    return '%s %s' % (MONTHS[int(month[5:]) - 1], month[:4])


def median_text(x):
    return ('%g' % x)


def number_text(n):
    """A small count in words ("four sweeps"), a larger one in digits."""
    words = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']
    return words[n] if 0 <= n < len(words) else str(n)


def index_bands_section(issue_ads):
    """Site 45: "How long lines run, by category and tier", from data/survival-bands.json. Every number is read from that
    file (or counted from it or from the category files); the restraint line is the file's own, word for word."""
    b = survival_bands()
    mn, cells, few = b['min_n'], b['cells'], b['too_few']
    total = sum(c['n'] for c in cells + few)
    pages = winning_lines()
    on_pages = sum(w['ads_in_category'] for _, w in pages)
    from_pages = sum(c['n'] for c in cells + few if c['category'] in [w['category'] for _, w in pages])
    if on_pages != from_pages:
        fail('data/survival-bands.json counts %d ads in the categories that have a page, and the pages count %d' % (from_pages, on_pages))
    rows = ''.join('            <tr><th scope="row">%s</th><td>%s</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>\n' % (
        text(c['category']), c['tier'], c['n'], median_text(c['median']), median_text(c['q1']), median_text(c['q3'])) for c in cells)
    groups = []
    for c in few:
        if not groups or groups[-1][0] != c['category']:
            groups.append((c['category'], []))
        groups[-1][1].append('%s %d' % (c['tier'], c['n']))
    few_text = '; '.join('%s: %s' % (text(cat), ', '.join(parts)) for cat, parts in groups)
    judged = days([x for _, w in pages for x in (w['judged_first'], w['judged_last'])]) if pages else ''
    return '''    <h2>How long lines run, by category and tier</h2>
    <p>For each category and tier: the median number of days the ads had been running when we read them, and the first and third quartiles (a quarter of the ads had run less than the first quartile, a quarter more than the third). Quartiles are found by linear interpolation between ranks. A figure is shown only for a category and tier with at least %(mn)d ads.</p>
    <p class="warnings">%(restraint)s</p>
    <div class="table-wrap">
      <table class="value-table">
        <thead>
          <tr><th scope="col">Category</th><th scope="col">Tier</th><th scope="col">Ads</th><th scope="col">Median days running</th><th scope="col">First quartile</th><th scope="col">Third quartile</th></tr>
        </thead>
        <tbody>
%(rows)s        </tbody>
      </table>
    </div>
    <p><b>Too few ads to show a figure</b> (fewer than %(mn)d; the number of ads is after each tier). %(few)s.</p>
    <p>This table counts %(total)d ads by category and tier, computed %(generated)s. %(on_pages)d of them are the ads on the Winning lines pages, read %(judged)s. Its counts are not the counts in the tables above, which are for the %(issue_ads)d ads of this issue.</p>
''' % {'mn': mn, 'restraint': text(b['restraint']), 'rows': rows, 'few': few_text, 'total': total,
       'generated': day(b['generated']), 'on_pages': on_pages, 'judged': judged, 'issue_ads': issue_ads}


def index_issue_page(month, d):
    where = 'data/index-%s.json' % month
    n, t, flagged, brands = d['ads_read'], d['tiers'], d['flagged'], d['brands']
    if d['month'] != month or sum(t.values()) != n or t['Red'] + t['Yellow'] != flagged or not 0 < brands <= n:
        fail(where + ': the counts do not add up')
    sweeps, recorded, left_out = d['sweeps'], d['sweeps_recorded'], d['brand_lookups_left_out']
    if not 0 < recorded <= sweeps or left_out < 0:
        fail(where + ': the sweeps (%d, %d with their filters recorded) or the brand lookups left out (%d) are wrong' % (
            sweeps, recorded, left_out))
    top, all_rules = d['rules_top'], {r['key']: r for r in d['rules_all']}
    if len(top) != 5 or sum(r['ads'] for r in d['rules_all']) != flagged:
        fail(where + ': the rules must be five, and every flagged ad must be under one rule')
    if [r['ads'] for r in top] != sorted((r['ads'] for r in top), reverse=True) or top[-1]['ads'] < max(
            r['ads'] for r in d['rules_all'][5:]):
        fail(where + ': the five rules are not the five most hit')
    cats = d['categories']
    if sum(c['ads'] for c in cats) != n or sum(c['flagged'] for c in cats) != flagged:
        fail(where + ': the categories do not add up to the ads read')
    run = d['running']
    if [run[k]['ads'] + run[k]['no_age'] for k in ('Red', 'Yellow', 'Green')] != [t['Red'], t['Yellow'], t['Green']]:
        fail(where + ': the running table and the tiers disagree')
    if not all(run[k]['ads'] for k in run):
        fail(where + ': a tier has no ad with a days-running row, so the age sentence cannot be written')
    missing_age = sum(run[k]['no_age'] for k in run)
    first, last = d['read_first'], d['read_last']
    month_label = month_name(month)
    title = 'Supplement ad index: %s' % month_label
    covered = days([first, last])
    desc = ('We read %d supplement ads in Meta’s public Ad Library, %s: %d%% carried a line Vera flags. The rules most hit, '
            'by category, and how long the ads had been running.' % (n, covered, d['share_flagged']))
    covered_in_text = covered if first[:4] == last[:4] else None
    if covered_in_text is None:
        fail(where + ': the reading dates run across two years')

    def pc(v):
        return '%d%%' % v

    rows = ''.join(
        '            <tr><th scope="row">%s</th><td>%d</td><td>%s</td></tr>\n' % (label, t[k], pc(d['share_by_tier'][k]))
        for k, label in (('Red', 'Red'), ('Yellow', 'Yellow'), ('Green', 'Green')))
    rows += '            <tr><th scope="row">Red and Yellow (flagged)</th><td>%d</td><td>%s</td></tr>\n' % (flagged, pc(d['share_flagged']))
    rules = ''
    for r in top:
        red = ('%d of them Red' % r['red']) if r['red'] else 'none of them Red'
        rules += ('      <li><b>%s: %s.</b> %d ads, %s. %s <i>Example:</i> %s</li>\n' % (
            r['authority'], text(r['name'][0].lower() + r['name'][1:]), r['ads'], red, text(r['plain']), text(r['example'])))
    top_total = sum(r['ads'] for r in top)
    cat_items = ''
    for c in cats:
        if not c['ads']:
            continue
        def short(k):
            s = all_rules[k]['short']
            return s[0].lower() + s[1:]
        if not c['top_rule']:
            tail = ' Nothing flagged.'
        elif c['top_rule_tied_with']:
            tail = ' Most hit, tied at %d ads each: %s.' % (c['top_rule_ads'], text(' and '.join(
                [short(c['top_rule'])] + [short(k) for k in c['top_rule_tied_with']])))
        else:
            tail = ' Most hit: %s, %d ads.' % (text(short(c['top_rule'])), c['top_rule_ads'])
        cat_items += '      <li><b>%s.</b> %d ads read, %d flagged (%s).%s</li>\n' % (
            text(c['name']), c['ads'], c['flagged'], pc(c['share_flagged']), tail)
    small = [c['name'] for c in cats if 0 < c['ads'] < 15 and c['name'] != 'Other']
    if len(small) > 1:
        small_text = 'Small groups: %s and %s each have fewer than 15 ads, so read their shares as counts.' % (
            ', '.join(small[:-1]), small[-1])
    elif small:
        small_text = 'Small group: %s has fewer than 15 ads, so read its share as a count.' % small[0]
    else:
        small_text = ''
    run_rows = ''
    for k in ('Red', 'Yellow', 'Green'):
        v = run[k]
        run_rows += ('            <tr><th scope="row">%s</th><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%d (%s)</td><td>%d (%s)</td></tr>\n' % (
            k, v['ads'], median_text(v['median_days']), median_text(v['q1_days']), median_text(v['q3_days']),
            v['at_90_plus'], pc(v['share_90_plus']), v['under_30'], pc(v['share_under_30'])))
    # Every number in the sentences below is read from the data file; none is typed here.
    older = '; '.join('%s %s' % (k, pc(run[k]['share_90_plus'])) for k in ('Red', 'Yellow', 'Green'))
    age_missing_text = (
        '<p>The days-running file had no row yet for %d of the %d ads read; they are counted everywhere else on this page and left out of this table.</p>\n    '
        % (missing_age, n)) if missing_age else ''
    if brands == n:
        brands_text = ', one ad from each of %d brands (counted by the website the ad leads to)' % brands
        one_per = ', one ad from each brand'
    else:
        brands_text = ', from %d brands (counted by the website the ad leads to)' % brands
        one_per = ''
    if recorded == sweeps:
        filters = 'active ads for the United States, sorted by impressions'
        order_text = 'Every sweep took the library’s active ads sorted by impressions'
    else:
        filters = ('active ads for the United States, sorted by impressions (only %d of the %d sweeps recorded their filters)'
                   % (recorded, sweeps))
        order_text = ('%d of the %d sweeps took the library’s active ads sorted by impressions; the others did not record '
                      'their order, or their filters' % (recorded, sweeps))
    left_out_text = (
        '<p>Not counted: %d more ads were found by looking up a brand by name, not by a search word. We chose those brands, '
        'a search did not find them, so they are left out of every number on this page.</p>\n    ' % left_out) if left_out else ''
    groups_rest = len(d['rules_all']) - len(top)
    wordpass = 0 if 'fda_wordpass' in [r['key'] for r in top] else all_rules.get('fda_wordpass', {}).get('ads', 0)
    other = [c for c in cats if c['name'] == 'Other' and c['ads']]
    other_text = ('“Other” holds the searches that fit none of the groups, such as %s.' % text(
        ', '.join(d['category_other_examples'][:-1]) + ' and ' + d['category_other_examples'][-1]
        if len(d['category_other_examples']) > 1 else ''.join(d['category_other_examples']))) if other and d['category_other_examples'] else ''
    body ='''    <p class="kicker"><a href="./">Ad index</a></p>
    <h1>%(title)s</h1>
    <p class="section-lede">Supplement ads running on Meta, the share that carried a line Vera flags, the rules most hit and how long the ads had been running when we read them.</p>
    <p class="warnings">Flagged for review, not a ruling. Meta makes the final call on every ad. Counts only.</p>

    <h2>Ads read</h2>
    <p>From %(covered)s we read %(n)d supplement ads in Meta’s public Ad Library, in %(sweeps)s%(brands_text)s. Vera, Merchient’s AI employee, read each ad’s words against Meta’s ad rules and the FTC and FDA guidance, and gave it a tier.</p>
    <ul class="checklist">
      <li><b>Red.</b> Wording Vera expects a regulator or a platform to act on.</li>
      <li><b>Yellow.</b> Every other finding, less likely to be acted on.</li>
      <li><b>Green.</b> Nothing to flag.</li>
    </ul>
    <div class="table-wrap">
      <table class="value-table">
        <thead>
          <tr><th scope="col">Tier</th><th scope="col">Ads</th><th scope="col">Share of ads read</th></tr>
        </thead>
        <tbody>
%(rows)s        </tbody>
      </table>
    </div>
    <p>%(flagged)d of the %(n)d ads (%(flagged_pc)s) carried a line Vera flags, Red or Yellow.</p>
    %(left_out_text)s
    <h2>The %(top_count)s rules most hit</h2>
    <p>Each flagged ad is counted once, under the rule its reason points to; we sorted Vera’s reasons into these groups. These %(top_count)s cover %(top_total)d of the %(flagged)d flagged ads.%(rest_text)s Examples are described, not quoted: no brand, product name or ad is named.</p>
    <ol class="checklist">
%(rules)s    </ol>

    <h2>By category</h2>
    <p>Ads are grouped by the search word that found them, one group for each ad. %(other)s</p>
    <ul class="checklist">
%(cats)s    </ul>
    <p>%(small)s</p>

    <h2>How long the ads had been running when we read them</h2>
    <p>Meta’s library shows the day each ad started. “Days running” is the number of days between that day and the day we read the ad. For each tier the table gives the median and the first and third quartiles of days running, from the days-running file of the ads in this issue.</p>
    <div class="table-wrap">
      <table class="value-table">
        <thead>
          <tr><th scope="col">Tier</th><th scope="col">Ads</th><th scope="col">Median days running</th><th scope="col">First quartile</th><th scope="col">Third quartile</th><th scope="col">90 days or more</th><th scope="col">Under 30 days</th></tr>
        </thead>
        <tbody>
%(run_rows)s        </tbody>
      </table>
    </div>
    %(age_missing_text)s<p><b>What it shows.</b> Of the %(n_red)d Red lines we read%(red_with_row)s, the median ad had been running %(med_red)s days; Green: %(med_green)s days. Correlation only. Running 90 days or longer: %(older)s.</p>
    <p><b>What it does not show.</b> These ads were running when we read them, so this cannot say how many flagged ads were stopped, by the brand or by Meta: an ad that had stopped before a sweep is not in these numbers. A recheck of the same ads would show that; this issue does not. It does not say whether Meta has reviewed any of these ads or what it decided. %(order_text)s, so the ads lean towards those that reach many people. These ads are not a random sample of supplement ads.</p>

%(bands)s
    <h2>What changed since last issue</h2>
    <p>This is the first issue, so there is nothing to compare with yet.</p>

    <h2>How Vera decides</h2>
    <p>Vera gives each ad one tier: Red for wording she expects a regulator or a platform to act on, Yellow for any other finding, Green for nothing to flag. Each finding carries the rule it rests on and is marked checked or not checked. <a href="%(up)ssample-report.html">See a finding laid out in the sample report</a>.</p>

    <h2>Method</h2>
    <p>We read supplement ads in Meta’s public Ad Library: %(filters)s, found by search words such as the ones grouped above%(one_per)s. Vera, an AI, read each ad’s words against Meta’s published ad rules and the FTC and FDA guidance. A tier and a rule show what Vera flagged. We do not know what Meta decided about any of these ads. Vera read each ad’s headline and the start of its text, not its picture or video or the page it leads to, so a Green ad had nothing to flag in those words and may still have a problem elsewhere. Start dates are the ones the library shows.</p>
    %(winning)s<p>Want to know where your own ads fall? Put your website in the box on the home page and <a href="%(up)sscan">see your own panel</a>.</p>
    <p class="warnings">Risk review, not legal advice.</p>
    <p class="more-link"><a class="sample-link" href="../">All issues</a> · <a class="sample-link" href="../../weekly/">Weekly</a> · <a class="sample-link" href="../../">Back to the home page</a></p>
''' % {
        'title': text(title), 'covered': covered, 'n': n, 'brands_text': brands_text, 'rows': rows,
        'sweeps': ('%s %s' % (number_text(sweeps), 'sweep' if sweeps == 1 else 'sweeps')),
        'flagged': flagged, 'flagged_pc': pc(d['share_flagged']), 'top_total': top_total,
        'top_count': number_text(len(top)), 'left_out_text': left_out_text, 'other': other_text,
        'rest_text': (' The other %d are spread over %s smaller %s%s.' % (
            flagged - top_total, number_text(groups_rest), 'group' if groups_rest == 1 else 'groups',
            ('; %d of those were flagged by a word check that named no rule' % wordpass) if wordpass else ''))
        if flagged > top_total else '',
        'rules': rules, 'cats': cat_items, 'run_rows': run_rows, 'older': older, 'age_missing_text': age_missing_text,
        'n_red': run['Red']['ads'],
        'red_with_row': ' that have a days-running row' if run['Red']['no_age'] else '',    # evidence reviewer: 81 of 83, not "the 81 read"
'med_red': median_text(run['Red']['median_days']),
        'med_green': median_text(run['Green']['median_days']), 'order_text': order_text, 'filters': filters,
        'one_per': one_per, 'up': '../../', 'small': small_text, 'bands': index_bands_section(n),
        'winning': ('<p>Which lines ran longest, each with Vera’s tier and rule: %s.</p>\n    ' % '; '.join(
            '<a href="../../winning-lines/%s/">%s</a>' % (slug, text(winning_lines_title(w))) for slug, w in winning_lines())
            if winning_lines() else ''),
    }
    return index_frame('../../', title + ' · Merchient', desc, SITE + 'index/%s/' % month, body)


def index_list_page(issues):
    if not issues:
        fail('data/: no index-<year>-<month>.json')
    items = ''.join('      <li><a href="%s/">Supplement ad index: %s</a> · %d ads read, %s</li>\n' % (
        m, month_name(m), d['ads_read'], days([d['read_first'], d['read_last']])) for m, d in issues)
    body = '''    <p class="kicker">Ad index</p>
    <h1>Supplement ad index.</h1>
    <p class="section-lede">Supplement ads read in Meta’s public Ad Library, the rules their lines meet and how long the ads had been running.</p>

    <h2>The issues</h2>
    <ul class="checklist">
%s    </ul>

    <p>What Meta’s ad rules catch, week by week: <a href="../weekly/">the weekly page</a>.</p>
    <p>Want to know where your own ads fall? Put your website in the box on the <a href="../scan">home page</a> for the preview.</p>

    <p class="warnings">Risk review, not legal advice.</p>
    <p class="more-link"><a class="sample-link" href="../weekly/">Weekly</a> · <a class="sample-link" href="../">Back to the home page</a></p>
''' % items
    return index_frame('../', 'Supplement ad index · Merchient',
                       'Supplement ads read in Meta’s public Ad Library: the rules their lines meet, by category, and how long the ads had been running.',
                       SITE + 'index/', body)


# Winning lines (site 42, 3 Nov 2026): /winning-lines/ lists the categories, /winning-lines/<slug>/ is one category's page,
# each built from data/winning-lines-<slug>.json. reports/tools/sync_winning42.py copies that file from the mining lane's
# public file and refuses anything that is not public. The page shows rows 1 to 3 as the data says (quoted or described),
# every later row as a locked row (rank, days running, tier, rule; the line hidden). No price on these pages.
WL_TOP = {'category', 'generated', 'ads_in_category', 'judged_first', 'judged_last', 'median_age_days', 'rows', 'restraint'}
WL_SHOWN_FIRST = 3
WL_TIERS = ('Red', 'Yellow', 'Green')
WL_RULES = ('FTC', 'FDA', 'Meta')

# The band table (site 45): data/survival-bands.json is the mining lane's public file, copied by the same script. It gives
# the median and quartiles of days running for each category and tier with at least min_n ads, and names the cells with too
# few. The November issue shows it; a category page shows a tier's median only where the table has a cell for it.
BANDS_TOP = {'generated', 'restraint', 'unit', 'method', 'min_n', 'cells_shown', 'cells', 'too_few'}
BANDS_CELL = {'category', 'tier', 'n', 'median', 'q1', 'q3'}
BANDS_FEW = {'category', 'tier', 'n'}
_bands = None


def survival_bands():
    """data/survival-bands.json, checked: {min_n, restraint, generated, cells, too_few, by: {(category, tier): entry}}."""
    global _bands
    if _bands is not None:
        return _bands
    where = 'data/survival-bands.json'
    try:
        with open(os.path.join(ROOT, 'data', 'survival-bands.json'), encoding='utf-8') as f:
            b = json.load(f)
    except FileNotFoundError:
        fail(where + ' is missing (python3 -I reports/tools/sync_winning42.py copies it)')
    if set(b) != BANDS_TOP:
        fail(where + ': fields outside the public set (%s)' % sorted(set(b) ^ BANDS_TOP))
    mn, by = b['min_n'], {}
    if not isinstance(mn, int) or mn < 1 or not isinstance(b['restraint'], str) or not b['restraint'] or not b['cells']:
        fail(where + ': min_n, the restraint line or the cells are wrong')
    if b['cells_shown'] != len(b['cells']):
        fail(where + ': cells_shown is %s but there are %d cells' % (b['cells_shown'], len(b['cells'])))
    for kind, items, fields in (('cell', b['cells'], BANDS_CELL), ('too_few', b['too_few'], BANDS_FEW)):
        for c in items:
            if set(c) != fields or c['tier'] not in WL_TIERS or not isinstance(c['n'], int) or c['n'] < 0:
                fail(where + ': a %s entry has fields or values outside the public set: %s' % (kind, c))
            if (c['category'], c['tier']) in by:
                fail(where + ': %s %s appears twice' % (c['category'], c['tier']))
            if (kind == 'cell') != (c['n'] >= mn):
                fail(where + ': %s %s has %d ads, which is %s min_n %d' % (
                    c['category'], c['tier'], c['n'], 'below' if kind == 'cell' else 'not below', mn))
            if kind == 'cell' and not c['q1'] <= c['median'] <= c['q3']:
                fail(where + ': %s %s: the quartiles and the median are out of order' % (c['category'], c['tier']))
            by[(c['category'], c['tier'])] = dict(c, shown=(kind == 'cell'))
    b['by'] = by
    _bands = b
    return b


def winning_lines():
    """The categories in data/, in file-name order: (slug, the data)."""
    out = []
    for name in sorted(os.listdir(os.path.join(ROOT, 'data'))):
        m = re.fullmatch(r'winning-lines-([a-z0-9-]+)\.json', name)
        if m:
            with open(os.path.join(ROOT, 'data', name), encoding='utf-8') as f:
                out.append((m.group(1), json.load(f)))
    return out


def winning_lines_title(d):
    return 'What runs longest: %s supplement ads' % d['category']


def winning_lines_check(slug, d):
    where = 'data/winning-lines-%s.json' % slug
    if set(d) != WL_TOP:
        fail(where + ': fields outside the public set (%s)' % sorted(set(d) ^ WL_TOP))
    rows = d['rows']
    if len(rows) != d['ads_in_category'] or not rows:
        fail(where + ': ads_in_category is %s but there are %d rows' % (d['ads_in_category'], len(rows)))
    for i, r in enumerate(rows, 1):
        if r['rank'] != i or (i > 1 and r['age_days'] > rows[i - 2]['age_days']):
            fail(where + ': row %d is out of order (rank, then longest-running first)' % i)
        if r['tier'] not in WL_TIERS or r['rule'] not in WL_RULES + (None,) or (r['tier'] == 'Green') != (r['rule'] is None):
            fail(where + ': row %d has a tier or rule the page does not know' % i)
        # site 45: a shown row is one of the first three; the file may lock some of them (Brain locks ranks 1 and 2)
        if r['shown'] != 'locked' and i > WL_SHOWN_FIRST:
            fail(where + ': row %d must be locked (only rows 1 to %d may be shown)' % (i, WL_SHOWN_FIRST))
        if r['shown'] == 'locked' and set(r) != {'rank', 'shown', 'age_days', 'tier', 'rule'}:
            fail(where + ': locked row %d carries more than rank, age, tier and rule' % i)
    if all(r['shown'] == 'locked' for r in rows):
        fail(where + ': no row is shown')
    if set(d['median_age_days']) != set(WL_TIERS) or d['judged_first'] > d['judged_last']:
        fail(where + ': the medians or the dates are wrong')
    for t in WL_TIERS:
        ages = sorted(r['age_days'] for r in rows if r['tier'] == t)
        if not ages:
            fail(where + ': no %s row, so the median by tier cannot be shown' % t)
        mid = len(ages) // 2
        median = ages[mid] if len(ages) % 2 else (ages[mid - 1] + ages[mid]) / 2
        if abs(median - d['median_age_days'][t]) > 1e-9:
            fail(where + ': the %s median is %s in the file but %s from the rows' % (t, d['median_age_days'][t], median))
        # site 45: the band table must agree with the rows: same ads in the tier, and the same median where it shows one
        cell = survival_bands()['by'].get((d['category'], t))
        if not cell:
            fail(where + ': data/survival-bands.json has no %s %s entry' % (d['category'], t))
        if cell['n'] != len(ages):
            fail(where + ': %s has %d ads in the rows but %d in the band table' % (t, len(ages), cell['n']))
        if cell['shown'] and abs(cell['median'] - median) > 1e-9:
            fail(where + ': the %s median is %s from the rows but %s in the band table' % (t, median, cell['median']))
    if len(d['restraint']) != 2 or not all(isinstance(x, str) and x for x in d['restraint']):
        fail(where + ': the two restraint lines are missing')


def winning_lines_page(slug, d):
    winning_lines_check(slug, d)
    title, rows = winning_lines_title(d), d['rows']
    judged = days([d['judged_first'], d['judged_last']])
    desc = ('Lines from ads in Meta’s public Ad Library for %s supplements, longest-running first, each with Vera’s '
            'tier and rule.' % d['category'])
    table = ''
    for r in rows:
        if r['shown'] == 'described':
            line = text(r['described'])
        elif r['shown'] == 'quoted':
            line = '“%s”' % text(r['quote'])
        else:
            line = 'Locked'
        table += '          <tr><th scope="row">%d</th><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>\n' % (
            r['rank'], r['age_days'], r['tier'], r['rule'] or 'None: nothing to flag', line)
    bands = survival_bands()
    few = [t for t in WL_TIERS if not bands['by'][(d['category'], t)]['shown']]
    medians = ''.join('          <tr><th scope="row">%s</th><td>%d</td><td>%s</td></tr>\n' % (
        t, sum(1 for r in rows if r['tier'] == t),
        'Too few ads for a median' if t in few else median_text(d['median_age_days'][t])) for t in WL_TIERS)
    few_text = ('    <p>A median is shown only for a tier with at least %d ads. %s %s fewer, so no median is shown for %s.</p>\n' % (
        bands['min_n'], ' and '.join(few), 'has' if len(few) == 1 else 'have', 'it' if len(few) == 1 else 'them')) if few else ''
    if [r['rank'] for r in rows if r['shown'] != 'locked'] == list(range(1, WL_SHOWN_FIRST + 1)):
        shown_text = 'The first %s lines are shown' % number_text(WL_SHOWN_FIRST)
    else:
        sr = [r['rank'] for r in rows if r['shown'] != 'locked']
        shown_text = 'The %s at %s %s %s shown' % (
            'line' if len(sr) == 1 else 'lines', 'rank' if len(sr) == 1 else 'ranks',
            (', '.join(str(x) for x in sr[:-1]) + ' and ' + str(sr[-1])) if len(sr) > 1 else str(sr[0]),
            'is' if len(sr) == 1 else 'are')
    body = '''    <p class="kicker"><a href="../">Winning lines</a></p>
    <h1>%(title)s</h1>
    <p class="section-lede">Lines from ads in Meta’s public Ad Library, longest-running first, each with Vera’s tier and rule.</p>
    <p class="warnings">%(r1)s</p>
    <p class="warnings">%(r2)s</p>

    <h2>Longest-running first</h2>
    <p>%(n)d ads in this category, read by Vera from %(judged)s. Days running is how long each ad had been running when we read it, from the start date the library shows. %(shown)s; the rest are locked, with the rank, the days running, the tier and the rule in view and the line hidden.</p>
    <p>Tiers: Red is wording Vera expects a regulator or a platform to act on, Yellow is any other finding, Green is nothing to flag. The rule is where the finding comes from: the FTC, the FDA or Meta’s ad rules.</p>
    <div class="table-wrap">
      <table class="value-table">
        <thead>
          <tr><th scope="col">Rank</th><th scope="col">Days running</th><th scope="col">Tier</th><th scope="col">Rule</th><th scope="col">The line</th></tr>
        </thead>
        <tbody>
%(table)s        </tbody>
      </table>
    </div>
    <p>Want your own page read the same way? <a href="../../scan">Put your website in the preview</a>.</p>

    <h2>Median days running, by tier</h2>
    <div class="table-wrap">
      <table class="value-table">
        <thead>
          <tr><th scope="col">Tier</th><th scope="col">Ads</th><th scope="col">Median days running</th></tr>
        </thead>
        <tbody>
%(medians)s        </tbody>
      </table>
    </div>
%(few_text)s
    <h2>Method</h2>
    <p>We read ads in Meta’s public Ad Library. Vera, an AI, read each ad’s words against Meta’s published ad rules and the FTC and FDA guidance, and gave each a tier and the rule it rests on. A tier and a rule show what Vera flagged; we do not know what Meta decided about any of these ads. Vera read each ad’s headline and the start of its text, not its picture or video or the page it leads to.</p>
    <p class="warnings">Risk review, not legal advice.</p>
    <p class="more-link"><a class="sample-link" href="../">All categories</a> · <a class="sample-link" href="../../index/">Ad index</a> · <a class="sample-link" href="../../weekly/">Weekly</a> · <a class="sample-link" href="../../">Back to the home page</a></p>
''' % {
        'title': text(title), 'r1': text(d['restraint'][0]), 'r2': text(d['restraint'][1]), 'n': len(rows), 'judged': judged,
        'shown': shown_text, 'table': table, 'medians': medians, 'few_text': few_text,
    }
    return index_frame('../../', title + ' · Merchient', desc, SITE + 'winning-lines/%s/' % slug, body)


def winning_lines_list_page(cats):
    items = ''.join('      <li><a href="%s/">%s</a> · %d ads, read %s</li>\n' % (
        slug, text(winning_lines_title(d)), d['ads_in_category'], days([d['judged_first'], d['judged_last']])) for slug, d in cats)
    lines = []
    for _, d in cats:
        lines += [x for x in d['restraint'] if x not in lines]
    restraint = ''.join('    <p class="warnings">%s</p>\n' % text(x) for x in lines)
    body = '''    <p class="kicker">Winning lines</p>
    <h1>Winning lines.</h1>
    <p class="section-lede">By category: lines from ads in Meta’s public Ad Library, longest-running first, with Vera’s tier and rule for each ad on the category page.</p>
%(restraint)s
    <h2>The categories</h2>
    <ul class="checklist">
%(items)s    </ul>

    <p>Every ad we read, by category and rule: <a href="../index/">the supplement ad index</a>.</p>
    <p>Want your own page read the same way? <a href="../scan">Put your website in the preview</a>.</p>

    <p class="warnings">Risk review, not legal advice.</p>
    <p class="more-link"><a class="sample-link" href="../index/">Ad index</a> · <a class="sample-link" href="../weekly/">Weekly</a> · <a class="sample-link" href="../">Back to the home page</a></p>
''' % {'items': items, 'restraint': restraint}
    return index_frame('../', 'Winning lines · Merchient',
                       'Lines from ads in Meta’s public Ad Library, longest-running first, by category, each with Vera’s tier and rule.',
                       SITE + 'winning-lines/', body)


def smart(s):
    """Typographic quotes and apostrophes, as on the rest of the site."""
    s = re.sub(r'(^|[\s(\[])"', '\\1\u201c', s).replace('"', '\u201d')
    s = re.sub(r"(^|[\s(\[])'", '\\1\u2018', s)
    return s.replace("'", '\u2019')


def text(s):
    return html.escape(smart(s), quote=False)


def attr(s):
    return html.escape(smart(s), quote=True)


def day(iso):
    y, m, d = (int(x) for x in iso.split('-'))
    return '%d %s %d' % (d, MONTHS[m - 1], y)


def days(isos):
    first, last = min(isos), max(isos)
    if first == last:
        return day(first)
    if first[:7] == last[:7]:
        return '%d to %s' % (int(first[8:]), day(last))
    return day(first) + ' to ' + day(last)


def count(n, one, many):
    return '%d %s' % (n, one if n == 1 else many)


def link(source):
    return '<a href="%s">%s</a>' % (html.escape(source['url'], quote=True), text(source['name']))


def load():
    """Reads data/, and stops at anything the pages would not show faithfully."""
    data = os.path.join(ROOT, 'data')
    with open(os.path.join(data, 'index.json'), encoding='utf-8') as f:
        index = json.load(f)
    guides = []
    for entry in index['guides']:
        slug = entry['slug']
        if not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', slug):
            fail('data/index.json: bad slug %r' % slug)
        where = 'data/%s.json' % slug
        with open(os.path.join(data, slug + '.json'), encoding='utf-8') as f:
            g = json.load(f)
        keys = set(g)
        if not GUIDE_KEYS <= keys or keys - GUIDE_KEYS - GUIDE_OPTIONAL:
            fail('%s: unexpected or missing fields %s' % (where, sorted((keys ^ GUIDE_KEYS) - GUIDE_OPTIONAL)))
        if g['slug'] != slug:
            fail(where + ': its slug does not match its file name')
        if (entry['supported_wordings'], entry['wordings_to_avoid']) != (len(g['supported_wordings']), len(g['wordings_to_avoid'])):
            fail(where + ': its counts differ from data/index.json')
        if not g['disclaimer'].startswith(NOT_ADVICE):
            fail(where + ': the disclaimer no longer starts with "Not legal advice."')
        if not g['sources'] and LINKED_BELOW not in g['disclaimer']:
            fail(where + ': no sources, and the disclaimer has changed; update guide_page() in build.py')
        if not TITLE.fullmatch(g['title']):
            fail(where + ': the title no longer reads "What can you say about ... in your ads and on your site?"')
        if not re.fullmatch(r'\d{4}-\d\d-\d\d', g['date_reviewed']):
            fail(where + ': date_reviewed is not a date')
        if not g['supported_wordings'] and 'evidence_gap' not in g:
            fail(where + ': no supported wording, and no evidence_gap saying why')
        meta_supported, meta_avoid = set(), set()
        for w in g['supported_wordings']:
            k = set(w)
            if not SUPPORTED_KEYS <= k or k - SUPPORTED_KEYS - SUPPORTED_OPTIONAL:
                fail('%s: unexpected or missing fields in a supported wording %s' % (where, sorted((k ^ SUPPORTED_KEYS) - SUPPORTED_OPTIONAL)))
            if w['evidence_strength'] not in g['evidence_strengths']:
                fail(where + ': unknown evidence strength ' + w['evidence_strength'])
            if not w['sources']:
                fail(where + ': a supported wording has no source')
            if 'meta_ads' in w:
                meta_supported.add(w['wording'])
        for w in g['wordings_to_avoid']:
            if set(w) != AVOID_KEYS:
                fail('%s: unexpected or missing fields in a wording to avoid %s' % (where, sorted(set(w) ^ AVOID_KEYS)))
            if w['reason'] not in g['reasons_to_avoid']:
                fail(where + ': unknown reason ' + w['reason'])
            if w['meta_ads_only']:
                meta_avoid.add(w['wording'])
        if meta_supported != meta_avoid:
            fail(where + ': the Meta-ads-only wordings to avoid and the supported wordings marked for Meta ads differ')
        for s in g['sources'] + [s for w in g['supported_wordings'] for s in w['sources']]:
            if not s['url'].startswith('https://'):
                fail(where + ': a source is not an https link')
        guides.append(g)
    names = sorted(f[:-5] for f in os.listdir(data) if f.endswith('.json') and f not in ('index.json', 'sweeps.json', 'survival-bands.json')
                   and not re.fullmatch(r'index-\d{4}-\d\d\.json', f) and not f.startswith('winning-lines-'))
    if names != sorted(g['slug'] for g in guides) or index['count'] != len(guides):
        fail('data/ and data/index.json list different guides')
    return index, guides


def guide_page(g):
    ingredient, supported, avoid = g['ingredient'], g['supported_wordings'], g['wordings_to_avoid']
    title = 'What you can say about %s \u00b7 Merchient' % TITLE.fullmatch(g['title']).group(1)
    sources = ', and the sources' if g['sources'] else ''
    if supported:
        description = '%s in supplement ads and on your site: %s with the daily dose and evidence strength, %s%s.' % (
            ingredient, count(len(supported), 'supported wording', 'supported wordings'),
            count(len(avoid), 'wording to avoid', 'wordings to avoid'), sources)
    else:
        description = '%s in supplement ads and on your site: why no wording is supported yet, and %s%s.' % (
            ingredient, count(len(avoid), 'wording to avoid', 'wordings to avoid'), sources)
    disclaimer = g['disclaimer'][len(NOT_ADVICE):]
    if not g['sources']:
        disclaimer = disclaimer.replace(LINKED_BELOW, '', 1)
    out = [HEAD.format(title=attr(title), description=attr(description),
                       url=SITE + 'ingredients/' + g['slug'] + '.html')]

    also = ''
    if g['also_called']:
        also = '      <p class="also"><b>Also called:</b> %s</p>\n' % text(', '.join(g['also_called']))
    flag = ''
    if 'review_flag' in g:
        flag = '      <p class="warnings"><b>Flagged for review.</b> %s</p>\n' % text(g['review_flag']['text'])
    out.append(TOP.format(h1=text(g['title']), summary=text(g['summary']), also=also, flag=flag,
                          iso=g['date_reviewed'], date=day(g['date_reviewed']), disclaimer=text(disclaimer)))

    if supported:
        cards = []
        for n, w in enumerate(supported, 1):
            strength = w['evidence_strength']
            head = '<span class="tier ev-%s">%s evidence</span>' % (strength, strength.capitalize())
            if 'meta_ads' in w:
                head += '<span class="tier tier-yellow">Not in Meta ads</span>'
            rows = [('Daily dose', text(w['daily_dose'])), ('Support', text(w['why'])),
                    ('Dose details', text(w['dose_details']))]
            if 'dose_warning' in w:
                rows.append(('Dose warning', text(w['dose_warning'])))
            rows.append(('Form', text(w['form'])))
            if 'where_sources_disagree' in w:
                rows.append(('Where sources disagree', text(w['where_sources_disagree'])))
            if 'meta_ads' in w:
                rows.append(('Meta ads', text(w['meta_ads'])))
            rows.append(('Source' if len(w['sources']) == 1 else 'Sources', '<br>'.join(link(s) for s in w['sources'])))
            cards.append(CARD.format(head=head, n=n, wording=text(w['wording']), rows='\n'.join(
                '              <tr><th scope="row">%s</th><td>%s</td></tr>' % r for r in rows)))
        legend = ''.join('        <div><dt><span class="tier ev-%s">%s evidence</span></dt><dd>%s</dd></div>\n' % (
            k, k.capitalize(), text(v)) for k, v in g['evidence_strengths'].items())
        body = ('      <div class="items items-2">\n' + '\n'.join(cards) + '\n      </div>\n'
                '      <h3 class="legend-head">How strong the evidence is</h3>\n'
                '      <dl class="legend">\n' + legend + '      </dl>\n')
    else:
        body = GAP.format(gap=text(g['evidence_gap']))
    out.append(SUPPORTED.format(body=body))

    rows = []
    for w in avoid:
        mark = ' <span class="tier tier-yellow">Meta ads only</span>' if w['meta_ads_only'] else ''
        rows.append('            <tr><td><b>\u201c%s\u201d</b>%s<small>%s</small></td><td>%s</td></tr>' % (
            text(w['wording']), mark, text(w['why']), w['reason'].capitalize()))
    notes = ' '.join('%s: %s.' % (k.capitalize(), text(v)) for k, v in g['reasons_to_avoid'].items())
    if any(w['meta_ads_only'] for w in avoid):
        notes += ' Meta ads only: keep it out of Meta ads; on your own site it is supported wording.'
    out.append(AVOID.format(ingredient=text(ingredient), rows='\n'.join(rows), notes=notes))

    if g['sources']:
        items = ('      <ul class="sources">\n' + '\n'.join('        <li>%s</li>' % link(s) for s in g['sources'])
                 + '\n      </ul>')
    else:
        items = '      <p class="section-lede">This guide cites no source yet; “What you can say” above explains why.</p>'
    out.append(SOURCES.format(items=items))
    out.append(FINAL)
    return ''.join(out)


def pointers(guides):
    """Places where a guide points at a part of the library that no page shows."""
    found = {}
    for g in guides:
        for s in re.findall(r'"((?:[^"\\]|\\.)*)"', json.dumps(g, ensure_ascii=False)):
            for m in POINTER.finditer(s):
                found.setdefault(m.group(0), set()).add(g['slug'])
    return found


def index_page(index, guides):
    disclaimer = index['disclaimer']
    for old, new in ((NOT_ADVICE, ''), ('This guide shows', 'Each guide shows'),
                     ('from the sources linked below', 'from the sources it links')):
        if old not in disclaimer:
            fail('data/index.json: the disclaimer has changed; update index_page() in build.py')
        disclaimer = disclaimer.replace(old, new, 1)
    items = []
    for g in guides:
        n = len(g['supported_wordings'])
        said = ('%d supported' % n) if n else 'None supported yet'
        items.append('          <li><a href="%s.html">%s</a><span>%s \u00b7 %d to avoid</span></li>' % (
            g['slug'], text(g['ingredient']), said, len(g['wordings_to_avoid'])))
    description = ('What you can say about %d supplement ingredients in ads and on your site: supported wordings '
                   'with the daily dose and evidence strength, wordings to avoid, and the sources.' % len(guides))
    return (HEAD.format(title='Ingredient guides \u00b7 Merchient', description=attr(description), url=SITE + 'ingredients/')
            + INDEX.format(n=len(guides), with_wording=sum(1 for g in guides if g['supported_wordings']),
                           reviewed=days([g['date_reviewed'] for g in guides]), iso=index['generated_on'],
                           date=day(index['generated_on']), disclaimer=text(disclaimer), items='\n'.join(items))
            + FINAL)


def sitemap(guides, winning):
    # Site 54 (11 Nov 2026): the sitemap lists the home page and nothing else: no old pages, ingredient guides, index
    # issues, winning lines, method, cases or d/. The old pages stay in the repo, reachable only by their addresses.
    urls = [SITE]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + ''.join('  <url><loc>%s</loc></url>\n' % u for u in urls) + '</urlset>\n')


def pages():
    """The site's own pages, outside the generated folder. Site 53: d/ (the demo pages, written by
    tools/make_demo_pages.py) is never walked, so no footer, count or field step touches a file under it; and
    order-desk-template.html is the demo pages' source, not a page (its {{COMPANY}} is not a build field).
    Site 55: example/ (Varma's hand-written example page, noindex) is never walked or rewritten either."""
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in ('ingredients', 'data', 'fonts', 'reports', 'previews')
                         and not (folder == ROOT and d in ('d', 'example')))
        for name in sorted(files):
            if name.endswith('.html') and not (folder == ROOT and name == 'order-desk-template.html'):
                yield os.path.relpath(os.path.join(folder, name), ROOT)


def main():
    args = sys.argv[1:]
    if args not in ([], ['--check']):
        sys.exit('usage: python3 build.py [--check]')
    if (type(FOUNDING_PLACES) is not int or type(FOUNDING_PLACES_LEFT) is not int
            or not 0 <= FOUNDING_PLACES_LEFT <= FOUNDING_PLACES):
        fail('config/links.json: founding_open must be a whole number from 0 to founding_total')
    index, guides = load()

    want, shown = {}, 0
    for p in pages():
        if p == 'index.html':
            # Site 54 (11 Nov 2026): the home page is hand-written and plain (Varma's text). The build leaves it exactly
            # as written: no scan box, proof line, blocks, founder link, fields or founding-places count, no markers.
            continue
        with open(os.path.join(ROOT, p), encoding='utf-8') as f:
            was = f.read()
        new, n = PLACES.subn(lambda m: m.group(1) + str(FOUNDING_PLACES_LEFT) + m.group(2), was)
        new = blocks_apply(new, p)  # site 51: the configurator, Vera's screen (pricing.html); the home page no longer (site 54)
        new = fields_apply(founder_link(new, p))
        if n or new != was or PLACEHOLDER.search(new) or FIELD_SPAN.search(new):
            want[p], shown = new, shown + n
    if not shown:
        fail('no page shows the founding places left (<strong class="places-left">)')
    for g in guides:
        want[os.path.join('ingredients', g['slug'] + '.html')] = guide_page(g)
    want[os.path.join('ingredients', 'index.html')] = index_page(index, guides)
    winning = winning_lines()
    want['sitemap.xml'] = sitemap(guides, winning)
    issues = index_issues()
    for month, d in issues:
        want[os.path.join('index', month, 'index.html')] = index_issue_page(month, d)
    want[os.path.join('index', 'index.html')] = index_list_page(issues)
    for slug, d in winning:
        want[os.path.join('winning-lines', slug, 'index.html')] = winning_lines_page(slug, d)
    if winning:
        want[os.path.join('winning-lines', 'index.html')] = winning_lines_list_page(winning)
    if SCAN_API_ON:
        want['scan.js'] = SCAN_JS

    folder = os.path.join(ROOT, 'ingredients')
    stale = sorted(os.path.join('ingredients', f) for f in (os.listdir(folder) if os.path.isdir(folder) else [])
                   if f.endswith('.html') and os.path.join('ingredients', f) not in want)
    if not SCAN_API_ON and os.path.exists(os.path.join(ROOT, 'scan.js')):
        stale.append('scan.js')
    changed = []
    for p, content in sorted(want.items()):
        try:
            with open(os.path.join(ROOT, p), encoding='utf-8') as f:
                if f.read() == content:
                    continue
        except FileNotFoundError:
            pass
        changed.append(p)

    for phrase, slugs in sorted(pointers(guides).items()):
        print('build.py: note: "%s" points at nothing the page shows, in %s (fix it in the library)' % (
            phrase, ', '.join(sorted(slugs))), file=sys.stderr)
    left = unfilled(want)
    for p, name in left:
        print('build.py: unfilled placeholder {{%s}} in %s (no such field in %s)' % (
            name, p, ' or '.join(sorted(FIELD_FILES))), file=sys.stderr)
    if args == ['--check']:
        if changed or stale or left:
            if changed or stale:
                print('build.py --check: out of date: ' + ', '.join(changed + stale))
            if left:
                print('build.py --check: %d unfilled placeholder(s)' % len(left))
            sys.exit(1)
        print('build.py --check: up to date (%d guides; %d founding places left, shown %d times; scan box %s)' % (
            len(guides), FOUNDING_PLACES_LEFT, shown, 'posts to the scan service' if SCAN_API_ON else 'opens the email'))
        return
    os.makedirs(folder, exist_ok=True)
    for p in changed:
        os.makedirs(os.path.dirname(os.path.join(ROOT, p)), exist_ok=True)
        with open(os.path.join(ROOT, p), 'w', encoding='utf-8', newline='\n') as f:
            f.write(want[p])
    for p in stale:
        os.remove(os.path.join(ROOT, p))
    print('build.py: %d guides and the index; %d founding places left, shown %d times; %d files written, %d removed' % (
        len(guides), FOUNDING_PLACES_LEFT, shown, len(changed), len(stale)))


if __name__ == '__main__':
    main()
