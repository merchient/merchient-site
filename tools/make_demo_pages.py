#!/usr/bin/env python3
"""Makes the order-desk demonstration pages (site 53).

    python3 tools/make_demo_pages.py --campaign <name> [--contacts <path>] [--dry-run]
    python3 -I tools/make_demo_pages.py --selftest

For each row of the campaign's contacts file that has a company and a domain, it writes
d/<company-slug>-<six random lowercase letters and digits>/index.html from order-desk-template.html: both
{{COMPANY}} placeholders become the company name, HTML-escaped, and nothing else in the template changes. The tool
checks that, and refuses to write a page that is not the template with only those two replacements, or that lacks
<meta name="robots" content="noindex, nofollow">.

d/map.tsv (campaign, domain, company, slug, demo_url, created) is the file the sales lane reads
(`scout campaign demo-urls`). One page per domain per campaign: a domain already in the map keeps its page and its
URL. The contacts file (the sales lane's) is only read; this tool writes nothing outside this folder's d/ and
reports/. build.py never lists or touches anything under d/.

Never pushed from here; a person publishes.
"""

import argparse
import csv
import datetime
import html
import json
import os
import re
import secrets
import string
import sys
import tempfile
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://merchient.com/'
PLACEHOLDER = '{{COMPANY}}'
NOINDEX = '<meta name="robots" content="noindex, nofollow">'
MAP_COLUMNS = ['campaign', 'domain', 'company', 'slug', 'demo_url', 'created']
MAX_SLUG = 40            # the whole slug, company part and random part together
RANDOM_LEN = 6
ALPHABET = string.ascii_lowercase + string.digits
SLUG_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
FALLBACK_WORD = 'demo'   # a company name with no ASCII letter or digit in it


class Refuse(Exception):
    """The tool will not write this."""


def clean_name(s):
    return ' '.join((s or '').split())


def clean_domain(s):
    d = (s or '').strip().lower()
    d = re.sub(r'^[a-z][a-z0-9+.-]*://', '', d)
    d = d.split('/')[0].split('?')[0].split('#')[0]
    d = re.sub(r'^www\.', '', d).rstrip('.')
    return d


def company_slug(company, room=MAX_SLUG - RANDOM_LEN - 1):
    """Lower case ASCII words joined by hyphens, cut at a word edge so the company part is at most `room` long."""
    ascii_ = unicodedata.normalize('NFKD', company).encode('ascii', 'ignore').decode('ascii').lower()
    words = re.findall(r'[a-z0-9]+', ascii_)
    out = ''
    for w in words:
        nxt = w if not out else out + '-' + w
        if len(nxt) > room:
            if not out:
                out = w[:room]  # one very long first word
            break
        out = nxt
    return out or FALLBACK_WORD


def random_part():
    return ''.join(secrets.choice(ALPHABET) for _ in range(RANDOM_LEN))


def new_slug(company, taken):
    base = company_slug(company)
    for _ in range(1000):
        slug = base + '-' + random_part()
        if slug not in taken:
            return slug
    raise Refuse('could not find a free slug for %r' % company)


def render(template, company):
    """The template with only its two {{COMPANY}} placeholders replaced by the escaped name; checked, or refused."""
    if NOINDEX not in template:
        raise Refuse('the template has no ' + NOINDEX)
    parts = template.split(PLACEHOLDER)
    if len(parts) != 3:
        raise Refuse('the template must hold exactly two %s (it holds %d)' % (PLACEHOLDER, len(parts) - 1))
    esc = html.escape(company, quote=True)
    if PLACEHOLDER in esc:
        raise Refuse('the company name contains %s' % PLACEHOLDER)
    out = template.replace(PLACEHOLDER, esc)
    check(template, out, esc)
    return out


def check(template, out, esc):
    """The output is the template with only those two replacements, and is noindex."""
    p0, p1, p2 = template.split(PLACEHOLDER)
    if out != p0 + esc + p1 + esc + p2:
        raise Refuse('the page is not the template with only the two replacements')
    if not (out.startswith(p0) and out.endswith(p2) and out[len(p0):len(out) - len(p2)] == esc + p1 + esc):
        raise Refuse('the page differs from the template outside the two replacements')
    if PLACEHOLDER in out:
        raise Refuse('a %s is left in the page' % PLACEHOLDER)
    if NOINDEX not in out:
        raise Refuse('the page has no ' + NOINDEX)


def read_map(path):
    rows = []
    if os.path.exists(path):
        with open(path, encoding='utf-8', newline='') as f:
            rd = csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE)
            if rd.fieldnames != MAP_COLUMNS:
                raise Refuse('%s: the columns must be %s' % (path, ', '.join(MAP_COLUMNS)))
            rows = [dict(r) for r in rd]
    return rows


def write_map(path, rows):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n', quoting=csv.QUOTE_NONE, escapechar=None)
        w.writerow(MAP_COLUMNS)
        for r in rows:
            w.writerow([r[c] for c in MAP_COLUMNS])
    os.replace(tmp, path)


def read_contacts(path):
    """(company, domain) per usable row, and the drops. The header names are matched without case."""
    rows, drops = [], {}
    with open(path, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f, delimiter='\t')
        names = {(n or '').strip().lower(): n for n in (rd.fieldnames or [])}
        if 'company' not in names or 'domain' not in names:
            raise Refuse('%s: needs a company and a domain column (has %s)' % (path, ', '.join(rd.fieldnames or []) or 'none'))
        for r in rd:
            company, domain = clean_name(r.get(names['company'])), clean_domain(r.get(names['domain']))
            if not company:
                drops['no company'] = drops.get('no company', 0) + 1
            elif not domain or '.' not in domain or ' ' in domain:
                drops['no domain'] = drops.get('no domain', 0) + 1
            else:
                rows.append((company, domain))
    return rows, drops


def run(campaign, contacts, root=ROOT, template_path=None, dry_run=False, now=None):
    """Returns (plan, counts). plan: [(status, domain, company, slug, url)], status created | kept."""
    template_path = template_path or os.path.join(root, 'order-desk-template.html')
    with open(template_path, encoding='utf-8', newline='') as f:
        template = f.read()
    rows, drops = read_contacts(contacts)
    dfolder = os.path.join(root, 'd')
    map_path = os.path.join(dfolder, 'map.tsv')
    mp = read_map(map_path)
    taken = {r['slug'] for r in mp}
    if os.path.isdir(dfolder):
        taken |= set(os.listdir(dfolder))
    have = {(r['campaign'], r['domain']): r for r in mp}
    created = (now or datetime.datetime.now(datetime.timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ')
    plan, seen = [], set()
    in_n = len(rows) + sum(drops.values())
    for company, domain in rows:
        if domain in seen:
            drops['duplicate domain in this file'] = drops.get('duplicate domain in this file', 0) + 1
            continue
        seen.add(domain)
        old = have.get((campaign, domain))
        if old:
            plan.append(('kept', domain, old['company'], old['slug'], old['demo_url']))
            continue
        slug = new_slug(company, taken)
        taken.add(slug)
        plan.append(('created', domain, company, slug, SITE + 'd/' + slug + '/'))
    # Render everything before writing anything: one refusal and nothing is written.
    pages = {}
    for status, domain, company, slug, url in plan:
        page_path = os.path.join(dfolder, slug, 'index.html')
        if status == 'created' or not os.path.exists(page_path):
            pages[slug] = render(template, company)  # a kept domain whose page file went missing gets it back at the same URL
        assert SLUG_RE.match(slug) and len(slug) <= MAX_SLUG, slug
    counts = {'in': in_n, 'out': len(plan),
              'dropped': [{'reason': k, 'n': v} for k, v in sorted(drops.items())]}
    assert counts['in'] == counts['out'] + sum(d['n'] for d in counts['dropped'])
    if dry_run:
        return plan, counts, pages
    os.makedirs(dfolder, exist_ok=True)
    for slug, content in pages.items():
        os.makedirs(os.path.join(dfolder, slug), exist_ok=True)
        with open(os.path.join(dfolder, slug, 'index.html'), 'w', encoding='utf-8', newline='') as f:
            f.write(content)
    add = [{'campaign': campaign, 'domain': d, 'company': c, 'slug': s, 'demo_url': u, 'created': created}
           for st, d, c, s, u in plan if st == 'created']
    if add:
        write_map(map_path, mp + add)
    rep = os.path.join(root, 'reports')
    os.makedirs(rep, exist_ok=True)
    with open(os.path.join(rep, 'make_demo_pages.counts.json'), 'w', encoding='utf-8') as f:
        json.dump(counts, f, indent=1)
        f.write('\n')
    return plan, counts, pages


# ---------------------------------------------------------------- selftest

def selftest():
    import importlib.util
    import shutil
    failures = []

    def ok(name, cond):
        print(('ok   ' if cond else 'FAIL ') + name)
        if not cond:
            failures.append(name)

    def refuses(fn):
        try:
            fn()
        except Refuse:
            return True
        return False

    real = os.path.join(ROOT, 'order-desk-template.html')
    mini = ('<!doctype html>\n<html><head>\n' + NOINDEX + '\n<title>Demo for ' + PLACEHOLDER + '</title></head>\n'
            '<body><span id="co">' + PLACEHOLDER + '</span> a &amp; b <script>var x = "{ }";</script></body></html>\n')

    # escaping, both placeholders, no other byte changed, noindex
    name = 'Smith & <Sons>'
    out = render(mini, name)
    ok('escaping: Smith & <Sons> becomes Smith &amp; &lt;Sons&gt;', 'Demo for Smith &amp; &lt;Sons&gt;</title>' in out and 'Smith & <' not in out)
    ok('both placeholders replaced', PLACEHOLDER not in out and out.count('Smith &amp; &lt;Sons&gt;') == 2)
    ok('no other byte changed', out == mini.replace(PLACEHOLDER, html.escape(name, quote=True)) and len(out) - len(mini) == 2 * (len(html.escape(name, quote=True)) - len(PLACEHOLDER)))
    ok('quotes escaped too', 'O&#x27;Neil &quot;Co&quot;' in render(mini, 'O\'Neil "Co"'))
    ok('noindex present in the output', NOINDEX in out)
    ok('refuses a template without noindex', refuses(lambda: render(mini.replace(NOINDEX, ''), 'A')))
    ok('refuses a template with one placeholder', refuses(lambda: render(mini.replace(PLACEHOLDER, 'x', 1), 'A')))
    ok('refuses a name that holds the placeholder', refuses(lambda: render(mini, 'A ' + PLACEHOLDER)))
    ok('check() refuses a page with one extra byte', refuses(lambda: check(mini, out + ' ', html.escape(name, quote=True))))
    ok('check() refuses a page without noindex', refuses(lambda: check(mini, out.replace(NOINDEX, ''), html.escape(name, quote=True))))
    if os.path.exists(real):
        with open(real, encoding='utf-8', newline='') as f:
            t = f.read()
        o = render(t, name)
        ok('the real template: two placeholders, noindex, only those replaced', t.count(PLACEHOLDER) == 2 and NOINDEX in o and o == t.replace(PLACEHOLDER, 'Smith &amp; &lt;Sons&gt;'))
    else:
        ok('the real template is present', False)

    # slug rules
    cases = {'Acme Rocket Co.': 'acme-rocket-co', 'Café Zürich & Sons': 'cafe-zurich-sons',
             '  --Weird___Name!!  ': 'weird-name', '東京': FALLBACK_WORD, 'Smith & <Sons>': 'smith-sons'}
    ok('company slug: lower case ASCII words joined by hyphens', all(company_slug(k) == v for k, v in cases.items()))
    long_name = 'The International Association of Extremely Long Company Names and Holdings Limited ' * 2
    s = new_slug(long_name, set())
    ok('long name: slug at most 40 characters, valid, ends in six random characters', len(s) <= MAX_SLUG and SLUG_RE.match(s) and re.search(r'-[a-z0-9]{6}$', s))
    s2 = new_slug('x' * 100, set())
    ok('one 100-letter word: still at most 40', len(s2) <= MAX_SLUG and SLUG_RE.match(s2))
    sm = sys.modules[__name__]
    calls = []
    orig = secrets.choice
    sm.secrets = type('S', (), {'choice': staticmethod(lambda a: (calls.append(1), orig(a))[1])})
    s3 = new_slug('Acme', set())
    sm.secrets = sys.modules['secrets']
    ok('the random part comes from secrets (six calls)', len(calls) == RANDOM_LEN and re.fullmatch(r'acme-[a-z0-9]{6}', s3))
    ok('two slugs for one company differ', len({new_slug('Acme', set()) for _ in range(20)}) == 20)

    # a whole run in a temporary folder: pages, map, idempotency, dry run
    tmp = tempfile.mkdtemp(prefix='demo53-')
    try:
        site, sales = os.path.join(tmp, 'site'), os.path.join(tmp, 'sales')
        os.makedirs(site)
        os.makedirs(sales)
        with open(os.path.join(site, 'order-desk-template.html'), 'w', encoding='utf-8', newline='') as f:
            f.write(mini)
        contacts = os.path.join(sales, 'contacts.tsv')
        rows = [('Contact', 'Company', 'Domain'), ('A', 'Smith & <Sons>', 'https://www.Smith-Sons.com/about'), ('B', 'Acme', 'acme.com'),
                ('C', 'Acme Again', 'acme.com'), ('D', '', 'nocompany.com'), ('E', 'No Domain', ''), ('F', 'Zürich Café', 'zurich.ch')]
        with open(contacts, 'w', encoding='utf-8', newline='') as f:
            f.write('\n'.join('\t'.join(r) for r in rows) + '\n')
        before = open(contacts, 'rb').read()
        plan, counts, _ = run('camp1', contacts, root=site, dry_run=True)
        ok('--dry-run: plans three pages, writes nothing', len(plan) == 3 and not os.path.exists(os.path.join(site, 'd')) and not os.path.exists(os.path.join(site, 'reports')))
        plan, counts, _ = run('camp1', contacts, root=site)
        mp = read_map(os.path.join(site, 'd', 'map.tsv'))
        ok('three pages and three map rows', len(mp) == 3 and all(os.path.exists(os.path.join(site, 'd', r['slug'], 'index.html')) for r in mp))
        ok('map columns and demo_url', open(os.path.join(site, 'd', 'map.tsv'), encoding='utf-8').readline().rstrip('\n').split('\t') == MAP_COLUMNS
           and all(r['demo_url'] == SITE + 'd/' + r['slug'] + '/' for r in mp))
        ok('domains cleaned (scheme, www, path, case)', [r['domain'] for r in mp] == ['smith-sons.com', 'acme.com', 'zurich.ch'])
        ok('counts: in = out + drops', counts == {'in': 6, 'out': 3, 'dropped': [
            {'reason': 'duplicate domain in this file', 'n': 1}, {'reason': 'no company', 'n': 1}, {'reason': 'no domain', 'n': 1}]}
           and json.load(open(os.path.join(site, 'reports', 'make_demo_pages.counts.json'))) == counts)
        page = open(os.path.join(site, 'd', mp[0]['slug'], 'index.html'), encoding='utf-8').read()
        ok('page = template with only the two replacements, noindex kept', page == mini.replace(PLACEHOLDER, 'Smith &amp; &lt;Sons&gt;') and NOINDEX in page)
        ok('the contacts file was not changed', open(contacts, 'rb').read() == before)
        snap = {r['slug']: open(os.path.join(site, 'd', r['slug'], 'index.html'), 'rb').read() for r in mp}
        mapbytes = open(os.path.join(site, 'd', 'map.tsv'), 'rb').read()
        plan2, _, _ = run('camp1', contacts, root=site)
        ok('idempotent: second run keeps every page and URL, map and pages byte-identical',
           [p[0] for p in plan2] == ['kept'] * 3 and open(os.path.join(site, 'd', 'map.tsv'), 'rb').read() == mapbytes
           and sorted(os.listdir(os.path.join(site, 'd'))) == sorted([r['slug'] for r in mp] + ['map.tsv'])
           and all(open(os.path.join(site, 'd', s, 'index.html'), 'rb').read() == b for s, b in snap.items()))
        gone = mp[1]['slug']
        shutil.rmtree(os.path.join(site, 'd', gone))
        run('camp1', contacts, root=site)
        ok('a kept domain whose page went missing gets it back at the same URL', open(os.path.join(site, 'd', gone, 'index.html'), 'rb').read() == snap[gone]
           and read_map(os.path.join(site, 'd', 'map.tsv')) == mp)
        plan3, _, _ = run('camp2', contacts, root=site)
        mp3 = read_map(os.path.join(site, 'd', 'map.tsv'))
        ok('another campaign gets its own pages for the same domains', [p[0] for p in plan3] == ['created'] * 3 and len(mp3) == 6
           and len({r['slug'] for r in mp3}) == 6)
        with open(os.path.join(site, 'order-desk-template.html'), 'w', encoding='utf-8', newline='') as f:
            f.write(mini.replace(NOINDEX, ''))
        with open(contacts, 'w', encoding='utf-8', newline='') as f:
            f.write('company\tdomain\nNew Co\tnew.com\n')
        ok('refuses to write a page without noindex, and writes nothing', refuses(lambda: run('camp3', contacts, root=site))
           and len(read_map(os.path.join(site, 'd', 'map.tsv'))) == 6 and len(os.listdir(os.path.join(site, 'd'))) == 7)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # build.py: the sitemap never lists d/, and no build step walks it
    spec = importlib.util.spec_from_file_location('build_for_selftest', os.path.join(ROOT, 'build.py'))
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    tmp = tempfile.mkdtemp(prefix='demo53b-')
    saved = b.ROOT
    try:
        os.makedirs(os.path.join(tmp, 'd', 'acme-abc123'))
        os.makedirs(os.path.join(tmp, 'ingredients'))
        for rel in ('index.html', 'order-desk-template.html', os.path.join('d', 'acme-abc123', 'index.html'), 'rescue.html'):
            with open(os.path.join(tmp, rel), 'w', encoding='utf-8') as f:
                f.write('<p>' + PLACEHOLDER + '</p>')
        with open(os.path.join(tmp, 'sitemap.xml'), 'w', encoding='utf-8') as f:
            f.write('<urlset><url><loc>%s</loc></url><url><loc>%sd/acme-abc123/</loc></url><url><loc>%srescue</loc></url></urlset>' % (SITE, SITE, SITE))
        b.ROOT = tmp
        sm_text = b.sitemap([], [])
        ok('build.sitemap(): a d/ URL in the old sitemap is dropped, the others stay', SITE + 'd/' not in sm_text and SITE + 'rescue' in sm_text and '<loc>' + SITE + '</loc>' in sm_text)
        walked = sorted(b.pages())
        ok('build.pages(): nothing under d/, and not the template', walked == ['index.html', 'rescue.html'])
    finally:
        b.ROOT = saved
        shutil.rmtree(tmp, ignore_errors=True)
    with open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8') as f:
        real_sm = f.read()
    ok('the real sitemap.xml lists nothing under d/', SITE + 'd/' not in real_sm and '/d/' not in real_sm)
    with open(os.path.join(ROOT, 'build.py'), encoding='utf-8') as f:
        src = f.read()
    ok('build.py skips d/ in pages() and filters it in sitemap()', "d == 'd'" in src and "SITE + 'd/'" in src)

    print('%d failed' % len(failures) if failures else 'selftest: all ok')
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser(description='Make the order-desk demonstration pages.')
    ap.add_argument('--campaign', help='the campaign name')
    ap.add_argument('--contacts', help='contacts.tsv (default ~/code/merchient-sales/campaigns/<campaign>/contacts.tsv; read only)')
    ap.add_argument('--dry-run', action='store_true', help='print what would be written; write nothing')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.campaign:
        ap.error('--campaign is required')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', a.campaign):
        ap.error('--campaign: letters, digits, dot, hyphen, underscore only')
    contacts = a.contacts or os.path.expanduser('~/code/merchient-sales/campaigns/%s/contacts.tsv' % a.campaign)
    contacts = os.path.expanduser(contacts)
    if not os.path.isfile(contacts):
        sys.exit('make_demo_pages: no contacts file at %s' % contacts)
    try:
        plan, counts, pages = run(a.campaign, contacts, dry_run=a.dry_run)
    except Refuse as e:
        sys.exit('make_demo_pages: refused: %s' % e)
    for status, domain, company, slug, url in plan:
        print('%s%-8s %-30s %s' % ('would write: ' if a.dry_run and status == 'created' else '', status, domain, url))
    n = sum(1 for p in plan if p[0] == 'created')
    print('%s%d new pages, %d kept; in %d, out %d, dropped %s' % ('dry run: ' if a.dry_run else '', n, len(plan) - n, counts['in'], counts['out'],
                                                              ', '.join('%s %d' % (d['reason'], d['n']) for d in counts['dropped']) or 'none'))


if __name__ == '__main__':
    main()
