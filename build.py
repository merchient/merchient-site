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
    <p class="footer-more"><a href="../rescue">Send a rejected ad</a> · <a href="../claims-watch">Claims Watch</a> · <a href="../pricing">Price</a> · <a href="../agencies">Agencies</a></p>
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
    csp = CSP_BASE + ("script-src 'self'; connect-src %s; form-action mailto:" % SCAN_API_URL.rsplit('/', 2)[0]
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


def fail(message):
    sys.exit('build.py: ' + message)


# The ad index (site 39, 3 Nov 2026): /index/ lists the issues, /index/<year>-<month>/ is one issue. Each issue is built
# from data/index-<year>-<month>.json, which reports/tools/make_index39.py writes from the sweep files (counts only:
# no brand, domain, page name, ad id or quote). The sentences that depend on the numbers are checked here; if a number
# makes one untrue, the build stops and the sentence has to be reworded.
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
    <p class="footer-more"><a href="@UP@rescue">Send a rejected ad</a> · <a href="@UP@claims-watch">Claims Watch</a> · <a href="@UP@pricing">Price</a> · <a href="@UP@agencies">Agencies</a></p>
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


def index_issue_page(month, d):
    where = 'data/index-%s.json' % month
    n, t, flagged, brands = d['ads_read'], d['tiers'], d['flagged'], d['brands']
    if d['month'] != month or sum(t.values()) != n or t['Red'] + t['Yellow'] != flagged or not 0 < brands <= n:
        fail(where + ': the counts do not add up')
    if brands != n or d['sweeps'] != 5:
        fail(where + ': the page says one ad from each brand, and that four of the five sweeps sorted by impressions; '
                     'with %d ads, %d brands and %d sweeps, reword both sentences' % (n, brands, d['sweeps']))
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
    if [run[k]['ads'] for k in ('Red', 'Yellow', 'Green')] != [t['Red'], t['Yellow'], t['Green']]:
        fail(where + ': the running table and the tiers disagree')
    if not all(run[k]['share_90_plus'] > 50 for k in run):
        fail(where + ': "more than half had been running 90 days or longer" is no longer true for every tier; reword that paragraph')
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
    wordpass = all_rules.get('fda_wordpass', {}).get('ads', 0)
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
        run_rows += ('            <tr><th scope="row">%s</th><td>%d</td><td>%s</td><td>%d (%s)</td><td>%d (%s)</td></tr>\n' % (
            k, v['ads'], median_text(v['median_days']), v['at_90_plus'], pc(v['share_90_plus']),
            v['under_30'], pc(v['share_under_30'])))
    shares = sorted(run[k]['share_90_plus'] for k in run)
    medians = (median_text(run['Red']['median_days']), median_text(run['Green']['median_days']))
    body = '''    <p class="kicker"><a href="./">Ad index</a></p>
    <h1>%(title)s</h1>
    <p class="section-lede">Supplement ads running on Meta, the share that carried a line Vera flags, the rules most hit and how long the ads had been running when we read them.</p>

    <h2>Ads read</h2>
    <p>From %(covered)s we read %(n)d supplement ads in Meta’s public Ad Library, in five sweeps, one ad from each of %(brands)d brands (counted by the website the ad leads to). Vera, Merchient’s AI employee, read each ad’s words against Meta’s ad rules and the FTC and FDA guidance, and gave it a tier.</p>
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

    <h2>The five rules most hit</h2>
    <p>Each flagged ad is counted once, under the rule its reason points to; we sorted Vera’s reasons into these groups. These five cover %(top_total)d of the %(flagged)d flagged ads. The other %(rest)d are spread over six smaller groups%(wordpass)s. Examples are described, not quoted: no brand, product name or ad is named.</p>
    <ol class="checklist">
%(rules)s    </ol>

    <h2>By category</h2>
    <p>Ads are grouped by the search word that found them, one group for each ad. “Other” holds the searches that fit none of the groups above it, such as prostate, blood pressure, ashwagandha and shilajit.</p>
    <ul class="checklist">
%(cats)s    </ul>
    <p>%(small)s</p>

    <h2>How long the ads had been running when we read them</h2>
    <p>Meta’s library shows the day each ad started. “Days running” is the number of days between that day and the day we read the ad.</p>
    <div class="table-wrap">
      <table class="value-table">
        <thead>
          <tr><th scope="col">Tier</th><th scope="col">Ads</th><th scope="col">Median days running</th><th scope="col">90 days or more</th><th scope="col">Under 30 days</th></tr>
        </thead>
        <tbody>
%(run_rows)s        </tbody>
      </table>
    </div>
    <p><b>What it shows.</b> Most of these ads were not new. In every tier more than half (%(lo)d%% to %(hi)d%%) had been running for 90 days or longer when we read them. The median Red ad had been running %(med_red)s days, the median Green ad %(med_green)s.</p>
    <p><b>What it does not show.</b> These ads were running when we read them, so this cannot say how many flagged ads were stopped, by the brand or by Meta: an ad that had stopped before a sweep is not in these numbers. A recheck of the same ads would show that; this issue does not. It does not say whether Meta has reviewed any of these ads or what it decided. Four of the five sweeps took the library’s active ads sorted by impressions, so the ads lean towards those that reach many people; the first sweep did not record its order, or its filters. These ads are not a random sample of supplement ads.</p>

    <h2>What changed since last issue</h2>
    <p>This is the first issue, so there is nothing to compare with yet.</p>

    <h2>Method</h2>
    <p>We read supplement ads in Meta’s public Ad Library: active ads for the United States (the first sweep did not record its filters), found by search words such as the ones grouped above, one ad from each brand. Vera, an AI, read each ad’s words against Meta’s published ad rules and the FTC and FDA guidance. A tier and a rule show what Vera flagged, never what Meta rejected. We do not know what Meta decided about any of these ads. Vera read each ad’s headline and the start of its text, not its picture or video or the page it leads to, so a Green ad had nothing to flag in those words and may still have a problem elsewhere. Start dates are the ones the library shows.</p>
    <p>Want to know where your own ads fall? Put your website in the box on the home page and <a href="%(up)sscan">see your own panel</a>.</p>
    <p class="warnings">Risk review, not legal advice.</p>
    <p class="more-link"><a class="sample-link" href="../">All issues</a> · <a class="sample-link" href="../../weekly/">Weekly</a> · <a class="sample-link" href="../../">Back to the home page</a></p>
''' % {
        'title': text(title), 'covered': covered, 'n': n, 'brands': brands, 'rows': rows,
        'flagged': flagged, 'flagged_pc': pc(d['share_flagged']), 'top_total': top_total, 'rest': flagged - top_total,
        'wordpass': ('; %d of those were flagged by a word check that named no rule' % wordpass) if wordpass else '',
        'rules': rules, 'cats': cat_items, 'run_rows': run_rows, 'lo': shares[0], 'hi': shares[-1],
        'med_red': medians[0], 'med_green': medians[1], 'up': '../../',
        'small': small_text,
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
    names = sorted(f[:-5] for f in os.listdir(data) if f.endswith('.json') and f not in ('index.json', 'sweeps.json')
                   and not re.fullmatch(r'index-\d{4}-\d\d\.json', f))
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


def sitemap(guides):
    with open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8') as f:
        listed = re.findall(r'<loc>([^<]+)</loc>', f.read())
    urls = [u for u in listed if not u.startswith(SITE + 'ingredients/')]
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
            new, n = PLACES.subn(lambda m: m.group(1) + str(FOUNDING_PLACES_LEFT) + m.group(2), f.read())
        if p == 'index.html':
            new = sweeps_apply(scan_apply(new))
        if n or p == 'index.html':
            want[p], shown = new, shown + n
    if not shown:
        fail('no page shows the founding places left (<strong class="places-left">)')
    for g in guides:
        want[os.path.join('ingredients', g['slug'] + '.html')] = guide_page(g)
    want[os.path.join('ingredients', 'index.html')] = index_page(index, guides)
    want['sitemap.xml'] = sitemap(guides)
    issues = index_issues()
    for month, d in issues:
        want[os.path.join('index', month, 'index.html')] = index_issue_page(month, d)
    want[os.path.join('index', 'index.html')] = index_list_page(issues)
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
    if args == ['--check']:
        if changed or stale:
            print('build.py --check: out of date: ' + ', '.join(changed + stale))
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
