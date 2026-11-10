#!/usr/bin/env python3
"""Clean the Tesseract Latin of PG 12-14 (Origen in Latin) for the census. No tokens.

  python3 -I studies/sensus/scripts/pg_latin_clean.py            # all three volumes
  python3 -I studies/sensus/scripts/pg_latin_clean.py 013

Per page (sources/editions/ocr/pgNNN/p-NNNN.txt):
  1. columns: Migne's running head prints the page's two column numbers ("991 ORIGENIS . 992");
     read them, so every line carries a PG column.
  2. keep lines that are >80% Latin script (drops the Greek column on bilingual pages);
  3. rejoin words hyphenated across a line end;
  4. rules for the systematic Tesseract errors, applied only to a non-word whose repair IS a word in
     the PL lexicon: ae read as z / x (czesus, przdixissent, Judzeos), c/e and n/u confusions.
  5. count what is still not a word (the residue PatroLLM is for).
Writes sources/editions/ocr/pgNNN-latin.txt ("\x01COL\x01" markers + text) and prints rates.
The lexicon (every word form occurring 2+ times in the PL TEI) is cached in sources/pl-lexicon.txt.
"""
import collections, glob, os, re, sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ED = os.path.join(HERE, 'sources', 'editions')
TEI = os.path.expanduser('~/patrologia/sources/pl/tei')
LEXF = os.path.join(HERE, 'sources', 'pl-lexicon.txt')

def norm(w):
    return w.lower().replace('j', 'i').replace('v', 'u').replace('æ', 'ae').replace('œ', 'oe')

def _count(f):
    t = re.sub(r'<[^>]+>', ' ', open(f, encoding='utf-8', errors='replace').read())
    return collections.Counter(re.findall(r'[a-z]+', norm(t)))

def lexicon():
    if os.path.exists(LEXF):
        return set(open(LEXF, encoding='utf-8').read().split())
    c = collections.Counter()
    with ProcessPoolExecutor(6) as ex:
        for x in ex.map(_count, sorted(glob.glob(os.path.join(TEI, '*.xml'))), chunksize=20):
            c.update(x)
    lex = sorted(w for w, n in c.items() if n >= 2)
    open(LEXF, 'w', encoding='utf-8').write('\n'.join(lex))
    return set(lex)

RULES = (('z', 'ae'), ('x', 'ae'), ('z', 'x'), ('c', 'e'), ('e', 'c'), ('u', 'n'), ('n', 'u'), ('ii', 'u'), ('in', 'm'), ('rn', 'm'), ('l', 'i'))
def fix(w, lex):
    n = norm(w)
    if n in lex or len(n) < 3:
        return w, n in lex, False
    for a, b in RULES:
        for m in re.finditer(re.escape(a), n):
            c = n[:m.start()] + b + n[m.end():]
            if c in lex:
                return c, True, True
    return w, False, False

HEAD = re.compile(r'^\s*(\d{1,4})\b')
def page(path, lex, last=None):
    """The running head's first number is the page's left column (odd). Taken only if it fits the
    sequence (within 6 of last+2), so a stray numeral in the first lines is not read as a column."""
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    col = None
    for l in [x for x in lines if x.strip()][:4]:
        m = HEAD.match(l)
        if m:
            n = int(m.group(1))
            if n % 2 == 1 and (last is None or abs(n - (last + 2)) <= 6) and n > 0:
                col = n; break
    keep = []
    for l in lines:
        letters = [c for c in l if c.isalpha()]
        if len(letters) >= 3 and sum(c.isascii() for c in letters) > 0.8 * len(letters):
            keep.append(l)
    t = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', '\n'.join(keep))
    out, st = [], collections.Counter()
    for tok in re.findall(r"[A-Za-zæœÆŒ]+|[^A-Za-zæœÆŒ]+", t):
        if tok[0].isalpha() and len(tok) >= 3:
            w, ok, fixed = fix(tok, lex)
            st['words'] += 1; st['ok'] += ok; st['fixed'] += fixed
            out.append(w)
        else:
            out.append(tok)
    return col, ''.join(out), st

def head_number(path):
    for l in [x for x in open(path, encoding='utf-8', errors='replace').read().split('\n') if x.strip()][:4]:
        m = HEAD.match(l)
        if m and int(m.group(1)) % 2 == 1:
            return int(m.group(1))
    return None

def columns(pages, win=15):
    """col(i) = 2i + offset, the offset taken as the mode of (head - 2i) over pages i-win..i+win.
    Stray numerals in a running head cannot outvote the sequence; plates shift the offset locally."""
    off = [None if (n := head_number(p)) is None else n - 2 * i for i, p in enumerate(pages)]
    out = []
    for i in range(len(pages)):
        c = collections.Counter(o for o in off[max(0, i - win):i + win + 1] if o is not None)
        out.append(2 * i + c.most_common(1)[0][0] if c and c.most_common(1)[0][1] >= 3 else None)
    return out, sum(o is not None for o in off)

def run(vol):
    lex = lexicon()
    pages = sorted(glob.glob(os.path.join(ED, 'ocr', f'pg{vol}', 'p-*.txt')))
    cols, heads = columns(pages)
    tot = collections.Counter()
    with open(os.path.join(ED, 'ocr', f'pg{vol}-latin.txt'), 'w', encoding='utf-8') as o:
        for p, col in zip(pages, cols):
            _, text, st = page(p, lex)
            tot.update(st)
            raw = open(p, encoding='utf-8', errors='replace').read()
            letters = [c for c in raw if c.isalpha()]
            greek = sum('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff' for c in letters) / max(len(letters), 1)
            kind = 'bi' if greek >= 0.15 else 'la'      # bi = Greek + Migne's facing Latin; la = Latin only
            tot['pages_' + kind] += 1
            o.write(f'\x01{col if col and col > 0 else ""}|{kind}\x01\n{text}\n')
    w = max(tot['words'], 1)
    print(f'PG {vol}: {len(pages)} pages; a head numeral on {heads}; column assigned on {sum(1 for c in cols if c and c > 0)}; '
          f'Latin-only pages {tot["pages_la"]}, bilingual {tot["pages_bi"]}; {tot["words"]} Latin words; in lexicon {100 * tot["ok"] / w:.1f}% (repaired by rule {100 * tot["fixed"] / w:.1f}%); residue {100 * (w - tot["ok"]) / w:.1f}%')

if __name__ == '__main__':
    for v in sys.argv[1:] or ['012', '013', '014']:
        run(v)
