#!/usr/bin/env python3
"""The citation spine, v0 (PLAN 5.3 stage C; the canon Study's stage 1). No tokens.

  python3 -I studies/canon/scripts/spine.py notes     # stream 0: migne.app's own scripture index
  python3 -I studies/canon/scripts/spine.py ngram     # stream 1: rare 5-grams, PL TEI x Clementine
  python3 -I studies/canon/scripts/spine.py inline    # stream 2: Migne's own parenthetical citations in the text
  python3 -I studies/canon/scripts/spine.py recall    # how much of stream 0 stream 1 recovers
  python3 -I studies/canon/scripts/spine.py calibrate # inline (verse-level) vs ngram: recall and precision
  python3 -I studies/canon/scripts/spine.py profile   # each volume's citation practice; calibrate by practice
  python3 -I studies/canon/scripts/spine.py fuzzy     # stream 3: ordered stem pairs, for Old Latin wording
  python3 -I studies/canon/scripts/spine.py bydate    # inline recall of ngram, fuzzy and both, by author date

Every row: idno, PL vol, column, author, year, the verse in Vulgate numbering (`vulg`, OSIS book
codes on Clementine numbers) and in KJV/WEB numbering (`kjv`, via the Scriptura crosswalk), the
stream that found it, and its evidence. The Vulgate numbering is kept because that is what the
Fathers and Migne cite; the KJV key is the join to every other layer (LAYERS.md).

Stream 1 matches the Clementine (1592), not the Old Latin many Fathers quote, so it undercounts
pre-Jerome citation; the fuzzy stream (to come) is for that. A 5-gram counts only if it occurs in at
most RARE verses of the Vulgate; adjacent hits on one verse merge into a run; a run must cover at
least MINRUN words to be kept. The machine finds candidates; it never decides.
"""
import bisect, collections, csv, glob, html, json, os, re, sys
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from refkey import parse, parse_many, to_kjv, book  # noqa: E402

TEI = os.path.expanduser('~/patrologia/sources/pl/tei')
VULG = os.path.expanduser('~/patrologia/sources/vulgate/clementine-flat.txt')
INDEX = os.path.expanduser('~/patrologia/data/index/pl')
LOC = os.path.join(ROOT, 'studies', 'sensus', 'data', 'pl-locator.tsv')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spine')
N, RARE, MINRUN = 5, 3, 6

def norm_words(s):
    s = s.lower().replace('j', 'i').replace('v', 'u')
    s = re.sub(r'ae|oe|æ|œ', 'e', s)
    s = s.replace('mihi', 'mi').replace('nihil', 'nil').replace('michi', 'mi')
    return re.findall(r'[a-z]+', s)

def meta():
    return {r['idno']: r for r in csv.DictReader(open(LOC, encoding='utf-8'), delimiter='\t')}

def vulgate():
    verses = []   # (osis key in Vulgate numbering, words)
    for line in open(VULG, encoding='utf-8'):
        if '\t' not in line:
            continue
        ref, text = line.rstrip('\n').split('\t', 1)
        r = parse(ref, scheme='vulg')
        if r and r.v1 is not None:
            verses.append((r.osis, norm_words(text)))
    return verses

_IDX = None
def build_index():
    global _IDX
    vs = vulgate()
    grams = collections.defaultdict(set)
    for vi, (_, w) in enumerate(vs):
        for i in range(len(w) - N + 1):
            grams[' '.join(w[i:i + N])].add(vi)
    _IDX = ({g: tuple(s) for g, s in grams.items() if len(s) <= RARE}, [k for k, _ in vs])
    return _IDX

def kjv_of(v):
    k = to_kjv(v)
    return k[0] if k else ''

def scan(f):
    grams, keys = _IDX
    raw = open(f, encoding='utf-8', errors='replace').read()
    body = raw[raw.find('<text'):] if '<text' in raw else raw
    body = re.sub(r'<pb\s+n="0*(\d+)([A-D]?)"\s*/?>', lambda m: f' \x01{m.group(1)}{m.group(2).lower()}\x01 ', body)
    body = html.unescape(re.sub(r'<[^>]+>', ' ', body))
    words, cols, cur = [], [], ''
    for k, seg in enumerate(re.split(r'\x01([^\x01]*)\x01', body)):
        if k % 2:
            cur = seg; continue
        w = norm_words(seg)
        words += w; cols += [cur] * len(w)
    hits = collections.defaultdict(list)          # verse index -> word positions where a rare gram starts
    for i in range(len(words) - N + 1):
        for vi in grams.get(' '.join(words[i:i + N]), ()):
            hits[vi].append(i)
    rows = []
    for vi, pos in hits.items():
        run_start = prev = pos[0]
        for p in pos[1:] + [None]:
            if p is not None and p <= prev + 2:
                prev = p; continue
            length = prev - run_start + N
            if length >= MINRUN:
                rows.append((cols[run_start], keys[vi], length, ' '.join(words[run_start:run_start + min(length, 14)])))
            if p is not None:
                run_start = prev = p
    return os.path.basename(f)[:-4], rows

PAREN = re.compile(r'\(([^()]{2,90})\)')
STARTS = re.compile(r'^\s*(?:I{1,3}V?|IV|[1-4])?\s?[A-Z][A-Za-z\u00c0-\u00ff]+\.?,?\s+[IVXLC\d]')
def body_text(f):
    raw = open(f, encoding='utf-8', errors='replace').read()
    body = raw[raw.find('<text'):] if '<text' in raw else raw
    body = re.sub(r'<pb\s+n="0*(\d+)([A-D]?)"\s*/?>', lambda m: f' \x01{m.group(1)}{m.group(2).lower()}\x01 ', body)
    return html.unescape(re.sub(r'<[^>]+>', ' ', body))

def _within(key, osis):
    """Does verse key `key` (Book.c.v) fall inside reference `osis` (verse, chapter, or range)?"""
    b, c, v = key.split('.'); c, v = int(c), int(v)
    a, _, z = osis.partition('-'); z = z or a
    pa, pz = a.split('.'), z.split('.')
    if pa[0] != b:
        return False
    lo = (int(pa[1]), int(pa[2]) if len(pa) > 2 else 0)
    hi = (int(pz[1]), int(pz[2]) if len(pz) > 2 else 999)
    return lo <= (c, v) <= hi

def _near(key, osis, slop=2):
    """Within `slop` verses of a verse-level reference, same chapter."""
    b, c, v = key.split('.')
    a, _, z = osis.partition('-'); z = z or a
    pa, pz = a.split('.'), z.split('.')
    if len(pa) < 3 or pa[0] != b or pa[1] != c or pz[1] != c:
        return False
    return int(pa[2]) - slop <= int(v) <= int(pz[2]) + slop

_VALID = None
def _valid():
    global _VALID
    if _VALID is None:
        ks = _IDX[1]
        _VALID = (set(ks), {k.rsplit('.', 1)[0] for k in ks})
    return _VALID

def exists(osis):
    vs, cs = _valid()
    return all((p in vs) if p.count('.') == 2 else (p in cs) for p in osis.split('-'))

def scan_inline(f):
    """Parenthetical citations: '(Psal. LXXX, 3)', '(I Cor. II, 6)', '(Matth. XXII; Marc. XII)'.
    Each row keeps the ~12 words before it (the quotation it is attached to) as evidence, and says
    whether that verse exists in the Clementine (`exists`) and whether the 25 words before the
    parenthesis share a rare 5-gram with it (`confirmed`; `ngram_saw` lists what they did match)."""
    grams, keys = _IDX
    body = body_text(f)
    cols = [(m.start(), m.group(1)) for m in re.finditer(r'\x01([^\x01]*)\x01', body)]
    starts = [c[0] for c in cols]
    rows, unparsed = [], collections.Counter()
    for m in PAREN.finditer(body):
        inner = re.sub(r'\s+', ' ', m.group(1).replace('\x01', ' ')).strip()
        if not STARTS.match(inner):
            continue
        refs = parse_many(inner, scheme='vulg')
        if not refs:
            if book(re.split(r'[\s.,]', inner.strip())[0] + '.') and not inner.upper().startswith('VERS'):
                unparsed[inner] += 1
            continue
        i = bisect.bisect_right(starts, m.start()) - 1
        col = cols[i][1] if i >= 0 else ''
        before = re.sub(r'\x01[^\x01]*\x01', ' ', body[max(0, m.start() - 700):m.start()])
        before = re.sub(r'\([^()]*\)', ' ', before)
        prev = re.findall(r"[A-Za-z\u00c0-\u00ff']+", before)
        w = norm_words(' '.join(prev[-25:]))
        saw = sorted({keys[vi] for j in range(len(w) - N + 1) for vi in grams.get(' '.join(w[j:j + N]), ())})
        for r in refs:
            osis = r.osis
            if r.book == 'Jude' and re.match(r'^\s*Jud\b', inner):      # Migne's 'Jud.' is Judges as often as Jude
                alt = osis.replace('Jude.', 'Judg.')
                if r.c1 > 1 or (any(_within(k, alt) for k in saw) and not any(_within(k, osis) for k in saw)):
                    osis = alt
            ok = exists(osis)
            conf = 'y' if any(_within(k, osis) for k in saw) else 'near' if any(_near(k, osis) for k in saw) else 'n'
            rows.append((col, osis, 'verse' if r.v1 is not None else 'chapter', 'y' if ok else 'n', conf,
                         ' '.join(saw[:6]), inner.replace('\t', ' '), ' '.join(prev[-12:])))
    return os.path.basename(f)[:-4], rows, unparsed

def cmd_inline():
    m = meta()
    build_index()
    files = sorted(glob.glob(os.path.join(TEI, '*.xml')))
    os.makedirs(OUT, exist_ok=True)
    n = 0; c = collections.Counter(); un = collections.Counter()
    with open(os.path.join(OUT, 'spine-inline.tsv'), 'w', encoding='utf-8') as out, ProcessPoolExecutor(6, initializer=build_index) as ex:
        out.write('idno\tvol\tcol\tauthor\tauthor_year\tvulg\tkjv\tstream\tlevel\texists\tconfirmed\tngram_saw\tcited\tevidence\n')
        for idno, rows, unparsed in ex.map(scan_inline, files, chunksize=10):
            un.update(unparsed)
            w = m.get(idno, {})
            for col, v, level, ok, conf, saw, cited, ev in rows:
                first = v.split('-')[0]
                k = kjv_of(first) if level == 'verse' else (to_kjv(first) or [''])[0]
                out.write('\t'.join([idno, w.get('volume', ''), col, w.get('author', ''), w.get('author_year', ''), v, k,
                                     'inline', level, ok, conf, saw, cited, ev]) + '\n')
                n += 1; c[(level, ok, conf)] += 1
    with open(os.path.join(OUT, 'inline-unparsed.tsv'), 'w', encoding='utf-8') as o:
        for s_, k in un.most_common():
            o.write(f'{k}\t{s_}\n')
    print(n, 'rows ->', os.path.join(OUT, 'spine-inline.tsv'))
    for lv in ('verse', 'chapter'):
        t = sum(v for k, v in c.items() if k[0] == lv)
        bad = sum(v for k, v in c.items() if k[0] == lv and k[1] == 'n')
        cf = sum(v for k, v in c.items() if k[0] == lv and k[2] == 'y')
        nr = sum(v for k, v in c.items() if k[0] == lv and k[2] == 'near')
        print(f'  {lv}: {t}; not in the Clementine: {bad} ({100 * bad / t:.1f}%); confirmed by a rare 5-gram before it: {cf} ({100 * cf / t:.1f}%)'
              + (f', within 2 verses: {nr} ({100 * nr / t:.1f}%)' if nr else ''))
    print(sum(un.values()), 'book-led parentheticals refkey could not parse (', len(un), 'distinct) -> inline-unparsed.tsv')

def cmd_ngram():
    m = meta()
    build_index()
    print('rare 5-grams in the Clementine:', len(_IDX[0]))
    files = sorted(glob.glob(os.path.join(TEI, '*.xml')))
    os.makedirs(OUT, exist_ok=True)
    n = 0
    with open(os.path.join(OUT, 'spine-ngram.tsv'), 'w', encoding='utf-8') as out, ProcessPoolExecutor(6, initializer=build_index) as ex:
        out.write('idno\tvol\tcol\tauthor\tauthor_year\tvulg\tkjv\tstream\trun_words\tevidence\n')
        for idno, rows in ex.map(scan, files, chunksize=10):
            w = m.get(idno, {})
            for col, v, length, ev in rows:
                out.write('\t'.join([idno, w.get('volume', ''), col, w.get('author', ''), w.get('author_year', ''), v, kjv_of(v),
                                     'ngram', str(length), ev]) + '\n'); n += 1
    print(n, 'rows ->', os.path.join(OUT, 'spine-ngram.tsv'))

def cmd_notes():
    m = meta()
    os.makedirs(OUT, exist_ok=True)
    n = chap = 0
    with open(os.path.join(OUT, 'spine-notes.tsv'), 'w', encoding='utf-8') as out:
        out.write('idno\tvol\tcol\tauthor\tauthor_year\tvulg\tkjv\tstream\tlevel\tevidence\n')
        for f in sorted(glob.glob(os.path.join(INDEX, '*.json'))):
            idno = os.path.basename(f)[:-5]; w = m.get(idno, {})
            for x in json.load(open(f, encoding='utf-8')).get('scripture', []):
                k = x['refKey']; first = k.split('-')[0]
                level = 'verse' if first.count('.') == 2 else 'chapter'
                chap += level == 'chapter'
                out.write('\t'.join([idno, w.get('volume', ''), str(x.get('column', '')), w.get('author', ''), w.get('author_year', ''),
                                     k, kjv_of(first) if level == 'verse' else (to_kjv(first) or [''])[0], 'migne-notes', level,
                                     x.get('refDisplay', '').replace('\t', ' ')]) + '\n'); n += 1
    print(n, 'rows,', chap, 'chapter-level ->', os.path.join(OUT, 'spine-notes.tsv'))

def cmd_recall():
    """Of Migne's verse-level notes, how many does the n-gram stream find in the same work within
    one column? (Migne's notes are themselves uneven, so this measures recall, not precision.)"""
    colnum = lambda c: int(re.match(r'\d+', c).group()) if re.match(r'\d+', c or '') else -9
    ng = collections.defaultdict(set)
    for r in csv.DictReader(open(os.path.join(OUT, 'spine-ngram.tsv'), encoding='utf-8'), delimiter='\t'):
        ng[(r['idno'], r['vulg'])].add(colnum(r['col']))
    tot = hit = 0
    for r in csv.DictReader(open(os.path.join(OUT, 'spine-notes.tsv'), encoding='utf-8'), delimiter='\t'):
        if r['level'] != 'verse' or '-' in r['vulg']:
            continue
        tot += 1; c = colnum(r['col'])
        hit += any(abs(c - x) <= 1 for x in ng.get((r['idno'], r['vulg']), ()))
    print(f'migne verse-level notes: {tot}; found by the n-gram stream in the same work within a column: {hit} ({100 * hit / max(tot, 1):.1f}%)')

def cmd_calibrate():
    """Inline (Migne's own in-text citations) against the n-gram stream, in the works where Migne
    prints them. Recall: of inline verse citations, how many the n-gram stream finds (same work, +/-1
    column, the verse or within 2 of it). Precision: of n-gram rows in those works, how many sit
    within a column of an inline citation of that verse or its chapter, by run length."""
    colnum = lambda c: int(re.match(r'\d+', c).group()) if re.match(r'\d+', c or '') else -9
    inl = collections.defaultdict(list); dens = collections.Counter()
    for r in csv.DictReader(open(os.path.join(OUT, 'spine-inline.tsv'), encoding='utf-8'), delimiter='\t'):
        if r['exists'] == 'y':
            inl[r['idno']].append((colnum(r['col']), r['vulg'])); dens[r['idno']] += 1
    ng = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(OUT, 'spine-ngram.tsv'), encoding='utf-8'), delimiter='\t'):
        ng[r['idno']].append((colnum(r['col']), r['vulg'], int(r['run_words'])))
    # works where Migne cites inline: at least 1 inline citation per 3 n-gram rows
    works = [w for w in inl if dens[w] >= max(20, len(ng.get(w, ())) / 3)]
    print(f'works with inline citation: {len(inl)}; dense enough to calibrate against: {len(works)}')
    tot = hit = 0
    for w in works:
        by = collections.defaultdict(list)
        for c, v, _ in ng.get(w, ()):
            by[c].append(v)
        for c, ref in inl[w]:
            if ref.split('-')[0].count('.') != 2:
                continue
            tot += 1
            hit += any(_within(v, ref) or _near(v, ref) for x in (c - 1, c, c + 1) for v in by.get(x, ()))
    print(f'recall: inline verse citations found by the n-gram stream: {hit}/{tot} ({100 * hit / max(tot, 1):.1f}%)')
    buck = collections.Counter(); ok = collections.Counter()
    for w in works:
        by = collections.defaultdict(list)
        for c, ref in inl[w]:
            by[c].append(ref)
        for c, v, n in ng.get(w, ()):
            b = '6' if n == 6 else '7' if n == 7 else '8-9' if n < 10 else '10-14' if n < 15 else '15+'
            buck[b] += 1
            ok[b] += any(_within(v, ref) or _near(v, ref) for x in (c - 1, c, c + 1) for ref in by.get(x, ()))
    print('precision floor (an n-gram row Migne also cites inline), by run length:')
    for b in ('6', '7', '8-9', '10-14', '15+'):
        print(f'  {b:>5} words: {ok[b]}/{buck[b]} ({100 * ok[b] / max(buck[b], 1):.1f}%)')

def practice(n_inl, n_ng, verse_share):
    """A volume's citation practice, from its inline stream. Thresholds are first guesses, kept here."""
    if n_inl < max(20, n_ng / 10):
        return 'sparse'
    return 'chapter' if verse_share < 0.2 else 'verse' if verse_share > 0.8 else 'mixed'

def cmd_profile():
    """Per volume: inline density, verse share, the share of citations the Clementine lacks, and the
    5-gram confirmation rate; a practice class; then n-gram recall against inline per class.
    Volumes reprint different editions (Wilson 2026-11-10), so pooled calibration hides them."""
    colnum = lambda c: int(re.match(r'\d+', c).group()) if re.match(r'\d+', c or '') else -9
    v = collections.defaultdict(collections.Counter); inl = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(OUT, 'spine-inline.tsv'), encoding='utf-8'), delimiter='\t'):
        c = v[r['vol']]; c['n'] += 1; c['verse'] += r['level'] == 'verse'
        c['bad'] += r['exists'] == 'n'; c['conf'] += r['confirmed'] != 'n'
        if r['exists'] == 'y' and r['level'] == 'verse':
            inl[r['vol']].append((r['idno'], colnum(r['col']), r['vulg']))
    ng = collections.defaultdict(lambda: collections.defaultdict(list)); nng = collections.Counter()
    for r in csv.DictReader(open(os.path.join(OUT, 'spine-ngram.tsv'), encoding='utf-8'), delimiter='\t'):
        ng[r['vol']][(r['idno'], colnum(r['col']))].append(r['vulg']); nng[r['vol']] += 1
    vols = sorted(set(v) | set(nng), key=lambda x: int(x) if x.isdigit() else 9999)
    cls = collections.defaultdict(lambda: [0, 0, 0])
    with open(os.path.join(OUT, 'volume-practice.tsv'), 'w', encoding='utf-8') as o:
        o.write('vol\tinline\tngram\tinline_per_ngram\tverse_share\tnot_in_clementine\tconfirmed\tpractice\tngram_recall\n')
        for vol in vols:
            c = v[vol]; n = c['n']
            vs = c['verse'] / n if n else 0
            pr = practice(n, nng[vol], vs)
            tot = hit = 0
            for idno, col, ref in inl[vol]:
                tot += 1
                hit += any(_within(x, ref) or _near(x, ref) for k in (col - 1, col, col + 1) for x in ng[vol].get((idno, k), ()))
            cls[pr][0] += 1; cls[pr][1] += tot; cls[pr][2] += hit
            o.write('\t'.join([vol, str(n), str(nng[vol]), f'{n / max(nng[vol], 1):.2f}', f'{vs:.2f}', f'{c["bad"] / max(n, 1):.3f}',
                                f'{c["conf"] / max(n, 1):.2f}', pr, f'{hit / tot:.2f}' if tot else '']) + '\n')
    print('-> ' + os.path.join(OUT, 'volume-practice.tsv'))
    print('| practice | volumes | inline verse citations | n-gram recall |')
    print('|---|---:|---:|---:|')
    for pr in ('verse', 'mixed', 'chapter', 'sparse'):
        n, t, h = cls[pr]
        print(f'| {pr} | {n} | {t} | ' + (f'{100 * h / t:.1f}%' if t else '–') + ' |')

# ---- stream 3: fuzzy (ordered stem pairs) --------------------------------------------------
STEM, GAP, STOP, FRARE, MINPAIRS, SPAN = 5, 3, 150, 3, 3, 20
_FZ = None
def build_fuzzy():
    """Stems = first STEM letters. Pairs: stem a then stem b within GAP words in one verse, neither
    among the STOP commonest stems; kept if the pair occurs in at most FRARE verses."""
    global _FZ
    vs = vulgate()
    freq = collections.Counter(w[:STEM] for _, ws in vs for w in ws)
    stop = {w for w, _ in freq.most_common(STOP)}
    pairs = collections.defaultdict(set)
    for vi, (_, ws) in enumerate(vs):
        st = [w[:STEM] for w in ws if len(w) > 2 and w[:STEM] not in stop]
        for i in range(len(st)):
            for j in range(i + 1, min(i + 1 + GAP, len(st))):
                if st[i] != st[j]:
                    pairs[(st[i], st[j])].add(vi)
    _FZ = ({k: tuple(v) for k, v in pairs.items() if len(v) <= FRARE}, [k for k, _ in vs], stop)
    return _FZ

def scan_fuzzy(f):
    pairs, keys, stop = _FZ
    body = body_text(f)
    words, cols, cur = [], [], ''
    for k, seg in enumerate(re.split(r'\x01([^\x01]*)\x01', body)):
        if k % 2:
            cur = seg; continue
        w = [x[:STEM] for x in norm_words(seg) if len(x) > 2 and x[:STEM] not in stop]
        words += w; cols += [cur] * len(w)
    hits = collections.defaultdict(list)          # verse -> (position, pair)
    for i in range(len(words)):
        for j in range(i + 1, min(i + 1 + GAP, len(words))):
            for vi in pairs.get((words[i], words[j]), ()):
                hits[vi].append((i, (words[i], words[j])))
    rows = []
    for vi, hs in hits.items():
        hs.sort()
        k = 0
        while k < len(hs):
            m = k
            while m + 1 < len(hs) and hs[m + 1][0] - hs[k][0] <= SPAN:
                m += 1
            distinct = {p for _, p in hs[k:m + 1]}
            if len(distinct) >= MINPAIRS:
                a = hs[k][0]
                rows.append((cols[a], keys[vi], len(distinct), ' '.join(words[a:hs[m][0] + 2])))
                k = m + 1
            else:
                k += 1
    return os.path.basename(f)[:-4], rows

def cmd_fuzzy():
    m = meta()
    build_fuzzy()
    print('rare stem pairs in the Clementine:', len(_FZ[0]))
    files = sorted(glob.glob(os.path.join(TEI, '*.xml')))
    n = 0
    with open(os.path.join(OUT, 'spine-fuzzy.tsv'), 'w', encoding='utf-8') as out, ProcessPoolExecutor(6, initializer=build_fuzzy) as ex:
        out.write('idno\tvol\tcol\tauthor\tauthor_year\tvulg\tkjv\tstream\tpairs\tevidence\n')
        for idno, rows in ex.map(scan_fuzzy, files, chunksize=10):
            w = m.get(idno, {})
            for col, v, np_, ev in rows:
                out.write('\t'.join([idno, w.get('volume', ''), col, w.get('author', ''), w.get('author_year', ''), v, kjv_of(v),
                                     'fuzzy', str(np_), ev]) + '\n'); n += 1
    print(n, 'rows ->', os.path.join(OUT, 'spine-fuzzy.tsv'))

def _band(y):
    try:
        y = int(y)
    except ValueError:
        return 'undated'
    if y <= 0: return 'undated'
    for hi, lab in ((400, '<=400'), (600, '401-600'), (800, '601-800'), (1000, '801-1000'), (1100, '1001-1100'), (1200, '1101-1200')):
        if y <= hi: return lab
    return '1201+'

def cmd_bydate():
    """In verse- and mixed-practice volumes: of Migne's inline verse citations, the share found by
    ngram, by fuzzy, by either (same work, +/-1 column, the verse or within 2). And each stream's
    precision floor (rows sitting on an inline citation) by the same bands."""
    colnum = lambda c: int(re.match(r'\d+', c).group()) if re.match(r'\d+', c or '') else -9
    prac = {r['vol']: r['practice'] for r in csv.DictReader(open(os.path.join(OUT, 'volume-practice.tsv'), encoding='utf-8'), delimiter='\t')}
    ok = lambda vol: prac.get(vol) in ('verse', 'mixed')
    streams = {}
    for name in ('ngram', 'fuzzy'):
        d = collections.defaultdict(list)
        for r in csv.DictReader(open(os.path.join(OUT, f'spine-{name}.tsv'), encoding='utf-8'), delimiter='\t'):
            if ok(r['vol']):
                d[(r['idno'], colnum(r['col']))].append((r['vulg'], _band(r['author_year'])))
        streams[name] = d
    inl = collections.defaultdict(list)
    tot = collections.Counter(); hit = collections.Counter()
    for r in csv.DictReader(open(os.path.join(OUT, 'spine-inline.tsv'), encoding='utf-8'), delimiter='\t'):
        if r['exists'] != 'y' or r['level'] != 'verse' or not ok(r['vol']):
            continue
        c = colnum(r['col']); b = _band(r['author_year']); ref = r['vulg']
        inl[(r['idno'], c)].append(ref)
        tot[b] += 1
        f = {}
        for name, d in streams.items():
            f[name] = any(_within(x, ref) or _near(x, ref) for k in (c - 1, c, c + 1) for x, _ in d.get((r['idno'], k), ()))
            hit[(b, name)] += f[name]
        hit[(b, 'either')] += f['ngram'] or f['fuzzy']
    prec = collections.Counter(); ptot = collections.Counter()
    for name, d in streams.items():
        for (idno, c), xs in d.items():
            refs = [ref for k in (c - 1, c, c + 1) for ref in inl.get((idno, k), ())]
            for x, b in xs:
                ptot[(b, name)] += 1
                prec[(b, name)] += any(_within(x, ref) or _near(x, ref) for ref in refs)
    print('| author died | inline verse cites | ngram | fuzzy | either | ngram floor | fuzzy floor | fuzzy rows |')
    print('|---|---:|---:|---:|---:|---:|---:|---:|')
    for b in ('<=400', '401-600', '601-800', '801-1000', '1001-1100', '1101-1200', '1201+', 'undated'):
        t = max(tot[b], 1)
        pc = lambda n: f'{100 * prec[(b, n)] / max(ptot[(b, n)], 1):.0f}%'
        print(f"| {b} | {tot[b]} | {100 * hit[(b, 'ngram')] / t:.1f}% | {100 * hit[(b, 'fuzzy')] / t:.1f}% | {100 * hit[(b, 'either')] / t:.1f}% | {pc('ngram')} | {pc('fuzzy')} | {ptot[(b, 'fuzzy')]} |")

if __name__ == '__main__':
    {'notes': cmd_notes, 'ngram': cmd_ngram, 'inline': cmd_inline, 'recall': cmd_recall, 'calibrate': cmd_calibrate, 'profile': cmd_profile, 'fuzzy': cmd_fuzzy, 'bydate': cmd_bydate}[sys.argv[1]]()
