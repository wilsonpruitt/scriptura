#!/usr/bin/env python3
"""Stage B: the vocabulary census of the sense terms across the PL TEI (no tokens).

  python3 -I scripts/census.py [TEI_DIR]      (default ~/patrologia/sources/pl/tei)

Every occurrence of each sense term, by work, author and century, plus every *stated formula*:
a window of WIN words holding formula-grade terms from three or more of the four senses
(letter, allegory, tropology, anagogy). Spelling is normalized for matching (lower case, j->i,
v->u), and the variants the plan names are counted apart (spiritalis / spiritualis,
intellegentia / intelligentia).

Grades: `core` = technical terms that almost never mean anything but a sense of scripture;
`broad` = common words that often do (historia, littera, figura, mysterium, sacramentum, typus,
mysticus, moralis, spiritualis). Read broad counts as an upper bound.

Term list frozen by Wilson 2026-11-10 (41 terms): the starter list opened, plus iuxta/secundum
historiam, mystica intelligentia / mysticus sensus, sensus moralis / moralis intelligentia,
parabolice, allegorizare, theoria, theorice. theoria/theorice are filed under S (the Greek bridge).

Writes census/terms-by-work.tsv, terms-by-century.tsv, formulas.tsv and census/CENSUS.md.
Caveat: the TEI carries Migne's editorial matter (prefaces, notes, testimonia) under the
work's author; nothing here separates it.
"""
import bisect, collections, csv, glob, html, os, re, sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEI = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/patrologia/sources/pl/tei')
OUT = os.path.join(HERE, 'census')
WIN = 60

I = r'(?:us|a|um|i|ae|o|am|os|is|orum|arum|as|e|em|es|ibus)'   # common case endings
SP = r'spirit(?P<u>u?)al'
INT = r'intel+(?P<e>[ei])gent(?:ia|iae|iam)'
# (term, family, grade, pattern). Family: L letter, A allegory, T tropology, N anagogy, S spiritual.
TERMS = [
    ('historia', 'L', 'broad', r'histori(?:a|ae|am|arum|as)'),
    ('historice', 'L', 'core', r'historice'),
    ('historicus', 'L', 'broad', r'historic' + I),
    ('historialis', 'L', 'core', r'historial(?:is|e|em|i|ium|ibus|es)'),
    ('historialiter', 'L', 'core', r'historialiter'),
    ('iuxta/secundum historiam', 'L', 'core', r'(?:iuxta|secundum) histori(?:am|ae)'),
    ('ad litteram', 'L', 'core', r'ad lit+eram'),
    ('iuxta/secundum litteram', 'L', 'core', r'(?:iuxta|secundum) lit+eram'),
    ('litteralis', 'L', 'core', r'lit+eral(?:is|e|em|i|ium|ibus|es)'),
    ('litteraliter', 'L', 'core', r'lit+eraliter'),
    ('littera', 'L', 'broad', r'lit+er(?:a|ae|am|arum|is|as)'),
    ('allegoria', 'A', 'core', r'allegori(?:a|ae|am|arum|is|as)'),
    ('allegorice', 'A', 'core', r'allegorice'),
    ('allegoricus', 'A', 'core', r'allegoric' + I),
    ('mystice', 'A', 'core', r'mystice'),
    ('mystica intelligentia / mysticus sensus', 'A', 'core', r'mystic(?:a|am|ae) intel+[ei]gent(?:ia|iae|iam)|intel+[ei]gent(?:ia|iae|iam) mystic(?:a|am|ae)|mystic(?:us|um|o|i) (?:sensu[ms]?|intellectu[ms]?)|(?:sensu[ms]?|intellectu[ms]?) mystic(?:us|um|o|i)'),
    ('mysticus', 'A', 'broad', r'mystic' + I),
    ('mysterium', 'A', 'broad', r'mysteri(?:um|a|i|o|orum|is)'),
    ('typus', 'A', 'broad', r'typ(?:us|i|o|um|os|orum|is)'),
    ('typice', 'A', 'core', r'typice'),
    ('typicus', 'A', 'core', r'typic' + I),
    ('figura', 'A', 'broad', r'figur(?:a|ae|am|arum|is|as)'),
    ('figuraliter', 'A', 'core', r'figuraliter'),
    ('figurate', 'A', 'core', r'figurat(?:iue|e)'),
    ('parabolice', 'A', 'core', r'parabolice'),
    ('allegorizare', 'A', 'core', r'allegoriz[a-z]*'),
    ('sacramentum', 'A', 'broad', r'sacrament(?:um|a|i|o|orum|is)'),
    ('tropologia', 'T', 'core', r'tropologi(?:a|ae|am|arum|is|as)'),
    ('tropologice', 'T', 'core', r'tropologice'),
    ('tropologicus', 'T', 'core', r'tropologic' + I),
    ('moraliter', 'T', 'core', r'moraliter'),
    ('moralitas', 'T', 'core', r'moralitat(?:is|em|e|es|um|ibus)|moralitas'),
    ('sensus moralis / moralis intelligentia', 'T', 'core', r'moral(?:is|em|i|e) (?:sensu[ms]?|intellectu[ms]?|intel+[ei]gent(?:ia|iae|iam))|(?:sensu[ms]?|intellectu[ms]?|intel+[ei]gent(?:ia|iae|iam)) moral(?:is|em|i|e)'),
    ('moralis', 'T', 'broad', r'moral(?:is|e|em|i|ium|ibus|es)'),
    ('anagoge', 'N', 'core', r'anagog(?:e|es|en|ia|iae|iam|en)'),
    ('anagogice', 'N', 'core', r'anagogice'),
    ('anagogicus', 'N', 'core', r'anagogic' + I),
    ('spiritualiter', 'S', 'core', r'spirit(?P<u>u?)aliter'),
    ('spiritualis intelligentia', 'S', 'core', SP + r'(?:is|em|i|e) ' + INT + '|' + INT.replace('?P<e>', '?:') + ' ' + SP.replace('?P<u>', '?:') + r'(?:is|em|i|e)'),
    ('spiritualis sensus/intellectus', 'S', 'core', SP + r'(?:is|em|i|e) (?:sensu[ms]?|intellectu[ms]?)|(?:sensu[ms]?|intellectu[ms]?) ' + SP.replace('?P<u>', '?:') + r'(?:is|em|i|e)'),
    ('theoria', 'S', 'core', r'theori(?:a|ae|am|arum|is|as)'),
    ('theorice', 'S', 'core', r'theorice'),
    ('spiritualis', 'S', 'broad', SP + r'(?:is|e|em|i|ium|ibus|es)'),
]
# formula-grade: core terms, plus historia (the head of every stated list)
FORMULA = {t for t, f, g, _ in TERMS if g == 'core' and f in 'LATN'} | {'historia'}
RX = re.compile('|'.join(rf'\b(?P<t{k}>{p.replace("?P<u>", f"?P<u{k}>").replace("?P<e>", f"?P<e{k}>")})\b'
                         for k, (_, _, _, p) in enumerate(TERMS)))

def norm(s):
    return s.lower().replace('j', 'i').replace('v', 'u')

def meta():
    m = {}
    for r in csv.DictReader(open(os.path.join(HERE, 'data', 'pl-locator.tsv'), encoding='utf-8'), delimiter='\t'):
        m[r['idno']] = r
    return m

def one(f):
    raw = open(f, encoding='utf-8', errors='replace').read()
    vol = re.search(r'Patrologia Latina, vol\. (\d+)', raw)
    body = raw[raw.find('<text'):] if '<text' in raw else raw
    # columns: replace <pb n="0153D"/> with a marker, then strip tags
    body = re.sub(r'<pb\s+n="0*(\d+)([A-D]?)"\s*/?>', lambda m: f' \x01{m.group(1)}{m.group(2)}\x01 ', body)
    body = re.sub(r'<[^>]+>', ' ', body)
    body = html.unescape(body)
    text = norm(body)
    parts = re.split(r'\x01([^\x01]*)\x01', text)
    col_at = []   # (offset in clean text, column)
    buf, off, cur = [], 0, ''
    for k, p in enumerate(parts):
        if k % 2:
            cur = p
            col_at.append((off, cur))
        else:
            p = re.sub(r'\s+', ' ', p)
            buf.append(p); off += len(p)
    text = ''.join(buf)
    words = len(re.findall(r'[a-z]+', text))
    hits = []   # (offset, term index, variant)
    for m in RX.finditer(text):
        k = int(next(g for g, v in m.groupdict().items() if v and g.startswith('t'))[1:])
        var = ''
        g = m.group()
        if g.startswith('spirit'):
            var = 'spiritu-' if g.startswith('spiritu') else 'spirit-'
            if re.search(r'intel+[ei]gent', g):
                var += ' intellegentia' if re.search(r'intel+egent', g) else ' intelligentia'
        elif 'spirit' in g:   # intelligentia spiritualis
            var = ('spiritu-' if 'spiritu' in g else 'spirit-') + (' intellegentia' if re.search(r'intel+egent', g) else ' intelligentia' if re.search(r'intel+igent', g) else '')
        hits.append((m.start(), k, var))
    # stated formulas: word windows
    wpos = [m.start() for m in re.finditer(r'[a-z]+', text)]
    widx = lambda o: bisect.bisect_right(wpos, o) - 1
    fhits = [(widx(o), o, k) for o, k, _ in hits if TERMS[k][0] in FORMULA]
    formulas, i = [], 0
    while i < len(fhits):
        j, fams = i, set()
        while j < len(fhits) and fhits[j][0] - fhits[i][0] <= WIN:
            fams.add(TERMS[fhits[j][2]][1]); j += 1
        if len(fams) >= 3:
            # extend while the next hit stays within WIN of the last one
            while j < len(fhits) and fhits[j][0] - fhits[j - 1][0] <= WIN:
                fams.add(TERMS[fhits[j][2]][1]); j += 1
            a, b = fhits[i][1], fhits[j - 1][1]
            ci = bisect.bisect_right([c[0] for c in col_at], a) - 1
            formulas.append(dict(col=col_at[ci][1] if ci >= 0 else '', fams=''.join(x for x in 'LATN' if x in fams),
                                 terms=' '.join(TERMS[h[2]][0].replace(' ', '_') for h in fhits[i:j]),
                                 snippet=text[max(0, a - 80):min(len(text), b + 120)].strip()))
            i = j
        else:
            i += 1
    counts = collections.Counter((TERMS[k][0], v) for _, k, v in hits)
    return os.path.basename(f)[:-4], vol.group(1) if vol else '', words, counts, formulas

def main():
    m = meta()
    files = sorted(glob.glob(os.path.join(TEI, '*.xml')))
    os.makedirs(OUT, exist_ok=True)
    fam = {t: (f, g) for t, f, g, _ in TERMS}
    bywork, cent_words, cent_terms, formulas = [], collections.Counter(), collections.Counter(), []
    def century(y):
        y = int(y) if str(y).isdigit() else 0
        return str((y - 1) // 100 + 1) if y > 0 else 'undated'
    with ProcessPoolExecutor(6) as ex:
        for idno, vol, words, counts, fs in ex.map(one, files, chunksize=20):
            w = m.get(idno, {})
            a, y = w.get('author', ''), w.get('author_year', '')
            c = century(y)
            cent_words[c] += words
            for (t, v), n in counts.items():
                bywork.append([idno, vol or w.get('volume', ''), a, y, c, t, fam[t][0], fam[t][1], v, n, words])
                cent_terms[(c, t)] += n
            for x in fs:
                formulas.append([idno, vol or w.get('volume', ''), x['col'], a, y, c, w.get('title', ''), x['fams'], x['terms'], x['snippet']])
    W = lambda name, head, rows: open(os.path.join(OUT, name), 'w', encoding='utf-8').write(
        '\t'.join(head) + '\n' + ''.join('\t'.join(str(v).replace('\t', ' ') for v in r) + '\n' for r in rows))
    W('terms-by-work.tsv', ['idno', 'vol', 'author', 'author_year', 'century', 'term', 'family', 'grade', 'variant', 'n', 'work_words'], bywork)
    cents = sorted((c for c in cent_words if c != 'undated'), key=int) + ['undated']
    W('terms-by-century.tsv', ['century', 'words', 'term', 'family', 'grade', 'n', 'per_million'],
      [[c, cent_words[c], t, fam[t][0], fam[t][1], cent_terms[(c, t)], f'{1e6 * cent_terms[(c, t)] / cent_words[c]:.1f}' if cent_words[c] else '']
       for c in cents for t, *_ in TERMS])
    W('formulas.tsv', ['idno', 'vol', 'col', 'author', 'author_year', 'century', 'title', 'families', 'terms', 'snippet'], formulas)
    # summary
    tot = collections.Counter()
    for r in bywork:
        tot[r[5]] += r[9]
    var = collections.Counter()
    for r in bywork:
        if r[8]:
            var[(r[5], r[8])] += r[9]
    core = [t for t, f, g, _ in TERMS if g == 'core']
    md = ['# Stage B: the sense vocabulary across the PL', '',
          f'Generated by `scripts/census.py` over {len(files):,} TEI files ({sum(cent_words.values()):,} words). '
          'Counts are occurrences after spelling normalization (lower case, j→i, v→u). `broad` terms are common words that often, '
          'not always, name a sense: read them as an upper bound, never as rates. Term list frozen 2026-11-10 (41 terms). Migne\'s editorial matter is counted with the work it sits in.', '',
          '## 1. Totals', '', '| term | sense | grade | occurrences |', '|---|---|---|---:|'] + \
         [f'| {t} | {f} | {g} | {tot[t]:,} |' for t, f, g, _ in TERMS] + \
         ['', 'Senses: L letter, A allegory, T tropology, N anagogy, S spiritual.', '',
          '## 2. Spelling variants', '', '| term | variant | n |', '|---|---|---:|'] + \
         [f'| {t} | {v} | {n:,} |' for (t, v), n in sorted(var.items())] + \
         ['', '## 3. Core terms per million words, by century of the author\'s death', '',
          '| century | words | ' + ' | '.join(core) + ' |', '|---|---:|' + '---:|' * len(core)] + \
         [f'| {c} | {cent_words[c]:,} | ' + ' | '.join(f'{1e6 * cent_terms[(c, t)] / cent_words[c]:.1f}' if cent_words[c] else '' for t in core) + ' |'
          for c in cents] + \
         ['', f'## 4. Stated formulas (three or more of L, A, T, N within {WIN} words)', '',
          f'{len(formulas):,} places, in `census/formulas.tsv`.', '', '| century | formulas | with all four |', '|---|---:|---:|']
    fc = collections.Counter(r[5] for r in formulas); f4 = collections.Counter(r[5] for r in formulas if r[7] == 'LATN')
    md += [f'| {c} | {fc[c]} | {f4[c]} |' for c in cents if fc[c]]
    fa = collections.Counter(r[3] or '(none)' for r in formulas)
    yr = {r[3]: r[4] for r in formulas}
    md += ['', '### Authors with the most stated formulas', '', '| author | d. | formulas |', '|---|---:|---:|'] + \
          [f'| {a} | {yr.get(a, "")} | {n} |' for a, n in fa.most_common(30)]
    open(os.path.join(OUT, 'CENSUS.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    print('\n'.join(md[:6])); print(len(formulas), 'formulas')

if __name__ == '__main__':
    main()
