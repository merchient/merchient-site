#!/usr/bin/env python3
"""Builds the generated parts of merchient.com.

Run it from this folder after changing FOUNDING_PLACES_LEFT or anything in data/:

    python3 build.py            writes the pages
    python3 build.py --check    changes nothing, and fails if a page is out of date

It writes three things and changes nothing else:
1. The number of founding places left, into each <strong class="places-left">
   on the site's pages.
2. The ingredient guides: ingredients/index.html, and ingredients/<slug>.html for
   each guide in data/ (the guides' JSON, copied unchanged from Merchient's library).
3. sitemap.xml: the pages it already lists stay, and the ingredient guides follow.

The terms state only the total of 5 founding places: a count that changes would
change the contract each time a place goes.

The guides' words are the library's, unchanged. Where a guide points at a part of
the library that no page shows, such as "(see notes)", the build says so; fix it
in the library, copy the JSON into data/ again and run the build.
"""

# Founding places still open, out of 5. When a founding brand joins, lower this
# by one, run python3 build.py, then commit and push.
FOUNDING_PLACES_LEFT = 5

# The scan box in the home page's hero. False: the box opens the "Free scan request"
# email, and the site runs no JavaScript. True: the box posts the website and work
# email as JSON to SCAN_API_URL with scan.js, and falls back to that email if the
# service does not answer. Switching it on also loosens the home page's content
# security policy (script-src 'self', connect-src for the service) and means the
# privacy and security pages must say where the scan data goes. Then run build.py.
# (Off, Chrome logs one console notice on https: a form that targets "mailto:" is
# not a secure endpoint. It changes nothing for the visitor.)
SCAN_API_ON = False
SCAN_API_URL = 'https://api.merchient.com/api/scan'

import html
import json
import os
import re
import sys

FOUNDING_PLACES = 5
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
      <a href="../#pricing">Price</a>
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
    <p class="footer-more"><a href="../rescue">Send a rejected ad</a> · <a href="../claims-watch">Claims Watch</a></p>
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
          <form class="scan" method="get" data-api="%s">
            <label for="scan-website">Your website</label>
            <input id="scan-website" name="website" type="text" inputmode="url" autocomplete="url" placeholder="yourbrand.com" required>
            <label for="scan-email">Your work email</label>
            <input id="scan-email" name="email" type="email" autocomplete="email" placeholder="you@yourbrand.com" required>
            <button class="btn" type="submit">Get your free scan</button>
            <p class="scan-note">We send your website and work email to Merchient\u2019s scan service to start your scan. If it does not answer, your email app opens with the request ready.</p>
            <p class="scan-msg" role="status"></p>
          </form>
          <script src="scan.js"></script>
          <!--/scan-->'''
SCAN_JS = '''// Posts the home page's scan form to Merchient's scan service. If the service does not answer, opens the "Free scan request" email instead.
(function () {
  var form = document.querySelector('form.scan[data-api]');
  if (!form) { return; }
  var msg = form.querySelector('.scan-msg');
  var button = form.querySelector('button');
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var website = form.elements.website.value.trim();
    var email = form.elements.email.value.trim();
    var mailto = 'mailto:hello@merchient.com?subject=Free%20scan%20request&body=' + encodeURIComponent('Website: ' + website + '\\r\\nWork email: ' + email + '\\r\\n');
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 10000);
    button.disabled = true;
    msg.textContent = 'Sending\u2026';
    fetch(form.getAttribute('data-api'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ website: website, email: email }),
      signal: controller.signal
    }).then(function (response) {
      clearTimeout(timer);
      if (!response.ok) { throw new Error('status ' + response.status); }
      msg.textContent = 'Thank you. Vera is reading your site, and your scan will be emailed to ' + email + '.';
    }).catch(function () {
      clearTimeout(timer);
      button.disabled = false;
      msg.textContent = 'Opening your email app instead.';
      window.location.href = mailto;
    });
  });
}());
'''


def scan_apply(page):
    """Writes the scan box, and the home page's content security policy, for SCAN_API_ON."""
    csp = CSP_BASE + ("script-src 'self'; connect-src %s; form-action 'none'" % SCAN_API_URL.rsplit('/', 2)[0]
                      if SCAN_API_ON else 'form-action mailto:')
    box = SCAN_ON % html.escape(SCAN_API_URL, quote=True) if SCAN_API_ON else SCAN_OFF
    page, n = SCAN_BLOCK.subn(lambda m: box, page)
    page, c = CSP_META.subn(lambda m: '<meta http-equiv="Content-Security-Policy" content="%s">' % csp, page)
    if n != 1 or c != 1:
        fail('index.html: the scan box markers or the content security policy meta are missing')
    return page


def fail(message):
    sys.exit('build.py: ' + message)


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
    names = sorted(f[:-5] for f in os.listdir(data) if f.endswith('.json') and f != 'index.json')
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
            new = scan_apply(new)
        if n:
            want[p], shown = new, shown + n
    if not shown:
        fail('no page shows the founding places left (<strong class="places-left">)')
    for g in guides:
        want[os.path.join('ingredients', g['slug'] + '.html')] = guide_page(g)
    want[os.path.join('ingredients', 'index.html')] = index_page(index, guides)
    want['sitemap.xml'] = sitemap(guides)
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
        with open(os.path.join(ROOT, p), 'w', encoding='utf-8', newline='\n') as f:
            f.write(want[p])
    for p in stale:
        os.remove(os.path.join(ROOT, p))
    print('build.py: %d guides and the index; %d founding places left, shown %d times; %d files written, %d removed' % (
        len(guides), FOUNDING_PLACES_LEFT, shown, len(changed), len(stale)))


if __name__ == '__main__':
    main()
