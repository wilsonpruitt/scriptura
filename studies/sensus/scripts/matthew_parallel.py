#!/usr/bin/env python3
"""The translator's effect, three layers on one page: Origen's Commentary on Matthew in PG 13 prints the
Greek (tomes 10-17), Migne's humanist Latin facing it, and below both, under a "VETUS INTERPRETATIO"
heading, the ancient Latin translation (6th c.?) of the same passage. No tokens.

  python3 -I studies/sensus/scripts/matthew_parallel.py

Greek from Kraken (~/patrologia/raw/kraken/origen-pg013/text); Latin from Tesseract
(sources/editions/ocr/pg013). On each page with the heading, Latin above it = humanist, below it =
vetus (Greek letters stripped from mixed lines, since Tesseract runs the two columns together).
Page-level counts: a guide, not an alignment. The vetus block runs a little behind or ahead of the Greek
on the same page, so totals over the whole span are the measure, page pairs only the illustration.
"""
import collections, glob, os, re, unicodedata
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESS = os.path.join(HERE, 'sources', 'editions', 'ocr', 'pg013')
KRAK = os.path.expanduser('~/patrologia/raw/kraken/origen-pg013/text')
HEAD = re.compile(r'(?m)^.{0,8}[VYX]ETUS INTERPRETATIO')
GK = {'αναγωγ': 'anagoge', 'τροπολογ': 'tropologia', 'αλληγορ': 'allegoria', 'θεωρ': 'theoria', 'ιστορ': 'historia',
      'πνευματικ': 'spiritualis', 'μυστικ': 'mysticus', 'ηθικ': 'ethicus', 'λεξ': 'lexis', 'ρητ': 'rhetos'}
LA = {'anagoge': r'anagog\w*', 'tropologia': r'tropolog\w*', 'allegoria': r'allegor\w*', 'moralis': r'moral\w*',
      'spiritualis': r'spiritual\w*', 'mysticus': r'mystic\w*|mystice', 'historia': r'histori\w*', 'figura': r'figur\w*',
      'typus': r'typ(?:us|i|o|um|ice|icus|ica|ic\w*)', 'littera': r'litter\w*|liter(?:a|am|ae|is)\b|literal\w*',
      'intellectus': r'intellect\w*|intelligenti\w*', 'sensus': r'sens(?:us|um|u|ibus)', 'theoria': r'theori\w*|contemplat\w*'}

def ngr(t):
    return ''.join(c for c in unicodedata.normalize('NFD', t) if not unicodedata.combining(c)).lower().replace('ς', 'σ')

def greek(c):
    return 'Ͱ' <= c <= 'Ͽ' or 'ἀ' <= c <= '῿'

def latin_count(text):
    t = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text).lower().replace('j', 'i').replace('æ', 'ae')
    t = re.sub(r'\s+', ' ', t)
    return collections.Counter({k: len(re.findall(r'\b(?:' + rx + r')', t)) for k, rx in LA.items()}), len(re.findall(r'[a-z]+', t))

def split(t):
    m = HEAD.search(t)
    above, below = t[:m.start()], t[m.end():]
    hum = '\n'.join(l for l in above.split('\n') if sum(map(greek, l)) < 0.3 * max(sum(c.isalpha() for c in l), 1))
    vet = ''.join(c for c in below if not greek(c))
    return hum, vet

def main():
    pages = []
    for p in sorted(glob.glob(os.path.join(TESS, 'p-*.txt'))):
        t = open(p, encoding='utf-8', errors='replace').read()
        n = int(os.path.basename(p)[2:6])
        if HEAD.search(t) and os.path.exists(os.path.join(KRAK, f'p-{n:04d}.txt')):
            pages.append((n, t))
    G, H, V = collections.Counter(), collections.Counter(), collections.Counter()
    gw = hw = vw = 0; rows = []
    for n, t in pages:
        g = re.findall(r'[α-ω]+', ngr(re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', open(os.path.join(KRAK, f'p-{n:04d}.txt'), encoding='utf-8').read())))
        gc = collections.Counter(name for w in g for st, name in GK.items() if w.startswith(st))
        hum, vet = split(t)
        hc, hn = latin_count(hum); vc, vn = latin_count(vet)
        G.update(gc); H.update(hc); V.update(vc); gw += len(g); hw += hn; vw += vn
        if any(gc[k] for k in ('anagoge', 'tropologia', 'allegoria')):
            rows.append((n, gc, hc, vc))
    print(f'{len(pages)} pages (PG 13, p. {pages[0][0]}-{pages[-1][0]}); Greek {gw} words, humanist Latin {hw}, vetus Latin {vw}\n')
    print('Greek (Kraken):', ', '.join(f'{k} {v}' for k, v in G.most_common() if v))
    per = lambda c, w, k: f'{c[k]:>4} ({100000 * c[k] / w:5.1f})'
    print(f'\n{"Latin term":<12} {"humanist":>13} {"vetus":>13}   (count, per 100K words)')
    for k in LA:
        print(f'{k:<12} {per(H, hw, k)} {per(V, vw, k)}')
    print('\npages where the Greek names anagoge / tropologia / allegoria: Greek | humanist | vetus')
    show = lambda c, ks: ' '.join(f'{k}{c[k]}' for k in ks if c[k]) or '-'
    sk = ('anagoge', 'tropologia', 'allegoria', 'moralis', 'spiritualis', 'mysticus', 'intellectus', 'figura', 'typus')
    for n, gc, hc, vc in rows:
        print(f'  p{n}  {show(gc, ("anagoge", "tropologia", "allegoria")):<28} | {show(hc, sk):<40} | {show(vc, sk)}')

if __name__ == '__main__':
    main()
