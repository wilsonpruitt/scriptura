#!/usr/bin/env python3
"""Stage B for the Greek: the sense-term census over raw Kraken Greek (G1 passed: census-grade). No tokens.

  python3 -I studies/sensus/scripts/census_gr.py              # every Kraken work on disk
  python3 -I studies/sensus/scripts/census_gr.py origen-pg013 origen-pg014

The Greek term list, FROZEN by Wilson 2026-11-10 (proposal counted on 373K words of Origen and 245K of
six other Kraken works). It mirrors the frozen 41-term Latin list (census.py): the same families
(L letter, A allegory, T tropology, N anagogy, S spirit), the same tiers (core = a technical term,
counts toward a stated formula; broad = counted, an upper bound), the same formula rule (core terms
from 3+ of L/A/T/N within WIN words; historia joins as in the Latin). Wilson's rulings on the four open
calls: σωματικῶς core L (Greek-only: the Latin list has no carnaliter); τροπικῶς/τροπικώτερον core A
(like figuraliter, not T); βαθύτερον broad S; ψυχικός broad T.
Left out on purpose: παραβολή (the Gospel parables; only παραβολικῶς counts), ἀνάλογον
("correspondingly"), νοητέον ("it must be understood"), the verb θεωρεῖν ("to see"), διάνοια (the mind).
Text is normalized as the G1 gate measured it: accents, breathings and case dropped, final sigma
folded, hyphenated line ends rejoined.
Writes census/gr-terms.tsv (term counts per work) and census/gr-formulas.tsv, prints the summary.
"""
import collections, glob, os, re, sys, unicodedata
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K = os.path.expanduser('~/patrologia/raw/kraken')
OUT = os.path.join(HERE, 'census')
WIN = 60
A = r'(?:την |τη |τησ )?'          # optional article
TERMS = [
    # L: the letter
    ('κατα/προσ το ρητον', 'L', 'core', r'(?:κατα|προσ) το ρητον'),
    ('κατα/προσ την λεξιν', 'L', 'core', r'(?:κατα|προσ) ' + A + r'λεξιν'),
    ('κατα/προσ την ιστοριαν', 'L', 'core', r'(?:κατα|προσ) ' + A + r'ιστοριαν'),
    ('σωματικωσ', 'L', 'core', r'σωματικωσ'),
    ('ιστορια', 'L', 'broad', r'ιστορι(?:α|ασ|αν|αι|ων|αισ)'),
    ('ρητον', 'L', 'broad', r'ρητ(?:ον|ου|ω|α|ων|οισ)'),
    ('λεξισ', 'L', 'broad', r'λεξ(?:ισ|εωσ|ει|ιν|εισ|εσι|εων)'),
    ('γραμμα', 'L', 'broad', r'γραμμα(?:τοσ|τι)?'),
    ('σωματικοσ', 'L', 'broad', r'σωματικ(?:οσ|ον|ου|ω|οι|ων|οισ|ουσ|η|ησ|ην|αι|αισ|α|ασ)'),
    # A: allegory and the figure
    ('αλληγορ-', 'A', 'core', r'αλληγορ\w*'),
    ('τροπικωσ/τροπικωτερον', 'A', 'core', r'τροπικ(?:ωσ|ωτερον|ωτερα|ωτερου)'),
    ('μυστικωσ/μυστικωτερον', 'A', 'core', r'μυστικ(?:ωσ|ωτερον|ωτερα|ωτερου)'),
    ('τυπικωσ/τυπικοσ', 'A', 'core', r'τυπικ\w*'),
    ('συμβολικωσ', 'A', 'core', r'συμβολικ\w*'),
    ('παραβολικωσ', 'A', 'core', r'παραβολικ\w*'),
    ('μυστικοσ', 'A', 'broad', r'μυστικ(?:οσ|ον|ου|ω|οι|ων|οισ|ουσ|η|ησ|ην|αι|αισ|α|ασ)'),
    ('μυστηριον', 'A', 'broad', r'μυστηρι(?:ον|ου|ω|α|ων|οισ)'),
    ('τυποσ', 'A', 'broad', r'τυπ(?:οσ|ου|ω|ον|οι|ων|οισ|ουσ)'),
    ('συμβολον', 'A', 'broad', r'συμβολ(?:ον|ου|ω|α|ων|οισ)'),
    ('αινιγμα', 'A', 'broad', r'αινιγμ\w*'),
    ('υπονοια', 'A', 'broad', r'υπονοι(?:α|ασ|αν|αι|ων|αισ)'),
    ('σκια', 'A', 'broad', r'σκι(?:α|ασ|αν|αι|ων|αισ)'),
    # T: tropology
    ('τροπολογ-', 'T', 'core', r'τροπολογ\w*'),
    ('ηθικοσ/ηθικωσ', 'T', 'core', r'ηθικ\w*'),
    ('ψυχικοσ', 'T', 'broad', r'ψυχικ\w*'),
    # N: anagogy
    ('αναγωγ-', 'N', 'core', r'αναγωγ\w*'),
    # S: spirit and contemplation (outside the formula, as in the Latin)
    ('πνευματικωσ', 'S', 'core', r'πνευματικωσ'),
    ('κατα το πνευματικον', 'S', 'core', r'κατα το πνευματικον'),
    ('νοητωσ', 'S', 'core', r'νοητωσ'),
    ('θεωρια', 'S', 'core', r'θεωρι(?:α|ασ|αν|αι|ων|αισ)'),
    ('βαθυτερον', 'S', 'broad', r'βαθυτερ\w*'),
    ('πνευματικοσ', 'S', 'broad', r'πνευματικ(?:οσ|ον|ου|ω|οι|ων|οισ|ουσ|η|ησ|ην|αι|αισ|α|ασ)'),
    ('νοητοσ', 'S', 'broad', r'νοητ(?:οσ|ον|ου|ω|οι|ων|οισ|ουσ|η|ησ|ην|αι|αισ|α|ασ)'),
]
FORMULA = {t for t, f, g, _ in TERMS if g == 'core' and f in 'LATN'} | {'ιστορια'}
RX = re.compile('|'.join(rf'(?P<t{i}>\b(?:{rx})\b)' for i, (_, _, _, rx) in enumerate(TERMS)))

def _n(t):
    return ''.join(c for c in unicodedata.normalize('NFD', t) if not unicodedata.combining(c)).lower().replace('ς', 'σ')

_LEX = None
def lexicon():
    """Every form in ~/patrologia/raw/greek-lexicon.tsv, normalized like the text."""
    global _LEX
    if _LEX is None:
        _LEX = {_n(l.split('\t')[0]) for l in open(os.path.expanduser('~/patrologia/raw/greek-lexicon.tsv'), encoding='utf-8')}
    return _LEX

def norm(t):
    """Whole-volume runs read every page, and Kraken turns a Latin-only page or front matter into
    Greek-looking junk (about 10% of PG 1-2 pages; Origen's run, fed Greek pages only, had none).
    So a line is kept only if half or more of its 4+-letter words are Greek lexicon forms; lines
    with no such word (numerals, short words) are kept. Measured on the six checked works and
    Origen: real Greek runs 90-95% in the lexicon."""
    t = re.sub(r'\[b:\s*\w+\]', ' ', t)
    t = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', _n(t))
    lex, keep = lexicon(), []
    for line in t.split('\n'):
        ws = re.findall(r'[α-ω]+', line)
        long = [w for w in ws if len(w) >= 4]
        if not long or sum(w in lex for w in long) >= 0.5 * len(long):
            keep += ws
    return ' '.join(keep)

def scan(work):
    """One work: (words, term counts, formulas). Page-level offsets so a formula carries its page."""
    text, pstart = [], []
    off = 0
    for p in sorted(glob.glob(os.path.join(K, work, 'text', 'p-*.txt'))):
        t = norm(open(p, encoding='utf-8', errors='replace').read()) + ' '
        pstart.append((off, os.path.basename(p)[:-4])); text.append(t); off += len(t)
    text = ''.join(text)
    hits = [(m.start(), int(next(g for g, v in m.groupdict().items() if v)[1:])) for m in RX.finditer(text)]
    wpos = [m.start() for m in re.finditer(r'\S+', text)]
    import bisect
    widx = lambda o: bisect.bisect_right(wpos, o) - 1
    page = lambda o: pstart[bisect.bisect_right([s for s, _ in pstart], o) - 1][1]
    fh = [(widx(o), o, k) for o, k in hits if TERMS[k][0] in FORMULA]
    forms, i = [], 0
    while i < len(fh):
        j, fams = i, set()
        while j < len(fh) and fh[j][0] - fh[i][0] <= WIN:
            fams.add(TERMS[fh[j][2]][1]); j += 1
        if len(fams) >= 3:
            while j < len(fh) and fh[j][0] - fh[j - 1][0] <= WIN:
                fams.add(TERMS[fh[j][2]][1]); j += 1
            a, b = fh[i][1], fh[j - 1][1]
            forms.append((work, page(a), ''.join(x for x in 'LATN' if x in fams),
                          ' '.join(TERMS[h[2]][0].replace(' ', '_') for h in fh[i:j]),
                          text[max(0, a - 120):b + 160]))
            i = j
        else:
            i += 1
    return len(wpos), collections.Counter(TERMS[k][0] for _, k in hits), forms

def main():
    works = sys.argv[1:] or sorted(d for d in os.listdir(K) if glob.glob(os.path.join(K, d, 'text', 'p-*.txt')))
    res = {w: scan(w) for w in works}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'gr-terms.tsv'), 'w', encoding='utf-8') as o:
        o.write('term\tfamily\ttier\t' + '\t'.join(works) + '\n')
        o.write('(words)\t\t\t' + '\t'.join(str(res[w][0]) for w in works) + '\n')
        for t, f, g, _ in TERMS:
            o.write(f'{t}\t{f}\t{g}\t' + '\t'.join(str(res[w][1][t]) for w in works) + '\n')
    allf = [f for w in works for f in res[w][2]]
    with open(os.path.join(OUT, 'gr-formulas.tsv'), 'w', encoding='utf-8') as o:
        o.write('work\tpage\tfamilies\tterms\tsnippet\n')
        for r in allf:
            o.write('\t'.join(r) + '\n')
    tw = sum(r[0] for r in res.values())
    print(f'{len(works)} works, {tw} Greek words; stated formulas (core terms of 3+ of L/A/T/N within {WIN} words): {len(allf)}')
    for w in works:
        print(f'  {w:<26} {res[w][0]:>7} words  {len(res[w][2]):>3} formulas')
    print('\ncore terms, count (per 100K words) over all works:')
    tot = collections.Counter()
    for w in works: tot.update(res[w][1])
    for t, f, g, _ in TERMS:
        if g == 'core':
            print(f'  {f} {t:<26} {tot[t]:>5} ({100000 * tot[t] / tw:5.1f})')
    print('\nformulas:')
    for r in allf:
        print(f'  {r[0]} {r[1]} {r[2]:<5} {r[3]}')

if __name__ == '__main__':
    main()
