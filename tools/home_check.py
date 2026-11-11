#!/usr/bin/env python3
"""Site 54: the check for the plain home page. Run: python3 -I tools/home_check.py

Exits 0 only when all nine checks hold; prints one line per check.
  1. index.html carries Varma's text (11 Nov 2026) word for word, and nothing else, on its visible text.
  2. Every href and src is one of the allowed few; none points at any page or page folder of the repo.
  3. No script, form, img, svg, iframe, og:, twitter:, external URL; the CSP meta has no script-src.
  4. sitemap.xml has exactly one <loc>: https://merchient.com/
  5. Nothing under d/ and not order-desk-template.html differs from HEAD.
  6. Every .html file that HEAD tracks still exists.
Site 55 adds three:
  7. example/outbound/index.html exists and has <meta name="robots" content="noindex, nofollow">.
  8. sitemap.xml does not list it (check 4 holds: exactly one <loc>, the home page).
  9. index.html has no link to example/.
"""
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://merchient.com/'

HEADING = 'We build and run automation for businesses'
EXPECTED = [  # Varma's text, word for word; the labels are not page text
    HEADING,
    'Merchient takes one task your team does by hand every day and makes it run by itself, with a person checking anything unclear.',
    'How we work',
    'You see it working first. Before you pay, we show the task running on sample work, and then on a piece of your own.',
    'A fixed price and a date. One page says what will be built, the price, and the day it goes live. '
    'We aim for 7 days from the day you give us access. Half is paid to start. If it is not live on the agreed day, that half is returned.',
    'We keep it running. A monthly plan covers watching it, fixing it, and changing it as your business changes. You can stop the plan in any month.',
    'How we check our work',
    'We test each system against cases with known right answers before it touches real work. '
    'It is built to stop and ask a person when it is not sure, instead of guessing.',
    'Contact',
    'akhil@merchient.com',
    'Merchient is a trading name of Orbline LLC, 30 N Gould St, Ste R, Sheridan, WY 82801, USA.',
]
FOOTER = EXPECTED[-1]
OLD_NAMES = ('rescue', 'claims-watch', 'pricing', 'agencies', 'founder', 'method', 'cases', 'ingredients', 'index',
             'winning-lines', 'scan', 'start', 'connect', 'findings', 'privacy', 'terms', 'security', 'data-deletion',
             'welcome', 'sample-report', 'sample-morning', 'vera-month', 'shopify', 'previews', 'weekly', 'd')
ALLOWED_EXACT = {'/', './', SITE, 'mailto:akhil@merchient.com', 'styles.css'}
ALLOWED_PATTERNS = (r'fonts/[A-Za-z0-9._-]+', r'favicon[A-Za-z0-9._-]*\.(?:ico|svg|png)', r'apple-touch-icon[A-Za-z0-9._-]*\.png')


def collapse(s):
    return ' '.join(s.split())


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.metas, self.header, self.body = [], [], [], []
        self.stack = []
        self.part = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k in ('href', 'src'):
            if k in a:
                self.links.append((tag, k, a[k]))
        if tag == 'meta':
            self.metas.append(a)
        if tag in ('header', 'main', 'footer'):
            self.part = tag
        if tag in ('script', 'style', 'title'):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        if tag in ('header', 'main', 'footer'):
            self.part = None

    def handle_data(self, data):
        if self.stack:
            return
        if self.part == 'header':
            self.header.append(data)
        elif self.part in ('main', 'footer'):
            self.body.append(data)


def repo_page_names():
    """Every .html file in the repo (name, stem, path) and every top-level folder that holds one, plus OLD_NAMES."""
    names = set(OLD_NAMES)
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if f.endswith('.html'):
                rel = os.path.relpath(os.path.join(folder, f), ROOT)
                names.add(rel)
                names.add(rel[:-5])
                top = rel.split(os.sep)[0]
                if os.sep in rel:
                    names.add(top)
    return names


def git(*args):
    return subprocess.run(['git', '-C', ROOT] + list(args), capture_output=True, text=True)


def main():
    results = []

    def check(name, problems):
        results.append((name, problems))

    with open(os.path.join(ROOT, 'index.html'), encoding='utf-8') as f:
        raw = f.read()
    page = Page()
    page.feed(raw)

    # 1. the text, word for word, in order, and nothing added
    visible = collapse(' '.join(page.body))
    problems, at = [], 0
    for want in EXPECTED:
        i = visible.find(want, at)
        if i < 0:
            problems.append('missing or out of order: ' + want[:50])
        else:
            at = i + len(want)
    if visible != collapse(' '.join(EXPECTED)):
        problems.append('the page text differs from Varma\'s text (something added, left out or reworded)')
    if collapse(' '.join(page.header)) != 'Merchient':
        problems.append('the header is not the plain word "Merchient"')
    h1 = re.findall(r'<h1[ >]', raw)
    h2 = re.findall(r'<h2[ >]', raw)
    if len(h1) != 1 or len(h2) != 3:
        problems.append('want one h1 and three h2, found %d and %d' % (len(h1), len(h2)))
    check('text: Varma\'s paragraphs, headings and footer line word for word, nothing added', problems)

    # 2. every href and src
    pages = repo_page_names()
    problems = []
    for tag, k, v in page.links:
        ok = v in ALLOWED_EXACT or any(re.fullmatch(p, v) for p in ALLOWED_PATTERNS)
        bare = v.split('#')[0].split('?')[0].lstrip('./').strip('/')
        old = bare in pages or (bare + '.html') in pages or bare.split('/')[0] in pages
        if v.startswith('mailto:') or v in ('/', './', SITE):
            old = False
        if not ok or old:
            problems.append('<%s %s="%s">%s' % (tag, k, v, ' (a page of the repo)' if old else ''))
    if not page.links:
        problems.append('no links found (the parser read nothing)')
    check('links: only /, ./, the canonical, mailto:akhil@merchient.com, styles.css, fonts, icons (%d checked, %d pages and folders barred)'
          % (len(page.links), len(pages)), problems)

    # 3. nothing else on the page
    problems = []
    for t in ('<script', '<form', '<img', '<svg', '<iframe'):
        if t in raw.lower():
            problems.append(t + ' found')
    for m in page.metas:
        key = (m.get('property') or m.get('name') or '').lower()
        if key.startswith(('og:', 'twitter:')):
            problems.append('meta ' + key)
    csp = [m.get('content', '') for m in page.metas if (m.get('http-equiv') or '').lower() == 'content-security-policy']
    if len(csp) != 1:
        problems.append('want one Content-Security-Policy meta, found %d' % len(csp))
    elif 'script-src' in csp[0]:
        problems.append('the CSP has a script-src')
    for u in re.findall(r'https?://[^\s"\'<>]+', raw):
        if u != SITE:
            problems.append('external URL ' + u)
    check('page: no script, form, img, svg, iframe, og:, twitter:, external URL; the CSP has no script-src', problems)

    # 4. the sitemap
    with open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8') as f:
        locs = re.findall(r'<loc>([^<]*)</loc>', f.read())
    check('sitemap: exactly one <loc>, ' + SITE, [] if locs == [SITE] else ['found %r' % locs])

    # 5. d/ and the template untouched
    r = git('diff', '--quiet', 'HEAD', '--', 'd', 'order-desk-template.html')
    check('git diff --quiet HEAD -- d order-desk-template.html', [] if r.returncode == 0 else ['exit %d %s' % (r.returncode, r.stderr.strip())])

    # 6. every tracked old page still exists
    r = git('ls-tree', '-r', '--name-only', 'HEAD')
    tracked = [p for p in r.stdout.splitlines() if p.endswith('.html')]
    gone = [p for p in tracked if not os.path.exists(os.path.join(ROOT, p))]
    check('pages: all %d .html files tracked at HEAD still exist' % len(tracked),
          gone + ([] if r.returncode == 0 and tracked else ['git ls-tree found nothing']))

    # 7. Varma's example page exists and is noindex
    problems = []
    ex = os.path.join(ROOT, 'example', 'outbound', 'index.html')
    if not os.path.isfile(ex):
        problems.append('example/outbound/index.html does not exist')
    else:
        with open(ex, encoding='utf-8') as f:
            ex_page = Page()
            ex_page.feed(f.read())
        robots = [(m.get('content') or '').replace(' ', '').lower() for m in ex_page.metas
                  if (m.get('name') or '').lower() == 'robots']
        if 'noindex,nofollow' not in robots:
            problems.append('no <meta name="robots" content="noindex, nofollow">; found %r' % robots)
    check('example: example/outbound/index.html exists and has the noindex, nofollow meta', problems)

    # 8. the sitemap does not list it
    with open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8') as f:
        sm = f.read()
    problems = []
    if 'example' in sm:
        problems.append('sitemap.xml mentions "example"')
    if locs != [SITE]:
        problems.append('sitemap.xml <loc> list is %r, not just %s' % (locs, SITE))
    check('sitemap: does not list example/outbound/ (still the one <loc>, ' + SITE + ')', problems)

    # 9. the home page does not link to it
    problems = []
    for tag, k, v in page.links:
        if 'example' in v.lower():
            problems.append('<%s %s="%s">' % (tag, k, v))
    if re.search(r'example/', raw, re.I):
        problems.append('index.html contains the text "example/"')
    check('links: index.html has no link to example/', problems)

    bad = 0
    for name, problems in results:
        print(('ok    ' if not problems else 'FAIL  ') + name)
        for p in problems:
            print('        - ' + p)
        bad += bool(problems)
    print('words in the page text (main and footer): %d; Varma\'s text: %d' % (
        len(visible.split()), len(' '.join(EXPECTED).split())))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
