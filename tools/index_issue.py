"""Site 43: builds one issue of the supplement ad index, data/index-<year>-<month>.json. Counts only: the JSON holds no brand,
domain, page name, ad id or quote (the script reads them to join the files and to sort the reasons, and writes none of them).

  python3 -I tools/index_issue.py build --month 2026-11 [--through YYYY-MM-DD]
  python3 -I tools/index_issue.py selftest

It is reports/tools/make_index39.py promoted (that file stays where it is, unchanged). What moved over unchanged: the rule
table, the plain-words texts for the five most-hit rules, the search-word groups, rule_of() and the percentage rounding.
What is new: the month and --through window, the brand-lookup exclusion, the duplicate rule, the age block from survival.tsv,
the sweep facts, the counts file, and selftest.

Reads (read only):
  ~/code/merchient-sales/handoff/adlibrary/*-lines.tsv   Vera's reading of each ad: fit, tier, rule, reason. The day an ad was
                                                         judged is the date at the start of its file name.
  ~/code/merchient-mining/sources/adlibrary/             the ads (search word, start date, note) and survival.tsv (days running)
Writes: data/index-<month>.json, and reports/index-<month>.counts.json (in = out + drops).

Rules of the count:
  * Only rows with fit = yes are ads read. A file counts if its date is in the month and not after --through.
  * An ad is counted once, at the first reading of it in any lines file (survival.tsv does the same). A later row for the same
    ad is a re-reading and is dropped.
  * An ad found only by a brand lookup (every mining row for it has a search that reads "brand: ...") is left out of every
    count: those brands were chosen by us, not by a search. An ad that a keyword sweep also found stays in.
  * Days running is survival.tsv's age_days_at_judgment, for the issue's own ads only. An ad with no row there is counted
    everywhere else, and in the table is shown as "no age yet" (running.<tier>.no_age).
"""
import argparse
import calendar
import collections
import csv
import datetime
import glob
import json
import os
import re
import statistics
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser('~/code')
LINES_DIR = HOME + '/merchient-sales/handoff/adlibrary'
MINING_DIR = HOME + '/merchient-mining/sources/adlibrary'
MONTHS = {m: i + 1 for i, m in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split())}
TIERS = ('Red', 'Yellow', 'Green')

# ---- moved unchanged from make_index39.py -------------------------------------------------------------------------------
# The rules: the reason Vera gave is sorted by its words into one of these. Order matters: the first match wins.
RULES = [
    ('fda_wordpass', 'FDA', r'The judge named no rule'),
    ('fda_disclaimer', 'FDA', r'disclaimer'),
    ('fda_drug', 'FDA', r'prescription drug|prescription class|\bdrugs\b|statin|Prozac|surgical'),
    ('fda_disease', 'FDA', r'.'),
    ('ftc_testimonial', 'FTC', r'testimonial|story centres'),
    ('ftc_deadline', 'FTC', r'deadline'),
    ('ftc_figure', 'FTC', r'figure|numbered comparison'),
    ('ftc_proof', 'FTC', r'.'),
    ('meta_weight', 'Meta', r'weight-loss|waist|burning fat|body part'),
    ('meta_urgency', 'Meta', r'countdown|urgency|price goes back'),
    ('meta_personal', 'Meta', r'.'),
]
NAMES = {
    'fda_disease': 'A line that promises relief from, or names, a disease or a symptom',
    'fda_drug': 'The product set beside a prescription drug, a medical device or surgery',
    'fda_disclaimer': 'No supplement disclaimer beside a claim about how the body works',
    'fda_wordpass': 'A word that points to a condition, with no rule named',
    'ftc_proof': 'Proof or ranking words with no basis shown',
    'ftc_figure': 'A number with no source',
    'ftc_deadline': 'A result by a deadline, or a guarantee',
    'ftc_testimonial': 'A customer story about a disease or an unusual result',
    'meta_personal': 'A line that tells or asks the viewer about their own health',
    'meta_weight': 'A weight-loss promise, or picking on a body part',
    'meta_urgency': 'A countdown or a rising price that is not true',
}
AUTH = {'fda': 'FDA', 'ftc': 'FTC', 'meta': 'Meta'}
SHORT = {
    'fda_disease': 'Disease or symptom claim (FDA)',
    'fda_drug': 'Beside a prescription drug (FDA)',
    'fda_disclaimer': 'Missing disclaimer (FDA)',
    'fda_wordpass': 'A condition word, no rule named (FDA)',
    'ftc_proof': 'Proof or ranking words (FTC)',
    'ftc_figure': 'A number with no source (FTC)',
    'ftc_deadline': 'A deadline or a guarantee (FTC)',
    'ftc_testimonial': 'A customer story (FTC)',
    'meta_personal': 'Speaks to the viewer’s health (Meta)',
    'meta_weight': 'Weight loss, body parts (Meta)',
    'meta_urgency': 'A false countdown (Meta)',
}
# The five rules most hit: the rule in plain words, and one example, described. No brand, domain, ad id or quote;
# each kind of line is in many ads. A rule that enters the top five in a later month needs its text here.
TOP_TEXT = {
    'fda_disease': (
        'The FDA reads a line that says a product relieves, fixes or prevents a disease or a symptom as a drug claim. '
        'A supplement can describe how it supports the body; it can’t say it treats a condition.',
        'A headline that promises to fix a named gland.'),
    'ftc_proof': (
        'The FTC expects a brand to be able to prove what its words claim. “Clinically proven”, “science-backed”, '
        '“best-selling” and “the only” need evidence behind them, and an ad that shows none is flagged.',
        'An ad that calls its product “scientifically proven” and names no study.'),
    'meta_personal': (
        'Meta’s personal-attributes rule bars an ad that tells or asks the viewer about their own health, with words such as '
        '“you have”, “struggling with” or “diagnosed with”.',
        'A line that tells the viewer they have a named urinary symptom.'),
    'fda_drug': (
        'Naming a prescription drug, a medical device or surgery next to a supplement, or pitching the supplement to people on a '
        'drug, reads to the FDA as a disease claim.',
        'A headline that offers a supplement to people on a weight-loss drug.'),
    'meta_weight': (
        'Meta’s health-and-wellness standards bar weight-loss promises and before-and-after bodies, and an ad that picks on a '
        'body part or appearance.',
        'A review that sells a product by the slimmer waist it gave.'),
    # added in site 43: the rule entered the top five when October's ads left the November issue
    'fda_wordpass': (
        'Vera’s word pass flagged a word that points to a health condition, but the judge named no rule for the line, '
        'so a person should read it before it leads an ad.',
        'A line with a symptom word in it that only the word pass flagged.'),
}
# The sweep's search word, grouped. A word not listed is "other". One ad is in one group.
CATEGORIES = [
    ('GLP-1 and weight', ['GLP-1 supplement', 'weight loss supplement', 'weight loss gummies', 'keto supplement',
                          'metabolism booster', 'ozempic alternative', 'acv gummies']),
    ('Sleep', ['magnesium sleep', 'sleep supplement']),
    ('Gut', ['gut health supplement', 'bloating supplement', 'digestive enzymes', 'probiotic for women',
             'colon cleanse', 'parasite cleanse', 'greens powder']),
    ('Immunity', ['immune support supplement', 'colostrum supplement']),
    ('Brain', ['focus brain supplement', 'nootropic', 'focus gummies', 'lions mane', 'memory supplement']),
    ('Hormones', ['cortisol supplement', 'cortisol belly', 'libido supplement women', 'menopause supplement',
                  'perimenopause supplement', 'PCOS supplement', 'testosterone men over 40', 'testosterone booster',
                  'tongkat ali', 'hormone balance supplement', 'fertility supplement', 'thyroid support']),
    ('Joints', ['joint pain supplement', 'gout supplement', 'bone density supplement']),
    ('Skin and hair', ['hair growth supplement', 'collagen supplement']),
]
SEARCH_TO_CAT = {w: c for c, ws in CATEGORIES for w in ws}


def rule_of(row):
    first = re.split(r'(?<=[.!?])\s+', row['reason'].strip())[0]    # the closing sentences are the same for every rule
    if first.startswith('Naming a disease, a drug or a medical device'):
        # a stock sentence for two kinds of line (evidence reviewer, site 39): a drug named, or only a disease named
        if re.search(r'GLP|Ozempic|Wegovy|statin|medication|\bmeds\b', row['quote']):
            return 'fda_drug'
        return 'fda_disease'
    for key, auth, pattern in RULES:
        if auth == row['rule'] and re.search(pattern, first):
            return key
    raise SystemExit('no rule for a row with authority %r' % row['rule'])


def pct(a, b):
    return int(100.0 * a / b + 0.5)    # halves go up (5 of 8 is 63%)
# ---- end of the moved part ---------------------------------------------------------------------------------------------


def read(path):
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE))


def file_day(path):
    m = re.match(r'(\d{4})-(\d\d)-(\d\d)', os.path.basename(path))
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def started(s):
    """'2 Nov 2026' (a brand-lookup row may carry more text after the year)."""
    m = re.match(r'\s*(\d{1,2}) (\w{3}) (\d{4})', s)
    if not m or m.group(2) not in MONTHS:
        return None
    return datetime.date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))


def is_brand_lookup(search):
    return search.strip().lower().startswith('brand:')


def mining_files(mining_dir):
    out = []
    for p in sorted(glob.glob(mining_dir + '/????-??-??*.tsv')):
        name = os.path.basename(p)
        if re.fullmatch(r'\d{4}-\d\d-\d\d(-[A-Za-z0-9]+)?\.tsv', name) and not re.search(r'-(contacts|people)\.tsv$', name):
            out.append(p)
    return out


def load_mining(mining_dir):
    """library_id -> the mining rows for it, in file order: (file name, row)."""
    mined = collections.defaultdict(list)
    for p in mining_files(mining_dir):
        for r in read(p):
            mined[r['library_id']].append((os.path.basename(p), r))
    return mined


def sweep_recorded(mining_dir, name):
    """A sweep file whose notes record the filters the issue states: active ads, US, sorted by impressions."""
    notes = [r.get('note', '') for r in read(os.path.join(mining_dir, name))]
    return any('active' in n and re.search(r'\bUS\b', n) and 'sorted by impressions' in n for n in notes)


def quartiles(v):
    v = sorted(v)
    if len(v) == 1:
        return float(v[0]), float(v[0]), float(v[0])
    q = statistics.quantiles(v, n=4, method='inclusive')    # linear interpolation, as the mining lane's survival-number.json
    return float(q[0]), float(statistics.median(v)), float(q[2])


def window(month, through):
    if not re.fullmatch(r'\d{4}-\d\d', month):
        raise SystemExit('--month must look like 2026-11')
    y, m = int(month[:4]), int(month[5:])
    if not 1 <= m <= 12:
        raise SystemExit('--month must look like 2026-11')
    first = datetime.date(y, m, 1)
    last = datetime.date(y, m, calendar.monthrange(y, m)[1])
    if through:
        t = datetime.date.fromisoformat(through)
        if not first <= t <= last:
            raise SystemExit('--through %s is not in %s' % (through, month))
        last = t
    return first, last


def collect(month, through, lines_dir, mining_dir):
    """Returns (ads counted, the counts for the counts file, brand lookups left out)."""
    first, last = window(month, through)
    mined = load_mining(mining_dir)
    survival = {r['library_id']: r for r in read(mining_dir + '/survival.tsv')}
    seen = set()
    ads = []
    c = collections.Counter()
    for p in sorted(glob.glob(lines_dir + '/*-lines.tsv')):
        day = file_day(p)
        in_window = first <= day <= last
        for r in read(p):
            if in_window:
                c['in'] += 1
            lid = r['library_id']
            is_fit = r['fit'].strip().lower() == 'yes'
            if not is_fit:
                if in_window:
                    c['not_fit'] += 1
                continue
            if lid in seen:
                if in_window:
                    c['read_twice'] += 1
                continue
            seen.add(lid)
            if not in_window:
                continue
            rows = mined.get(lid)
            if not rows:
                raise SystemExit('an ad read has no mining row (no start date, no search word): ' + lid)
            kw = [(f, m) for f, m in rows if not is_brand_lookup(m['search'])]
            if not kw:
                c['brand_lookup'] += 1
                continue
            if r['tier'] not in TIERS:
                raise SystemExit('an ad read has no tier: ' + lid)
            f, m = kw[0]
            s = survival.get(lid)
            if s is not None and s['tier'] != r['tier']:
                raise SystemExit('survival.tsv gives a different tier from the lines file for ' + lid + ': ask the mining lane to rebuild it')
            if s is not None:
                age = int(s['age_days_at_judgment'])
                if age < 0:
                    raise SystemExit('an ad started after it was read: ' + lid)
            else:
                age = None
            ads.append({
                'tier': r['tier'], 'age': age, 'read': day.isoformat(), 'sweep': f,
                'rule': rule_of(r) if r['tier'] != 'Green' else None,
                'cat': SEARCH_TO_CAT.get(m['search'], 'Other'), 'search': m['search'], 'domain': r['domain'],
            })
    c['out'] = len(ads)
    if c['in'] != c['out'] + c['not_fit'] + c['read_twice'] + c['brand_lookup']:
        raise SystemExit('the counts do not add up: %r' % dict(c))
    return ads, c


def age_table(ads):
    out = {}
    for tier in TIERS:
        group = [a for a in ads if a['tier'] == tier]
        d = [a['age'] for a in group if a['age'] is not None]
        if d:
            q1, med, q3 = quartiles(d)
        else:
            q1 = med = q3 = None
        out[tier] = {
            'ads': len(d), 'no_age': len(group) - len(d), 'median_days': med, 'q1_days': q1, 'q3_days': q3,
            'at_90_plus': sum(1 for x in d if x >= 90), 'under_30': sum(1 for x in d if x < 30),
            'share_90_plus': pct(sum(1 for x in d if x >= 90), len(d)) if d else None,
            'share_under_30': pct(sum(1 for x in d if x < 30), len(d)) if d else None,
        }
    return out


def build(month, through, lines_dir, mining_dir, out_path, counts_path):
    ads, c = collect(month, through, lines_dir, mining_dir)
    if not ads:
        raise SystemExit('no ads read in %s%s' % (month, ' through ' + through if through else ''))
    tiers = collections.Counter(a['tier'] for a in ads)
    flagged = [a for a in ads if a['tier'] != 'Green']
    n = len(ads)
    by_rule = collections.Counter(a['rule'] for a in flagged)
    rules_all = [{'key': k, 'authority': AUTH[k.split('_')[0]], 'name': NAMES[k], 'ads': v,
                  'red': sum(1 for a in flagged if a['rule'] == k and a['tier'] == 'Red')}
                 for k, v in sorted(by_rule.items(), key=lambda kv: (-kv[1], kv[0]))]
    rules_top = []
    for r in rules_all[:5]:
        plain, example = TOP_TEXT[r['key']]     # a KeyError here means a new rule is in the top five: write its text first
        rules_top.append(dict(r, short=SHORT[r['key']], plain=plain, example=example))
    for r in rules_all:
        r['short'] = SHORT[r['key']]
    cats = []
    for name in [x for x, _ in CATEGORIES] + ['Other']:
        group = [a for a in ads if a['cat'] == name]
        fl = [a for a in group if a['tier'] != 'Green']
        rc = collections.Counter(a['rule'] for a in fl)
        top = sorted(rc.items(), key=lambda kv: (-kv[1], kv[0]))
        tied = [k for k, v in top if v == top[0][1]] if top else []
        cats.append({'name': name, 'ads': len(group), 'flagged': len(fl),
                     'share_flagged': pct(len(fl), len(group)) if group else 0,
                     'top_rule': tied[0] if tied else None, 'top_rule_ads': top[0][1] if top else 0,
                     'top_rule_tied_with': tied[1:]})
    sweep_files = sorted({a['sweep'] for a in ads})
    data = {
        'month': month,
        'through': through,
        'source': ('site 43: tools/index_issue.py build --month %s%s. The lines files in the sales lane (handoff/adlibrary, fit = yes) '
                   'judged in the month, joined by library id to the mining lane (sources/adlibrary) for search word and start date; '
                   'days running from its survival.tsv. Keyword sweeps only: ads found by a brand lookup are left out. Counts only: '
                   'no brand, domain, page name, ad id or quote.' % (month, (' --through ' + through) if through else '')),
        'sweeps': len(sweep_files),
        'sweeps_recorded': sum(1 for f in sweep_files if sweep_recorded(mining_dir, f)),
        'brand_lookups_left_out': c['brand_lookup'],
        'read_first': min(a['read'] for a in ads),
        'read_last': max(a['read'] for a in ads),
        'ads_read': n,
        'brands': len({a['domain'] for a in ads}),
        'tiers': {t: tiers[t] for t in TIERS},
        'flagged': len(flagged),
        'share_by_tier': {t: pct(tiers[t], n) for t in TIERS},
        'share_flagged': pct(len(flagged), n),
        'rules_top': rules_top,
        'rules_all': rules_all,
        'categories': cats,
        'category_other_words': sorted({a['search'] for a in ads if a['cat'] == 'Other'}),
        # the four search words with the most ads among "Other" (ties by name): the page names them as examples
        'category_other_examples': [w for w, _ in sorted(
            collections.Counter(a['search'] for a in ads if a['cat'] == 'Other').items(), key=lambda kv: (-kv[1], kv[0]))[:4]],
        'running': age_table(ads),
    }
    text = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    counts = {'in': c['in'], 'out': c['out'], 'dropped': [
        {'reason': 'brand lookup (the brand was chosen by us, not found by a search)', 'n': c['brand_lookup']},
        {'reason': 'read again in a later file (the first reading counts)', 'n': c['read_twice']},
        {'reason': 'not an ad read (fit is not yes)', 'n': c['not_fit']}]}
    os.makedirs(os.path.dirname(counts_path), exist_ok=True)
    with open(counts_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(counts, indent=2) + '\n')
    return data, c


# ---- selftest: ten ads in a temporary folder ----------------------------------------------------------------------------
LINE_COLS = ['domain', 'page', 'library_id', 'fit', 'fit_reason', 'quote', 'reason', 'safer', 'tier', 'rule', 'new_claim_check', 'forecast']
MINE_COLS = ['library_id', 'started', 'spend_shown', 'page', 'domain', 'headline', 'ad_text', 'search', 'note']
SURV_COLS = ['library_id', 'domain', 'tier', 'rule', 'judged_on', 'started', 'age_days_at_judgment', 'last_checked', 'status',
             'source_file', 'hours_note', 'lines_file']
R_DISEASE = 'Naming a disease, a drug or a medical device makes this a drug claim.'
R_PROOF = 'A proof word with no study named beside it.'
R_PERSONAL = 'This tells the viewer about their own health.'
NOTE = 'sweep, active US ad, sorted by impressions'


def _write(path, cols, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write('\t'.join(cols) + '\n')
        for r in rows:
            f.write('\t'.join(str(r.get(c, '')) for c in cols) + '\n')


def selftest():
    failures = []

    def check(ok, what):
        print(('ok    ' if ok else 'FAIL  ') + what)
        if not ok:
            failures.append(what)

    # id, date read, tier, rule, reason, search, start, age
    ads = [
        ('1001', '2026-10-31', 'Green', '', '', 'sleep supplement', '1 Oct 2026', 30),        # October: outside the month
        ('1002', '2026-11-01', 'Red', 'FDA', R_DISEASE, 'sleep supplement', '2 Aug 2026', 10),
        ('1003', '2026-11-01', 'Yellow', 'FTC', R_PROOF, 'ashwagandha', '25 Oct 2026', 7),
        ('1004', '2026-11-01', 'Green', '', '', 'nootropic', '2 Sep 2026', 30),
        ('1005', '2026-11-01', 'Red', 'Meta', R_PERSONAL, 'gut health supplement', '12 Oct 2026', 20),
        ('1006', '2026-11-02', 'Green', '', '', 'lions mane', '13 Sep 2026', 50),
        ('1007', '2026-11-02', 'Red', 'FDA', R_DISEASE, 'tinnitus', '3 Sep 2026', 60),
        ('1008', '2026-11-02', 'Yellow', 'FTC', R_PROOF, 'brand: Fixture Brand', '1 Jun 2026', 154),   # a brand lookup: left out
        ('1009', '2026-11-03', 'Red', 'FDA', R_DISEASE, 'sleep supplement', '4 Oct 2026', 30),         # after --through
        ('1010', '2026-11-03', 'Green', '', '', 'nootropic', '5 Oct 2026', 29),                        # after --through
    ]
    with tempfile.TemporaryDirectory() as tmp:
        lines, mining, out = tmp + '/lines', tmp + '/mining', tmp + '/site'
        os.makedirs(lines)
        os.makedirs(mining)
        by_day = collections.defaultdict(list)
        for a in ads:
            by_day[a[1]].append(a)
        for day, group in by_day.items():
            lrows = [{'domain': 'fixture-%s.example' % a[0], 'page': 'Fixture Page %s' % a[0], 'library_id': a[0], 'fit': 'yes',
                      'quote': 'FIXTURE QUOTE %s' % a[0], 'reason': a[4], 'tier': a[2], 'rule': a[3]} for a in group]
            if day == '2026-11-02':      # a re-reading of an ad first read on 1 Nov: not a new ad
                lrows.append({'domain': 'fixture-1002.example', 'library_id': '1002', 'fit': 'yes', 'quote': 'FIXTURE QUOTE 1002',
                              'reason': R_DISEASE, 'tier': 'Red', 'rule': 'FDA'})
                lrows.append({'domain': 'x.example', 'library_id': '9999', 'fit': 'no', 'tier': '', 'rule': ''})
            _write('%s/%s-lines.tsv' % (lines, day), LINE_COLS, lrows)
            mrows = [{'library_id': a[0], 'started': a[6], 'page': 'Fixture Page', 'domain': 'fixture-%s.example' % a[0],
                      'search': a[5], 'note': NOTE} for a in group]
            _write('%s/%s.tsv' % (mining, day), MINE_COLS, mrows)
        _write(mining + '/2026-11-01-contacts.tsv', ['x'], [{'x': 'must be ignored'}])
        srows = [{'library_id': a[0], 'tier': a[2], 'age_days_at_judgment': a[7], 'judged_on': a[1], 'status': 'running'} for a in ads]
        _write(mining + '/survival.tsv', SURV_COLS, srows)

        o, cts = out + '/data/index-2026-11.json', out + '/reports/index-2026-11.counts.json'
        d, c = build('2026-11', '2026-11-02', lines, mining, o, cts)
        first_bytes = open(o, 'rb').read()
        check(d['ads_read'] == 6 and d['tiers'] == {'Red': 3, 'Yellow': 1, 'Green': 2},
              'window: the October ad and the two ads after --through 2026-11-02 are out; 6 ads, tiers 3 Red, 1 Yellow, 2 Green')
        check(d['read_first'] == '2026-11-01' and d['read_last'] == '2026-11-02', 'reading dates are the first and last file in the window')
        check(d['brand_lookups_left_out'] == 1, 'the brand lookup is left out and counted (1)')
        check(c['read_twice'] == 1 and c['not_fit'] == 1 and c['in'] == c['out'] + c['read_twice'] + c['not_fit'] + c['brand_lookup'],
              'in = out + drops (the re-read row and the fit = no row are drops)')
        r = d['running']
        check((r['Red']['ads'], r['Red']['median_days'], r['Red']['q1_days'], r['Red']['q3_days']) == (3, 20.0, 15.0, 40.0),
              'age block, Red: 3 ads, median 20, Q1 15, Q3 40 (from the fixture survival file)')
        check((r['Green']['ads'], r['Green']['median_days'], r['Green']['q1_days'], r['Green']['q3_days']) == (2, 40.0, 35.0, 45.0),
              'age block, Green: 2 ads, median 40, Q1 35, Q3 45')
        check((r['Yellow']['ads'], r['Yellow']['median_days']) == (1, 7.0), 'age block, Yellow: 1 ad, median 7')
        check(r['Red']['at_90_plus'] == 0 and r['Green']['under_30'] == 0 and r['Red']['under_30'] == 2, '90+ and under-30 counts follow the ages')
        check(d['sweeps'] == 2 and d['sweeps_recorded'] == 2, 'two keyword sweeps, both with their filters recorded')
        check(d['rules_all'][0]['key'] == 'fda_disease' and d['rules_all'][0]['ads'] == 2 and d['flagged'] == 4,
              'rules: 4 flagged ads, the disease rule first with 2')
        text = open(o, encoding='utf-8').read()
        leaked = [w for w in ('fixture-', 'Fixture', 'FIXTURE', '1002', '1008', '.example') if w in text]
        check(not leaked, 'the JSON holds no brand, domain, page name, ad id or quote' + (' (found %r)' % leaked if leaked else ''))
        build('2026-11', '2026-11-02', lines, mining, o, cts)
        check(open(o, 'rb').read() == first_bytes, 'a second build is byte-identical')
        d2, c2 = build('2026-11', None, lines, mining, o, cts)
        check(d2['ads_read'] == 8 and d2['read_last'] == '2026-11-03' and d2['through'] is None, 'no --through: the ads of 3 Nov are in (8 ads)')
        # a survival file that lacks one counted ad: it stays in every count and is shown as no age yet
        _write(mining + '/survival.tsv', SURV_COLS, [s for s in srows if s['library_id'] != '1007'])
        d3, _ = build('2026-11', '2026-11-02', lines, mining, o, cts)
        check(d3['ads_read'] == 6 and d3['running']['Red']['ads'] == 2 and d3['running']['Red']['no_age'] == 1,
              'an ad missing from survival.tsv stays in the counts and is marked no_age')
        try:
            build('2026-11', '2026-12-01', lines, mining, o, cts)
            check(False, '--through outside the month is refused')
        except SystemExit:
            check(True, '--through outside the month is refused')
    if failures:
        print('selftest: %d failed' % len(failures))
        return 1
    print('selftest: all ok')
    return 0


def main():
    ap = argparse.ArgumentParser(prog='index_issue.py')
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--month', required=True, help='for example 2026-11')
    b.add_argument('--through', help='YYYY-MM-DD, a day in the month: lines files dated after it are left out')
    sub.add_parser('selftest')
    a = ap.parse_args()
    if a.cmd == 'selftest':
        sys.exit(selftest())
    out = '%s/data/index-%s.json' % (ROOT, a.month)
    counts = '%s/reports/index-%s.counts.json' % (ROOT, a.month)
    d, c = build(a.month, a.through, LINES_DIR, MINING_DIR, out, counts)
    print('wrote data/index-%s.json: %d ads read (Red %d, Yellow %d, Green %d), %d flagged, read %s to %s, %d sweeps'
          % (a.month, d['ads_read'], d['tiers']['Red'], d['tiers']['Yellow'], d['tiers']['Green'], d['flagged'],
             d['read_first'], d['read_last'], d['sweeps']))
    print('left out: %d found by a brand lookup, %d read again in a later file, %d not an ad read (fit is not yes); '
          'no days-running row in survival.tsv for %d counted ads'
          % (c['brand_lookup'], c['read_twice'], c['not_fit'], sum(v['no_age'] for v in d['running'].values())))


if __name__ == '__main__':
    main()
