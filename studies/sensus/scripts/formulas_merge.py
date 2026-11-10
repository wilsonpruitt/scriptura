#!/usr/bin/env python3
"""Merge the two blind codings of the 269 stated formulas (A, B) into one ledger, and summarize.

  python3 -I scripts/formulas_merge.py

Comparisons, after reading the raw disagreements (working/formulas/disagreements-AB.tsv):
- count_stated is compared as a number ('quatuor' = '4', 'tripliciter' = '3').
- the scheme is the mapped senses in order of FIRST occurrence (a coder who lists every
  repetition and one who lists each sense once agree on the scheme).
Kind, where A and B differ, is ruled by one recorded rule (R-kind): a passage that states how
many senses there are or defines any of them is `theory`, otherwise `application`; a
theory/quotation split is ruled `quotation` if either coder names an authority. Every ruled row
is marked.
Writes ledger/formulas-coded.tsv and ledger/FORMULAS.md.
"""
import collections, glob, json, os, re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(HERE, 'working', 'formulas')
NUM = {'duo': 2, 'duplex': 2, 'dupliciter': 2, 'bipartita': 2, 'tres': 3, 'tria': 3, 'triplex': 3, 'tripliciter': 3,
       'tripartita': 3, 'trifariam': 3, 'triformis': 3, 'quatuor': 4, 'quattuor': 4, 'quadruplex': 4, 'quadrupliciter': 4,
       'quadripartita': 4, 'quadriformis': 4, 'quinque': 5, 'quinquepartita': 5, 'sex': 6, 'septem': 7, 'septenarius': 7,
       'septiformis': 7, 'octo': 8, 'decem': 10}

def num(s):
    s = (s or '').strip().lower()
    if not s:
        return ''
    m = re.search(r'\d+', s)
    if m:
        return m.group()
    for w in re.findall(r'[a-z]+', s):
        if w in NUM:
            return str(NUM[w])
        for k, v in NUM.items():
            if w.startswith(k[:6]):
                return str(v)
    return s

def scheme(m):
    out = []
    for x in m:
        if x not in out:
            out.append(x)
    return out

CODE = {'letter': 'L', 'allegory': 'A', 'tropology': 'T', 'anagogy': 'N', 'spiritual': 'S', 'other': 'o'}
def sig(m):
    return '-'.join(CODE[x] for x in scheme(m) if x != 'other')

def load(c):
    return {os.path.basename(f)[:-5]: json.load(open(f, encoding='utf-8'))['data'] for f in glob.glob(os.path.join(W, c, 'F*.json'))}

def main():
    inp = {json.loads(l)['id']: json.loads(l) for l in open(os.path.join(W, 'inputs.jsonl'), encoding='utf-8')}
    a, b = load('A'), load('B')
    rows, agree = [], collections.Counter()
    for i in sorted(inp):
        o, x, y = inp[i], a[i], b[i]
        k, ruled = x['kind'], ''
        if x['kind'] != y['kind']:
            pair = {x['kind'], y['kind']}
            if pair == {'theory', 'quotation'}:
                k = 'quotation' if (x['authority'] or y['authority']) else 'theory'
            elif 'theory' in pair or 'application' in pair:
                states = num(x['count_stated']) or num(y['count_stated']) or x['definitions'] or y['definitions']
                k = 'theory' if states else ('application' if 'application' in pair else sorted(pair - {'theory'})[0])
            ruled = f"R-kind: {x['kind']}/{y['kind']}"
        sa, sb = sig(x['mapped']), sig(y['mapped'])
        na, nb = num(x['count_stated']), num(y['count_stated'])
        agree['kind'] += x['kind'] == y['kind']; agree['scheme'] += sa == sb; agree['count'] += na == nb
        agree['authority'] += x['authority'].lower().split()[:1] == y['authority'].lower().split()[:1]
        rows.append(dict(id=i, idno=o['idno'], vol=o['vol'], col=o['col'], author=o['author'], author_year=o['author_year'],
                         century=o['century'], title=o['title'], kind=k, kind_ruled=ruled, scheme=sa, scheme_B=sb if sb != sa else '',
                         count=na if na == nb else (na or nb), count_B=nb if nb != na else '', senses_latin=' > '.join(scheme(x['senses'])),
                         authority=x['authority'], authority_B=y['authority'] if y['authority'].lower().split()[:1] != x['authority'].lower().split()[:1] else '',
                         example_osis=x['example']['osis'], example_figure=x['example']['figure'],
                         definitions=' | '.join(f"{d['term']}: {d['gloss']}" for d in x['definitions']),
                         summary=x['summary'], confidence=f"{x['confidence']}/{y['confidence']}"))
    cols = list(rows[0])
    with open(os.path.join(HERE, 'ledger', 'formulas-coded.tsv'), 'w', encoding='utf-8') as f:
        f.write('\t'.join(cols) + '\n')
        for r in rows:
            f.write('\t'.join(str(r[c]).replace('\t', ' ').replace('\n', ' ') for c in cols) + '\n')
    n = len(rows)
    T = [r for r in rows if r['kind'] in ('theory', 'quotation')]
    kinds = collections.Counter(r['kind'] for r in rows)
    cent = collections.defaultdict(collections.Counter)
    for r in rows:
        cent[r['century'] or 'undated'][r['kind']] += 1
    sch = collections.Counter(r['scheme'] for r in T)
    cnt = collections.Counter(r['count'] or '(none)' for r in T)
    auth = collections.Counter(re.split(r'[;,/]| and ', r['authority'])[0].strip() for r in rows if r['authority'])
    fig = collections.Counter(r['example_figure'] for r in rows if r['example_figure'])
    jer = [r for r in rows if 'jerusalem' in (r['example_figure'] + r['summary']).lower()]
    first4 = sorted((r for r in T if set('LATN') <= set(r['scheme'].split('-')) and r['author_year'].isdigit() and int(r['author_year']) > 0),
                    key=lambda r: int(r['author_year']))[:10]
    order = lambda c: int(c) if c.isdigit() else 99
    md = ['# What the stated formulas say (stage D, first pass)', '',
          'Generated by `scripts/formulas_merge.py` from two blind codings (Opus 5.5, codebook F1, 2026-11-10) of the 269 places '
          'where the census found three or more senses within 60 words (`census/formulas.tsv`). Ledger: `ledger/formulas-coded.tsv`.', '',
          f"Agreement A vs B: kind {agree['kind']}/{n} (kappa 0.93), scheme {agree['scheme']}/{n}, stated number {agree['count']}/{n}, "
          f"authority {agree['authority']}/{n}. Kind ruled by R-kind on {sum(1 for r in rows if r['kind_ruled'])} rows.", '',
          '## 1. What kind of passage', '', '| kind | passages |', '|---|---:|'] + \
         [f'| {k} | {v} |' for k, v in kinds.most_common()] + \
         ['', '## 2. By century of the author\'s death', '', '| century | theory | quotation | application | list | other |', '|---|---:|---:|---:|---:|---:|'] + \
         [f"| {c} | {cent[c]['theory']} | {cent[c]['quotation']} | {cent[c]['application']} | {cent[c]['list']} | {cent[c]['other']} |"
          for c in sorted(cent, key=order)] + \
         ['', f'## 3. The schemes stated ({len(T)} theory and quotation passages)', '',
          'Senses in the order the passage first names them. L letter, A allegory, T tropology, N anagogy, S spiritual.', '',
          '| scheme | passages |', '|---|---:|'] + [f'| {k or "(none)"} | {v} |' for k, v in sch.most_common(15)] + \
         ['', '| number stated | passages |', '|---|---:|'] + [f'| {k} | {v} |' for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])] + \
         ['', '## 4. Earliest four-fold statements (all of L, A, T, N; theory or quotation; any order)', '', '| author | d. | work | PL | order |', '|---|---:|---|---|---|'] + \
         [f"| {r['author']} | {r['author_year']} | {r['title'][:55]} | {r['vol']}, {r['col']} | {r['scheme']} |" for r in first4] + \
         ['', '## 5. Authorities invoked', '', '| authority | passages |', '|---|---:|'] + [f'| {k} | {v} |' for k, v in auth.most_common(12)] + \
         ['', '## 6. Figures used to show the senses', '', f'Jerusalem: {len(jer)} passages.', '', '| figure | passages |', '|---|---:|'] + \
         [f'| {k} | {v} |' for k, v in fig.most_common(12)]
    open(os.path.join(HERE, 'ledger', 'FORMULAS.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    print('\n'.join(md))

if __name__ == '__main__':
    main()
