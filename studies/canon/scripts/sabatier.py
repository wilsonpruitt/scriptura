#!/usr/bin/env python3
"""Sabatier, Bibliorum Sacrorum Latinae Versiones Antiquae (Reims 1743-49): the Old Latin column,
cut into verses and keyed to the Clementine. No tokens.

  python3 -I studies/canon/scripts/sabatier.py 3        # vol. III (NT); 1, 2 = OT
  python3 -I studies/canon/scripts/sabatier.py check 3  # sample rows for reading
  python3 -I studies/canon/scripts/sabatier.py notes 3  # the NOTAE: Fathers' and MSS' readings, keyed by verse

Input: the Archive's djvu text (sources/oldlatin/sabatierN_djvu.txt). Each page prints three
blocks: VULGATA NOVA, VERSIO ANTIQUA, NOTAE AD VERSIONEM ANTIQUAM. We keep the VERSIO ANTIQUA
blocks only (the notes, the Fathers' readings by locus, are a later step).

1. Long s: the OCR reads it as f. A word containing f is rewritten with s where the f-form is not in
   the PL lexicon and an s-form is ('fermo' -> 'sermo', 'ipfum' -> 'ipsum').
2. The block is cut at verse numbers ('2.', '3;').
3. Each chunk is keyed to a Clementine verse by content (idf-weighted shared stems, restricted to the
   volume's books). A weak content match takes its chapter from the previous anchor and its verse
   from its own number ('sequence'). Unkeyable chunks are dropped and counted.
Output: sources/oldlatin/sabatier-vN.tsv (key, method, score, text). Not versioned (sources/).
"""
import collections, csv, glob, importlib.util, math, os, random, re, sys, unicodedata
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('sp', os.path.join(HERE, 'scripts', 'spine.py'))
sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)
SRC = os.path.join(HERE, 'sources', 'oldlatin')
NT = {'Matt', 'Mark', 'Luke', 'John', 'Acts', 'Rom', '1Cor', '2Cor', 'Gal', 'Eph', 'Phil', 'Col', '1Thess', '2Thess',
      '1Tim', '2Tim', 'Titus', 'Phlm', 'Heb', 'Jas', '1Pet', '2Pet', '1John', '2John', '3John', 'Jude', 'Rev'}

OL = re.compile(r'^\W{0,4}VERSIO\s+[AÀÁ]NT[IÍ]QU[AÆ]', re.I)
NOTES = re.compile(r'VERSIONEM\s+[AÀÁ]NT[IÍ]QU', re.I)
VULG = re.compile(r'VULGATA', re.I)

def deacc(s):
    s = s.replace('æ', 'ae').replace('Æ', 'Ae').replace('œ', 'oe').replace('Œ', 'Oe').replace('&', ' et ')
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def lexicon(n=1500):
    lex = collections.Counter()
    fs = sorted(glob.glob(os.path.join(sp.TEI, '*.xml'))); random.seed(0)
    for f in random.sample(fs, min(n, len(fs))):
        t = re.sub(r'<[^>]+>', ' ', open(f, encoding='utf-8', errors='replace').read())
        lex.update(sp.norm_words(deacc(t)))
    for _, ws in sp.vulgate():
        lex.update(ws)
    return {w for w, c in lex.items() if c >= 2}

def longs(w, lex):
    if 'f' not in w or w in lex:
        return w
    idx = [i for i, c in enumerate(w) if c == 'f']
    if len(idx) > 4:
        return w.replace('f', 's')
    best = None
    for mask in range(1, 1 << len(idx)):          # fewest substitutions first is not needed: any lexicon hit
        c = list(w)
        for b, i in enumerate(idx):
            if mask >> b & 1:
                c[i] = 's'
        c = ''.join(c)
        if c in lex:
            best = c; break
    return best or w

def blocks(text):
    out, cur, on = [], [], False
    for line in text.split('\n'):
        if OL.search(line) and not NOTES.search(line):
            if on and cur:
                out.append('\n'.join(cur))
            cur, on = [], True; continue
        if NOTES.search(line) or VULG.search(line):
            if on and cur:
                out.append('\n'.join(cur))
            cur, on = [], False; continue
        if on:
            cur.append(line)
    if on and cur:
        out.append('\n'.join(cur))
    return out

VNUM = re.compile(r'(?:^|(?<=[\s.;:,]))((?=[\dlIr]*\d)[1-9lIr][\doOlI]{0,2})\s?[.;:,»](?=\s)')
def vnum(t):
    return int(t.translate(str.maketrans('lIroO', '11100')))
def chunks(block):
    t = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', block)
    t = re.sub(r'\s+', ' ', t)
    parts = VNUM.split(t)
    out = [(None, parts[0])] if parts[0].strip() else []
    for k in range(1, len(parts) - 1, 2):
        out.append((vnum(parts[k]), parts[k + 1]))
    return out

def main(vol):
    lex = lexicon()
    vs = sp.vulgate()
    books = NT if vol == 3 else None
    verses = [(k, ws) for k, ws in vs if (books is None or k.split('.')[0] in books) and (books is not None or k.split('.')[0] not in NT)]
    freq = collections.Counter(w[:sp.STEM] for _, ws in vs for w in ws)
    stop = {w for w, _ in freq.most_common(sp.STOP)}
    inv = collections.defaultdict(set); df = collections.Counter()
    for vi, (_, ws) in enumerate(verses):
        st = {w[:sp.STEM] for w in ws if len(w) > 2} - stop
        for s in st:
            inv[s].add(vi); df[s] += 1
    N = len(verses)
    idf = {s: math.log(N / df[s]) for s in df}
    text = open(os.path.join(SRC, f'sabatier{vol}_djvu.txt'), encoding='utf-8', errors='replace').read()
    bl = blocks(text)
    rows, stat, prev = [], collections.Counter(), None
    for bi, b in enumerate(bl):
        for num, chunk in chunks(b):
            words = [longs(w, lex) for w in sp.norm_words(deacc(chunk))]
            if len(words) < 3:
                stat['short'] += 1; continue
            st = {w[:sp.STEM] for w in words if len(w) > 2} - stop
            sc = collections.Counter()
            for s in st:
                for vi in inv.get(s, ()):
                    sc[vi] += idf[s]
            key, method, score = None, '', 0.0
            if sc:
                (vi, s1), *rest = sc.most_common(2)
                tot = sum(idf.get(s, 0) for s in st) or 1
                score = s1 / tot
                cand = verses[vi][0]
                b_, c_, v_ = cand.split('.')
                agrees = num is None or int(v_) == num or (prev and cand.rsplit('.', 1)[0] == prev.rsplit('.', 1)[0])
                if (score >= 0.45 and agrees) or (score >= 0.25 and num is not None and int(v_) == num):
                    key, method = cand, 'content'
            if key is None and prev and num is not None:
                pb, pc, pv = prev.split('.')
                if num > int(pv) and num - int(pv) <= 6:
                    key, method = f'{pb}.{pc}.{num}', 'sequence'
            if key is None:
                stat['unkeyed'] += 1; continue
            stat[method] += 1; prev = key
            rows.append((key, method, f'{score:.2f}', ' '.join(words)))
    out = os.path.join(SRC, f'sabatier-v{vol}.tsv')
    with open(out, 'w', encoding='utf-8') as o:
        o.write('key\tmethod\tscore\ttext\n')
        for r in rows:
            o.write('\t'.join(r) + '\n')
    keys = {r[0] for r in rows}
    allk = {k for k, _ in verses}
    print(f'vol {vol}: {len(bl)} Versio antiqua blocks; chunks keyed: content {stat["content"]}, sequence {stat["sequence"]}; '
          f'unkeyed {stat["unkeyed"]}, too short {stat["short"]}')
    print(f'distinct verses keyed: {len(keys)} of {len(allk)} in the volume\'s books ({100 * len(keys) / len(allk):.0f}%) -> {out}')
    byb = collections.Counter(k.split('.')[0] for k in keys); allb = collections.Counter(k.split('.')[0] for k in allk)
    print(' '.join(f'{b}:{100 * byb[b] // allb[b]}%' for b in sorted(allb, key=lambda b: -allb[b])))

NMARK = re.compile(r'(?:^|(?<=\s))[^\s\w]?(?:Yý|Vv|[VvyYWẏỳýÿŸ¥Ý])\s?\.?\s?((?=[\dlIo]*\d)[1-9lI][\doOlI]{0,2})\s?\.(?=\s)')
def notes(vol):
    """Walk the volume once: OL chunks set the current book.chapter (via sabatier-vN.tsv order is
    lost, so re-key here with the same content anchor); each NOTAE block is cut at verse markers
    and keyed to book.chapter of the last keyed OL chunk + the marker's verse."""
    lex = lexicon()
    vs = sp.vulgate()
    valid = {k for k, _ in vs}
    keyed = {}
    for r in csv.DictReader(open(os.path.join(SRC, f'sabatier-v{vol}.tsv'), encoding='utf-8'), delimiter='\t'):
        keyed.setdefault(r['text'], r['key'])
    text = open(os.path.join(SRC, f'sabatier{vol}_djvu.txt'), encoding='utf-8', errors='replace').read()
    mode, buf, prev, rows, stat = None, [], None, [], collections.Counter()
    def flush():
        nonlocal prev
        if not buf:
            return
        b = '\n'.join(buf)
        if mode == 'ol':
            for num, chunk in chunks(b):
                words = ' '.join(longs(w, lex) for w in sp.norm_words(deacc(chunk)))
                if words in keyed:
                    prev = keyed[words]
        elif mode == 'notes' and prev:
            t = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', b); t = re.sub(r'\s+', ' ', t)
            parts = NMARK.split(t)
            bc = prev.rsplit('.', 1)[0]
            for k in range(1, len(parts) - 1, 2):
                key = f'{bc}.{vnum(parts[k])}'
                if key not in valid:
                    stat['bad-key'] += 1; continue
                words = [longs(w, lex) for w in sp.norm_words(deacc(parts[k + 1]))]
                if len(words) >= 4:
                    rows.append((key, ' '.join(words))); stat['notes'] += 1
    for line in text.split('\n'):
        if OL.search(line) and not NOTES.search(line):
            flush(); buf, mode = [], 'ol'; continue
        if NOTES.search(line):
            flush(); buf, mode = [], 'notes'; continue
        if VULG.search(line):
            flush(); buf, mode = [], 'vulg'; continue
        buf.append(line)
    flush()
    out = os.path.join(SRC, f'sabatier-notes-v{vol}.tsv')
    with open(out, 'w', encoding='utf-8') as o:
        o.write('key\ttext\n')
        for k, t in rows:
            o.write(f'{k}\t{t}\n')
    print(f'notes keyed: {stat["notes"]} ({len({k for k, _ in rows})} distinct verses); markers giving no valid verse: {stat["bad-key"]} -> {out}')

def check(vol):
    vs = dict(sp.vulgate())
    R = list(csv.DictReader(open(os.path.join(SRC, f'sabatier-v{vol}.tsv'), encoding='utf-8'), delimiter='\t'))
    random.seed(1)
    for r in random.sample(R, 12):
        print(r['key'], r['method'], r['score']); print('   OL :', r['text'][:150]); print('   VUL:', ' '.join(vs.get(r['key'], []))[:150])

if __name__ == '__main__':
    if sys.argv[1] == 'check':
        check(int(sys.argv[2]))
    elif sys.argv[1] == 'notes':
        notes(int(sys.argv[2]))
    else:
        main(int(sys.argv[1]))
