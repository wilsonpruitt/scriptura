#!/usr/bin/env python3
"""The translator's effect, tested where it can be: Origen's Homilies on Jeremiah in PG 13, Greek
with Jerome's Latin of the same homily on the same page ("Interprete S. Hieronymo", "Eodem
interprete"). No tokens.

  python3 -I studies/sensus/scripts/jeremiah_parallel.py            # Greek from Tesseract (grc)
  python3 -I studies/sensus/scripts/jeremiah_parallel.py kraken     # Greek from Kraken, when run

Jerome spans: from each page whose Latin heading names Jerome as interpreter to the page before
the next homily title (a standalone "HOMILIA N" line) or the next interpreter heading. Homilies
whose Latin is the editor's own (no interpreter line) are left out.
For every Greek sense term on a Jerome page, the Latin sense terms on the same page are listed: what
Jerome put where Origen wrote ἀναγωγή, τροπολογία, ἀλληγορία. Totals per language at the end.
"""
import collections, glob, os, re, sys, unicodedata
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESS = os.path.join(HERE, 'sources', 'editions', 'ocr', 'pg013')
KRAK = os.path.expanduser('~/patrologia/raw/kraken/origen-pg013/text')
GK = {'αναγωγ': 'anagoge', 'τροπολογ': 'tropologia', 'αλληγορ': 'allegoria', 'θεωρ': 'theoria', 'ιστορ': 'historia',
      'πνευματικ': 'spiritual', 'μυστικ': 'mystic', 'ρητ': 'rhetos (letter)', 'λεξ': 'lexis (letter)', 'σωματικ': 'bodily'}
LA = {r'anagog\w*': 'anagoge', r'tropolog\w*': 'tropologia', r'allegori\w*': 'allegoria', r'mystic\w*': 'mystic',
      r'spiritual\w* (?:intellig|intelleg|sensu)\w*|(?:intellig|intelleg)\w* spiritual\w*': 'spiritualis intelligentia',
      r'spiritualiter': 'spiritualiter', r'moraliter|moral\w* (?:intellig|sensu)\w*': 'moral', r'(?:iuxta|juxta|secundum) (?:litteram|literam)': 'secundum litteram',
      r'(?:iuxta|juxta|secundum) historiam|histori\w*': 'historia', r'ad (?:litteram|literam)': 'ad litteram', r'figur\w*': 'figura', r'typ\w*': 'typus'}

def norm_gr(t):
    return ''.join(c for c in unicodedata.normalize('NFD', t) if not unicodedata.combining(c)).lower().replace('ς', 'σ')

def is_greek_line(l):
    a = [c for c in l if c.isalpha()]
    return a and sum('Ͱ' <= c <= 'Ͽ' or 'ἀ' <= c <= '῿' for c in a) > 0.7 * len(a)

def spans():
    pages = sorted(glob.glob(os.path.join(TESS, 'p-*.txt')))
    start, out, cur = None, [], None
    for p in pages:
        n = int(os.path.basename(p)[2:6])
        if not 110 <= n <= 420:
            continue
        t = open(p, encoding='utf-8', errors='replace').read()
        jer = re.search(r'(?im)^\W*(?:I\s+)?(?:interprete s\.? hieronymo|interprete hieronymo|eodem interprete)', t)
        # a homily title line, OCR clutter allowed in front ("222 HOMILIA XV.", "14|HOMILIA XVII.",
        # "HOMILIA X VIII."), but not the running head "IN JEREMIAM HOMILIA XIV."
        title = re.search(r'(?m)^[^A-Za-z\n]{0,8}HOMILIA\s+[IVXL](?:\s?[IVXL]){0,5}\.?\s*$', t)
        if jer:
            if cur: out.append(cur)
            cur = [n, n]
        elif title and cur:
            out.append(cur); cur = None     # the title page belongs to the next homily: not counted
        elif cur:
            cur[1] = n
    if cur: out.append(cur)
    return out

def main(src):
    sp = spans()
    pages = [n for a, b in sp for n in range(a, b + 1)]
    gtot, ltot, pairs = collections.Counter(), collections.Counter(), collections.defaultdict(collections.Counter)
    gw = lw = 0; examples = []
    for n in pages:
        tp = os.path.join(TESS, f'p-{n:04d}.txt')
        if not os.path.exists(tp):
            continue
        tess = open(tp, encoding='utf-8', errors='replace').read()
        if src == 'kraken':
            kp = os.path.join(KRAK, f'p-{n:04d}.txt')
            gtext = open(kp, encoding='utf-8').read() if os.path.exists(kp) else ''
        else:
            gtext = '\n'.join(l for l in tess.split('\n') if is_greek_line(l))
        ltext = '\n'.join(l for l in tess.split('\n') if l.strip() and not is_greek_line(l))
        g = re.findall(r'[α-ω]+', norm_gr(re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', gtext)))
        lt = re.sub(r'\s+', ' ', re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', ltext)).lower()
        gw += len(g); lw += len(re.findall(r'[a-z]+', lt))
        lat_here = collections.Counter()
        for rx, name in LA.items():
            k = len(re.findall(r'\b(?:' + rx + r')\b', lt))
            if k: lat_here[name] += k; ltot[name] += k
        for i, w in enumerate(g):
            for st, name in GK.items():
                if w.startswith(st):
                    gtot[name] += 1
                    if name in ('anagoge', 'tropologia', 'allegoria', 'theoria'):
                        for ln, k in lat_here.items(): pairs[name][ln] += 1
                        if len(examples) < 14 and name in ('anagoge', 'tropologia'):
                            examples.append((n, ' '.join(g[max(0, i - 4):i + 5]), ', '.join(f'{a}×{b}' for a, b in lat_here.most_common()) or '—'))
    print(f'Jerome spans (pages): {sp}')
    print(f'{len(pages)} pages; Greek words {gw}, Latin words {lw} (source of Greek: {src})\n')
    print('Greek terms:', ', '.join(f'{k} {v}' for k, v in gtot.most_common()))
    print('Latin terms:', ', '.join(f'{k} {v}' for k, v in ltot.most_common()))
    print('\nWhere Origen writes X, the Latin terms on the same page (page-level, so a guide, not an alignment):')
    for name in ('anagoge', 'tropologia', 'allegoria', 'theoria'):
        if gtot[name]:
            print(f'  {name:<11} ({gtot[name]}): ' + ', '.join(f'{a} {b}' for a, b in pairs[name].most_common(6)))
    print('\nexamples (page | Greek | Latin sense terms on the page):')
    for e in examples:
        print('  ', *e, sep='  ')

if __name__ == '__main__':
    main('kraken' if sys.argv[1:] == ['kraken'] else 'tess')
