#!/usr/bin/env python3
"""build_method: writes method.html, cases/index.html and cases/0000/index.html (site 46, 5 Nov 2026).

The words are the content lane's, read only, and are not edited here:
  ~/code/merchient-content/copy/method/method.md       -> method.html
  ~/code/merchient-content/copy/cases/case-0000.md     -> cases/0000/index.html (and the case file's line on cases/index.html)

What the builder leaves out, and nothing else:
  * HTML comments (the content lane's notes to the builder).
  * The "Source" column of every table: it names the files the content lane took each fact from (judge.md, the
    claims rules, a line number), which are internal paths, not copy for a reader.
  * The few inline source marks in method.md: "(sample line 111)", "(judge.md)", "(sample)", "(case 0)".
It fails if a "Source" column or a "(... line N ...)" mark is left, or if a table row has the wrong number of cells.

  python3 tools/build_method.py            writes the three pages
  python3 tools/build_method.py --check    changes nothing; exit 1 if a page differs from what it would write
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = os.path.expanduser('~/code/merchient-content/copy')
SITE = 'https://merchient.com/'

# Marks to drop from a line of prose (each is a source note, in the content lane's abbreviations).
SOURCE_MARKS = re.compile(r' \((?:sample line \d+|judge\.md|sample|case 0)\)')
LEFTOVER = re.compile(r'\((?:[^()]*\bline[s]? \d+[^()]*|judge\.md|the claims rules[^()]*)\)')

FOOTER_MORE = ('<a href="{up}rescue">Send a rejected ad</a> · <a href="{up}claims-watch">Claims Watch</a> · '
               '<a href="{up}pricing">Price</a> · <a href="{up}agencies">Agencies</a> · '
               '<a href="{up}founder">Why I built this</a> · <a href="{up}method">How Vera decides</a> · '
               '<a href="{up}cases/">Case files</a>')

HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; font-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Merchient</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Merchient">
<meta property="og:title" content="{title} · Merchient">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="https://merchient.com/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Merchient. Keep the hook. Lose the claim.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title} · Merchient">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="https://merchient.com/og-image.png">
<meta name="twitter:image:alt" content="Merchient. Keep the hook. Lose the claim.">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f2eee3" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121210" media="(prefers-color-scheme: dark)">
<link rel="icon" href="{up}favicon.ico" sizes="32x32">
<link rel="icon" href="{up}favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{up}apple-touch-icon.png">
<link rel="preload" href="{up}fonts/archivo-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{up}styles.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="{up}">Merchient</a>
    <nav class="site-nav" aria-label="Main">
      <a href="{up}#how-it-works">How it works</a>
      <a href="{up}pricing">Price</a>
      <a href="{up}agencies">Agencies</a>
      <a href="{up}#faq">FAQ</a>
      <a href="{up}rescue">Send a rejected ad</a>
      <a class="btn btn-small" href="{up}#scan">Read my ads</a>
    </nav>
  </div>
</header>

<main id="main" class="legal">
  <div class="wrap narrow">
'''

TAIL = '''  </div>
</main>

<footer class="site-footer">
  <div class="wrap footer-inner">
    <p>Merchient is a trade name of Orbline LLC, 30 N Gould St, STE R, Sheridan, WY 82801, USA.</p>
    <p><a href="mailto:hello@merchient.com">hello@merchient.com</a></p>
    <p class="footer-more">{more}</p>
    <nav class="footer-links" aria-label="Legal">
      <a href="{up}privacy.html">Privacy</a>
      <a href="{up}terms.html">Terms</a>
      <a href="{up}data-deletion.html">Data deletion</a>
      <a href="{up}security.html">Security</a>
    </nav>
  </div>
</footer>
</body>
</html>
'''


def fail(msg):
    sys.exit('build_method: ' + msg)


def esc(s):
    return html.escape(s, quote=False)


def attr(s):
    return html.escape(s, quote=True)


def inline(s):
    """Escapes a line of copy; **bold** becomes <strong>."""
    return re.sub(r'\*\*(.+?)\*\*', lambda m: '<strong>%s</strong>' % m.group(1), esc(s))


def read(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    return re.sub(r'<!--.*?-->\n?', '', text, flags=re.S)


def blocks(text):
    """The copy as ('h1'|'h2'|'p'|'table', value) in order. A table is (header, rows)."""
    out, lines, i = [], text.split('\n'), 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1
        elif ln.startswith('# '):
            out.append(('h1', ln[2:].strip()))
            i += 1
        elif ln.startswith('## '):
            out.append(('h2', ln[3:].strip()))
            i += 1
        elif ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            head, sep, body = rows[0], rows[1], rows[2:]
            if not all(re.fullmatch(r':?-{3,}:?', c) for c in sep):
                fail('a table has no separator row after %r' % head)
            for r in body:
                if len(r) != len(head):
                    fail('a table row has %d cells, the header %d: %r' % (len(r), len(head), r))
            out.append(('table', (head, body)))
        else:
            para = [ln.strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(('|', '#')):
                para.append(lines[i].strip())
                i += 1
            out.append(('p', ' '.join(para)))
    return out


def colour(cell):
    word = cell.strip()
    return '<span class="tier tier-%s">%s</span>' % (word.lower(), esc(word)) if word in ('Red', 'Yellow', 'Green') else inline(cell)


def table(head, body):
    keep = [k for k, h in enumerate(head) if h != 'Source']
    cols = [head[k] for k in keep]
    out = ['<div class="rb-wrap">', '<table class="rb">', '<thead><tr>' + ''.join('<th scope="col">%s</th>' % esc(c) for c in cols) + '</tr></thead>', '<tbody>']
    for r in body:
        cells = []
        for k in keep:
            label = ' data-label="%s"' % attr(head[k]) if head[k] else ''
            cells.append('<td%s>%s</td>' % (label, colour(r[k]) if head[k] == 'Colour' else inline(r[k])))
        out.append('<tr>' + ''.join(cells) + '</tr>')
    out += ['</tbody>', '</table>', '</div>']
    return '\n'.join(out)


def render(items, skip_h1=False, link_case=False):
    out = []
    for kind, v in items:
        if kind == 'h1' and skip_h1:
            continue
        if kind == 'h2':
            out.append('<h2>%s</h2>' % esc(v))
        elif kind == 'table':
            out.append(table(*v))
        elif kind == 'p':
            v = SOURCE_MARKS.sub('', v)
            if LEFTOVER.search(v):
                fail('a source mark is left in: %r' % v)
            line = inline(v)
            if link_case:
                line = line.replace('Case file #0', '<a href="cases/0000/">Case file #0</a>', 1)
            out.append('<p>%s</p>' % line)
    return '\n'.join(out)


def method_page():
    items = blocks(read(os.path.join(COPY, 'method', 'method.md')))
    for kind, v in items:
        if kind == 'table' and 'Source' not in v[0]:
            fail('a method table has no Source column to drop: %r' % v[0])
    lede = items[0]
    if lede[0] != 'p':
        fail('method.md should open with its paragraph')
    desc = ('How Vera decides: the two questions every line gets, who would act, Red, Yellow and Green, '
            'CONFIRMED and GUESS, what she read, and what she never says.')
    page = HEAD.format(title='How Vera decides', description=attr(desc), url=SITE + 'method', up='./')  # './' so the header links read ./#faq, like pricing.html's
    page += '    <p class="kicker">Method</p>\n    <h1>How Vera decides.</h1>\n'
    page += '    <p class="section-lede">%s</p>\n' % inline(SOURCE_MARKS.sub('', lede[1]))
    page += render(items[1:], link_case=True).replace('\n', '\n    ').join(['    ', '']) + '\n'
    page += '\n    <p class="warnings">Risk review, not legal advice.</p>\n'
    page += '    <p class="more-link"><a class="sample-link" href="cases/">Case files</a></p>\n'
    return page + TAIL.format(up='./', more=FOOTER_MORE.format(up='./'))


def case_items():
    items = blocks(read(os.path.join(COPY, 'cases', 'case-0000.md')))
    if items[0] != ('h1', 'Case file #0: our own first ad') or items[1][0] != 'p':
        fail('case-0000.md does not open with its title and paragraph')
    return items


def case_page():
    items = case_items()
    intro = items[1][1]
    desc = ('Case file #0: Merchient reads its own first Meta ad the way it reads a brand’s. Every line, '
            'its colour, its rule, and what was and was not checked.')
    page = HEAD.format(title='Case file #0: our own first ad', description=attr(desc), url=SITE + 'cases/0000/', up='../../')
    page += '    <p class="kicker">Case file</p>\n    <h1>%s</h1>\n' % esc(items[0][1])
    page += '    <p class="section-lede">%s</p>\n' % inline(intro)
    page += render(items[2:]).replace('\n', '\n    ').join(['    ', '']) + '\n'
    page += '\n    <p class="warnings">Risk review, not legal advice.</p>\n'
    page += '    <p class="more-link"><a class="sample-link" href="../../method">How Vera decides</a> · <a class="sample-link" href="../">All case files</a></p>\n'
    return page + TAIL.format(up='../../', more=FOOTER_MORE.format(up='../../'))


def cases_index_page():
    items = case_items()
    closing = items[-1]
    if closing[0] != 'p' or not closing[1].startswith('Case files #1 onward'):
        fail('case-0000.md should end with the line about case files #1 onward')
    desc = 'Case files: the numbered list. Case file #0: our own first ad. Every line, with its colour and its rule, and what was and was not checked.'
    page = HEAD.format(title='Case files', description=attr(desc), url=SITE + 'cases/', up='../')
    page += '    <p class="kicker">Case file</p>\n    <h1>Case files.</h1>\n'
    page += '    <ol class="case-list" start="0">\n'
    page += ('      <li><h2><a href="0000/">%s</a></h2>\n        <p>%s</p></li>\n    </ol>\n'
             % (esc(items[0][1]), inline(items[1][1])))
    page += '    <p>%s</p>\n' % inline(closing[1])
    page += '\n    <p class="warnings">Risk review, not legal advice.</p>\n'
    page += '    <p class="more-link"><a class="sample-link" href="../method">How Vera decides</a></p>\n'
    return page + TAIL.format(up='../', more=FOOTER_MORE.format(up='../'))


def main():
    args = sys.argv[1:]
    if args not in ([], ['--check']):
        sys.exit('usage: python3 tools/build_method.py [--check]')
    want = {'method.html': method_page(), os.path.join('cases', 'index.html'): cases_index_page(),
            os.path.join('cases', '0000', 'index.html'): case_page()}
    stale = 0
    for rel, text in want.items():
        path = os.path.join(ROOT, rel)
        was = open(path, encoding='utf-8').read() if os.path.exists(path) else None
        if args:
            if was != text:
                print('out of date: ' + rel)
                stale += 1
        elif was != text:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            print('wrote ' + rel)
    if args:
        if stale:
            sys.exit(1)
        print('up to date (%d pages)' % len(want))


if __name__ == '__main__':
    main()
