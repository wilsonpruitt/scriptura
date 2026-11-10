#!/usr/bin/env python3
"""Stage D, second step (PLAN 7.2): the census's stated formulas set against de Lubac's citations. No tokens.

  python3 -I studies/sensus/scripts/formulas_vs_lubac.py            # both directions
  python3 -I studies/sensus/scripts/formulas_vs_lubac.py diagnose   # why the census misses his 3+ sense theory loci

Two directions, both by PL volume and column (within SLOP columns; Migne columns carry a-d, de
Lubac cites the bare number):
  1. Of the 269 coded formulas (132 theory), which does de Lubac cite, and for what (role)?
  2. Of de Lubac's PL citations with role 'theory', which fall on a census formula? Those that do
     not are split by how many senses he says the passage names, since the census only looked
     for three or more senses within 60 words.

Writes ledger/formulas-vs-lubac.tsv (one row per formula) and ledger/lubac-theory-vs-census.tsv
(one row per de Lubac theory citation), and prints the counts that go in STUDY.md.
"""
import collections, csv, os, re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LED = os.path.join(HERE, 'ledger')
SLOP = 1

def num(c):
    m = re.match(r'\d+', (c or '').strip())
    return int(m.group()) if m else None

def lubac_pl():
    """De Lubac's PL citations with a usable volume and column. Resolved locator columns
    (loc_vol/loc_col) win over the printed ones; non-PL series are dropped."""
    out = []
    for r in csv.DictReader(open(os.path.join(LED, 'claims-all.tsv'), encoding='utf-8'), delimiter='\t'):
        if r['series'] and r['series'] != 'PL':
            continue
        if r['verdict'] == 'not_a_reference' or r['author_final'] == 'modern':
            continue
        v, c = (r['loc_vol'], r['loc_col']) if r['loc_vol'] else (r['vol'], r['col']) if r['series'] == 'PL' else ('', '')
        v, c = num(v), num(c)
        if v and c:
            out.append(dict(r, _v=v, _c=c))
    return out

def nsenses(s):
    parts = {p.strip() for p in (s or '').split('>') if p.strip() and p.strip() not in ('other', 'none')}
    return len(parts)

def main():
    F = list(csv.DictReader(open(os.path.join(LED, 'formulas-coded.tsv'), encoding='utf-8'), delimiter='\t'))
    L = lubac_pl()
    byvol = collections.defaultdict(list)
    for r in L:
        byvol[r['_v']].append(r)
    near = lambda v, c: [r for r in byvol.get(v, ()) if abs(r['_c'] - c) <= SLOP]

    # 1. formula -> de Lubac
    unloc = collections.Counter()                 # theory citations he gives with no PL column, by author
    for r in csv.DictReader(open(os.path.join(LED, 'claims-all.tsv'), encoding='utf-8'), delimiter='\t'):
        if r['role'] == 'theory' and not (r['loc_col'] or (r['series'] == 'PL' and r['col'])):
            unloc[r['author_final']] += 1
    rows, tab = [], collections.Counter()
    for f in F:
        hits = near(num(f['vol']), num(f['col'])) if num(f['col']) else []
        roles = collections.Counter(h['role'] for h in hits)
        cited = 'no column' if not num(f['col']) else 'theory' if roles['theory'] else 'other-role' if hits else 'not cited'
        if cited in ('not cited', 'no column'):
            far = [r for r in byvol.get(num(f['vol']), ()) if r['role'] == 'theory' and r['author_final'] == f['author']
                   and (not num(f['col']) or abs(r['_c'] - num(f['col'])) <= 10)]
            if far:
                cited = 'theory, within 10 cols'
            elif unloc[f['author']]:
                cited = 'author cited for theory, no column'

        tab[(f['kind'], cited)] += 1
        rows.append([f['id'], f['vol'], f['col'], f['author'], f['author_year'], f['kind'], f['scheme'], cited,
                     ' '.join(f'{k}:{n}' for k, n in roles.most_common()),
                     ' | '.join(sorted({h['id'] for h in hits}))[:200], f['summary'][:160]])
    with open(os.path.join(LED, 'formulas-vs-lubac.tsv'), 'w', encoding='utf-8') as o:
        o.write('id\tvol\tcol\tauthor\tauthor_year\tkind\tscheme\tlubac\tlubac_roles\tlubac_ids\tsummary\n')
        for r in rows:
            o.write('\t'.join(str(x).replace('\t', ' ') for x in r) + '\n')
    kinds = ['theory', 'quotation', 'application', 'list', 'other']
    print('1. Census formulas against de Lubac (same PL vol, +/-%d col)' % SLOP)
    cats = ['theory', 'other-role', 'theory, within 10 cols', 'author cited for theory, no column', 'not cited', 'no column']
    print('| kind | formulas | ' + ' | '.join(cats) + ' |')
    print('|---|---:|' + '---:|' * len(cats))
    for k in kinds:
        t = sum(v for (kk, _), v in tab.items() if kk == k)
        print(f'| {k} | {t} | ' + ' | '.join(str(tab[(k, c)]) for c in cats) + ' |')

    # 2. de Lubac theory citation -> census
    fpos = collections.defaultdict(list)
    for f in F:
        if num(f['col']):
            fpos[num(f['vol'])].append((num(f['col']), f))
    T = [r for r in L if r['role'] == 'theory']
    out, tab2 = [], collections.Counter()
    for r in T:
        fs = [f for c, f in fpos.get(r['_v'], ()) if abs(c - r['_c']) <= SLOP]
        n = nsenses(r['senses'])
        band = '3+' if n >= 3 else str(n)
        found = 'formula' if fs else 'no'
        tab2[(band, found)] += 1
        out.append([r['id'], r['_v'], r['_c'], r['author_final'], r['year_final'], r['senses'], band, found,
                    ' '.join(f['id'] + ':' + f['kind'] for f in fs), (r['cited_for'] or '')[:200]])
    with open(os.path.join(LED, 'lubac-theory-vs-census.tsv'), 'w', encoding='utf-8') as o:
        o.write('id\tvol\tcol\tauthor\tyear\tlubac_senses\tsenses_named\tcensus\tformulas\tcited_for\n')
        for r in out:
            o.write('\t'.join(str(x).replace('\t', ' ') for x in r) + '\n')
    print(f'\n2. De Lubac theory citations in PL ({len(T)}) against the census formulas')
    print('| senses he says it names | citations | on a census formula | not |')
    print('|---|---:|---:|---:|')
    for b in ('3+', '2', '1', '0'):
        t = tab2[(b, 'formula')] + tab2[(b, 'no')]
        if t:
            print(f"| {b} | {t} | {tab2[(b, 'formula')]} ({100 * tab2[(b, 'formula')] / t:.0f}%) | {tab2[(b, 'no')]} |")
    distinct = {(r['_v'], r['_c']) for r in T}
    print(f'   distinct theory loci (vol, col): {len(distinct)}')

def diagnose():
    """Each de Lubac theory locus (3+ senses) the census missed, re-read at the TEI (columns c-1..c+1)
    with the census's own term list. The first test it passes is its cause:
      window   - formula-grade terms from 3+ of L/A/T/N in the columns, but never within 60 words
      broad    - 3+ of L/A/T/N within 60 words once broad terms (moralis, mysticus, littera...) count
      S        - 3+ families within 60 words once the spiritual family (S) counts as a sense
      wide     - 3+ families (all terms, S included) only in a window up to 200 words
      no-terms - fewer than 3 families anywhere in the three columns: he reads senses the vocabulary
                 does not name (figures, other words), or the column is off
      no-text  - the column is not in the TEI
    """
    import bisect, glob, html, importlib.util, json
    spec = importlib.util.spec_from_file_location('census', os.path.join(HERE, 'scripts', 'census.py'))
    cen = importlib.util.module_from_spec(spec); spec.loader.exec_module(cen)
    cols = json.load(open(os.path.join(HERE, 'data', 'pl-columns.json'), encoding='utf-8'))
    tei = os.path.expanduser('~/patrologia/sources/pl/tei')
    R = [r for r in csv.DictReader(open(os.path.join(LED, 'lubac-theory-vs-census.tsv'), encoding='utf-8'), delimiter='\t')
         if r['senses_named'] == '3+' and r['census'] == 'no']
    cache = {}
    def load(idno):
        if idno not in cache:
            raw = open(os.path.join(tei, idno + '.xml'), encoding='utf-8', errors='replace').read()
            body = raw[raw.find('<text'):] if '<text' in raw else raw
            body = re.sub(r'<pb\s+n="0*(\d+)([A-D]?)"\s*/?>', lambda m: f' \x01{m.group(1)}\x01 ', body)
            body = cen.norm(html.unescape(re.sub(r'<[^>]+>', ' ', body)))
            seg, cur = collections.defaultdict(list), ''
            for k, p in enumerate(re.split(r'\x01([^\x01]*)\x01', body)):
                if k % 2: cur = p
                else: seg[cur].append(p)
            cache[idno] = {c: ' '.join(v) for c, v in seg.items()}
        return cache[idno]
    def best(text, allowed, win):
        wpos = [m.start() for m in re.finditer(r'[a-z]+', text)]
        h = [(bisect.bisect_right(wpos, m.start()) - 1, cen.TERMS[int(next(g for g, v in m.groupdict().items() if v and g.startswith('t'))[1:])])
             for m in cen.RX.finditer(text)]
        h = [(w, t[1]) for w, t in h if allowed(t)]
        b = 0
        for i in range(len(h)):
            b = max(b, len({f for w, f in h[i:] if w - h[i][0] <= win}))
        return b, {f for _, f in h}
    formula = lambda t: t[0] in cen.FORMULA
    latn = lambda t: t[1] in 'LATN'
    every = lambda t: True
    out, tab, done = [], collections.Counter(), {}
    for r in R:
        key = (r['vol'], r['col'])
        if key not in done:
            v, c = r['vol'], int(r['col'])
            ids = sorted({i for x in (c - 1, c, c + 1) for i in cols.get(v, {}).get(str(x), [])})
            text = ' '.join(load(i).get(str(x), '') for i in ids for x in (c - 1, c, c + 1))
            if not text.strip():
                cause = 'no-text'
            else:
                fb, ffam = best(text, formula, 60)
                if len(ffam & set('LATN')) >= 3:
                    cause = 'window'
                elif best(text, latn, 60)[0] >= 3:
                    cause = 'broad'
                elif best(text, every, 60)[0] >= 3:
                    cause = 'S'
                elif best(text, every, 200)[0] >= 3:
                    cause = 'wide'
                else:
                    cause = 'no-terms'
            done[key] = cause
        tab[done[key]] += 1
        out.append([r['id'], r['vol'], r['col'], r['author'], r['year'], r['lubac_senses'], done[key], r['cited_for'][:200]])
    with open(os.path.join(LED, 'lubac-theory-misses.tsv'), 'w', encoding='utf-8') as o:
        o.write('id\tvol\tcol\tauthor\tyear\tlubac_senses\tcause\tcited_for\n')
        for x in out:
            o.write('\t'.join(str(y).replace('\t', ' ') for y in x) + '\n')
    loci = collections.Counter(done.values())
    print(f'{len(R)} missed citations, {len(done)} distinct loci')
    print('| cause | loci | citations |')
    print('|---|---:|---:|')
    for k in ('window', 'broad', 'S', 'wide', 'no-terms', 'no-text'):
        print(f'| {k} | {loci[k]} | {tab[k]} |')

if __name__ == '__main__':
    import sys
    diagnose() if sys.argv[1:] == ['diagnose'] else main()
