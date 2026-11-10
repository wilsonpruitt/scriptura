#!/usr/bin/env python3
"""PLAN G1, the census-grade gate for raw Kraken Greek (no tokens).

  python3 -I studies/sensus/scripts/g1_gate.py

For every Kraken work with a checked text beside the raw one (~/patrologia/raw/kraken/<work>/text vs
checked/), page by page: both texts normalized as the Greek census would see them (accents,
breathings and case dropped, final sigma folded, band letters and [b: X] marks removed, hyphenated
line ends rejoined), aligned word by word (difflib), and scored:
  - word accuracy: share of checked words that raw Kraken reproduces exactly (after normalization);
  - long-word accuracy: the same for words of 7+ letters (sense terms are long words);
  - sense-stem recall: for each checked occurrence of a sense stem (ιστορ-, θεωρ-, αλληγορ-,
    τροπολογ-, αναγωγ-, τυπικ-/τυπο-, πνευματικ-, μυστικ-, ηθικ-), whether the aligned raw word
    carries the same stem.
Dorotheus's checked text is the full paid plate check (the gold key); the others were checked by
the translation-flag method (kt), a lighter key.
The census question is not whether the Greek is right letter by letter (accents matter for the
edition, not the count) but whether the counted words survive.
"""
import collections, difflib, glob, os, re, unicodedata

K = os.path.expanduser('~/patrologia/raw/kraken')
STEMS = ['ιστορ', 'θεωρ', 'αλληγορ', 'τροπολογ', 'αναγωγ', 'τυπικ', 'τυπο', 'πνευματικ', 'μυστικ', 'ηθικ']

def words(path):
    t = open(path, encoding='utf-8', errors='replace').read()
    t = re.sub(r'\[b:\s*\w+\]', ' ', t)
    t = re.sub(r'(?<=[\u0370-\u03ff\u1f00-\u1fff])-?[ABCD](?=\s*$)', '', t, flags=re.M)   # glued band letters
    t = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', t)
    t = ''.join(c for c in unicodedata.normalize('NFD', t) if not unicodedata.combining(c)).lower().replace('ς', 'σ')
    return re.findall(r'[\u03b1-\u03c9]+', t)

def stem(w):
    return next((s for s in STEMS if w.startswith(s)), None)

def score(work):
    tot = collections.Counter(); sr = collections.Counter(); misses = []
    for cp in sorted(glob.glob(os.path.join(K, work, 'checked', 'p-*.txt'))):
        rp = os.path.join(K, work, 'text', os.path.basename(cp))
        if not os.path.exists(rp):
            continue
        c, r = words(cp), words(rp)
        if len(c) < 20:
            continue
        sm = difflib.SequenceMatcher(None, c, r, autojunk=False)
        aligned = {}
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal':
                for k in range(i2 - i1): aligned[i1 + k] = r[j1 + k]
            elif op == 'replace' and i2 - i1 == j2 - j1:
                for k in range(i2 - i1): aligned[i1 + k] = r[j1 + k]
        tot['pages'] += 1
        for i, w in enumerate(c):
            ok = aligned.get(i) == w
            tot['w'] += 1; tot['ok'] += ok
            if len(w) >= 7:
                tot['lw'] += 1; tot['lok'] += ok
            s = stem(w)
            if s:
                got = aligned.get(i, '')
                sr[(s, 'n')] += 1; sr[(s, 'hit')] += bool(got and got.startswith(s))
                if not (got and got.startswith(s)):
                    misses.append((os.path.basename(cp), w, got))
    return tot, sr, misses

def main():
    works = sorted(d for d in os.listdir(K) if os.path.isdir(os.path.join(K, d, 'checked')))
    print('| work | pages | words | word accuracy | 7+ letters | sense-stem occurrences | stem recall |')
    print('|---|---:|---:|---:|---:|---:|---:|')
    allsr = collections.Counter(); allmiss = []
    for w in works:
        t, sr, ms = score(w)
        if not t['w']:
            continue
        n = sum(v for (s, k), v in sr.items() if k == 'n'); h = sum(v for (s, k), v in sr.items() if k == 'hit')
        allsr.update(sr); allmiss += [(w,) + m for m in ms]
        print(f"| {w} | {t['pages']} | {t['w']} | {100 * t['ok'] / t['w']:.1f}% | {100 * t['lok'] / max(t['lw'], 1):.1f}% | {n} | "
              + (f'{100 * h / n:.1f}%' if n else '–') + ' |')
    print('\nby stem (all works):')
    for s in STEMS:
        n = allsr[(s, 'n')]
        if n:
            print(f'  {s:<10} {allsr[(s, "hit")]}/{n} ({100 * allsr[(s, "hit")] / n:.0f}%)')
    print('\nmissed stem occurrences (checked -> raw):')
    for m in allmiss[:25]:
        print('  ', *m)

if __name__ == '__main__':
    main()
