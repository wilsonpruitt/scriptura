#!/usr/bin/env python3
"""Stage B over the Latin Origen of PG 12-14 (Tesseract text, cleaned by pg_latin_clean.py). No tokens.

  python3 -I studies/sensus/scripts/pg_census.py

The same frozen 41-term list and the same stated-formula rule as the PL census (census.py): a window
of WIN words with formula-grade terms from three or more of letter, allegory, tropology, anagogy.
Writes census/pg-formulas.tsv (vol, column, families, terms, snippet) and census/pg-terms.tsv (term
counts per volume, with the PL rate per 100K words beside them), and prints the summary.
OCR caveat: about 5-6% of Latin words are still non-words after the rules; the sense terms are long
and survive OCR well, but counts are a lower bound.
"""
import bisect, collections, importlib.util, os, re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('census', os.path.join(HERE, 'scripts', 'census.py'))
cen = importlib.util.module_from_spec(spec); spec.loader.exec_module(cen)
OCR = os.path.join(HERE, 'sources', 'editions', 'ocr')
OUT = os.path.join(HERE, 'census')

def scan(vol, kind=None):
    """kind: 'la' = Latin-only pages (the ancient translations: Rufinus, Jerome, the old Latin
    Matthew series); 'bi' = Greek pages with Migne's facing Latin (early-modern humanist
    translations); None = all."""
    raw = open(os.path.join(OCR, f'pg{vol}-latin.txt'), encoding='utf-8').read()
    parts = re.split(r'\x01([^\x01]*)\x01', raw)
    buf, col_at, off, on = [], [], 0, True
    for k, p in enumerate(parts):
        if k % 2:
            c, _, kd = p.partition('|')
            # front matter (no column: roman-paginated prefaces, the editors' own Latin) is skipped
            on = bool(c) and (kind is None or kd == kind)
            col_at.append((off, c)); continue
        if not on or re.search(r'\bINDEX\b|\bINDICES\b', p[:300]):
            continue                      # and so are index pages
        p = re.sub(r'\s+', ' ', cen.norm(p)); buf.append(p); off += len(p)
    text = ''.join(buf)
    words = len(re.findall(r'[a-z]+', text))
    hits = []
    for m in cen.RX.finditer(text):
        k = int(next(g for g, v in m.groupdict().items() if v and g.startswith('t'))[1:])
        hits.append((m.start(), k))
    wpos = [m.start() for m in re.finditer(r'[a-z]+', text)]
    widx = lambda o: bisect.bisect_right(wpos, o) - 1
    fh = [(widx(o), o, k) for o, k in hits if cen.TERMS[k][0] in cen.FORMULA]
    forms, i = [], 0
    cols = [c[0] for c in col_at]
    while i < len(fh):
        j, fams = i, set()
        while j < len(fh) and fh[j][0] - fh[i][0] <= cen.WIN:
            fams.add(cen.TERMS[fh[j][2]][1]); j += 1
        if len(fams) >= 3:
            while j < len(fh) and fh[j][0] - fh[j - 1][0] <= cen.WIN:
                fams.add(cen.TERMS[fh[j][2]][1]); j += 1
            a, b = fh[i][1], fh[j - 1][1]
            ci = bisect.bisect_right(cols, a) - 1
            forms.append((vol, col_at[ci][1] if ci >= 0 else '', ''.join(x for x in 'LATN' if x in fams),
                          ' '.join(cen.TERMS[h[2]][0].replace(' ', '_') for h in fh[i:j]),
                          text[max(0, a - 100):min(len(text), b + 140)].strip()))
            i = j
        else:
            i += 1
    return words, collections.Counter(cen.TERMS[k][0] for _, k in hits), forms

def pl_rates():
    """PL term rate per 100K words, from census/terms-by-century.tsv if present."""
    import csv
    p = os.path.join(OUT, 'terms-by-century.tsv')
    tot = collections.Counter(); words = 0
    if not os.path.exists(p):
        return {}
    rows = list(csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'))
    return rows

import sys
KIND = sys.argv[1] if len(sys.argv) > 1 else None
def main():
    allf, terms, words = [], collections.Counter(), 0
    per = {}
    for v in ('012', '013', '014'):
        w, c, f = scan(v, KIND)
        per[v] = (w, c, f); words += w; terms.update(c); allf += f
    with open(os.path.join(OUT, f'pg-formulas{"-" + KIND if KIND else ""}.tsv'), 'w', encoding='utf-8') as o:
        o.write('vol\tcol\tfamilies\tterms\tsnippet\n')
        for r in allf:
            o.write('\t'.join(str(x).replace('\t', ' ') for x in r) + '\n')
    with open(os.path.join(OUT, f'pg-terms{"-" + KIND if KIND else ""}.tsv'), 'w', encoding='utf-8') as o:
        o.write('term\t' + '\t'.join(f'pg{v}' for v in per) + '\ttotal\tper_100k\n')
        for t, n in terms.most_common():
            o.write(f'{t}\t' + '\t'.join(str(per[v][1][t]) for v in per) + f'\t{n}\t{100000 * n / words:.1f}\n')
    print(f'Latin words: {words}  ' + '  '.join(f'PG {int(v)}: {per[v][0]}' for v in per))
    print(f'stated formulas (3+ senses within {cen.WIN} words): {len(allf)}  ' + '  '.join(f'PG {int(v)}: {len(per[v][2])}' for v in per))
    print('families:', collections.Counter(r[2] for r in allf).most_common())
    print('\nterms per 100K words (core terms):')
    for t, n in terms.most_common():
        g = next(x[2] for x in cen.TERMS if x[0] == t)
        if g == 'core':
            print(f'  {t:<42} {n:>5}  {100000 * n / words:6.1f}')

if __name__ == '__main__':
    main()
