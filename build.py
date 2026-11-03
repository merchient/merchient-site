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

# Founding places still open, out of 3. When a founding brand joins, lower this
# by one, run python3 build.py, then commit and push.
FOUNDING_PLACES_LEFT = 3

# The scan box in the home page's hero. False: the box opens the "Free scan request"
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

import html
import json
import os
import re
import sys

FOUNDING_PLACES = 3
ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = 'https://merchient.com/'
SCAN = ('mailto:hello@merchient.com?subject=Free%20scan%20request&amp;'
        'body=Brand%20name%3A%20%0D%0AWebsite%3A%20%0D%0A')
BOOK = ('https://calendar.google.com/calendar/appointments/schedules/'
        'AcZssZ0OC3aykWqaXz8QQ8TZ6hiOhituHjqaoqzefFYIUnyb4OZb6Bv5aZZUh2n_WvxcSyDtiHJmdkrZ')
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
      <a class="btn btn-small" href="''' + SCAN + '''">Get your free scan</a>
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
      <h2>Check the claims on your own site. Free.</h2>
      <p>Vera, Merchient’s AI employee, reads your site and emails you the riskiest line, why, a safer rewrite and how many more like it she found. Reply, and you get the free first report.</p>
      <div class="cta-row">
        <a class="btn" href="''' + SCAN + '''">Get your free scan</a>
        <a class="secondary-link" href="''' + BOOK + '''" target="_blank" rel="noopener">Book a 20-minute call</a>
      </div>
      <p class="alt">Or write to hello@merchient.com</p>
    </div>
  </section>

</main>

<footer class="site-footer">
  <div class="wrap footer-inner">
    <p>Merchient is a trade name of Orbline LLC, 30 N Gould St, STE R, Sheridan, WY 82801, USA.</p>
    <p><a href="mailto:hello@merchient.com">hello@merchient.com</a></p>
    <p class="footer-more"><a href="../rescue">Send a rejected ad</a> · <a href="../claims-watch">Claims Watch</a> · <a href="../pricing">Price</a> · <a href="../agencies">Agencies</a> · <a href="../founder">Why I built this</a></p>
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
            <input type="hidden" name="subject" value="Free&nbsp;scan&nbsp;request">
            <label for="scan-website">Your website</label>
            <input id="scan-website" name="body" type="text" inputmode="url" autocomplete="url" placeholder="yourbrand.com" required>
            <button class="btn" type="submit">Get your free scan</button>
            <p class="scan-note">Your email app opens with the request ready to send.</p>
          </form>
          <!--/scan-->'''
SCAN_ON = '''<!--scan-->
          <form class="scan" action="mailto:hello@merchient.com" method="get" data-api="%s">
            <input type="hidden" name="subject" value="Free&nbsp;scan&nbsp;request">
            <label for="scan-website">Your website</label>
            <input id="scan-website" name="body" type="text" inputmode="url" autocomplete="url" placeholder="yourbrand.com" required>
            <label for="scan-email">Your work email</label>
            <input id="scan-email" name="email" type="email" autocomplete="email" required>
            <button class="btn" type="submit">Get your free scan</button>
            <p class="scan-note">We send your website and work email to Merchient\u2019s scan service (api.merchient.com), which emails you a link to confirm. If it does not answer, your email app opens with the request ready.</p>
            <p class="scan-msg" role="status"></p>
          </form>
          <script src="scan.js"></script>
          <!--/scan-->'''
SCAN_JS = '''// The scan box on the home page. Without this script the form opens the "Free scan request" email. With it, the
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
    window.location.href = 'mailto:hello@merchient.com?subject=Free%20scan%20request&body=' +
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


FOOTER_MORE = re.compile(r'(<p class="footer-more">)(.*?)(</p>)', re.S)


def founder_link(page, rel):
    """Adds "Why I built this" to the footer line of a hand-written page. The generated pages carry it in their templates."""
    prefix = '/' if rel == '404.html' else '../' * rel.count(os.sep)
    link = ' · <a href="%sfounder">Why I built this</a>' % prefix
    return FOOTER_MORE.sub(lambda m: m.group(0) if 'founder"' in m.group(2) else m.group(1) + m.group(2) + link + m.group(3), page)


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
      <a class="btn btn-small" href="@SCAN@">Get your free scan</a>
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
    <p class="footer-more"><a href="@UP@rescue">Send a rejected ad</a> · <a href="@UP@claims-watch">Claims Watch</a> · <a href="@UP@pricing">Price</a> · <a href="@UP@agencies">Agencies</a> · <a href="@UP@founder">Why I built this</a></p>
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
    <p>Want to know where your own ads fall? Put your website in the box on the <a href="../scan">home page</a> for a free scan.</p>

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
    <p>Want your own page read the same way? <a href="../../scan">Get your free scan</a>.</p>

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
    <p>Want your own page read the same way? <a href="../scan">Get your free scan</a>.</p>

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
    with open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8') as f:
        listed = re.findall(r'<loc>([^<]+)</loc>', f.read())
    urls = [u for u in listed if not u.startswith((SITE + 'ingredients/', SITE + 'winning-lines/'))]
    if winning:
        urls += [SITE + 'winning-lines/'] + [SITE + 'winning-lines/%s/' % slug for slug, _ in winning]
    urls += [SITE + 'ingredients/'] + [SITE + 'ingredients/%s.html' % g['slug'] for g in guides]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + ''.join('  <url><loc>%s</loc></url>\n' % u for u in urls) + '</urlset>\n')


def pages():
    """The site's own pages, outside the generated folder."""
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in ('ingredients', 'data', 'fonts', 'reports', 'previews'))
        for name in sorted(files):
            if name.endswith('.html'):
                yield os.path.relpath(os.path.join(folder, name), ROOT)


def main():
    args = sys.argv[1:]
    if args not in ([], ['--check']):
        sys.exit('usage: python3 build.py [--check]')
    if type(FOUNDING_PLACES_LEFT) is not int or not 0 <= FOUNDING_PLACES_LEFT <= FOUNDING_PLACES:
        fail('FOUNDING_PLACES_LEFT must be a whole number from 0 to %d' % FOUNDING_PLACES)
    index, guides = load()

    want, shown = {}, 0
    for p in pages():
        with open(os.path.join(ROOT, p), encoding='utf-8') as f:
            was = f.read()
        new, n = PLACES.subn(lambda m: m.group(1) + str(FOUNDING_PLACES_LEFT) + m.group(2), was)
        if p == 'index.html':
            # Site 47: the home page's proof is the v3 {{index...}} fields; the weekly sweeps line (sweeps_apply) is no
            # longer on it.
            new = scan_apply(new)
        new = fields_apply(founder_link(new, p))
        if n or p == 'index.html' or new != was or PLACEHOLDER.search(new) or FIELD_SPAN.search(new):
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
